"""Smoke test for a *packaged* backend (the PyInstaller build), run by CI on macOS
and usable locally on any OS:

    python .github/scripts/smoke_test_backend.py --base http://127.0.0.1:8000

Needs only httpx, python-docx and Pillow (all in backend/requirements.txt). Exits
non-zero, with a clear message, on the first failed check. Everything it creates
is deleted again.
"""
import argparse
import io
import re
import sys
import time
import zipfile

import httpx
from docx import Document
from PIL import Image, ImageDraw

failures = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)
    if not condition:
        failures.append(name)


def sample_score_report() -> bytes:
    chart = Image.new("RGB", (900, 480), "white")
    draw = ImageDraw.Draw(chart)
    for i, value in enumerate([104, 96, 88, 79, 91]):
        x0 = 80 + i * 150
        draw.rectangle([x0, 440 - value * 3, x0 + 90, 440], fill=(60, 110, 190))
    chart_png = io.BytesIO()
    chart.save(chart_png, format="PNG")

    document = Document()
    document.add_paragraph("WISC-V Primary Index Scores")
    table = document.add_table(rows=3, cols=3)
    for r, row in enumerate([["Index", "Score", "Percentile"], ["VCI", "104", "61"], ["VSI", "96", "39"]]):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    document.add_paragraph("Index Score Profile")
    document.add_picture(io.BytesIO(chart_png.getvalue()))
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def graph_pdf() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (900, 480), (60, 110, 190)).save(out, format="PDF")
    return out.getvalue()


def header_text(docx_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as archive:
        xml = " ".join(
            archive.read(n).decode("utf8") for n in archive.namelist() if re.fullmatch(r"word/header\d*\.xml", n)
        )
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml)).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--wait", type=int, default=120, help="seconds to wait for the backend")
    args = parser.parse_args()
    api = args.base.rstrip("/") + "/api"
    client = httpx.Client(timeout=180)

    deadline = time.time() + args.wait
    healthy = False
    while time.time() < deadline and not healthy:
        try:
            healthy = client.get(args.base + "/health").status_code == 200
        except httpx.HTTPError:
            time.sleep(1)
    check("backend is healthy", healthy)
    if not healthy:
        return 1

    templates = client.get(api + "/templates/").json()
    check("7 default templates auto-seeded", len(templates) == 7, f"{len(templates)} found")
    check("fresh install has no reports", client.get(api + "/reports/").json() == [])

    # Word score report -> tables + graph
    docx = client.post(api + "/score-reports/extract", files={"file": ("wisc.docx", sample_score_report())}).json()
    kinds = [i["kind"] for i in docx.get("items", [])]
    check("Word score report: table + graph extracted", kinds == ["table", "image"], str(kinds))

    # PDF score report -> graph rendered (pdfplumber + pypdfium2)
    pdf = client.post(
        api + "/score-reports/extract", files={"file": ("graph.pdf", graph_pdf(), "application/pdf")}
    ).json()
    check("PDF score report: graph rendered", any(i["kind"] == "image" for i in pdf.get("items", [])))

    bad = client.post(api + "/score-reports/extract", files={"file": ("x.docx", b"not a zip")})
    check("corrupt upload gives a readable 400", bad.status_code == 400 and "couldn't be opened" in bad.text)

    # Create + export a Psycho-Ed report with attached results, a pasted table, and a client name
    template = next(t for t in templates if t["name"].strip().startswith("Psycho-Educational Assessment - Boy"))
    pasted = "<table><tr><td>Index</td><td>Score</td></tr><tr><td>PASTED-ROW</td><td>7</td></tr></table>"
    created = client.post(
        api + "/reports/generate",
        json={
            "title": template["name"].strip(),
            "patient_name": "Smoke Test",
            "report_type": "psychoeducational",
            "template_id": template["id"],
            "additional_inputs": {"Report Metadata (Front Page)": "Client Full Name: Smoke Test"},
            "test_results": [{"test_name": "WISC-V", "pasted_html": pasted, "items": docx["items"]}],
        },
    )
    check("report with attached score results is created", created.status_code == 200, f"HTTP {created.status_code}")
    report_id = created.json()["id"]

    summary = client.get(f"{api}/reports/{report_id}/test-results").json()
    check("summary counts 2 tables + 1 graph", summary == [{"test_name": "WISC-V", "tables": 2, "images": 1}], str(summary))

    exported = client.get(f"{api}/reports/{report_id}/export-docx")
    check("Word export succeeds", exported.status_code == 200, f"{len(exported.content) // 1024} KB")
    doc = Document(io.BytesIO(exported.content))
    cells = {c.text for t in doc.tables for row in t.rows for c in row.cells}
    check("export holds the uploaded and pasted tables", {"VCI", "PASTED-ROW"} <= cells)
    check("export holds the graph", len(doc.inline_shapes) >= 13, f"{len(doc.inline_shapes)} images")
    header = header_text(exported.content)
    check("page header shows the client's name", "smoke" in header.lower() and "lastname" not in header.lower(), header[:70])

    plain = client.post(
        api + "/reports/generate",
        json={"title": "Standard Intake Assessment", "patient_name": "Smoke Test", "report_type": "intake",
              "template_id": templates[0]["id"], "additional_inputs": {"Reason for Referral": "Smoke."}},
    ).json()
    plain_export = client.get(f"{api}/reports/{plain['id']}/export-docx")
    check("plain (non-branded) Word export succeeds", plain_export.status_code == 200)

    for rid in (report_id, plain["id"]):
        client.delete(f"{api}/reports/{rid}")
    check("test reports cleaned up", client.get(api + "/reports/").json() == [])

    print(f"\n{'ALL CHECKS PASSED' if not failures else 'FAILED: ' + ', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
