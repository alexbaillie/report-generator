"""Changes from Emma's review of a Sunny Hill CDBC report (all names and numbers are made up)."""
import io
from types import SimpleNamespace

from docx import Document
from docx.oxml.ns import qn

from services.docx_exporter import _readable_dates, _structured_blocks, create_report_docx
from services.report_generator import build_section_prompt, wants_bullets

CDBC = "SunnyHill CDBC Psychology Assessment - Boy"
PSYCHED = "Psycho-Educational Assessment - Boy"


def export(title, content, **kwargs):
    stream = create_report_docx(title=title, patient_name="Alex Test", report_type="x", content=content, **kwargs)
    return Document(io.BytesIO(stream.getvalue()))


def lines(doc):
    return [p.text for p in doc.paragraphs]


def front(**fields):
    return "# Report Metadata (Front Page)\n" + "\n".join(f"{k}: {v}" for k, v in fields.items()) + "\n"


# --------------------------------------------------------------------------- #
# front page: team names, layout, dates
# --------------------------------------------------------------------------- #
def test_team_members_are_written_into_the_templates_team_lines():
    doc = export(CDBC, front(**{
        "Client full name": "Alex Test", "Psychologist": "Rachel Weber", "Social worker": "Ann Lee",
        "Assessing Clinician": "Sam Poe",
    }))
    text = lines(doc)
    assert "\tPsychologist:\tRachel Weber, Ph.D., R.Psych." in text
    assert "\tSocial worker:\tAnn Lee" in text
    assert "\tAssessing Clinician*:\tSam Poe" in text        # the template's asterisk is kept
    assert "\tCase manager:  " in text                        # no name given: the line is left as it was


def test_typed_credentials_are_not_added_twice():
    doc = export(CDBC, front(**{"Client full name": "Alex Test", "Psychologist": "Rachel Weber, Ph.D., R.Psych."}))
    assert "\tPsychologist:\tRachel Weber, Ph.D., R.Psych." in lines(doc)


def test_an_older_report_with_one_team_box_still_fills_the_team_lines():
    doc = export(CDBC, front(**{
        "Client full name": "Alex Test", "Sunny Hill team": "Psychologist: Rachel Weber, Case manager: Bo Kim",
    }))
    text = lines(doc)
    assert "\tPsychologist:\tRachel Weber, Ph.D., R.Psych." in text
    assert "\tCase manager:\tBo Kim" in text


def test_front_page_lines_keep_the_templates_tab_layout_and_readable_dates():
    doc = export(CDBC, front(**{
        "Client full name": "Alex Test", "Chart number": "123-456-789", "Date of birth": "2015-03-08",
        "Date(s) of assessment": "2026-10-15", "Age at assessment": "11 years",
    }))
    text = lines(doc)
    assert "\tCHART NUMBER:\t123-456-789" in text
    assert "\tDATE OF BIRTH:\tMarch 8, 2015" in text
    assert "\tDATE OF ASSESSMENT:\tOctober 15, 2026" in text
    assert "\tAGE AT ASSESSMENT:\t11 years" in text


def test_dates_are_only_reworded_when_they_are_iso_dates():
    assert _readable_dates("2015-03-08") == "March 8, 2015"
    assert _readable_dates("2026-09-01, 2026-09-08") == "September 1, 2026 and September 8, 2026"
    assert _readable_dates("2026-09-01, 2026-09-08, 2026-09-15") == "September 1, 2026; September 8, 2026 and September 15, 2026"
    assert _readable_dates("March 8, 2015") == "March 8, 2015"
    assert _readable_dates("2015-13-40") == "2015-13-40"


# --------------------------------------------------------------------------- #
# bullet points, sub-headings, never italic
# --------------------------------------------------------------------------- #
CONCERNS = (
    "# Presenting Concerns (as provided by parents)\n"
    "Attention\n- Has difficulty planning tasks.\n- Follows requests about 80% of the time.\n"
    "Anxiety\n- No concerns with anxiety were indicated.\n"
)


def generated_paragraphs(doc, after_heading):
    body = list(doc.element.body)
    start = next(i for i, el in enumerate(body) if el.tag == qn("w:p") and "".join(
        t.text or "" for t in el.iter(qn("w:t"))).strip().lower() == after_heading.lower())
    out = []
    for el in body[start + 1:start + 8]:
        if el.tag == qn("w:p") and "".join(t.text or "" for t in el.iter(qn("w:t"))).strip():
            out.append(el)
    return out


def test_generated_bullets_become_real_word_bullets_under_plain_headings():
    doc = export(CDBC, front(**{"Client full name": "Alex Test"}) + CONCERNS)
    paragraphs = generated_paragraphs(doc, "Presenting Concerns as provided by parents")
    texts = ["".join(t.text or "" for t in p.iter(qn("w:t"))) for p in paragraphs]
    assert texts[:5] == [
        "Attention", "Has difficulty planning tasks.", "Follows requests about 80% of the time.",
        "Anxiety", "No concerns with anxiety were indicated.",
    ]
    is_bullet = [p.find(qn("w:pPr")) is not None and p.find(qn("w:pPr")).find(qn("w:numPr")) is not None
                 for p in paragraphs[:5]]
    assert is_bullet == [False, True, True, False, True]
    assert not any(t.startswith("-") for t in texts)           # no literal dashes left over
    heading_run = paragraphs[0].find(qn("w:r")).find(qn("w:rPr"))
    assert heading_run is not None and heading_run.find(qn("w:b")) is not None   # headings are bold


def test_generated_text_is_never_italic():
    doc = export(CDBC, front(**{"Client full name": "Alex Test"}) + CONCERNS)
    for p in generated_paragraphs(doc, "Presenting Concerns as provided by parents")[:5]:
        assert not list(p.iter(qn("w:i"))), "generated paragraph is italic"
        assert not list(p.iter(qn("w:iCs")))
    # bullets are plain text too (the template's own first bullet happens to be bold)
    for p in generated_paragraphs(doc, "Presenting Concerns as provided by parents")[1:3]:
        assert not list(p.iter(qn("w:b"))), "bullet is bold"


def test_dash_bullets_in_other_templates_become_bullets_too():
    doc = export(PSYCHED, front(**{"Client full name": "Alex Test"}) + "# Reason for Referral\n- First point.\n- Second point.\n")
    assert not any(line.startswith("- ") for line in lines(doc))


def test_numbered_lists_are_left_alone_and_plain_paragraphs_stay_paragraphs():
    assert _structured_blocks("1. First\n2. Second\nA normal sentence. Another one.") == [
        ("para", "1. First"), ("para", "2. Second"), ("para", "A normal sentence. Another one."),
    ]


def test_a_long_line_before_bullets_is_not_mistaken_for_a_heading():
    blocks = _structured_blocks("Joe struggles with planning and following instructions at school.\n- Item")
    assert blocks[0][0] == "para"


# --------------------------------------------------------------------------- #
# the prompt asks for bullets only where the clinic wants them
# --------------------------------------------------------------------------- #
def template(name):
    return SimpleNamespace(name=name, template_type="x", content="")


def test_bullets_are_requested_for_the_cdbc_background_sections_only():
    assert wants_bullets(template(CDBC), "Presenting Concerns (as provided by parents)")
    assert wants_bullets(template(CDBC), "Family History")
    assert wants_bullets(template(CDBC), "Previous Assessments & Interventions")
    assert not wants_bullets(template(CDBC), "Reason for Referral")
    assert not wants_bullets(template(PSYCHED), "Family History")

    prompt = build_section_prompt(template(CDBC), "Family History", [], {"Lives with": "mom and dad"})
    assert 'starting with "- "' in prompt and "Do not write paragraphs" in prompt
    assert "well-structured paragraph" not in prompt
    plain = build_section_prompt(template(PSYCHED), "Family History", [], {"Lives with": "mom and dad"})
    assert "well-structured paragraph" in plain


# --------------------------------------------------------------------------- #
# BASC-3 results land under the template's BASC-3 block
# --------------------------------------------------------------------------- #
def test_basc_tables_go_under_the_basc_heading_not_another_test():
    table = {"kind": "table", "caption": "BASC-3 UNIQUE CAPTION",
             "rows": [["Scale", "Parent Report"], ["Externalizing Problems", "Average"], ["Atypicality", "At-Risk"]]}
    report = []
    doc = export(CDBC, front(**{"Client full name": "Alex Test"}),
                 test_results=[{"test_name": "BASC-3", "items": [table]}], fill_report=report)
    assert report[0]["result"] == "replaced"
    body = list(doc.element.body)
    texts = ["".join(t.text or "" for t in el.iter(qn("w:t"))).strip() if el.tag == qn("w:p") else None for el in body]
    caption = texts.index("BASC-3 UNIQUE CAPTION")
    heading_before = next(t for t in reversed(texts[:caption]) if t and len(t) < 60 and t.startswith(("BASC-3", "Bayley", "SCARED", "Achenbach")))
    assert heading_before == "BASC-3 Scales"


def test_the_cdbc_seed_has_one_field_per_team_role():
    import json
    from pathlib import Path

    for name in ("06_cdbc_boy.json", "07_cdbc_girl.json"):
        seed = json.loads((Path(__file__).parent.parent / "seeds" / name).read_text(encoding="utf-8"))
        labels = [f["label"] for f in seed["content"][0]["fields"]]
        assert "Sunny Hill team" not in labels
        assert {"Psychologist", "Case manager", "Social worker", "Physiotherapist"} <= set(labels)


def test_presenting_concerns_are_generated_one_area_at_a_time_under_the_forms_own_headings(monkeypatch):
    import asyncio

    from services import report_generator

    prompts = []

    async def fake_generate(prompt, max_tokens=0):
        prompts.append(prompt)
        return "- A fact about it."

    monkeypatch.setattr(report_generator, "generate_text", fake_generate)
    inputs = {
        "Attention / Impulsivity / Activity / Executive Functions": "forgets things",
        "Anxiety / Mood": "",                 # nothing given: left out, not invented
        "Social concerns": "plays alone",
        "Learning": "No concerns",          # a plain "no concerns" is written without asking the model
    }
    text = asyncio.run(report_generator.generate_by_area(
        template(CDBC), "Presenting Concerns (as provided by parents)", [], inputs))
    assert text == (
        "Attention\n- A fact about it.\nSocial concerns\n- A fact about it.\n"
        "Learning\n- No concerns with learning were indicated."
    )
    assert len(prompts) == 2 and "plays alone" in prompts[1] and "forgets things" not in prompts[1]
    assert report_generator.area_heading("Anxiety / Mood") == "Anxiety"
