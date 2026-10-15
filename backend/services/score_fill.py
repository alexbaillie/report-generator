"""Fill the blank score cells of a Word template's tables from a score report's tables.

The clinic templates ship with curated score tables: the row labels are already
written ("Similarities (SI)", "Verbal Comprehension (VCI)", ...) and only the score
cells are blank. A score report (Pearson's Q-global etc.) holds the same scores in
its own layout. Filling the template's tables keeps the template's look, which is
what the psychologists use.

Accuracy matters more than coverage here: a wrong number in a clinical table is
worse than a blank cell. So matching is strict and everything that can't be
matched is left blank and *reported*:

* a template row only takes values from a score-report row with the same code
  (SI, VCI, FSIQ, ...) or the exact same name -- never a fuzzy match;
* a column is only filled from the same kind of score (a "Scaled Score" column from
  a scaled score, a "Standard Score" column from a standard/composite/index score);
* only empty cells are filled, and existing text is never overwritten;
* "-" in the score report means not administered: the cell stays blank;
* if two score-report rows claim the same code with different values, neither is used.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

DASHES = {"-", "–", "—", "n/a", "na", "--"}

# Header text (whitespace/punctuation stripped, lowercase) -> the kind of score.
_EXACT_FIELDS = {
    "standardscore": "standard", "standardscores": "standard",
    "compositescore": "standard", "indexscore": "standard",
    "scaledscore": "scaled", "scaledscores": "scaled",
    "percentilerank": "percentile", "percentile": "percentile",
    "percentileranks": "percentile", "percentiles": "percentile",
    "confidenceinterval": "ci", "95ci": "ci",
    "qualitativedescription": "description", "qualitativedescriptor": "description",
    "descriptor": "description", "classification": "description",
    "totalrawscore": "raw", "rawscore": "raw", "rawscores": "raw",
    "ageequivalent": "age", "sem": "sem",
}

# A row counts as administered when it has an actual score (a raw score alone doesn't).
SCORE_FIELDS = {"scaled", "standard", "percentile"}

# The same subtest is abbreviated differently in different documents.
CODE_ALIASES = {"LNS": "LN"}
NAME_ALIASES = {"letter number seq": "letter number sequencing"}


# --------------------------------------------------------------------------- #
# reading a score report's tables
# --------------------------------------------------------------------------- #
@dataclass
class SourceRecord:
    name: str            # normalised name, e.g. "verbal comprehension"
    code: str            # e.g. "VCI" ("" if none)
    display: str
    fields: Dict[str, str]
    administered: bool


def header_field(text: str) -> Optional[str]:
    compact = re.sub(r"[^a-z0-9%]", "", (text or "").lower())
    if compact in _EXACT_FIELDS:
        return _EXACT_FIELDS[compact]
    if compact.startswith("95%confidence") or compact.startswith("90%confidence"):
        return "ci"
    if compact.startswith("sumof"):
        return "sum"
    return None


def _norm_name(text: str) -> str:
    name = re.sub(r"[^a-z0-9]+", " ", (text or "").lower().replace("&", " and ")).strip()
    return NAME_ALIASES.get(name, name)


def _canon_code(code: str) -> str:
    code = (code or "").strip().upper()
    return CODE_ALIASES.get(code, code)


def split_label(text: str):
    """"Similarities (SI)" -> ("similarities", "SI"); "(Information)" -> ("information", "");
    "Full Scale (FSIQ)*" -> ("full scale", "FSIQ")."""
    t = re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip().rstrip("*").strip()
    code = ""
    match = re.search(r"\(([A-Za-z]{2,6})\)\s*\**\s*$", t)
    if match:
        code = _canon_code(match.group(1))
        t = t[: match.start()].strip()
    if t.startswith("(") and t.endswith(")"):
        t = t[1:-1]
    return _norm_name(t), code


def _is_dash(value: str) -> bool:
    return value.strip().lower() in DASHES


def parse_source_tables(tables: Iterable[Mapping]) -> List[SourceRecord]:
    """Score records from every table that looks like a score summary (a header row
    with percentile rank plus a scaled/standard/composite score)."""
    records: List[SourceRecord] = []
    for table in tables:
        rows = table.get("rows") or []
        header_index, col_fields = None, {}
        for i, row in enumerate(rows):
            found: Dict[int, str] = {}
            for c, cell in enumerate(row):
                kind = header_field(cell)
                if kind and kind not in found.values():
                    found[c] = kind
            kinds = set(found.values())
            if "percentile" in kinds and kinds & {"scaled", "standard"}:
                header_index, col_fields = i, found
                break
        if header_index is None:
            continue

        header = rows[header_index]
        first_field_col = min(col_fields)
        label_cols = [c for c in range(first_field_col)]
        if not label_cols:
            continue
        skip_headers = {"domain", "scale", "group", ""}
        name_col = next(
            (c for c in label_cols if re.sub(r"[^a-z]", "", header[c].lower()) not in skip_headers),
            label_cols[0],
        )
        code_col = next((c for c in label_cols if c > name_col), None)

        for row in rows[header_index + 1:]:
            raw_name = row[name_col].strip() if name_col < len(row) else ""
            raw_code = row[code_col].strip() if code_col is not None and code_col < len(row) else ""
            if not raw_name and not raw_code:
                continue
            name, code = split_label(raw_name)
            if not code and re.fullmatch(r"[A-Za-z]{2,6}", raw_code):
                code = _canon_code(raw_code)
            values = {
                f: row[c].strip()
                for c, f in col_fields.items()
                if c < len(row) and row[c].strip()
            }
            if not values:
                continue  # a group heading such as "Ancillary"
            records.append(
                SourceRecord(
                    name=name,
                    code=code,
                    display=raw_name,
                    fields=values,
                    administered=any(not _is_dash(v) for f, v in values.items() if f in SCORE_FIELDS),
                )
            )
    return records


# --------------------------------------------------------------------------- #
# filling the template's tables
# --------------------------------------------------------------------------- #
@dataclass
class FillStats:
    filled: int = 0
    tables_seen: int = 0
    tables_filled: int = 0
    not_administered: List[str] = field(default_factory=list)   # in the score report, but "-"
    not_in_report: List[str] = field(default_factory=list)      # template rows with no matching score-report row
    ambiguous: List[str] = field(default_factory=list)
    unfilled_columns: List[str] = field(default_factory=list)   # e.g. template wants "scaled", report only has "standard"
    not_in_template: List[str] = field(default_factory=list)    # administered in the report, no row in the template's tables


def _cell_text(tc) -> str:
    parts: List[str] = []
    for p in tc.findall(qn("w:p")):
        pieces = []
        for node in p.iter():
            if node.tag == qn("w:t") and node.text:
                pieces.append(node.text)
            elif node.tag in (qn("w:br"), qn("w:cr"), qn("w:tab")):
                pieces.append(" ")
        parts.append("".join(pieces))
    return re.sub(r"\s+", " ", " ".join(parts).replace("\xa0", " ")).strip()


def _set_cell_text(tc, text: str) -> None:
    """Write into a blank cell keeping the template's own formatting: reuse the
    cell's empty run if it has one, otherwise start one from the paragraph mark's
    run properties (where the template stores the cell's font and size)."""
    paragraph = tc.find(qn("w:p"))
    if paragraph is None:
        paragraph = OxmlElement("w:p")
        tc.append(paragraph)
    run = paragraph.find(qn("w:r"))
    if run is None:
        run = OxmlElement("w:r")
        p_pr = paragraph.find(qn("w:pPr"))
        mark = p_pr.find(qn("w:rPr")) if p_pr is not None else None
        if mark is not None:
            props = copy.deepcopy(mark)
            for tag in ("w:ins", "w:del", "w:moveFrom", "w:moveTo", "w:rPrChange"):
                for stray in props.findall(qn(tag)):
                    props.remove(stray)
            run.append(props)
        paragraph.append(run)
    node = run.find(qn("w:t"))
    if node is None:
        node = OxmlElement("w:t")
        run.append(node)
    node.text = text
    node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def _is_complex(rows) -> bool:
    for tr in rows:
        for tc in tr.findall(qn("w:tc")):
            tc_pr = tc.find(qn("w:tcPr"))
            if tc_pr is not None and (tc_pr.find(qn("w:gridSpan")) is not None or tc_pr.find(qn("w:vMerge")) is not None):
                return True
    return False


def fill_template_tables(shell_tables: Sequence, records: Sequence[SourceRecord]) -> FillStats:
    stats = FillStats()
    by_code: Dict[str, List[SourceRecord]] = {}
    by_name: Dict[str, List[SourceRecord]] = {}
    for record in records:
        if record.code:
            by_code.setdefault(record.code, []).append(record)
        if record.name:
            by_name.setdefault(record.name, []).append(record)

    def lookup(name: str, code: str):
        for candidates in ((by_code.get(code) if code else None), by_name.get(name)):
            if not candidates:
                continue
            distinct = {tuple(sorted(r.fields.items())) for r in candidates}
            if len(distinct) > 1:
                return "ambiguous"
            return candidates[0]
        return None

    used = set()
    last_header: Dict[int, str] = {}
    last_width = 0
    for table in shell_tables:
        stats.tables_seen += 1
        rows = table.findall(qn("w:tr"))
        if not rows or _is_complex(rows):
            continue

        first_cells = rows[0].findall(qn("w:tc"))
        width = len(first_cells)
        header_fields = {c: header_field(_cell_text(tc)) for c, tc in enumerate(first_cells)}
        header_fields = {c: f for c, f in header_fields.items() if f}
        if header_fields:
            data_rows = rows[1:]
            last_header, last_width = header_fields, width
        elif last_header and width == last_width:
            # A headerless table (e.g. the supplementary subtests) shares the columns
            # of the table before it.
            header_fields, data_rows = last_header, rows
        else:
            continue

        filled_here = 0
        for tr in data_rows:
            cells = tr.findall(qn("w:tc"))
            if len(cells) != width:
                continue
            label = _cell_text(cells[0])
            if not label:
                continue
            name, code = split_label(label)
            found = lookup(name, code)
            if found is None:
                stats.not_in_report.append(label)
                continue
            if found == "ambiguous":
                stats.ambiguous.append(label)
                continue
            used.add(id(found))
            if not found.administered:
                stats.not_administered.append(label)
                continue
            for col, kind in header_fields.items():
                if _cell_text(cells[col]):
                    continue  # never overwrite what the template already says
                value = found.fields.get(kind)
                if value is None or _is_dash(value):
                    if kind in ("scaled", "standard") and not value:
                        other = "standard" if kind == "scaled" else "scaled"
                        if found.fields.get(other) and not _is_dash(found.fields[other]):
                            stats.unfilled_columns.append(f"{label}: the report gives a {other} score, the table wants {kind}")
                    continue
                _set_cell_text(cells[col], value)
                stats.filled += 1
                filled_here += 1
        if filled_here:
            stats.tables_filled += 1
    # Whatever the template has no row for (a score the clinic doesn't tabulate) is
    # reported rather than silently dropped. Alias records (same code/name) count as used.
    used_keys = {(r.code, r.name) for r in records if id(r) in used}
    for record in records:
        if record.administered and id(record) not in used and (record.code, record.name) not in used_keys:
            if record.display not in stats.not_in_template:
                stats.not_in_template.append(record.display)
    return stats


def summarize(stats: FillStats, limit: int = 12) -> dict:
    """A compact, JSON-friendly description for the UI."""
    def cap(items):
        shown = items[:limit]
        return shown + ([f"... and {len(items) - limit} more"] if len(items) > limit else [])

    return {
        "filled": stats.filled,
        "tables_filled": stats.tables_filled,
        "not_administered": cap(stats.not_administered),
        "not_in_report": cap(stats.not_in_report),
        "ambiguous": cap(stats.ambiguous),
        "unfilled_columns": cap(stats.unfilled_columns),
        "not_in_template": cap(stats.not_in_template),
    }
