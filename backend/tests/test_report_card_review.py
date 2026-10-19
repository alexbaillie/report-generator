"""Appendix 1: Report Card Review (names and text are made up)."""
import io
import json
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from services.docx_exporter import create_report_docx
from services.docx_test_results import _text
from services.report_card_review import PARTS, SECTION_TITLE, YEARS, compose_report_card_review, field_label

CDBC = "SunnyHill CDBC Psychology Assessment - Boy"
PSYCHED = "Psycho-Educational Assessment - Boy"
METADATA = "# Report Metadata (Front Page)\nClient Full Name: Alex Test\n"


def inputs(**by_key):
    """by_key like year1_grade="..." -> the form's "Year 1: ..." labels."""
    out = {}
    for name, value in by_key.items():
        year, key = name[len("year"):].split("_")
        out[field_label(int(year), key)] = value
    return out


def export(title, content):
    stream = create_report_docx(title=title, patient_name="Alex Test", report_type="x", content=content)
    return Document(io.BytesIO(stream.getvalue()))


def paragraphs(doc):
    return [t for t in (_text(el) for el in doc.element.body if el.tag == qn("w:p")) if t]


# --------------------------------------------------------------------------- #
# laying the answers out
# --------------------------------------------------------------------------- #
def test_parts_are_laid_out_as_headings_and_bullets_and_empty_parts_are_left_out():
    text = compose_report_card_review(inputs(
        year1_grade="Grade 5, Maple Elementary (French immersion)",
        year1_iep="- Improve reading fluency\n- Use a checklist",
        year1_term1="Alex is working hard.\nNeeds reminders.",
        year1_term3="Strong finish to the year.",
    ))
    assert text.splitlines() == [
        "**Grade 5, Maple Elementary (French immersion)**",
        "**IEP (Designation) Major Goals**",
        "- Improve reading fluency",
        "- Use a checklist",
        "**Comments from Report Card(s)**",
        "**Term 1**",
        "- Alex is working hard.",
        "- Needs reminders.",
        "**Term 3/Final Report**",
        "- Strong finish to the year.",
    ]
    assert "Learning Support" not in text and "Term 2" not in text      # nothing entered: left out


def test_comments_not_split_by_term_have_no_term_headings():
    text = compose_report_card_review(inputs(year1_all="Positive attitude.\nGood effort in math."))
    assert text.splitlines() == ["**Comments from Report Card(s)**", "- Positive attitude.", "- Good effort in math."]


def test_years_with_nothing_in_them_are_skipped_and_nothing_gives_an_empty_text():
    text = compose_report_card_review(inputs(year2_grade="Grade 4", year2_support="Resource room"))
    assert text.splitlines()[0] == "**Grade 4**"
    assert compose_report_card_review({}) == ""
    assert compose_report_card_review(inputs(year1_iep="   \n  ")) == ""


def test_a_pasted_secondary_bullet_is_kept_as_one():
    text = compose_report_card_review(inputs(year1_all="• Math\n    • fractions\n• Reading"))
    assert text.splitlines()[1:] == ["- Math", "  - fractions", "- Reading"]


# --------------------------------------------------------------------------- #
# the form
# --------------------------------------------------------------------------- #
def test_every_psyched_and_cdbc_seed_has_the_section_with_matching_labels():
    seeds = Path(__file__).parent.parent / "seeds"
    expected = [field_label(y, key) for y in range(1, YEARS + 1) for key, *_ in PARTS]
    for name in ("04_psyched_boy.json", "05_psyched_girl.json", "06_cdbc_boy.json", "07_cdbc_girl.json"):
        content = json.loads((seeds / name).read_text(encoding="utf-8"))["content"]
        section = next(s for s in content if s["title"] == SECTION_TITLE)
        assert [f["label"] for f in section["fields"]] == expected


# --------------------------------------------------------------------------- #
# the Word export
# --------------------------------------------------------------------------- #
APPENDIX = (
    "# Appendix 1: Report Card Review\n"
    "**Grade 5, Maple Elementary**\n**IEP (Designation) Major Goals**\n- Improve reading fluency\n  - daily practice\n"
    "**Comments from Report Card(s)**\n**Term 1**\n- Working hard.\n"
)


def test_the_appendix_is_filled_in_the_templates_format_and_the_staff_instructions_go():
    for title in (CDBC, PSYCHED):
        doc = export(title, METADATA + APPENDIX)
        items = paragraphs(doc)
        start = next(i for i, t in enumerate(items) if t.startswith("Appendix 1: Report Card Review"))
        body = items[start + 1:start + 9]
        assert body[:4] == ["Grade 5, Maple Elementary", "IEP (Designation) Major Goals",
                            "Improve reading fluency", "daily practice"], title
        assert "Comments from Report Card(s)" in body and "Term 1" in body
        assert not any("If none, delete this subsection" in t for t in items)
        assert not any(t.startswith("Please use this exact format") for t in items)
        # the sections after it are untouched
        assert any(t.startswith("Appendix 2") for t in items), title


def test_the_appendix_uses_real_bullets_with_a_second_level():
    doc = export(CDBC, METADATA + APPENDIX)
    by_text = {_text(p): p for p in doc.element.body.iter(qn("w:p"))}
    first, second = by_text["Improve reading fluency"], by_text["daily practice"]
    level = lambda p: p.find(qn("w:pPr")).find(qn("w:numPr")).find(qn("w:ilvl")).get(qn("w:val"))
    assert (level(first), level(second)) == ("0", "1")
    assert not list(first.iter(qn("w:i"))) and not list(first.iter(qn("w:b")))
    heading = by_text["IEP (Designation) Major Goals"]
    assert list(heading.iter(qn("w:b")))                                    # sub-headings are bold...
    assert not list(heading.iter(qn("w:numPr")))                             # ...and are not bulleted


def test_with_nothing_entered_the_appendix_and_its_instructions_are_removed():
    for title in (CDBC, PSYCHED):
        items = paragraphs(export(title, METADATA))
        assert not any(t.startswith("Appendix 1: Report Card Review") for t in items), title
        assert not any(t.startswith("Please use this exact format") for t in items), title
        assert not any("If none, delete this subsection" in t for t in items), title
        assert any(t.startswith("Appendix 2") for t in items), title


# --------------------------------------------------------------------------- #
# a generated section no longer runs on to the end of the document
# --------------------------------------------------------------------------- #
def test_generated_last_section_keeps_the_signatures_and_appendices():
    cases = ((CDBC, "Cognitive, Memory & Academic Results"), (PSYCHED, "Recommendations"))
    for title, section in cases:
        items = paragraphs(export(title, METADATA + f"# {section}\nSome generated text.\n"))
        assert "Charmaine Miranda, Ph.D." in items, title
        assert any(t.startswith("Appendix 2") for t in items), title
        assert any(t.startswith("Some generated text") for t in items), title


# --------------------------------------------------------------------------- #
# no AI in the middle
# --------------------------------------------------------------------------- #
def test_the_generate_section_endpoint_returns_the_appendix_without_calling_the_model(monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from database.db import Base, get_db
    from main import app
    from services import report_generator

    async def boom(*args, **kwargs):
        raise AssertionError("the model must not be used for the report card review")

    monkeypatch.setattr(report_generator, "generate_text", boom)
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
        client = TestClient(app)
        template_id = client.post("/api/templates/", json={
            "name": CDBC, "description": "d", "template_type": "psychology", "content": "[]"}).json()["id"]
        response = client.post("/api/reports/generate-section", json={
            "template_id": template_id, "section_name": SECTION_TITLE, "document_ids": [],
            "section_inputs": inputs(year1_grade="Grade 5", year1_all="Doing well."),
        })
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 200
    assert response.json()["section_content"] == "**Grade 5**\n**Comments from Report Card(s)**\n- Doing well."


def test_generating_any_section_never_deletes_an_appendix_in_any_branded_template():
    """Every section of every branded template generated at once: the appendices are all still there."""
    from services.docx_exporter import ASD_SECTION_TARGETS, CDBC_SECTION_TARGETS, PSYCHED_SECTION_TARGETS

    cases = (
        ("ASD Clinical Diagnostic Assessment Report", ASD_SECTION_TARGETS, ["APPENDIX 2: Additional Resources", "APPENDIX 3:"]),
        (CDBC, CDBC_SECTION_TARGETS, ["Appendix 2: More information about ADHD", "Appendix 2: Apps to Support Academic Areas"]),
        (PSYCHED, PSYCHED_SECTION_TARGETS, ["Appendix 2: Compass Clinic Homework Checklists", "Appendix 3: Daily Report Card"]),
    )
    for title, targets, appendices in cases:
        content = METADATA + "".join(
            f"# {name}\nGenerated text for {name}.\n" for name, _ in targets if not name.startswith("appendix 2")
        )
        items = paragraphs(export(title, content))
        for heading in appendices:
            assert any(t.startswith(heading) for t in items), f"{title}: lost {heading!r}"
        assert any(t.startswith("Generated text for") for t in items), title
