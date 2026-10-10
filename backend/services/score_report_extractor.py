"""Pull score tables and graphs out of a Word (.docx) or PDF score report.

Items come back in document order so they can be dropped into a report in the
same order the psychologist sees them in the score report:

    {"kind": "table", "caption": str, "rows": [[str, ...], ...]}
    {"kind": "image", "caption": str, "content_type": "image/png"|"image/jpeg",
     "data_b64": str, "width": int, "height": int}

Anything that can't be imported is reported in ``warnings`` rather than silently
dropped, so the user knows to add it by hand.
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import etree, html as lxml_html

MAX_IMAGE_WIDTH_PX = 2000
MIN_IMAGE_PX = (80, 50)  # smaller than this is a logo/icon, not a graph
MIN_IMAGE_INCHES = (0.5, 0.3)
CAPTION_MAX_CHARS = 120

DOCX_TYPES = ("wordprocessingml", "msword")


class ScoreReportError(Exception):
    """The file can't be read as a score report (message is user-facing)."""


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def extract_score_report(path: Path, content_type: Optional[str] = None) -> Dict[str, list]:
    suffix = path.suffix.lower()
    ctype = (content_type or "").lower()

    if suffix == ".doc":
        raise ScoreReportError("Legacy .doc files aren't supported. Please save the score report as .docx or PDF.")
    if suffix == ".docx" or any(t in ctype for t in DOCX_TYPES) and suffix != ".pdf":
        items, warnings = _extract_docx(path)
    elif suffix == ".pdf" or "pdf" in ctype:
        items, warnings = _extract_pdf(path)
    else:
        raise ScoreReportError("Please upload a Word (.docx) or PDF score report.")

    if not items and not warnings:
        warnings.append("No tables or graphs were found in this file.")
    for index, item in enumerate(items):
        item["id"] = f"item-{index}"
    return {"items": items, "warnings": warnings}


def html_to_tables(html: str) -> List[dict]:
    """Every <table> in pasted/uploaded HTML (not just the first)."""
    if not (html or "").strip():
        return []
    try:
        root = lxml_html.document_fromstring(html)
    except (etree.ParserError, ValueError):
        return []

    tables: List[dict] = []
    for table in root.iter("table"):
        if any(ancestor.tag == "table" for ancestor in table.iterancestors()):
            continue  # nested table: its text is already part of the outer cell
        rows: List[List[str]] = []
        for tr in table.iter("tr"):
            if tr.getparent() is not None and next(
                (a for a in tr.iterancestors() if a.tag == "table"), None
            ) is not table:
                continue
            cells: List[str] = []
            for cell in tr:
                if cell.tag not in ("td", "th"):
                    continue
                cells.append(_clean_text(cell.text_content()))
                span = _to_int(cell.get("colspan"), 1)
                cells.extend([""] * (span - 1))
            rows.append(cells)
        rows = _finish_rows(rows)
        if rows:
            tables.append({"kind": "table", "caption": "", "rows": rows})
    return tables


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _clean_text(value: str) -> str:
    value = (value or "").replace("\xa0", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r" ?\n ?", "\n", value)
    return value.strip()


def _to_int(value, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _finish_rows(rows: List[List[str]]) -> List[List[str]]:
    """Drop blank rows, pad to a rectangle, and reject non-data 'layout' tables."""
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        return []
    width = max(len(r) for r in rows)
    if width < 2:
        return []
    return [r + [""] * (width - len(r)) for r in rows]


def _normalize_image(data: bytes) -> Optional[Tuple[bytes, str, int, int]]:
    """Return (bytes, content_type, width, height) as PNG/JPEG, or None if the
    image can't be decoded (e.g. EMF/WMF on a platform without GDI)."""
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow ships with pdfplumber
        return None
    try:
        image = Image.open(io.BytesIO(data))
        fmt = (image.format or "").upper()
        if fmt in ("WMF", "EMF"):
            try:
                image.load(dpi=200)
            except TypeError:
                image.load()
        else:
            image.load()
    except Exception:
        return None

    width, height = image.size
    if width > MAX_IMAGE_WIDTH_PX:
        height = int(height * MAX_IMAGE_WIDTH_PX / width)
        width = MAX_IMAGE_WIDTH_PX
        image = image.resize((width, height))

    out = io.BytesIO()
    if fmt == "JPEG" and image.mode == "RGB":
        image.save(out, format="JPEG", quality=90)
        return out.getvalue(), "image/jpeg", width, height
    if image.mode not in ("RGB", "RGBA", "L"):
        image = image.convert("RGBA" if "A" in image.mode or "transparency" in image.info else "RGB")
    image.save(out, format="PNG")
    return out.getvalue(), "image/png", width, height


def _image_item(normalized: Tuple[bytes, str, int, int], caption: str) -> dict:
    data, content_type, width, height = normalized
    return {
        "kind": "image",
        "caption": caption,
        "content_type": content_type,
        "data_b64": base64.b64encode(data).decode("ascii"),
        "width": width,
        "height": height,
    }


# --------------------------------------------------------------------------- #
# Word
# --------------------------------------------------------------------------- #
def _extract_docx(path: Path) -> Tuple[List[dict], List[str]]:
    from docx import Document
    from docx.oxml.ns import qn

    try:
        document = Document(str(path))
    except Exception as exc:
        raise ScoreReportError("That file couldn't be opened as a Word document.") from exc

    items: List[dict] = []
    seen_images: set = set()
    skipped_unreadable = 0
    chart_count = 0
    caption = ""

    def paragraph_text(p) -> str:
        parts = []
        for node in p.iter():
            if node.tag == qn("w:t") and node.text:
                parts.append(node.text)
            elif node.tag in (qn("w:br"), qn("w:cr")):
                parts.append("\n")
            elif node.tag == qn("w:tab"):
                parts.append(" ")
        return _clean_text("".join(parts))

    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            for drawing in child.iter(qn("w:drawing")):
                if drawing.findall(".//" + qn("c:chart")):
                    chart_count += 1
                for blip in drawing.iter(qn("a:blip")):
                    rid = blip.get(qn("r:embed"))
                    rel = document.part.rels.get(rid) if rid else None
                    if rel is None or rel.is_external:
                        continue
                    extent = next(drawing.iter(qn("wp:extent")), None)
                    if extent is not None:
                        inches = (int(extent.get("cx", 0)) / 914400, int(extent.get("cy", 0)) / 914400)
                        if inches[0] < MIN_IMAGE_INCHES[0] or inches[1] < MIN_IMAGE_INCHES[1]:
                            continue
                    normalized = _normalize_image(rel.target_part.blob)
                    if normalized is None:
                        skipped_unreadable += 1
                        continue
                    digest = hashlib.sha1(normalized[0]).hexdigest()
                    if digest in seen_images or normalized[2] < MIN_IMAGE_PX[0] or normalized[3] < MIN_IMAGE_PX[1]:
                        continue
                    seen_images.add(digest)
                    items.append(_image_item(normalized, caption))
                    caption = ""
            text = paragraph_text(child)
            if text:
                caption = text if len(text) <= CAPTION_MAX_CHARS else ""
        elif child.tag == qn("w:tbl"):
            rows = _finish_rows(_docx_table_rows(child, qn, paragraph_text))
            if rows:
                items.append({"kind": "table", "caption": caption, "rows": rows})
                caption = ""

    warnings: List[str] = []
    if chart_count:
        warnings.append(
            f"{chart_count} native Word chart(s) can't be imported. In the score report, "
            "right-click the chart, copy it as a picture, and upload that instead."
        )
    if skipped_unreadable:
        warnings.append(
            f"{skipped_unreadable} picture(s) couldn't be read (an unsupported image format) and were skipped."
        )
    return items, warnings


def _docx_table_rows(tbl, qn, paragraph_text) -> List[List[str]]:
    rows: List[List[str]] = []
    for tr in tbl.findall(qn("w:tr")):
        cells: List[str] = []
        for tc in tr.findall(qn("w:tc")):
            text = "\n".join(t for t in (paragraph_text(p) for p in tc.findall(qn("w:p"))) if t)
            cells.append(text)
            grid_span = tc.find(qn("w:tcPr") + "/" + qn("w:gridSpan"))
            if grid_span is not None:
                cells.extend([""] * (_to_int(grid_span.get(qn("w:val")), 1) - 1))
        rows.append(cells)
    return rows


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def _extract_pdf(path: Path) -> Tuple[List[dict], List[str]]:
    import pdfplumber

    items: List[dict] = []
    seen_images: set = set()
    skipped_unreadable = 0

    try:
        pdf = pdfplumber.open(str(path))
    except Exception as exc:
        raise ScoreReportError("That file couldn't be opened as a PDF.") from exc

    with pdf:
        for page in pdf.pages:
            page_items: List[Tuple[float, dict]] = []

            try:
                found_tables = page.find_tables()
            except Exception:
                found_tables = []
            for table in found_tables:
                try:
                    rows = _finish_rows([[_clean_text(c or "") for c in row] for row in table.extract()])
                except Exception:
                    continue
                if rows:
                    page_items.append(
                        (table.bbox[1], {"kind": "table", "caption": _pdf_caption(page, table.bbox), "rows": rows})
                    )

            for image in page.images:
                x0, top = max(image["x0"], 0), max(image["top"], 0)
                x1, bottom = min(image["x1"], page.width), min(image["bottom"], page.height)
                if (x1 - x0) < 40 or (bottom - top) < 25:
                    continue
                try:
                    rendered = page.crop((x0, top, x1, bottom)).to_image(resolution=150).original
                    buffer = io.BytesIO()
                    rendered.save(buffer, format="PNG")
                    normalized = _normalize_image(buffer.getvalue())
                except Exception:
                    normalized = None
                if normalized is None:
                    skipped_unreadable += 1
                    continue
                digest = hashlib.sha1(normalized[0]).hexdigest()
                if digest in seen_images or normalized[2] < MIN_IMAGE_PX[0] or normalized[3] < MIN_IMAGE_PX[1]:
                    continue
                seen_images.add(digest)
                page_items.append((top, _image_item(normalized, _pdf_caption(page, (x0, top, x1, bottom)))))

            page_items.sort(key=lambda pair: pair[0])
            items.extend(item for _, item in page_items)

    warnings: List[str] = []
    if skipped_unreadable:
        warnings.append(f"{skipped_unreadable} picture(s) in the PDF couldn't be read and were skipped.")
    if not any(i["kind"] == "table" for i in items):
        warnings.append(
            "No tables were detected in this PDF. A Word version of the score report usually "
            "imports more reliably."
        )
    warnings.append(
        "Graphs drawn as vector shapes (rather than embedded pictures) can't be detected in a PDF. "
        "If one is missing, upload the Word version or add it in Word afterwards."
    )
    return items, warnings


def _pdf_caption(page, bbox) -> str:
    top = bbox[1]
    try:
        strip = page.crop((0, max(0, top - 30), page.width, max(top, 1)))
        lines = [ln.strip() for ln in (strip.extract_text() or "").splitlines() if ln.strip()]
    except Exception:
        return ""
    if not lines:
        return ""
    last = lines[-1]
    return last if len(last) <= CAPTION_MAX_CHARS else ""
