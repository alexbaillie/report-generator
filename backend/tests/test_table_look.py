"""Inserted score tables look like the clinic's own (Emma's blank tables) and keep the template's caption."""
import io

from docx import Document
from docx.oxml.ns import qn

from services.docx_exporter import create_report_docx
from services.docx_test_results import BORDER_COLOR, HEADER_FILL, TABLE_FONT_PT, _build_table, _text

PSYCHED = "Psycho-Educational Assessment - Boy"
PASTED = [["Thing", "Percentile Rank", "Scaled Score"], ["Widgets", "50", "10"]]      # matches no template row


def built(rows):
    document = Document()
    document.element.body.insert(0, _build_table(document, rows, None, None, None))
    return Document(io.BytesIO(_save(document))).tables[0]


def _save(document):
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def export(*groups):
    stream = create_report_docx(
        title=PSYCHED, patient_name="Alex Test", report_type="x",
        content="# Report Metadata (Front Page)\nClient Full Name: Alex Test\n", test_results=list(groups))
    return Document(io.BytesIO(stream.getvalue()))


def paragraphs(doc):
    return [t for t in (_text(el) for el in doc.element.body if el.tag == qn("w:p")) if t]


def test_the_clinic_look_is_grey_header_black_borders_and_ten_point_text():
    assert (HEADER_FILL, BORDER_COLOR, TABLE_FONT_PT) == ("D9D9D9", "000000", 10)
    table = built([["Index", "Score"], ["A", "1"]])
    borders = table._tbl.tblPr.find(qn("w:tblBorders"))
    assert {edge.get(qn("w:color")) for edge in borders} == {BORDER_COLOR}
    header_cell, body_cell = table.rows[0].cells[0], table.rows[1].cells[0]
    assert header_cell._tc.tcPr.find(qn("w:shd")).get(qn("w:fill")) == HEADER_FILL
    assert body_cell.paragraphs[0].runs[0].font.size.pt == TABLE_FONT_PT
    assert body_cell._tc.tcPr.find(qn("w:vAlign")).get(qn("w:val")) == "center"


def test_a_pasted_table_without_a_caption_keeps_the_templates_caption_above_it():
    doc = export({"test_name": "WISC-V", "items": [{"kind": "table", "rows": PASTED}]})
    items = paragraphs(doc)
    assert "WISC-V Index Scores Summary" in items                                 # the template's caption stays
    assert "WISC-V Verbal Comprehension Index – Subtest Scores Summary" not in items   # the other, now empty, ones go
    caption = next(el for el in doc.element.body if el.tag == qn("w:p") and _text(el) == "WISC-V Index Scores Summary")
    following = [el for el in caption.itersiblings() if el.tag == qn("w:tbl")][0]
    assert "Widgets" in _text(following)


def test_a_table_that_brings_its_own_caption_replaces_the_templates_caption():
    doc = export({"test_name": "WISC-V", "items": [{"kind": "table", "caption": "My own caption", "rows": PASTED}]})
    items = paragraphs(doc)
    assert "My own caption" in items and "WISC-V Index Scores Summary" not in items
