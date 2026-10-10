import pytest

from services.score_report_extractor import (
    ScoreReportError,
    extract_score_report,
    html_to_tables,
)
from tests.score_report_samples import (
    INDEX_ROWS,
    SUBTEST_ROWS,
    make_image_pdf,
    make_score_report_docx,
    make_score_report_pdf,
)


def test_docx_extracts_every_table_and_the_graph_in_document_order(tmp_path):
    path = make_score_report_docx(tmp_path / "wisc.docx")

    result = extract_score_report(path, None)
    kinds = [item["kind"] for item in result["items"]]

    assert kinds == ["table", "table", "image"]
    assert result["items"][0]["rows"] == INDEX_ROWS
    assert result["items"][1]["rows"] == SUBTEST_ROWS


def test_docx_captions_come_from_the_paragraph_above(tmp_path):
    path = make_score_report_docx(tmp_path / "wisc.docx")

    items = extract_score_report(path, None)["items"]

    assert [i["caption"] for i in items] == [
        "WISC-V Primary Index Scores",
        "Subtest Scaled Scores",
        "Index Score Profile",
    ]


def test_docx_ignores_tiny_logos_and_duplicate_images(tmp_path):
    path = make_score_report_docx(tmp_path / "wisc.docx")

    images = [i for i in extract_score_report(path, None)["items"] if i["kind"] == "image"]

    assert len(images) == 1  # logo skipped, repeated graph de-duplicated
    assert images[0]["content_type"] == "image/png"
    assert images[0]["width"] >= 800 and images[0]["data_b64"]


def test_items_get_stable_ids(tmp_path):
    items = extract_score_report(make_score_report_docx(tmp_path / "a.docx"), None)["items"]

    assert [i["id"] for i in items] == ["item-0", "item-1", "item-2"]


def test_pdf_extracts_a_ruled_table(tmp_path):
    result = extract_score_report(make_score_report_pdf(tmp_path / "scores.pdf"), "application/pdf")

    tables = [i for i in result["items"] if i["kind"] == "table"]
    assert len(tables) == 1
    assert tables[0]["rows"][1][0].startswith("Verbal Comprehens")
    assert tables[0]["rows"][0][0] == "Index"


def test_pdf_extracts_an_embedded_graph_as_png(tmp_path):
    result = extract_score_report(make_image_pdf(tmp_path / "graph.pdf"), "application/pdf")

    images = [i for i in result["items"] if i["kind"] == "image"]
    assert len(images) == 1
    assert images[0]["content_type"] == "image/png" and images[0]["width"] > 400


def test_pdf_without_tables_warns_instead_of_failing(tmp_path):
    result = extract_score_report(make_image_pdf(tmp_path / "graph.pdf"), "application/pdf")

    assert any("No tables were detected" in w for w in result["warnings"])


def test_unsupported_and_legacy_files_give_a_clear_error(tmp_path):
    other = tmp_path / "notes.txt"
    other.write_text("hello")
    legacy = tmp_path / "old.doc"
    legacy.write_bytes(b"x")

    with pytest.raises(ScoreReportError, match="Word"):
        extract_score_report(other, "text/plain")
    with pytest.raises(ScoreReportError, match=r"\.doc"):
        extract_score_report(legacy, None)


def test_corrupt_docx_gives_a_clear_error(tmp_path):
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"not a zip")

    with pytest.raises(ScoreReportError, match="couldn't be opened"):
        extract_score_report(bad, None)


def test_html_to_tables_keeps_every_table_not_just_the_first():
    html = (
        "<p>x</p><table><tr><th>Index</th><th>Score</th></tr><tr><td>VCI</td><td>104</td></tr></table>"
        "<table><tr><td>Subtest</td><td>Scaled</td></tr><tr><td>Vocabulary</td><td>10</td></tr></table>"
    )

    tables = html_to_tables(html)

    assert [t["rows"][1][0] for t in tables] == ["VCI", "Vocabulary"]


def test_html_to_tables_handles_colspan_nested_tables_and_junk():
    html = (
        "<table><tr><td colspan='2'>Title</td></tr>"
        "<tr><td>a</td><td><table><tr><td>inner</td><td>cell</td></tr></table></td></tr></table>"
    )

    tables = html_to_tables(html)

    assert len(tables) == 1  # nested table isn't a second table
    assert tables[0]["rows"][0] == ["Title", ""]
    assert html_to_tables("") == [] and html_to_tables("<p>no tables</p>") == []
