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
* "-" in the score report means not administered: the row's first score cell says
  "Not assessed" and the rest stay blank;
* if two score-report rows claim the same code with different values, neither is used.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

NOT_ASSESSED = "Not assessed"
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
    "relativestrengthweakness": "strength",
}

# A row counts as administered when it has an actual score (a raw score alone doesn't).
SCORE_FIELDS = {"scaled", "standard", "percentile"}

# The same subtest is abbreviated differently in different documents.
CODE_ALIASES = {"LNS": "LN"}
NAME_ALIASES = {
    "letter number seq": "letter number sequencing",
    # ABAS-3: the clinic's table says "Global", the publisher's report "General"; the
    # school form calls the same skill area "School Living" where the parent form says "Home Living".
    "global adaptive composite": "general adaptive composite",
    "school living": "home living",
}


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
    table: int = 0       # which of the score report's tables it came from
    sig: tuple = ()      # that table's column-heading signature (see _signature)
    token: str = ""      # who completed it, when the table's caption says ("parent", "teacher")


def _signature_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def respondent_token(text: str) -> str:
    """"ABAS-3 Score Summary Table: Teacher" -> "teacher"; "" if the text names nobody."""
    found = re.search(r"\b(parent|teacher|school|caregiver|guardian|self)\b", (text or "").lower())
    if not found:
        return ""
    return {"school": "teacher", "caregiver": "parent", "guardian": "parent"}.get(found.group(1), found.group(1))


def header_field(text: str) -> Optional[str]:
    compact = re.sub(r"[^a-z0-9%]", "", (text or "").lower())
    if compact in _EXACT_FIELDS:
        return _EXACT_FIELDS[compact]
    if compact.startswith("95%confidence") or compact.startswith("90%confidence"):
        return "ci"
    if compact.startswith("sumof"):
        return "sum"
    if compact.startswith("relativestrength"):
        return "strength"          # "Relative Strength/ Weakness (S/W)"
    if compact.startswith("ageequivalent"):
        return "age"               # "Age Equivalent (yr, mo)"
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
    t = re.sub(r"\s+", " ", (text or "").replace(" ", " ")).strip().rstrip("*").strip()
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


def _header_columns(row) -> Dict[int, str]:
    found: Dict[int, str] = {}
    for c, cell in enumerate(row):
        kind = header_field(cell)
        if kind and kind not in found.values():
            found[c] = kind
    return found


def parse_source_tables(tables: Iterable[Mapping]) -> List[SourceRecord]:
    """Score records from every table that looks like a score summary (a header row
    with percentile rank plus a scaled/standard/composite score). A table may hold
    several sections, each under its own header row (ABAS-3's composites, then its skill
    areas with a scaled score and no percentile): every row is read with the header
    above it."""
    records: List[SourceRecord] = []
    for table_index, table in enumerate(tables):
        rows = table.get("rows") or []
        headers: Dict[int, Dict[int, str]] = {}
        for i, row in enumerate(rows):
            found = _header_columns(row)
            kinds = set(found.values())
            if not headers:
                if "percentile" in kinds and kinds & {"scaled", "standard"}:
                    headers[i] = found
            elif len(kinds) >= 2 and kinds & {"scaled", "standard"}:
                headers[i] = found
        if not headers:
            continue

        first_header = min(headers)
        signature = tuple(_signature_text(rows[i][0]) for i in sorted(headers))
        token = respondent_token(table.get("caption") or "")
        col_fields: Dict[int, str] = {}
        name_col, code_col = 0, None
        for i in range(first_header, len(rows)):
            row = rows[i]
            if i in headers:
                col_fields = headers[i]
                label_cols = list(range(min(col_fields)))
                if not label_cols:
                    col_fields = {}
                    continue
                skip_headers = {"domain", "scale", "group", ""}
                name_col = next(
                    (c for c in label_cols if re.sub(r"[^a-z]", "", row[c].lower()) not in skip_headers),
                    label_cols[0],
                )
                code_col = next((c for c in label_cols if c > name_col), None)
                continue
            if not col_fields:
                continue
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
                    table=table_index,
                    sig=signature,
                    token=token,
                )
            )
    return records


# --------------------------------------------------------------------------- #
# filling the template's tables
# --------------------------------------------------------------------------- #
@dataclass
class FillStats:
    filled: int = 0
    marked_not_assessed: int = 0
    tables_seen: int = 0
    tables_filled: int = 0
    not_administered: List[str] = field(default_factory=list)   # in the score report, but "-"
    not_in_report: List[str] = field(default_factory=list)      # template rows with no matching score-report row
    ambiguous: List[str] = field(default_factory=list)
    unfilled_columns: List[str] = field(default_factory=list)   # e.g. template wants "scaled", report only has "standard"
    not_in_template: List[str] = field(default_factory=list)    # administered in the report, no row in the template's tables


def cell_text(tc) -> str:
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


def _setcell_text(tc, text: str) -> None:
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


@dataclass
class _Cell:
    tc: object
    start: int    # first grid column it covers
    span: int     # how many grid columns it covers (a merged header cell is wider than 1)


def _grid_cells(tr) -> List[_Cell]:
    """A row's cells with the grid column each starts at, so a table whose header cells
    are merged across several columns (ABAS-3's "Standard Score" over two columns) is
    read by where its cells sit rather than by how many there are."""
    position = 0
    row_pr = tr.find(qn("w:trPr"))
    if row_pr is not None:
        before = row_pr.find(qn("w:gridBefore"))
        if before is not None:
            position = int(before.get(qn("w:val")) or 0)
    cells: List[_Cell] = []
    for tc in tr.findall(qn("w:tc")):
        tc_pr = tc.find(qn("w:tcPr"))
        grid_span = tc_pr.find(qn("w:gridSpan")) if tc_pr is not None else None
        span = max(1, int(grid_span.get(qn("w:val")) or 1)) if grid_span is not None else 1
        cells.append(_Cell(tc, position, span))
        position += span
    return cells


def _has_vertical_merge(rows) -> bool:
    for tr in rows:
        for tc in tr.findall(qn("w:tc")):
            tc_pr = tc.find(qn("w:tcPr"))
            if tc_pr is not None and tc_pr.find(qn("w:vMerge")) is not None:
                return True
    return False


def _row_header(cells: Sequence[_Cell], minimum: int) -> Dict[int, tuple]:
    """{grid column: (kind of score, span)} if enough cells of the row are column headings."""
    fields = {}
    for cell in cells:
        kind = header_field(cell_text(cell.tc))
        if kind:
            fields[cell.start] = (kind, cell.span)
    return fields if len(fields) >= minimum else {}


def _is_shaded(tc) -> bool:
    tc_pr = tc.find(qn("w:tcPr"))
    shading = tc_pr.find(qn("w:shd")) if tc_pr is not None else None
    fill = (shading.get(qn("w:fill")) or "").lower() if shading is not None else ""
    return bool(fill) and fill not in ("auto", "ffffff")


def _plan_tables(shell_tables: Sequence) -> List[dict]:
    """Read each template table once: its rows with the column headings that apply to
    them. A table can hold several sections under their own heading rows (the WISC-V
    index rows, then a "Subtest | Scaled Score" heading, then the subtests), so the
    headings are tracked row by row. A table with no heading of its own shares the
    columns of the one before it when it has the same width (the supplementary subtests)."""
    plans: List[dict] = []
    last_header: Dict[int, tuple] = {}
    last_width = 0
    for table in shell_tables:
        rows = table.findall(qn("w:tr"))
        if not rows or _has_vertical_merge(rows):
            plans.append({"table": table, "rows": [], "sig": None})
            continue
        grid = [_grid_cells(tr) for tr in rows]
        width = sum(c.span for c in grid[0])
        current = _row_header(grid[0], 1)
        current_width = width
        signature: Optional[list] = None
        if current:
            signature = [_signature_text(cell_text(grid[0][0].tc))]
            last_header, last_width = current, width
        elif last_header and width == last_width:
            current = last_header
        else:
            plans.append({"table": table, "rows": [], "sig": None})
            continue
        planned = []
        for n, cells in enumerate(grid):
            if n == 0 and signature is not None:
                continue  # the heading row itself
            heading = _row_header(cells, 2)
            if heading:
                current_width = sum(c.span for c in cells)
                current, last_header, last_width = heading, heading, current_width
                if signature is not None and cells and cells[0].start == 0:
                    signature.append(_signature_text(cell_text(cells[0].tc)))
                continue
            planned.append((cells, current, current_width, sum(c.span for c in cells)))
        plans.append({
            "table": table, "rows": planned, "sig": tuple(signature) if signature else None,
            "headings": _group_headings(planned),
        })
    return plans


def _group_headings(planned) -> set:
    """Grey, empty rows that head a group of rows: a row that is shaded and blank, and whose
    name comes back on a later row of the same section (ABAS-3: the "Social" group, then the
    skill area "Social" under it). The later row is the one that takes the scores."""
    headings = set()
    for n, (cells, header, header_width, row_width) in enumerate(planned):
        if not cells or cells[0].start != 0 or len(cells) < 2:
            continue
        if not all(_is_shaded(c.tc) and not cell_text(c.tc) for c in cells[1:]):
            continue
        name = split_label(cell_text(cells[0].tc))[0]
        for later_cells, later_header, _, _ in planned[n + 1:]:
            if later_header is not header:
                break  # the next section
            if later_cells and split_label(cell_text(later_cells[0].tc))[0] == name:
                headings.add(id(cells[0].tc))
                break
    return headings


def _pair_tables(plans: List[dict], labels: Sequence[str], records: Sequence[SourceRecord]) -> None:
    """When a template holds the same table twice (ABAS-3 for the parent, then for the
    teacher) each copy takes its own table from the score report: by who completed it
    when both say so, otherwise in order. Sets ``plan["allowed"]`` to the report tables a
    copy may use (None: any)."""
    source: Dict[int, SourceRecord] = {}
    for record in records:
        source.setdefault(record.table, record)
    by_sig: Dict[tuple, List[int]] = {}
    for index, plan in enumerate(plans):
        plan["allowed"] = None
        plan["token"] = respondent_token(labels[index]) if index < len(labels) else ""
        if plan["sig"] and plan["rows"]:
            by_sig.setdefault(plan["sig"], []).append(index)
    for signature, members in by_sig.items():
        if len(members) < 2:
            continue
        offered = sorted(t for t, record in source.items() if record.sig == signature)
        if not offered:
            continue
        taken: Dict[int, int] = {}
        for index in members:  # who completed it, when both sides say
            wanted = plans[index]["token"]
            match = next((t for t in offered if wanted and source[t].token == wanted and t not in taken.values()), None)
            if match is not None:
                taken[index] = match
        rest = [t for t in offered if t not in taken.values()]
        for index in members:
            if index not in taken and rest:
                taken[index] = rest.pop(0)
        for index in members:
            plans[index]["allowed"] = {taken[index]} if index in taken else set()


def fill_template_tables(
    shell_tables: Sequence, records: Sequence[SourceRecord], labels: Sequence[str] = (),
) -> FillStats:
    """``labels`` holds the text above each table (its caption), used only to tell a
    table's twin apart ("ABAS-3 Score Summary Table: Teacher")."""
    stats = FillStats()
    by_code: Dict[str, List[SourceRecord]] = {}
    by_name: Dict[str, List[SourceRecord]] = {}
    for record in records:
        if record.code:
            by_code.setdefault(record.code, []).append(record)
        if record.name:
            by_name.setdefault(record.name, []).append(record)

    def lookup(name: str, code: str, primary: Optional[str], allowed):
        for pool in ((by_code.get(code) if code else None), by_name.get(name)):
            candidates = [r for r in (pool or []) if allowed is None or r.table in allowed]
            if not candidates:
                continue
            # ABAS-3 has a "Social" composite (standard score) and a "Social" skill area
            # (scaled score): a row takes the one that has its kind of score.
            preferred = [r for r in candidates if primary and primary in r.fields] or candidates
            distinct = {tuple(sorted(r.fields.items())) for r in preferred}
            if len(distinct) > 1:
                return "ambiguous"
            return preferred[0]
        return None

    plans = _plan_tables(shell_tables)
    _pair_tables(plans, labels, records)

    used = set()
    for index, plan in enumerate(plans):
        stats.tables_seen += 1
        if not plan["rows"]:
            continue
        allowed = plan["allowed"]
        if allowed is not None and not allowed:
            caption = (labels[index] if index < len(labels) else "") or "A table"
            stats.not_in_report.append(f"{caption}: no table for it in the score report")
            continue

        filled_here = 0
        for cells, header_fields, header_width, row_width in plan["rows"]:
            if not cells or cells[0].start != 0 or row_width != header_width:
                continue  # a row that doesn't have the heading's columns (a title row, a spacer)
            label = cell_text(cells[0].tc)
            if not label:
                continue
            by_start = {c.start: c for c in cells}
            targets = {
                start: (by_start[start], kind)
                for start, (kind, span) in header_fields.items()
                if start in by_start and by_start[start].span == span
            }
            if not targets:
                continue
            kinds = {kind for _, kind in targets.values()}
            primary = "scaled" if "scaled" in kinds else ("standard" if "standard" in kinds else None)
            name, code = split_label(label)
            if id(cells[0].tc) in plan["headings"]:
                continue  # a group heading ("Social" above the skill area "Social"), not a score row
            found = lookup(name, code, primary, allowed)
            if found is None:
                stats.not_in_report.append(label)
                continue
            if found == "ambiguous":
                stats.ambiguous.append(label)
                continue
            if primary and primary not in found.fields:
                # The report has the row, but not the score this section is built on (it
                # gives a standard score where the table wants a scaled one): a lone
                # percentile beside a blank score would mislead, and a group heading row
                # ("Conceptual" above its skill areas) must stay empty.
                other = "standard" if primary == "scaled" else "scaled"
                banded = all(_is_shaded(c.tc) and not cell_text(c.tc) for c in cells[1:])
                if found.fields.get(other) and not _is_dash(found.fields[other]) and not banded:
                    stats.unfilled_columns.append(f"{label}: the report gives a {other} score, the table wants {primary}")
                continue
            used.add(id(found))
            if not found.administered:
                # The score report has the row but marks it "-": say so in the first
                # blank score cell so the table never looks like a forgotten blank.
                stats.not_administered.append(label)
                for start in sorted(targets):
                    cell, _ = targets[start]
                    if not cell_text(cell.tc):
                        _setcell_text(cell.tc, NOT_ASSESSED)
                        stats.marked_not_assessed += 1
                        break
                continue
            for start in sorted(targets):
                cell, kind = targets[start]
                if cell_text(cell.tc):
                    continue  # never overwrite what the template already says
                value = found.fields.get(kind)
                if value is None or _is_dash(value):
                    continue
                _setcell_text(cell.tc, value)
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
        "marked_not_assessed": stats.marked_not_assessed,
        "tables_filled": stats.tables_filled,
        "not_administered": cap(stats.not_administered),
        "not_in_report": cap(stats.not_in_report),
        "ambiguous": cap(stats.ambiguous),
        "unfilled_columns": cap(stats.unfilled_columns),
        "not_in_template": cap(stats.not_in_template),
    }
