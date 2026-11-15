"""A parent called Jane or Joe must not be turned into the child (Emma's family history, 13 Nov)."""
import io

from docx import Document
from docx.oxml.ns import qn

from services.docx_exporter import create_report_docx
from services.docx_test_results import _text
from services.report_generator import as_entered_bullets, entry_lines

CDBC = "SunnyHill CDBC Psychology Assessment - Boy"
PSYCHED = "Psycho-Educational Assessment - Boy"
META = "# Report Metadata (Front Page)\nClient full name: John Doe\nAge at assessment: 11\n"

# what Emma typed in the family history box (her screenshot)
FAMILY = """The family speaks English at home.
Jane, John's mother, works as a school principal.
Joe, John's father, works as a hairdresser.
There are no current family stressors.
John lives at home with his mother, Jane, and father, Joe."""


def texts(title, content):
    doc = Document(io.BytesIO(create_report_docx(title=title, patient_name="John Doe", report_type="x", content=content).getvalue()))
    return [t for t in (_text(p) for p in doc.element.body.iter(qn("w:p"))) if t]


def test_the_parents_typed_names_survive_even_when_they_are_jane_and_joe():
    section = as_entered_bullets("Family History", {"Other relevant information": FAMILY})
    items = texts(CDBC, META + "# Family History\n" + section)
    assert "Jane, John's mother, works as a school principal." in items
    assert "Joe, John's father, works as a hairdresser." in items
    assert "John lives at home with his mother, Jane, and father, Joe." in items


def test_the_templates_own_placeholder_name_is_still_replaced():
    items = texts(CDBC, META)
    assert any(t.startswith("John is an 11-year-old boy referred") for t in items)       # "Joe is a xx-year-old ..." in the template
    assert not any(t.startswith("Joe is") for t in items)


def test_other_typed_sections_keep_names_too():
    content = META + "# Reason for Referral\nJoe's mother, Jane, asked for the assessment.\n" \
        "# Educational History\n- Jane, the principal, started the IEP.\n"
    items = texts(CDBC, content)
    assert "Joe's mother, Jane, asked for the assessment." in items
    assert "Jane, the principal, started the IEP." in items


def test_text_written_by_the_model_in_other_templates_still_gets_the_child_s_name():
    items = texts(PSYCHED, META + "# Reason for Referral\nJoe was referred by his doctor.\n")
    assert "John was referred by his doctor." in items


def test_a_pasted_markdown_heading_line_is_not_reported_as_an_entry():
    assert entry_lines("# Family History\n\n- The family speaks English.\n## Notes\nOne more") == ["The family speaks English.", "One more"]
    assert "Family History" not in as_entered_bullets("Family History", {"Box": "# Family History\n- Lives with mother"})
