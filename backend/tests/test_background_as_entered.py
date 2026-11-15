"""Sunny Hill background sections are written exactly as entered (Emma approved this on 13 Nov)."""
import io
import json
from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base, get_db
from main import app
from seed_data import content_hash, should_refresh_content
from services import report_generator
from services.docx_exporter import create_report_docx
from services.docx_test_results import _text
from services.report_generator import as_entered_bullets, entry_lines, wants_as_entered

CDBC = "SunnyHill CDBC Psychology Assessment - Boy"
PSYCHED = "Psycho-Educational Assessment - Boy"


def tpl(name):
    from types import SimpleNamespace
    return SimpleNamespace(name=name)


# --------------------------------------------------------------------------- #
# the writer
# --------------------------------------------------------------------------- #
def test_each_line_typed_is_one_bullet_in_the_forms_order_and_nothing_is_reworded():
    text = as_entered_bullets("Family History", {
        "Where the child lives / who they live with": "John lives at home with his mother, Jane, and father, John.",
        "Language / ESL": "The family speaks English at home.",
        "Other relevant information": "",
        "Recent / current family stressors": "There are no current family stressors.",
    })
    assert text.splitlines() == [
        "- John lives at home with his mother, Jane, and father, John.",
        "- The family speaks English at home.",
        "- There are no current family stressors.",
    ]


def test_an_entry_typed_as_one_paragraph_stays_one_bullet_with_its_detail():
    entry = ("John's mother consumed alcohol during pregnancy. He also endorsed drug, tobacco and medication use. "
             "Specifics were not provided.")
    assert as_entered_bullets("Developmental & Medical History", {"Pregnancy and birth information": entry}) == f"- {entry}"


def test_the_order_of_the_boxes_decides_the_order_of_the_bullets():
    text = as_entered_bullets("Family History", {"B": "second box", "A": "first box"})
    assert text.splitlines() == ["- second box", "- first box"]      # the form's order, whatever the labels say


def test_pasted_bullet_markers_are_not_doubled_and_blank_lines_are_dropped():
    assert entry_lines("• one\n\n- two\n   * three  \n") == ["one", "two", "three"]


def test_a_pasted_table_is_read_row_by_row():
    html = "<table><tr><td>June 19, 2024</td><td>Eligibility assessment</td></tr><tr><td>June 22, 2023</td><td>SD57 consultation</td></tr></table>"
    assert as_entered_bullets("Previous Assessments & Interventions", {"Previous assessments": html}).splitlines() == [
        "- June 19, 2024; Eligibility assessment", "- June 22, 2023; SD57 consultation"]


def test_presenting_concerns_keep_the_forms_area_names_as_headings():
    text = as_entered_bullets("Presenting Concerns (as provided by parents)", {
        "Attention / Impulsivity / Activity / Executive Functions": "Difficulty planning tasks.\nTrouble following instructions.",
        "Anxiety / Mood": "no concerns",
        "Communication": "",
        "Social concerns": "None",
    })
    assert text.splitlines() == [
        "**Attention**", "- Difficulty planning tasks.", "- Trouble following instructions.",
        "**Anxiety**", "- No concerns with anxiety were indicated.",
        "**Social concerns**", "- No social concerns were indicated.",
    ]


def test_only_the_sunny_hill_background_sections_are_written_as_entered():
    for section in ("Presenting Concerns (as provided by parents)", "Areas of Relative Strength & Interests", "Family History",
                    "Developmental & Medical History", "Educational History", "Previous Assessments & Interventions"):
        assert wants_as_entered(tpl(CDBC), section)
    assert not wants_as_entered(tpl(CDBC), "Reason for Referral")
    assert not wants_as_entered(tpl(CDBC), "Summary of Findings")
    assert not wants_as_entered(tpl(PSYCHED), "Family History")


# --------------------------------------------------------------------------- #
# in the Word report
# --------------------------------------------------------------------------- #
def test_entries_become_real_bullets_in_the_word_report_with_the_exact_text():
    content = "# Report Metadata (Front Page)\nClient full name: John Doe\n# Family History\n" + as_entered_bullets(
        "Family History", {"a": "John lives at home with his mother and father.", "b": "He has an older brother."})
    doc = Document(io.BytesIO(create_report_docx(title=CDBC, patient_name="John Doe", report_type="x", content=content).getvalue()))
    bullets = [p for p in doc.element.body.iter(qn("w:p"))
               if _text(p) in ("John lives at home with his mother and father.", "He has an older brother.")]
    assert [_text(p) for p in bullets] == ["John lives at home with his mother and father.", "He has an older brother."]
    assert all(p.find(qn("w:pPr")).find(qn("w:numPr")) is not None for p in bullets)


# --------------------------------------------------------------------------- #
# no model
# --------------------------------------------------------------------------- #
@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _section(client, template_name, section, inputs):
    existing = {t["name"]: t["id"] for t in client.get("/api/templates/").json()}
    template_id = existing.get(template_name) or client.post("/api/templates/", json={
        "name": template_name, "description": "d", "template_type": "x", "content": "[]"}).json()["id"]
    response = client.post("/api/reports/generate-section", json={
        "template_id": template_id, "section_name": section, "document_ids": [], "section_inputs": inputs})
    assert response.status_code == 200, response.text
    return response.json()["section_content"]


def test_the_background_sections_come_back_as_entered_without_calling_the_model(client, monkeypatch):
    async def boom(*args, **kwargs):
        raise AssertionError("the model must not be used for these sections")

    monkeypatch.setattr(report_generator, "generate_text", boom)
    assert _section(client, CDBC, "Educational History", {"Current school": "Grade 7 at Westwood Elementary.", "Goals": "To start work independently."}) == \
        "- Grade 7 at Westwood Elementary.\n- To start work independently."


def test_other_templates_still_use_the_model_for_the_same_section(client, monkeypatch):
    async def fake(prompt, max_tokens=0):
        return "model text"

    monkeypatch.setattr(report_generator, "generate_text", fake)
    assert _section(client, PSYCHED, "Family History", {"Lives with": "mom and dad"}) == "model text"


# --------------------------------------------------------------------------- #
# the form and how installed templates get it
# --------------------------------------------------------------------------- #
def test_the_school_related_area_is_gone_from_both_sunny_hill_forms():
    seeds = Path(__file__).parent.parent / "seeds"
    for name in ("06_cdbc_boy.json", "07_cdbc_girl.json"):
        content = json.loads((seeds / name).read_text(encoding="utf-8"))["content"]
        labels = [f["label"] for s in content if s["title"].startswith("Presenting") for f in s["fields"]]
        assert "School-related" not in labels and "Learning" in labels


def test_a_shorter_seed_still_replaces_the_version_it_supersedes_but_never_an_edited_template():
    older = json.dumps([{"title": "Presenting Concerns", "fields": [{"label": "A"}, {"label": "School-related"}]}])
    newer = json.dumps([{"title": "Presenting Concerns", "fields": [{"label": "A"}]}])
    seed = {"content": newer, "replaces": [content_hash(older)]}

    assert len(newer) < len(older)
    assert should_refresh_content(older, seed)                              # untouched older version: upgraded
    assert not should_refresh_content(older + " ", seed)                    # somebody edited it: left alone
    assert not should_refresh_content(older.replace("A", "B"), seed)
    assert not should_refresh_content(newer, seed)                          # already current
    assert should_refresh_content("", seed)                                 # missing content is repaired
    assert should_refresh_content("[]", seed)                               # truncated (shorter than the seed)
    assert should_refresh_content(older + " ", seed, force=True)            # --force overwrites


def test_both_sunny_hill_seeds_list_the_versions_they_replace():
    seeds = Path(__file__).parent.parent / "seeds"
    for name in ("06_cdbc_boy.json", "07_cdbc_girl.json"):
        replaces = json.loads((seeds / name).read_text(encoding="utf-8")).get("replaces")
        assert replaces and all(len(h) == 64 for h in replaces)
