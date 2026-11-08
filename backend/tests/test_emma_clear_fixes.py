"""Clear fixes from Emma's second review of a Sunny Hill report (all names are made up)."""
import io
import zipfile

import pytest
from docx import Document
from docx.oxml.ns import qn
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base, get_db
from main import app
from services import report_generator
from services.docx_exporter import create_report_docx
from services.docx_test_results import _text

CDBC = "SunnyHill CDBC Psychology Assessment - Boy"
CDBC_GIRL = "SunnyHill CDBC Psychology Assessment - Girl"
PSYCHED = "Psycho-Educational Assessment - Boy"


def front(**fields):
    return "# Report Metadata (Front Page)\n" + "\n".join(f"{k}: {v}" for k, v in fields.items()) + "\n"


def export_bytes(title, content, **kwargs):
    return create_report_docx(title=title, patient_name="Alex Test", report_type="x", content=content, **kwargs).getvalue()


def export(title, content, **kwargs):
    return Document(io.BytesIO(export_bytes(title, content, **kwargs)))


def lines(doc):
    return [p.text for p in doc.paragraphs]


def paragraphs(doc):
    return [t for t in (_text(el) for el in doc.element.body if el.tag == qn("w:p")) if t]


# --------------------------------------------------------------------------- #
# front page and header
# --------------------------------------------------------------------------- #
def test_the_chart_number_reaches_the_page_header():
    data = export_bytes(CDBC, front(**{"Client full name": "Alex Test", "Chart number": "123-45-67"}))
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        headers = " ".join(package.read(n).decode("utf8") for n in package.namelist() if n.startswith("word/header"))
    assert "123-45-67" in headers and "000-00-00" not in headers


def test_the_header_keeps_its_placeholder_when_no_chart_number_is_given():
    data = export_bytes(CDBC, front(**{"Client full name": "Alex Test"}))
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        headers = " ".join(package.read(n).decode("utf8") for n in package.namelist() if n.startswith("word/header"))
    assert "000-00-00" in headers


@pytest.mark.parametrize("typed, shown", [("14", "14 years"), ("14 years", "14 years"), ("7.5", "7.5 years"),
                                          ("14 years, 3 months", "14 years, 3 months")])
def test_a_bare_age_reads_as_years(typed, shown):
    doc = export(CDBC, front(**{"Client full name": "Alex Test", "Age at assessment": typed}))
    assert f"\tAGE AT ASSESSMENT:\t{shown}" in lines(doc)


def test_the_legal_guardian_is_written_on_the_front_page():
    doc = export(CDBC, front(**{"Client full name": "Alex Test", "Legal guardian": "Maria Lopez"}))
    assert "\tLEGAL GUARDIAN:\tMaria Lopez" in lines(doc)


def test_a_staff_instruction_in_the_template_never_reaches_the_report():
    doc = export(CDBC, front(**{"Client full name": "Alex Test"}))
    assert "Very brief summary of previous issues at school" not in paragraphs(doc)


# --------------------------------------------------------------------------- #
# tests administered: the template's list stays, no paragraph in its place
# --------------------------------------------------------------------------- #
def test_a_written_tests_paragraph_does_not_replace_the_list_or_the_interpretation_notes():
    content = front(**{"Client full name": "Alex Test"}) + (
        "# Tests Administered\nThe following standardized psychological tests were administered as part of the assessment.\n"
    )
    doc = export(CDBC, content, tests_administered=["WISC-V", "ABAS-III"])
    items = paragraphs(doc)
    assert not any(t.startswith("The following standardized psychological tests were administered") for t in items)
    assert "Wechsler Intelligence Scale for Children – 5th Edition (WISC-V)" in items      # the trimmed list
    assert "INFORMATION ON THE INTERPRETATION OF TEST SCORES" in items
    assert any(t.startswith("Test scores provide a") for t in items)
    assert "Validity Testing" in items


# --------------------------------------------------------------------------- #
# page break before Appendix 2
# --------------------------------------------------------------------------- #
def test_appendix_2_still_starts_on_its_own_page_when_appendix_1_is_filled_in():
    content = front(**{"Client full name": "Alex Test"}) + "# Appendix 1: Report Card Review\n**Grade 5**\n**Learning Support Programming**\n- Resource room\n"
    doc = export(CDBC, content)
    body = list(doc.element.body)
    heading = next(i for i, el in enumerate(body) if el.tag == qn("w:p") and _text(el).startswith("Appendix 2: More information"))
    before = [el for el in body[max(0, heading - 4):heading] if el.tag == qn("w:p")]
    assert any(br.get(qn("w:type")) == "page" for el in before for br in el.iter(qn("w:br")))


# --------------------------------------------------------------------------- #
# the clinic's standard wording
# --------------------------------------------------------------------------- #
def reason(doc):
    items = paragraphs(doc)
    start = next(i for i, t in enumerate(items) if t == "REASON FOR REFERRAL")
    return items[start + 1:items.index("SOURCES OF INFORMATION")]


def test_reason_for_referral_uses_the_standard_sentence_with_the_age_and_doctor_filled_in():
    doc = export(CDBC, front(**{"Client full name": "Alex Test", "Age at assessment": "11", "Referring doctor": "Smith"}))
    text = " ".join(reason(doc))
    assert "is an 11-year-old boy referred for a psychological assessment" in text
    assert "initiated by his doctor Dr. Smith" in text and "xx" not in text
    older = export(CDBC_GIRL, front(**{"Client full name": "Alex Test", "Age at assessment": "14 years", "Referring doctor": "Dr. Lee"}))
    assert "is a 14-year-old girl referred" in " ".join(reason(older)) and "doctor Dr. Lee" in " ".join(reason(older))


def test_anything_typed_for_the_referral_is_added_as_typed_after_the_standard_sentence():
    content = front(**{"Client full name": "Alex Test", "Age at assessment": "9"}) + (
        "# Reason for Referral\nQuery of FASD.\nPlease see Dr. Practitioner's letter.\n")
    items = reason(export(CDBC, content))
    assert items[0].startswith("Alex is a 9-year-old boy") or "9-year-old" in items[0]
    assert items[1:3] == ["Query of FASD.", "Please see Dr. Practitioner's letter."]


def test_sources_of_information_keeps_the_standard_sentence_unless_something_is_typed():
    standard = "Sources of information for this report include parent interview, review of file"
    kept = paragraphs(export(CDBC, front(**{"Client full name": "Alex Test"})))
    assert any(t.startswith(standard) for t in kept)
    typed = paragraphs(export(CDBC, front(**{"Client full name": "Alex Test"}) + "# Sources of Information\nParent interview and school file.\n"))
    assert "Parent interview and school file." in typed and not any(t.startswith(standard) for t in typed)


def test_the_diagnostic_summary_lists_only_what_was_typed():
    content = front(**{"Client full name": "Alex Test"}) + "# Diagnostic Summary (DSM-5-TR)\nSocial Anxiety Disorder (300.23)\n"
    items = paragraphs(export(CDBC, content))
    start = items.index("DIAGNOSTIC SUMMARY (DSM-5-TR)")
    assert items[start + 1] == "Social Anxiety Disorder (300.23)"
    assert "Global Developmental Delay (F88)" not in items[start:start + 6]      # the template's option list is replaced


# --------------------------------------------------------------------------- #
# no model for these sections
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


def test_sunny_hill_standard_sections_come_back_as_typed_without_the_model(client, monkeypatch):
    async def boom(*args, **kwargs):
        raise AssertionError("the model must not be used here")

    monkeypatch.setattr(report_generator, "generate_text", boom)
    assert _section(client, CDBC, "Diagnostic Summary (DSM-5-TR)",
                    {"Diagnoses (DSM-5-TR)": "Social Anxiety Disorder (300.23)\n\nADHD", "Other diagnoses": ""}) == \
        "Social Anxiety Disorder (300.23)\nADHD"
    assert _section(client, CDBC, "Reason for Referral", {"Reason for referral": "Query of FASD."}) == "Query of FASD."
    assert _section(client, CDBC, "Sources of Information", {"Sources of information": "File review"}) == "File review"
    assert _section(client, CDBC, "Tests Administered", {"Tests administered": "WISC-V"}) == ""      # the list is the template's


def test_other_templates_still_use_the_model_for_those_sections(client, monkeypatch):
    async def fake(prompt, max_tokens=0):
        return "model text"

    monkeypatch.setattr(report_generator, "generate_text", fake)
    assert _section(client, "Standard Intake Assessment", "Reason for Referral", {"Reason for referral": "x"}) == "model text"
    assert _section(client, PSYCHED, "Reason for Referral", {"Reason for referral": "x"}) == "model text"
