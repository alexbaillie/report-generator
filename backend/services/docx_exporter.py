"""Template-preserving Word export for completed reports."""

from __future__ import annotations

from copy import deepcopy
from html import unescape
from io import BytesIO
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


ASD_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "templates"
    / "asd_school_age_boy_template.docx"
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}


class DocxExportError(RuntimeError):
    """Raised when a report cannot be exported with a configured DOCX template."""


ASD_SECTION_TARGETS: Sequence[Tuple[str, Sequence[str]]] = (
    ("reason for referral", ("Reason for Referral",)),
    ("summary & conclusions", ("Summary & Conclusions",)),
    ("asd diagnostic criteria", ("ASD:",)),
    ("diagnostic considerations", ("All reports:",)),
    ("highlighted recommendations", ("Highlighted Recommendations",)),
    ("goals for the present assessment", ("Goals for the Present Assessment",)),
    ("presenting concerns", ("Presenting Concerns",)),
    ("family history", ("Family History",)),
    ("developmental & medical history", ("Developmental & Medical History",)),
    ("educational history", ("Educational History",)),
    ("previous assessments & interventions", ("Previous Assessments & Interventions",)),
    ("tests administered", ("Tests Administered",)),
    ("general behavioural observations", ("General Behavioural Observations",)),
    ("autism characteristics", ("Autism Characteristics",)),
    ("rating scales & adaptive behaviour", ("Adaptive Behaviour",)),
    ("additional recommendations", ("Additional Recommendations",)),
    ("appendices", ("APPENDIX 1: Interpretation of Test Results",)),
)


FRONT_TABLE_LABELS: Mapping[str, Sequence[str]] = {
    "name": ("client full name", "preferred name", "name"),
    "date of birth": ("date of birth",),
    "dates of evaluation": ("date(s) of evaluation", "dates of evaluation"),
    "date of report": ("date of report",),
    "chronological age": ("chronological age", "age at assessment"),
    "examiner": ("examiner", "assessing psychologist"),
    "copies to": ("copies to",),
}


def supports_asd_template(title: str) -> bool:
    normalized = _normalize(title)
    return "asd" in normalized or "autism" in normalized


def export_filename(title: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("._")
    return f"{safe or 'report'}.docx"


def parse_markdown_sections(content: str) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None

    for raw_line in (content or "").replace("\r\n", "\n").split("\n"):
        match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", raw_line)
        if match:
            current = _normalize(match.group(1))
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(raw_line)

    if not sections and content.strip():
        sections["report"] = [content.strip()]

    return {
        name: "\n".join(lines).strip()
        for name, lines in sections.items()
        if "\n".join(lines).strip()
    }


def create_report_docx(
    *,
    title: str,
    patient_name: str,
    report_type: str,
    content: str,
) -> BytesIO:
    del report_type  # The configured template controls the document type.
    if not supports_asd_template(title):
        raise DocxExportError("A Word template is not configured for this report type.")
    if not ASD_TEMPLATE_PATH.is_file():
        raise DocxExportError("The ASD Word template is missing from the application.")

    with ZipFile(ASD_TEMPLATE_PATH, "r") as source:
        document_xml = source.read("word/document.xml")

    root = etree.fromstring(document_xml)
    sections = parse_markdown_sections(content)
    metadata = _extract_labeled_values(sections.get("report metadata (front page)", ""))

    _fill_front_page(root, title=title, patient_name=patient_name, metadata=metadata)
    _fill_generated_sections(root, sections)

    patched_xml = etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        standalone=True,
    )
    return _write_patched_package(patched_xml)


def _write_patched_package(document_xml: bytes) -> BytesIO:
    output = BytesIO()
    with ZipFile(ASD_TEMPLATE_PATH, "r") as source, ZipFile(
        output, "w", compression=ZIP_DEFLATED
    ) as destination:
        for info in source.infolist():
            payload = document_xml if info.filename == "word/document.xml" else source.read(info.filename)
            destination.writestr(info, payload)
    output.seek(0)
    return output


def _fill_front_page(
    root,
    *,
    title: str,
    patient_name: str,
    metadata: Mapping[str, str],
) -> None:
    paragraphs = root.xpath("/w:document/w:body/w:p", namespaces=NS)
    report_title = metadata.get("report title") or title
    title_paragraph = _find_paragraph(paragraphs, ("Clinical Diagnostic Assessment Report",))
    if title_paragraph is not None:
        _set_element_text(title_paragraph, report_title)

    confidentiality = metadata.get("confidentiality statement")
    if confidentiality:
        for paragraph in paragraphs:
            if _normalize(_element_text(paragraph)).startswith("this is a confidential report"):
                _set_element_text(paragraph, confidentiality)
                break

    tables = root.xpath("/w:document/w:body/w:tbl", namespaces=NS)
    if not tables:
        return

    effective_metadata = dict(metadata)
    if patient_name and _normalize(patient_name) not in {"", "patient name"}:
        effective_metadata.setdefault("client full name", patient_name)

    for cell in tables[0].xpath(".//w:tc", namespaces=NS):
        original = _element_text(cell).strip()
        if ":" not in original:
            continue
        source_label = _normalize(original.split(":", 1)[0])
        aliases = FRONT_TABLE_LABELS.get(source_label)
        if not aliases:
            continue
        value = _first_value(effective_metadata, aliases)
        if not value:
            continue
        label_text = original.split(":", 1)[0].strip()
        _set_cell_text(cell, f"{label_text}: {value}")


def _fill_generated_sections(root, sections: Mapping[str, str]) -> None:
    body = root.find(f"{{{W_NS}}}body")
    if body is None:
        raise DocxExportError("The ASD Word template has no document body.")

    paragraphs = body.xpath("./w:p", namespaces=NS)
    located: List[Tuple[int, str, object]] = []
    children = list(body)

    for section_name, aliases in ASD_SECTION_TARGETS:
        paragraph = _find_paragraph(paragraphs, aliases)
        if paragraph is not None:
            located.append((children.index(paragraph), section_name, paragraph))

    located.sort(key=lambda item: item[0])
    for position, (_, section_name, heading) in enumerate(located):
        generated = sections.get(section_name)
        if not generated:
            continue

        current_children = list(body)
        start_index = current_children.index(heading)
        if position + 1 < len(located):
            end_index = current_children.index(located[position + 1][2])
        else:
            end_index = len(current_children)

        interval = current_children[start_index + 1 : end_index]
        style_source = next(
            (
                element
                for element in interval
                if element.tag == f"{{{W_NS}}}p" and _element_text(element).strip()
            ),
            heading,
        )
        for element in interval:
            if element.tag == f"{{{W_NS}}}p":
                body.remove(element)

        anchor = heading
        for block in _content_blocks(generated):
            new_paragraph = _paragraph_element(style_source, block)
            anchor.addnext(new_paragraph)
            anchor = new_paragraph


def _extract_labeled_values(text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in (text or "").splitlines():
        match = re.match(r"^\s*([^:#]{2,80}?):\s*(.+?)\s*$", line)
        if match and match.group(2).strip():
            values[_normalize(match.group(1))] = match.group(2).strip()
    return values


def _first_value(values: Mapping[str, str], aliases: Iterable[str]) -> Optional[str]:
    for alias in aliases:
        value = values.get(_normalize(alias))
        if value:
            return value
    return None


def _find_paragraph(paragraphs: Iterable, aliases: Iterable[str]):
    expected = {_normalize(alias) for alias in aliases}
    for paragraph in paragraphs:
        if _normalize(_element_text(paragraph)) in expected:
            return paragraph
    return None


def _element_text(element) -> str:
    return "".join(element.xpath(".//w:t/text()", namespaces=NS))


def _set_element_text(element, text: str) -> None:
    paragraph_properties = element.find(f"{{{W_NS}}}pPr")
    run_properties = element.find(f".//{{{W_NS}}}rPr")
    for child in list(element):
        if child is not paragraph_properties:
            element.remove(child)

    run = etree.Element(f"{{{W_NS}}}r")
    if run_properties is not None:
        run.append(deepcopy(run_properties))
    text_element = etree.SubElement(run, f"{{{W_NS}}}t")
    if text.startswith(" ") or text.endswith(" "):
        text_element.set(f"{{{XML_NS}}}space", "preserve")
    text_element.text = text
    element.append(run)


def _set_cell_text(cell, text: str) -> None:
    paragraphs = cell.xpath("./w:p", namespaces=NS)
    if paragraphs:
        _set_element_text(paragraphs[0], text)
        for paragraph in paragraphs[1:]:
            cell.remove(paragraph)
        return

    paragraph = etree.SubElement(cell, f"{{{W_NS}}}p")
    _set_element_text(paragraph, text)


def _paragraph_element(style_source, text: str):
    paragraph = etree.Element(f"{{{W_NS}}}p")
    paragraph_properties = style_source.find(f"{{{W_NS}}}pPr")
    if paragraph_properties is not None:
        paragraph.append(deepcopy(paragraph_properties))

    run = etree.SubElement(paragraph, f"{{{W_NS}}}r")
    run_properties = style_source.find(f".//{{{W_NS}}}rPr")
    if run_properties is not None:
        run.append(deepcopy(run_properties))
    text_element = etree.SubElement(run, f"{{{W_NS}}}t")
    if text.startswith(" ") or text.endswith(" "):
        text_element.set(f"{{{XML_NS}}}space", "preserve")
    text_element.text = text
    return paragraph


def _content_blocks(text: str) -> List[str]:
    cleaned = unescape(text or "")
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</(?:p|div|tr|li)>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    blocks = [
        re.sub(r"\s+", " ", block).strip()
        for block in re.split(r"\n\s*\n|\n", cleaned)
    ]
    return [block for block in blocks if block]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().casefold())
