"""Which table layout a clinician's score tables use, and the blank tables for it.

The clinic has more than one table layout for the same test:

* WISC-V: one combined table ("Index" rows, then "Subtest" rows) in the Sunny Hill
  templates, or an index table followed by one small table per index ("VCI Subtests",
  "VSI Subtests", ...) in the older tables and the Psycho-Educational templates.
* ABAS-3: parent and school scores side by side in one table ("Option 1", the Sunny Hill
  template), or a separate parent table and teacher table, each with composites and skill
  areas ("Option 2").

A clinician who pastes tables in one layout wants the report to use it. So the export
looks at which layout the pasted tables are in; if the template's own tables are in
another layout, the template's blank tables are swapped for the blank tables of the
pasted layout (``donor_elements``) and those are filled. Tables that come straight from
a publisher's score report belong to none of these layouts, and the template's own tables
are filled as they are.

The blank tables live in ``templates/score_layouts`` (``wisc5_by_index.docx`` and
``abas3_option2.docx``, taken from the clinic's own tables, scores cleared); the combined
WISC-V table is read from the Sunny Hill template itself, because its interpretation text
is written for a boy or a girl.
"""
from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import List, Optional, Sequence

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from services.score_fill import _header_columns, _signature_text

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
LAYOUT_DIR = TEMPLATE_DIR / "score_layouts"
SUNNY_HILL = {"boy": "sunnyhill_cdbc_boy_template.docx", "girl": "sunnyhill_cdbc_girl_template.docx"}

P, TBL = qn("w:p"), qn("w:tbl")
LABELS = {
    "wisc5_by_index": "the WISC-V tables by index",
    "wisc5_combined": "the combined WISC-V table",
    "abas3_option2": "separate ABAS-3 parent and teacher tables",
}
_INDEX_SUBTESTS = re.compile(r"^(vci|vsi|fri|wmi|psi|pri)subtests?$")


def table_signature(rows: Sequence[Sequence[str]]) -> tuple:
    """The first-column text of each of a table's column-heading rows, e.g.
    ("composite", "skillarea") for ABAS-3 option 2, ("index", "subtest") for the combined WISC-V table."""
    return tuple(_signature_text(row[0]) for row in rows if row and len(_header_columns(row)) >= 2)


def element_rows(table) -> List[List[str]]:
    return [
        ["".join(t.text or "" for t in tc.iter(qn("w:t"))) for tc in tr.findall(qn("w:tc"))]
        for tr in table.findall(qn("w:tr"))
    ]


def _layout_from(token: str, signatures: Sequence[tuple]) -> Optional[str]:
    if token == "wisc5":
        by_index = any(_INDEX_SUBTESTS.match(part) for sig in signatures for part in sig)
        combined = any("index" in sig and "subtest" in sig for sig in signatures)
        if by_index != combined:
            return "wisc5_by_index" if by_index else "wisc5_combined"
    elif token == "abas3":
        if any(sig == ("composite", "skillarea") for sig in signatures):
            return "abas3_option2"
        return "abas3_other"
    return None


def wanted_layout(token: str, table_items: Sequence[dict]) -> Optional[str]:
    """The layout the pasted tables are in, if they are in one of the clinic's layouts."""
    layout = _layout_from(token, [table_signature(item.get("rows") or []) for item in table_items])
    return None if layout == "abas3_other" else layout


def layout_of(token: str, tables: Sequence) -> Optional[str]:
    """The layout the template's own tables are in (None if it isn't one of the known ones)."""
    return _layout_from(token, [table_signature(element_rows(t)) for t in tables])


def _body_elements(document) -> List:
    return [el for el in document.element.body if el.tag in (P, TBL)]


def _combined_from_sunny_hill(gender: str) -> List:
    """The WISC-V captions and tables of the Sunny Hill template for a boy or a girl."""
    document = Document(TEMPLATE_DIR / SUNNY_HILL.get(gender, SUNNY_HILL["boy"]))
    children = _body_elements(document)
    text = lambda el: "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()  # noqa: E731
    start = next(
        (i for i, el in enumerate(children)
         if el.tag == P and text(el).startswith("Cognitive Score Summary Table") and "WISC-5" in text(el)),
        None,
    )
    if start is None:
        return []
    kept: List = []
    for el in children[start:]:
        if el.tag == P and re.match(r"^\(?\s*insert\b.*graph", text(el), re.I):
            break
        if el.tag == TBL:
            kept += [deepcopy(el), OxmlElement("w:p")]
        elif el is children[start]:
            kept.append(deepcopy(el))      # the caption above the first table; the notes and staff instructions are not carried
    return kept


def donor_elements(layout: str, gender: str = "boy") -> List:
    """Fresh copies of the blank captions and tables for a layout ([] if unavailable)."""
    if layout == "wisc5_combined":
        return _combined_from_sunny_hill(gender)
    path = LAYOUT_DIR / f"{layout}.docx"
    if not path.is_file():
        return []
    return [deepcopy(el) for el in _body_elements(Document(path))]
