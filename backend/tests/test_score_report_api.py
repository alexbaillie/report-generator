"""End-to-end API tests for importing score reports and exporting them to Word."""
import base64
import io

import pytest
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base, get_db
from database.models import ReportTestResult
from main import app
from tests.score_report_samples import bar_chart_png, make_score_report_docx

PASTED = (
    "<table><tr><td>Index</td><td>Score</td></tr><tr><td>PASTED-ONE</td><td>101</td></tr></table>"
    "<table><tr><td>Subtest</td><td>Scaled</td></tr><tr><td>PASTED-TWO</td><td>9</td></tr></table>"
)


@pytest.fixture()
def api():
    """A client on a private in-memory DB; restores whatever override was installed before."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), Session
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        Base.metadata.drop_all(bind=engine)


def _template_id(client):
    existing = client.get("/api/templates/").json()
    if existing:
        return existing[0]["id"]
    response = client.post(
        "/api/templates/",
        json={"name": "T", "description": "d", "template_type": "psychoeducational", "content": "[]"},
    )
    return response.json()["id"]


def test_extract_returns_tables_and_graph_from_an_uploaded_word_report(api, tmp_path):
    client, _ = api
    path = make_score_report_docx(tmp_path / "wisc.docx")

    with open(path, "rb") as handle:
        response = client.post(
            "/api/score-reports/extract",
            files={"file": ("wisc.docx", handle, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )

    body = response.json()
    assert response.status_code == 200 and body["filename"] == "wisc.docx"
    assert [i["kind"] for i in body["items"]] == ["table", "table", "image"]
    assert body["items"][0]["caption"] == "WISC-V Primary Index Scores"


def test_extract_rejects_unsupported_and_corrupt_files_with_a_readable_message(api):
    client, _ = api

    txt = client.post("/api/score-reports/extract", files={"file": ("n.txt", b"hello", "text/plain")})
    bad = client.post("/api/score-reports/extract", files={"file": ("x.docx", b"not a zip", "application/octet-stream")})

    assert txt.status_code == 400 and "Word" in txt.json()["detail"]
    assert bad.status_code == 400 and "couldn't be opened" in bad.json()["detail"]


def test_attached_results_are_saved_summarised_and_exported_to_word(api):
    client, _ = api
    image = {"kind": "image", "caption": "Profile", "content_type": "image/png",
             "data_b64": base64.b64encode(bar_chart_png()).decode(), "width": 900, "height": 480}
    table = {"kind": "table", "caption": "Index scores", "rows": [["Index", "Score"], ["CHOSEN-ROW", "99"]]}

    created = client.post(
        "/api/reports/generate",
        json={
            "title": "Psycho-Educational Assessment - Boy",
            "patient_name": "Alex Test",
            "report_type": "psychoeducational",
            "template_id": _template_id(client),
            "additional_inputs": {"Report Metadata (Front Page)": "Client Full Name: Alex Test"},
            "test_results": [{"test_name": "WISC-V", "pasted_html": PASTED, "items": [table, image]}],
        },
    )
    assert created.status_code == 200
    report_id = created.json()["id"]

    summary = client.get(f"/api/reports/{report_id}/test-results").json()
    assert summary == [{"test_name": "WISC-V", "tables": 3, "images": 1}]  # 1 chosen + 2 pasted

    exported = client.get(f"/api/reports/{report_id}/export-docx")
    assert exported.status_code == 200
    doc = Document(io.BytesIO(exported.content))
    cells = {c.text for t in doc.tables for r in t.rows for c in r.cells}
    assert {"CHOSEN-ROW", "PASTED-ONE", "PASTED-TWO"} <= cells  # both pasted tables, not just the first
    assert len(doc.inline_shapes) >= 13  # template's 12 signature/sample images + the graph


def test_a_report_without_results_still_works_and_deleting_a_report_removes_its_results(api):
    client, Session = api
    plain = client.post(
        "/api/reports/generate",
        json={"title": "Standard Intake Assessment", "patient_name": "A", "report_type": "intake",
              "template_id": _template_id(client), "additional_inputs": {"Reason for Referral": "x"}},
    )
    assert plain.status_code == 200
    assert client.get(f"/api/reports/{plain.json()['id']}/test-results").json() == []

    with_results = client.post(
        "/api/reports/generate",
        json={"title": "Standard Intake Assessment", "patient_name": "B", "report_type": "intake",
              "template_id": _template_id(client), "additional_inputs": {"Reason for Referral": "x"},
              "test_results": [{"test_name": "WISC-V", "pasted_html": PASTED}]},
    ).json()["id"]
    with Session() as db:
        assert db.query(ReportTestResult).count() == 1

    assert client.delete(f"/api/reports/{with_results}").status_code == 200
    with Session() as db:
        assert db.query(ReportTestResult).count() == 0


def test_a_group_with_nothing_in_it_is_ignored(api):
    client, Session = api

    response = client.post(
        "/api/reports/generate",
        json={"title": "Standard Intake Assessment", "patient_name": "A", "report_type": "intake",
              "template_id": _template_id(client), "additional_inputs": {"Reason for Referral": "x"},
              "test_results": [{"test_name": "WISC-V", "pasted_html": "<p>no table here</p>"},
                               {"test_name": "", "pasted_html": PASTED}]},
    )

    assert response.status_code == 200
    with Session() as db:
        assert db.query(ReportTestResult).count() == 0
