"""WISC-V in two layouts and ABAS-3 option 2 (Emma, 20 Nov): the report follows the layout that was pasted.

All numbers are made up.
"""
import io
import re

from docx import Document
from docx.oxml.ns import qn

from services import score_layouts
from services.docx_exporter import create_report_docx
from services.docx_test_results import _text
from services.score_fill import cell_text
from tests.test_score_fill import pearson_index_table, pearson_subtest_table

CDBC = "SunnyHill CDBC Psychology Assessment - Boy"
CDBC_GIRL = "SunnyHill CDBC Psychology Assessment - Girl"
PSYCHED = "Psycho-Educational Assessment - Boy"
PSYCHED_GIRL = "Psycho-Educational Assessment - Girl"


# --------------------------------------------------------------------------- #
# what a clinician pastes
# --------------------------------------------------------------------------- #
def wisc_by_index():
    """The older WISC-V tables: an index table, then one small table per index."""
    index = {
        "kind": "table", "caption": "WISC-V Index Scores Summary",
        "rows": [
            ["WISC-V\nIndex", "Standard\nScore", "Percentile\nRank", "95% Confidence\nInterval", "Qualitative\nDescription"],
            ["Verbal Comprehension (VCI)", "94", "34", "88-101", "Average"],
            ["Visual Spatial (VSI)", "101", "53", "94-108", "Average"],
            ["Fluid Reasoning (FRI)", "99", "47", "92-106", "Average"],
            ["Working Memory (WMI)", "88", "21", "82-96", "Low Average"],
            ["Processing Speed (PSI)", "76", "5", "70-88", "Very Low"],
            ["Full Scale (FSIQ)*", "91", "27", "86-97", "Average"],
            ["General Ability (GAI)", "98", "45", "92-104", "Average"],
            ["Nonverbal (NVI)", "96", "39", "90-102", "Average"],
            ["Cognitive Proficiency (CPI)", "81", "10", "75-90", "Low Average"],
        ],
    }

    def subtests(code, title, rows):
        return {
            "kind": "table", "caption": f"{title} Subtest Scores Summary",
            "rows": [[f"{code}\nSubtests", "Skills\nMeasured", "Scaled\nScore", "Percentile Rank"]] + rows,
        }

    return [
        index,
        subtests("VCI", "Verbal Comprehension Index", [["Similarities (SI)", "reasoning", "9", "37"], ["Vocabulary (VC)", "words", "10", "50"]]),
        subtests("VSI", "Visual Spatial Index", [["Block Design (BD)", "puzzles", "11", "63"], ["Visual Puzzles (VP)", "puzzles", "10", "50"]]),
        subtests("FRI", "Fluid Reasoning Index", [["Matrix Reasoning (MR)", "patterns", "9", "37"], ["Figure Weights (FW)", "balance", "11", "63"]]),
        subtests("WMI", "Working Memory Index", [["Digit Span (DS)", "memory", "8", "25"], ["Picture Span (PS)", "memory", "7", "16"]]),
        subtests("PSI", "Processing Speed Index", [["Coding (CD)", "speed", "5", "5"], ["Symbol Search (SS)", "speed", "6", "9"]]),
    ]


def wisc_combined():
    """The combined WISC-V table (index rows, then a Subtest heading and the subtests)."""
    return [{
        "kind": "table", "caption": "Cognitive Score Summary Table: WISC-5",
        "rows": [
            ["Index", "Standard Score", "Percentile", "Interpretation"],
            ["Verbal Comprehension", "94", "34", ""],
            ["Visual-Spatial", "101", "53", ""],
            ["Fluid Reasoning", "99", "47", ""],
            ["Working Memory", "88", "21", ""],
            ["Processing Speed", "76", "5", ""],
            ["Full Scale IQ (FSIQ)", "91", "27", ""],
            ["Subtest", "Scaled Score", "Percentile", "What the test involves"],
            ["Similarities", "9", "37", ""],
            ["Vocabulary", "10", "50", ""],
            ["Block Design", "11", "63", ""],
        ],
    }]


def abas_option2():
    """Option 2: a parent table and a teacher table, each with composites, then skill areas.
    Rows are laid out the way the extractor reads Word tables whose header cells are merged."""
    def table(caption, composites, skills):
        rows = [["Composite", "Standard\nScore", "", "Percentile\nRank", "", "Qualitative Description", ""]]
        rows += [[n, s, "", p, "", d, ""] for n, s, p, d in composites]
        rows.append(["Skill Area", "Scaled Score", "Relative Strength/\nWeakness (S/W)", "", "Qualitative Description", "", "Age Equivalent\n(yr, mo)"])
        for name, scaled, sw, desc, age in skills:
            rows.append([name, scaled, sw, "", desc, "", age])
        return {"kind": "table", "caption": caption, "rows": rows}

    parent = table("", [
        ("Global Adaptive Composite", "72", "3", "Below Average"), ("Conceptual", "77", "6", "Below Average"),
        ("Social", "64", "1", "Exceptionally Low"), ("Practical", "78", "7", "Below Average"),
    ], [
        ("Conceptual", "", "", "", ""), ("Communication", "3", "W", "Exceptionally Low", "<5:0"),
        ("Functional Academics", "8", "S", "Average", "9:8-9:11"), ("Self-Direction", "7", "", "Low Average", "8:0-8:3"),
        ("Social", "", "", "", ""), ("Leisure", "4", "", "Low Average", "5:0"), ("Social", "2", "W", "Exceptionally Low", "<5:0"),
        ("Practical", "", "", "", ""), ("Community Use", "6", "", "Low Average", "9:4-9:7"), ("Home Living", "7", "", "Low Average", "8:8-8:11"),
        ("Health and Safety", "8", "S", "Average", "8:8-8:11"), ("Self-Care", "5", "", "Below Average", "6:4-6:7"),
    ])
    teacher = table("Joe's teacher also completed the ABAS-3.", [
        ("Global Adaptive Composite", "51", "0.1", "Exceptionally Low"), ("Conceptual", "49", "<0.1", "Exceptionally Low"),
        ("Social", "56", "0.2", "Exceptionally Low"), ("Practical", "57", "0.2", "Exceptionally Low"),
    ], [
        ("Conceptual", "", "", "", ""), ("Communication", "1", "", "Exceptionally Low", "<5:0"),
        ("Functional Academics", "2", "", "Exceptionally Low", "6:0-6:3"), ("Self-Direction", "1", "", "Exceptionally Low", "<5:0"),
        ("Social", "", "", "", ""), ("Leisure", "1", "", "Exceptionally Low", "<5:0"), ("Social", "3", "", "Exceptionally Low", "<5:0"),
        ("Practical", "", "", "", ""), ("Community Use", "1", "", "Exceptionally Low", "<5:0"), ("School Living", "4", "", "Very Low", "5:2"),
        ("Health and Safety", "6", "S", "Low Average", "6:4-6:7"), ("Self-Care", "1", "", "Exceptionally Low", "<5:0"),
    ])
    return parent, teacher


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def export(title, *groups, name="Alex Test", administered=None):
    report = []
    stream = create_report_docx(
        title=title, patient_name=name, report_type="x",
        content=f"# Report Metadata (Front Page)\nClient full name: {name}\n",
        test_results=list(groups), fill_report=report, tests_administered=administered,
    )
    return Document(io.BytesIO(stream.getvalue())), report


def grid(table):
    """Rows as lists of cell text, one entry per Word cell (a merged cell counts once)."""
    return [[cell_text(tc) for tc in tr.findall(qn("w:tc"))] for tr in table._tbl.findall(qn("w:tr"))]


def tables_headed(doc, first_cell):
    return [t for t in doc.tables if grid(t)[0] and grid(t)[0][0].replace("\n", " ").strip().startswith(first_cell)]


def row(table, label, nth=0):
    rows = [r for r in grid(table) if r and r[0].strip() == label]
    return rows[nth]


def body_text(doc):
    return " ".join(_text(el) for el in doc.element.body)


# --------------------------------------------------------------------------- #
# why the scaled scores were missing: a second heading row inside one table
# --------------------------------------------------------------------------- #
def test_scaled_scores_fill_into_the_combined_table_under_its_own_subtest_heading():
    doc, report = export(CDBC, {"test_name": "WISC-V", "items": [pearson_index_table(), pearson_subtest_table()]},
                         administered=["WISC-V"])
    table = tables_headed(doc, "Index")[0]
    assert row(table, "Verbal Comprehension")[1:3] == ["101", "53"]          # index rows: standard score, percentile
    similarities = row(table, "Similarities")
    assert similarities[1:3] == ["11", "63"]                                # subtest rows: scaled score, percentile
    assert not any("Similarities" in c for c in report[0]["unfilled_columns"])
    assert "Subtest" not in report[0]["not_in_report"]                       # the heading row is not a row to match


# --------------------------------------------------------------------------- #
# WISC-V: the layout that is pasted is the layout that is reported
# --------------------------------------------------------------------------- #
def test_older_wisc_tables_replace_the_combined_table_in_the_sunny_hill_report():
    doc, report = export(CDBC, {"test_name": "WISC-V", "items": wisc_by_index()}, administered=["WISC-V"])
    assert report[0]["result"] == "filled"
    assert report[0]["layout"] == "wisc5_by_index" and "WISC-V tables by index" in report[0]["layout_label"]

    index = tables_headed(doc, "WISC-V Index")[0]
    assert row(index, "Verbal Comprehension (VCI)")[1:] == ["94", "34", "88-101", "Average"]
    assert row(index, "Nonverbal (NVI)")[1:] == ["96", "39", "90-102", "Average"]
    assert row(index, "Cognitive Proficiency (CPI)")[1:3] == ["81", "10"]
    assert row(tables_headed(doc, "VCI")[0], "Similarities (SI)")[-2:] == ["9", "37"]      # the scaled scores
    assert row(tables_headed(doc, "PSI")[0], "Coding (CD)")[-2:] == ["5", "5"]
    assert row(tables_headed(doc, "VCI")[0], "Similarities (SI)")[1] == "Verbal abstract reasoning, expressive language, conceptual reasoning, cognitive flexibility"

    text = body_text(doc)
    assert "Cognitive Score Summary Table: WISC-5" not in text                 # the old caption went with the old table
    assert "Additional subtests to add into table" not in text                 # and so did its note to staff
    assert "Joe" not in text and "Jane" not in text


def test_combined_table_replaces_the_per_index_tables_in_the_psychoed_report():
    doc, report = export(PSYCHED, {"test_name": "WISC-V", "items": wisc_combined()}, administered=["WISC-V"])
    assert report[0]["result"] == "filled" and report[0]["layout"] == "wisc5_combined"
    table = tables_headed(doc, "Index")[0]
    assert row(table, "Verbal Comprehension")[1:3] == ["94", "34"]
    assert row(table, "Similarities")[1:3] == ["9", "37"]
    assert not tables_headed(doc, "VCI")                                       # the per-index tables are gone
    text = body_text(doc)
    assert "Alex" in text and "Joe" not in text


def test_the_combined_tables_wording_follows_the_childs_sex():
    girl, _ = export(PSYCHED_GIRL, {"test_name": "WISC-V", "items": wisc_combined()}, name="Maya Lee", administered=["WISC-V"])
    interpretation = row(tables_headed(girl, "Index")[0], "Verbal Comprehension")[-1]
    assert "Maya" in interpretation and "her age" in interpretation and "his age" not in interpretation


def test_nothing_is_swapped_when_the_layout_already_matches():
    doc, report = export(PSYCHED, {"test_name": "WISC-V", "items": wisc_by_index()}, administered=["WISC-V"])
    assert report[0]["result"] == "filled" and "layout" not in report[0]
    doc, report = export(CDBC, {"test_name": "WISC-V", "items": wisc_combined()}, administered=["WISC-V"])
    assert report[0]["result"] == "filled" and "layout" not in report[0]


def test_a_publishers_score_report_keeps_the_templates_own_layout():
    for title in (CDBC, PSYCHED):
        _, report = export(title, {"test_name": "WISC-V", "items": [pearson_index_table(), pearson_subtest_table()]},
                           administered=["WISC-V"])
        assert report[0]["result"] == "filled" and "layout" not in report[0]


def test_insert_mode_keeps_what_was_asked_for_and_never_swaps():
    _, report = export(CDBC, {"test_name": "WISC-V", "mode": "insert", "items": wisc_by_index()}, administered=["WISC-V"])
    assert report[0]["result"] == "replaced" and "layout" not in report[0]


# --------------------------------------------------------------------------- #
# ABAS-3 option 2: a parent table and a teacher table, header cells merged
# --------------------------------------------------------------------------- #
def test_abas_option2_tables_replace_option1_in_the_sunny_hill_report_and_are_filled():
    doc, report = export(CDBC, {"test_name": "ABAS-III", "items": list(abas_option2())}, administered=["ABAS-III"])
    assert report[0]["result"] == "filled" and report[0]["layout"] == "abas3_option2"
    parent, teacher = tables_headed(doc, "Composite")[:2]

    assert row(parent, "Global Adaptive Composite")[1:] == ["72", "3", "Below Average"]
    assert row(teacher, "Global Adaptive Composite")[1:] == ["51", "0.1", "Exceptionally Low"]   # its own table, not the parent's
    assert row(parent, "Communication")[1:] == ["3", "W", "Exceptionally Low", "<5:0"]
    assert row(teacher, "Communication")[1:] == ["1", "", "Exceptionally Low", "<5:0"]
    assert row(parent, "Functional Academics")[1] == "8" and row(teacher, "Functional Academics")[1] == "2"
    assert row(parent, "Home Living")[1] == "7" and row(teacher, "School Living")[1] == "4"       # the school form's own name for it
    assert "Adaptive Functioning Score Summary Table: ABAS-3" not in body_text(doc)


def test_abas_group_rows_stay_empty_and_the_skill_area_takes_the_scores():
    doc, _ = export(CDBC, {"test_name": "ABAS-III", "items": list(abas_option2())}, administered=["ABAS-III"])
    parent = tables_headed(doc, "Composite")[0]
    social = [r for r in grid(parent) if r[0].strip() == "Social"]
    assert len(social) == 3                                                  # composite, group heading, skill area
    assert social[0][1:] == ["64", "1", "Exceptionally Low"]                 # the composite takes the standard score
    assert not any(social[1][1:])                                            # the grey group heading stays blank
    assert social[2][1:] == ["2", "W", "Exceptionally Low", "<5:0"]          # the skill area takes the scaled score
    for group in ("Conceptual", "Practical"):
        heading = [r for r in grid(parent) if r[0].strip() == group][1]
        assert not any(heading[1:]), group


def test_abas_option2_fills_the_psychoed_templates_own_pair_of_tables():
    doc, report = export(PSYCHED, {"test_name": "ABAS-III", "items": list(abas_option2())}, administered=["ABAS-III"])
    assert report[0]["result"] == "filled" and "layout" not in report[0]
    parent, teacher = tables_headed(doc, "Composite")[:2]
    assert row(parent, "General Adaptive Composite")[1:] == ["72", "3", "Below Average"]   # "Global" in the report, "General" here
    assert row(teacher, "General Adaptive Composite")[1:] == ["51", "0.1", "Exceptionally Low"]
    assert row(teacher, "Home Living")[1] == "4"


def test_a_table_for_one_respondent_goes_to_that_respondents_table_only():
    parent, teacher = abas_option2()
    doc, report = export(PSYCHED, {"test_name": "ABAS-III", "items": [teacher]}, administered=["ABAS-III"])
    parent_table, teacher_table = tables_headed(doc, "Composite")[:2]
    assert row(teacher_table, "Conceptual")[1] == "49"
    assert not any(row(parent_table, "Conceptual")[1:])                      # the parent's table is not filled with the teacher's scores
    assert any("no table for it" in line for line in report[0]["not_in_report"])


def test_two_tests_in_either_order_both_get_their_layout():
    wisc = {"test_name": "WISC-V", "items": wisc_by_index()}
    abas = {"test_name": "ABAS-III", "items": list(abas_option2())}
    for groups in ((wisc, abas), (abas, wisc)):
        _, report = export(CDBC, *groups, administered=["WISC-V", "ABAS-III"])
        by_test = {r["test_name"]: r for r in report if r["result"] != "pruned"}
        assert by_test["WISC-V"]["result"] == "filled" and by_test["WISC-V"]["layout"] == "wisc5_by_index"
        assert by_test["ABAS-III"]["result"] == "filled" and by_test["ABAS-III"]["layout"] == "abas3_option2"


# --------------------------------------------------------------------------- #
# recognising the layouts, and the blank tables that ship with the app
# --------------------------------------------------------------------------- #
def test_layouts_are_recognised_from_the_tables_that_were_pasted():
    assert score_layouts.wanted_layout("wisc5", wisc_by_index()) == "wisc5_by_index"
    assert score_layouts.wanted_layout("wisc5", wisc_combined()) == "wisc5_combined"
    assert score_layouts.wanted_layout("wisc5", [pearson_index_table(), pearson_subtest_table()]) is None
    assert score_layouts.wanted_layout("abas3", list(abas_option2())) == "abas3_option2"
    assert score_layouts.wanted_layout("abas3", [pearson_index_table()]) is None
    assert score_layouts.wanted_layout("wais4", wisc_by_index()) is None     # only the tests the clinic has layouts for


def test_the_blank_layouts_that_ship_with_the_app_have_no_scores_in_them():
    for layout, expected_tables in (("wisc5_by_index", 6), ("abas3_option2", 2)):
        elements = score_layouts.donor_elements(layout)
        tables = [el for el in elements if el.tag == qn("w:tbl")]
        assert len(tables) == expected_tables
        for table in tables:
            for r in grid_of(table)[1:]:
                assert not any(re.search(r"\d", c) for c in r[1:] if len(c) < 12), r   # no scores, descriptions or ages left behind


def grid_of(table):
    return [[cell_text(tc) for tc in tr.findall(qn("w:tc"))] for tr in table.findall(qn("w:tr"))]


# --------------------------------------------------------------------------- #
# through the API, the way the app does it
# --------------------------------------------------------------------------- #
from tests.test_tests_administered import client_and_session  # noqa: E402,F401  (the fixture)


def test_the_pasted_layout_survives_saving_and_exporting_through_the_api(client_and_session):
    import json

    client, _ = client_and_session
    template_id = client.post(
        "/api/templates/", json={"name": "T", "description": "d", "template_type": "psychoeducational", "content": "[]"}
    ).json()["id"]
    created = client.post("/api/reports/generate", json={
        "title": CDBC, "patient_name": "Alex Test", "report_type": "x", "template_id": template_id,
        "additional_inputs": {"Report Metadata (Front Page)": "Client Full Name: Alex Test"},
        "tests_administered": ["WISC-V", "ABAS-III"],
        "test_results": [
            {"test_name": "WISC-V", "mode": "fill", "items": wisc_by_index()},
            {"test_name": "ABAS-III", "mode": "fill", "items": list(abas_option2())},
        ],
    })
    assert created.status_code == 200
    exported = client.get(f"/api/reports/{created.json()['id']}/export-docx")
    assert exported.status_code == 200
    summary = {entry["test_name"]: entry for entry in json.loads(exported.headers["x-score-fill"]) if "layout" in entry}
    assert summary["WISC-V"]["layout"] == "wisc5_by_index" and summary["ABAS-III"]["layout"] == "abas3_option2"
    doc = Document(io.BytesIO(exported.content))
    parent = tables_headed(doc, "Composite")[0]
    assert row(parent, "Global Adaptive Composite")[1:] == ["72", "3", "Below Average"]
    assert row(tables_headed(doc, "VCI")[0], "Similarities (SI)")[-2:] == ["9", "37"]
