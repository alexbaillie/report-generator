from hashlib import sha256
from io import BytesIO
from pathlib import Path
import zipfile

from docx import Document

from services.docx_exporter import ASD_TEMPLATE_PATH, create_report_docx


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_asd_export_fills_metadata_and_preserves_template_structure():
    before_hash = _hash(ASD_TEMPLATE_PATH)
    exported = create_report_docx(
        title="ASD Clinical Diagnostic Assessment Report",
        patient_name="Patient Name",
        report_type="evaluation",
        content=(
            "# Report Metadata (Front Page)\n\n"
            "Report title: Test\n"
            "Client full name: Alex Example\n"
            "Date of birth: 2012-05-03"
        ),
    )

    output = Document(exported)
    assert _hash(ASD_TEMPLATE_PATH) == before_hash
    assert output.paragraphs[1].text == "Test"
    assert output.tables[0].cell(0, 0).text == "Name: Alex Example"
    assert output.tables[0].cell(0, 1).text == "Date of Birth: 2012-05-03"
    assert len(output.sections) == 1
    assert len(output.tables) == 11
    assert output.sections[0].different_first_page_header_footer is True


def test_asd_export_replaces_generated_section_body_only():
    exported = create_report_docx(
        title="ASD Clinical Diagnostic Assessment Report",
        patient_name="Alex Example",
        report_type="evaluation",
        content=(
            "# Reason for Referral\n\n"
            "Alex was referred for an autism assessment following concerns about social communication.\n\n"
            "# General Behavioural Observations\n\n"
            "Alex participated cooperatively and benefited from clear structure."
        ),
    )

    output = Document(exported)
    texts = [paragraph.text for paragraph in output.paragraphs]
    referral_index = texts.index("Reason for Referral")
    summary_index = texts.index("Summary & Conclusions")
    assert texts[referral_index + 1 : summary_index] == [
        "Alex was referred for an autism assessment following concerns about social communication."
    ]
    observations_index = texts.index("General Behavioural Observations")
    autism_index = texts.index("Autism Characteristics")
    assert texts[observations_index + 1 : autism_index] == [
        "Alex participated cooperatively and benefited from clear structure."
    ]
    assert "Highlighted Recommendations" in texts


def test_asd_export_retains_page_field_and_package_opens_as_docx():
    exported = create_report_docx(
        title="ASD Clinical Diagnostic Assessment Report",
        patient_name="Patient Name",
        report_type="evaluation",
        content="# Report Metadata (Front Page)\n\nReport title: Test",
    )

    with zipfile.ZipFile(BytesIO(exported.getvalue())) as archive:
        assert "word/document.xml" in archive.namelist()
        assert b"PAGE" in archive.read("word/footer1.xml")
