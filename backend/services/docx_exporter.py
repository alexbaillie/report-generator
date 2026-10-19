"""Template-preserving Word export for completed reports."""

from __future__ import annotations

from copy import deepcopy
from html import unescape
from io import BytesIO
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

from services.docx_test_results import apply_test_results, keep_when_section_is_generated
from services.test_pruning import prune_unadministered


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
ASD_TEMPLATE_PATH = _TEMPLATE_DIR / "asd_school_age_boy_template.docx"
CDBC_BOY_TEMPLATE_PATH = _TEMPLATE_DIR / "sunnyhill_cdbc_boy_template.docx"
CDBC_GIRL_TEMPLATE_PATH = _TEMPLATE_DIR / "sunnyhill_cdbc_girl_template.docx"
PSYCHED_BOY_TEMPLATE_PATH = _TEMPLATE_DIR / "psyched_boy_template.docx"
PSYCHED_GIRL_TEMPLATE_PATH = _TEMPLATE_DIR / "psyched_girl_template.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}


class DocxExportError(RuntimeError):
    """Raised when a report cannot be exported with a configured DOCX template."""


ASD_SECTION_TARGETS: Sequence[Tuple[str, Sequence[str]]] = (
    ("reason for referral", ("Reason for Referral",)),
    ("summary & conclusions", ("Summary & Conclusions",)),
    ("asd diagnostic criteria", ("ASD:",)),
    ("diagnostic considerations", ("All reports:",)),
    ("highlighted recommendations", ("Highlighted Recommendations",)),
    ("goals for the present assessment", ("Goals for the Present Assessment",)),
    ("presenting concerns", ("Presenting Concerns",)),
    ("family history", ("Family History",)),
    ("developmental & medical history", ("Developmental & Medical History",)),
    ("educational history", ("Educational History",)),
    ("previous assessments & interventions", ("Previous Assessments & Interventions",)),
    ("tests administered", ("Tests Administered",)),
    ("general behavioural observations", ("General Behavioural Observations",)),
    ("autism characteristics", ("Autism Characteristics",)),
    ("rating scales & adaptive behaviour", ("Adaptive Behaviour",)),
    ("additional recommendations", ("Additional Recommendations",)),
    ("appendices", ("APPENDIX 1: Interpretation of Test Results",)),
)


FRONT_TABLE_LABELS: Mapping[str, Sequence[str]] = {
    "name": ("client full name", "preferred name", "name"),
    "date of birth": ("date of birth",),
    "dates of evaluation": ("date(s) of evaluation", "dates of evaluation", "date(s) of assessment"),
    "date of evaluation": ("date(s) of evaluation", "dates of evaluation", "date(s) of assessment"),
    "date of assessment": ("date(s) of assessment", "dates of assessment", "date(s) of evaluation"),
    "date of report": ("date of report",),
    "chronological age": ("chronological age", "age at assessment"),
    "examiner": ("examiner", "assessing psychologist"),
    "copies to": ("copies to",),
}


# The Sunny Hill CDBC template uses ALL-CAPS/bold headings and a paragraph-based
# (not table) front page. Map each generated report section to the heading in the
# Word template whose following content it should replace.
CDBC_SECTION_TARGETS: Sequence[Tuple[str, Sequence[str]]] = (
    ("diagnostic summary (dsm-5-tr)", ("DIAGNOSTIC SUMMARY (DSM-5-TR)",)),
    ("summary of findings", ("SUMMARY OF FINDINGS",)),
    ("summary of assessment results", ("Summary of Assessment Results",)),
    ("highlighted recommendations", ("RECOMMENDATIONS",)),
    ("resources", ("RESOURCES",)),
    ("reason for referral", ("REASON FOR REFERRAL",)),
    ("sources of information", ("SOURCES OF INFORMATION",)),
    ("presenting concerns (as provided by parents)", ("Presenting Concerns as provided by parents",)),
    ("areas of relative strength & interests", ("Areas of Relative Strength and Interests",)),
    ("family history", ("Family History",)),
    ("developmental & medical history", ("Developmental & Medical History",)),
    ("educational history", ("Educational History",)),
    ("previous assessments & interventions", ("Previous Assessments & Interventions",)),
    ("behavioural observations", ("BEHAVIOURAL OBSERVATIONS",)),
    ("tests administered", ("TESTS ADMINISTERED",)),
    ("cognitive, memory & academic results", ("General Cognitive Abilities",)),
)


# The Psycho-Educational template has a table-based front page (same shape as
# ASD) and mostly-exact heading matches; a few sections cover several
# subsections in the Word doc (e.g. all the cognitive score tables between
# "Test Results" and "Academic Abilities") — anchoring on the first heading in
# that span means the generated content replaces the whole span, consistent
# with how ASD/CDBC handle "Recommendations"-style catch-all sections.
PSYCHED_SECTION_TARGETS: Sequence[Tuple[str, Sequence[str]]] = (
    ("reason for referral", ("Reason for Referral",)),
    ("presenting concerns (as reported by parents)", ("Presenting Concerns as Reported by Parents",)),
    ("teacher's perspective", ("Teacher's Perspective",)),
    ("child's perspective", ("Joe's Perspective", "Jane's Perspective")),
    ("areas of relative strength & interests", ("Areas of Relative Strength & Interests",)),
    ("family history", ("Family History",)),
    ("developmental & medical history", ("Developmental & Medical History",)),
    ("educational history", ("Educational History",)),
    ("previous assessments & interventions", ("Previous Assessments & Interventions",)),
    ("tests administered", ("Tests Administered",)),
    ("behavioural observations", ("Behavioural Observations",)),
    ("cognitive & neuropsychological results", ("Test Results",)),
    ("academic achievement", ("Academic Abilities",)),
    ("adaptive, behavioural & social-emotional functioning", ("Adaptive Behaviour",)),
    ("summary of assessment results", ("Summary of Assessment Results",)),
    ("diagnoses (dsm-5-tr)", ("Descriptors/Diagnoses (DSM-5-TR)",)),
    ("highlighted recommendations", ("Highlighted Recommendations",)),
    ("recommendations", ("Recommendations",)),
)


# Front-page paragraphs like "DATE OF BIRTH:" get the metadata value appended.
CDBC_FRONT_LABELS: Mapping[str, Sequence[str]] = {
    "chart number": ("chart number",),
    "date of birth": ("date of birth",),
    "date of assessment": ("date(s) of assessment", "dates of assessment", "date of assessment"),
    "age at assessment": ("age at assessment", "chronological age"),
    "date of report": ("date of report",),
    "date of conference": ("date of conference",),
}


CDBC_DATE_LABELS = frozenset({"date of birth", "date of assessment", "date of report", "date of conference"})


def supports_asd_template(title: str) -> bool:
    normalized = _normalize(title)
    return "asd" in normalized or "autism" in normalized


def supports_cdbc_template(title: str) -> bool:
    normalized = _normalize(title)
    return "cdbc" in normalized or "sunny hill" in normalized or "sunnyhill" in normalized


def supports_psyched_template(title: str) -> bool:
    normalized = _normalize(title)
    return "psycho-educational" in normalized or "psychoeducational" in normalized or "psyched" in normalized


def has_branded_template(title: str) -> bool:
    """True if this title matches a real branded Word template (ASD/CDBC/PsychEd).
    Every report is still exportable via the generic fallback below — this only
    tells you whether the output matches a clinic's specific letterhead/layout."""
    return supports_asd_template(title) or supports_cdbc_template(title) or supports_psyched_template(title)


def _select_profile(title: str):
    """Return (template_path, section_targets, front_page_filler) for the title,
    or None if there's no branded template — the caller falls back to a plain,
    generic export in that case."""
    if supports_cdbc_template(title):
        template = CDBC_GIRL_TEMPLATE_PATH if "girl" in _normalize(title) else CDBC_BOY_TEMPLATE_PATH
        return template, CDBC_SECTION_TARGETS, _fill_front_page_cdbc
    if supports_psyched_template(title):
        template = PSYCHED_GIRL_TEMPLATE_PATH if "girl" in _normalize(title) else PSYCHED_BOY_TEMPLATE_PATH
        return template, PSYCHED_SECTION_TARGETS, _fill_front_page_psyched
    if supports_asd_template(title):
        return ASD_TEMPLATE_PATH, ASD_SECTION_TARGETS, _fill_front_page_asd
    return None


def export_filename(title: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("._")
    return f"{safe or 'report'}.docx"


def parse_markdown_sections(content: str) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None

    for raw_line in (content or "").replace("\r\n", "\n").split("\n"):
        match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", raw_line)
        if match:
            current = _normalize(match.group(1))
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(raw_line)

    if not sections and content.strip():
        sections["report"] = [content.strip()]

    return {
        name: "\n".join(lines).strip()
        for name, lines in sections.items()
        if "\n".join(lines).strip()
    }


def parse_markdown_sections_ordered(content: str) -> List[Tuple[str, str]]:
    """Like parse_markdown_sections, but keeps the original heading text and
    document order — used for the generic export, which renders real headings
    rather than looking sections up by normalized key."""
    sections: List[Tuple[str, List[str]]] = []
    for raw_line in (content or "").replace("\r\n", "\n").split("\n"):
        match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", raw_line)
        if match:
            sections.append((match.group(1).strip(), []))
            continue
        if sections:
            sections[-1][1].append(raw_line)

    if not sections and content.strip():
        return [("Report", [content.strip()])]

    return [
        (heading, "\n".join(lines).strip())
        for heading, lines in sections
        if "\n".join(lines).strip()
    ]


def create_report_docx(
    *,
    title: str,
    patient_name: str,
    report_type: str,
    content: str,
    test_results: Optional[Sequence[Mapping]] = None,
    fill_report: Optional[List[dict]] = None,
    tests_administered: Optional[Sequence[str]] = None,
) -> BytesIO:
    """``test_results``: uploaded/pasted score tables and graphs per test, placed
    under that test's section by ``apply_test_results``. ``fill_report``, if given,
    receives a per-test account of what was done (see ``apply_test_results``)."""
    profile = _select_profile(title)
    if profile is None:
        generic = _create_generic_report_docx(
            title=title, patient_name=patient_name, report_type=report_type, content=content
        )
        return apply_test_results(generic, test_results, (), fill_report)
    template_path, section_targets, fill_front_page = profile
    if not template_path.is_file():
        raise DocxExportError("The Word template for this report type is missing from the application.")

    with ZipFile(template_path, "r") as source:
        document_xml = source.read("word/document.xml")

    root = etree.fromstring(document_xml)
    sections = parse_markdown_sections(content)
    metadata = _extract_labeled_values(sections.get("report metadata (front page)", ""))

    fill_front_page(root, title=title, patient_name=patient_name, metadata=metadata)
    pruned_entry = _prune_unadministered_tests(root, section_targets, sections, tests_administered, test_results)
    _fill_generated_sections(root, sections, section_targets, _bullet_prototype(root, template_path))

    # Make the leftover template boilerplate readable: use the real name instead
    # of the "Jane/Joe Lastname" placeholders, and drop instructional highlighting.
    clean_name = _clean_name(metadata.get("client full name") or metadata.get("name") or patient_name)
    _replace_placeholder_names(root, clean_name)
    _strip_highlighting(root)

    patched_xml = etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        standalone=True,
    )
    patched = _write_patched_package(
        patched_xml, template_path, _patched_header_footer_parts(template_path, clean_name)
    )
    result = apply_test_results(patched, test_results, section_targets, fill_report)
    if pruned_entry is not None and fill_report is not None:
        fill_report.append(pruned_entry)  # after the per-test entries, which tests index from the front
    return result


def _prune_unadministered_tests(root, section_targets, sections, tests_administered, test_results) -> Optional[dict]:
    """Take the tests that were not given out of the template (its lists and result blocks).
    A test counts as given if it was added to the report (with or without results). With no
    tests recorded at all nothing is removed: we cannot tell what was administered."""
    names = list(tests_administered or [])
    names += [group.get("test_name") or "" for group in test_results or []]
    names += [key[len("test table:"):].strip() for key in sections if key.startswith("test table:")]
    names = [name for name in names if name.strip()]
    if not names:
        return None
    protected = [alias for _, aliases in section_targets for alias in aliases] + ["Tests Administered"]
    pruned = prune_unadministered(root, names, protected)
    if not pruned:
        return None
    removed = [label if len(label) <= 70 else label[:67] + "..." for label in pruned["removed"]]
    return {
        "test_name": "Tests not marked as administered",
        "result": "pruned",
        "removed": removed[:30] + ([f"... and {len(removed) - 30} more"] if len(removed) > 30 else []),
    }


def _create_generic_report_docx(
    *,
    title: str,
    patient_name: str,
    report_type: str,
    content: str,
) -> BytesIO:
    """Plain, cleanly-formatted export for report types with no branded Word
    template (e.g. Standard Intake, Neuropsych) — a real heading per section
    instead of the clinic's specific letterhead/layout. Every report type is
    exportable this way; only some also get the branded version."""
    from docx import Document as _Document  # local import: only needed here

    document = _Document()
    ordered_sections = parse_markdown_sections_ordered(content)

    document.add_heading(title or "Psychological Report", level=0)

    info = document.add_paragraph()
    info.add_run(f"Patient: {patient_name or 'Unknown'}").bold = True
    if report_type:
        document.add_paragraph(f"Report type: {report_type.replace('_', ' ').title()}")

    # The front-page metadata section is structured "Label: value" lines (the
    # same convention the branded exporters read) — surface it as a compact
    # field list rather than rendering it as a regular narrative section.
    metadata_heading = next(
        (h for h, _ in ordered_sections if _normalize(h) in {"report metadata (front page)", "front page"}),
        None,
    )
    if metadata_heading:
        metadata_content = next(c for h, c in ordered_sections if h == metadata_heading)
        for label, value in _extract_labeled_values(metadata_content).items():
            if label in {"report title", "confidentiality statement"}:
                continue
            document.add_paragraph(f"{label.title()}: {value}")

    document.add_paragraph(
        "This is a confidential report. AI-generated content is a draft and must be "
        "reviewed by a licensed clinician before use."
    )

    for heading, section_content in ordered_sections:
        if heading == metadata_heading:
            continue
        document.add_heading(heading, level=1)
        for block in _content_blocks(section_content):
            document.add_paragraph(block)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer


def _write_patched_package(
    document_xml: bytes, template_path: Path, replacements: Optional[Mapping[str, bytes]] = None
) -> BytesIO:
    replacements = replacements or {}
    output = BytesIO()
    with ZipFile(template_path, "r") as source, ZipFile(
        output, "w", compression=ZIP_DEFLATED
    ) as destination:
        for info in source.infolist():
            if info.filename == "word/document.xml":
                payload = document_xml
            elif info.filename in replacements:
                payload = replacements[info.filename]
            else:
                payload = source.read(info.filename)
            destination.writestr(info, payload)
    output.seek(0)
    return output


def _patched_header_footer_parts(template_path: Path, full_name: str) -> Dict[str, bytes]:
    """The running header ("... Report for JOE LASTNAME") lives in its own part,
    not document.xml, so it needs the same placeholder-name swap as the body."""
    if not full_name:
        return {}
    parts: Dict[str, bytes] = {}
    with ZipFile(template_path, "r") as source:
        for name in source.namelist():
            if re.fullmatch(r"word/(header|footer)\d*\.xml", name):
                part_root = etree.fromstring(source.read(name))
                _replace_placeholder_names(part_root, full_name)
                parts[name] = etree.tostring(
                    part_root, encoding="UTF-8", xml_declaration=True, standalone=True
                )
    return parts


def _fill_front_page_table_based(
    root,
    *,
    title: str,
    patient_name: str,
    metadata: Mapping[str, str],
    title_anchor: str,
) -> None:
    """Shared front-page filler for templates with a title paragraph, a
    confidentiality sentence, and a labelled front-page table (ASD, PsychEd)."""
    paragraphs = root.xpath("/w:document/w:body/w:p", namespaces=NS)
    report_title = metadata.get("report title") or title
    title_paragraph = _find_paragraph(paragraphs, (title_anchor,))
    if title_paragraph is not None:
        _set_element_text(title_paragraph, report_title)

    confidentiality = metadata.get("confidentiality statement")
    if confidentiality:
        for paragraph in paragraphs:
            if _normalize(_element_text(paragraph)).startswith("this is a confidential report"):
                _set_element_text(paragraph, confidentiality)
                break

    tables = root.xpath("/w:document/w:body/w:tbl", namespaces=NS)
    if not tables:
        return

    effective_metadata = dict(metadata)
    if patient_name and _normalize(patient_name) not in {"", "patient name"}:
        effective_metadata.setdefault("client full name", patient_name)

    for cell in tables[0].xpath(".//w:tc", namespaces=NS):
        original = _element_text(cell).strip()
        if ":" not in original:
            continue
        source_label = _normalize(original.split(":", 1)[0])
        aliases = FRONT_TABLE_LABELS.get(source_label)
        if not aliases:
            continue
        value = _first_value(effective_metadata, aliases)
        if not value:
            continue
        label_text = original.split(":", 1)[0].strip()
        _set_cell_text(cell, f"{label_text}: {value}")


def _fill_front_page_asd(
    root,
    *,
    title: str,
    patient_name: str,
    metadata: Mapping[str, str],
) -> None:
    _fill_front_page_table_based(
        root,
        title=title,
        patient_name=patient_name,
        metadata=metadata,
        title_anchor="Clinical Diagnostic Assessment Report",
    )


def _fill_front_page_psyched(
    root,
    *,
    title: str,
    patient_name: str,
    metadata: Mapping[str, str],
) -> None:
    _fill_front_page_table_based(
        root,
        title=title,
        patient_name=patient_name,
        metadata=metadata,
        title_anchor="Psycho-Educational Assessment Report",
    )


def _fill_front_page_cdbc(
    root,
    *,
    title: str,
    patient_name: str,
    metadata: Mapping[str, str],
) -> None:
    paragraphs = root.xpath("/w:document/w:body/w:p", namespaces=NS)

    report_title = metadata.get("report title")
    if report_title:
        for paragraph in paragraphs:
            if _normalize(_element_text(paragraph)) == "psychology assessment report":
                _set_element_text(paragraph, report_title)
                break

    # The client's name is a stand-alone ALL-CAPS paragraph like "JANE LASTNAME".
    name = metadata.get("client full name") or metadata.get("name")
    if (not name) and patient_name and _normalize(patient_name) not in {"", "patient name"}:
        name = patient_name
    if name:
        for paragraph in paragraphs:
            normalized = _normalize(_element_text(paragraph))
            if normalized.endswith("lastname") and ":" not in normalized:
                _set_element_text(paragraph, name.upper())
                break
        # Swap the placeholder name inside the confidentiality sentence too.
        for paragraph in paragraphs:
            text = _element_text(paragraph)
            if _normalize(text).startswith("this is a confidential report"):
                swapped = re.sub(r"(?i)\b(?:jane|joe)\s+lastname\b", name, text)
                if swapped != text:
                    _set_element_text(paragraph, swapped)
                break

    # Labelled front-page paragraphs ("DATE OF BIRTH:") get their value after a tab,
    # keeping the template's own tab-aligned layout.
    for paragraph in paragraphs:
        text = _element_text(paragraph).strip()
        if ":" not in text:
            continue
        source_label = _normalize(text.split(":", 1)[0])
        aliases = CDBC_FRONT_LABELS.get(source_label)
        if not aliases:
            continue
        value = _first_value(metadata, aliases)
        if not value:
            continue
        if source_label in CDBC_DATE_LABELS:
            value = _readable_dates(value)
        _set_labelled_value(paragraph, text.split(":", 1)[0].strip(), value)

    _fill_team(paragraphs, metadata)


def _leading_tabs(paragraph) -> int:
    count = 0
    for run in paragraph.findall(f"{{{W_NS}}}r"):
        for child in run:
            if child.tag == f"{{{W_NS}}}tab":
                count += 1
            elif child.tag == f"{{{W_NS}}}t" and (child.text or "").strip():
                return count
    return count


def _set_labelled_value(paragraph, label: str, value: str) -> None:
    """"<tabs>LABEL:<tab>value", with the paragraph's own leading tabs and formatting."""
    _set_element_text(paragraph, "\t" * _leading_tabs(paragraph) + f"{label}:\t{value}")


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December")


def _readable_dates(value: str) -> str:
    """"2015-03-08" -> "March 8, 2015"; several dates read as a list. Anything that
    isn't made only of ISO dates is left as the person typed it."""
    parts = [part for part in re.split(r"\s*[;,]\s*", value.strip()) if part]
    matches = [re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", part) for part in parts]
    if not parts or not all(matches) or any(not 1 <= int(m.group(2)) <= 12 for m in matches):
        return value
    words = [f"{_MONTHS[int(m.group(2)) - 1]} {int(m.group(3))}, {m.group(1)}" for m in matches]
    if len(words) <= 2:
        return " and ".join(words)
    return "; ".join(words[:-1]) + " and " + words[-1]


# Sunny Hill team lines on the front page: template label -> metadata labels that fill it.
CDBC_TEAM_ROLES: Mapping[str, Sequence[str]] = {
    "developmental pediatrician": ("developmental pediatrician", "developmental paediatrician"),
    "psychologist": ("psychologist",),
    "assessing clinician": ("assessing clinician",),
    "speech language pathologist": ("speech language pathologist", "slp"),
    "occupational therapist": ("occupational therapist", "ot"),
    "physiotherapist": ("physiotherapist", "physical therapist", "pt"),
    "social worker": ("social worker",),
    "case manager": ("case manager",),
}
PSYCHOLOGIST_CREDENTIALS = ", Ph.D., R.Psych."


def _team_values(metadata: Mapping[str, str]) -> Dict[str, str]:
    """Team members by role. One field per role, or (older reports) a single "Sunny
    Hill team" box with "Role: Name" lines."""
    values: Dict[str, str] = {}
    free_text = metadata.get("sunny hill team", "")
    if free_text:
        for role, name in _extract_labeled_values(free_text.replace(" - ", ": ").replace(",", "\n")).items():
            values[role] = name
    for role, aliases in CDBC_TEAM_ROLES.items():
        value = _first_value(metadata, aliases) or _first_value(values, aliases)
        if value:
            values[role] = value
    return {role: values[role] for role in CDBC_TEAM_ROLES if role in values}


def _fill_team(paragraphs, metadata: Mapping[str, str]) -> None:
    team = _team_values(metadata)
    if not team:
        return
    in_team = False
    for paragraph in paragraphs:
        text = _element_text(paragraph).strip()
        if not in_team:
            in_team = _normalize(text) == "sunny hill team"
            continue
        if ":" not in text or text.startswith("*"):
            break  # past the team list
        label = text.split(":", 1)[0].strip()
        value = team.get(_normalize(label.rstrip("*")))
        if not value:
            continue
        if _normalize(label) == "psychologist" and not re.search(r"(?i)ph\.?\s?d|psy\.?\s?d|r\.?\s?psych", value):
            value += PSYCHOLOGIST_CREDENTIALS
        _set_labelled_value(paragraph, label, value)


def _fill_generated_sections(root, sections: Mapping[str, str], section_targets, bullet: Optional[dict] = None) -> None:
    body = root.find(f"{{{W_NS}}}body")
    if body is None:
        raise DocxExportError("The Word template has no document body.")

    paragraphs = body.xpath("./w:p", namespaces=NS)
    located: List[Tuple[int, str, object]] = []
    children = list(body)

    for section_name, aliases in section_targets:
        paragraph = _find_paragraph(paragraphs, aliases)
        if paragraph is not None:
            located.append((children.index(paragraph), section_name, paragraph))

    located.sort(key=lambda item: item[0])
    for position, (_, section_name, heading) in enumerate(located):
        generated = sections.get(section_name)
        if not generated:
            continue

        current_children = list(body)
        start_index = current_children.index(heading)
        if position + 1 < len(located):
            end_index = current_children.index(located[position + 1][2])
        else:
            end_index = len(current_children)

        interval = current_children[start_index + 1 : end_index]
        style_source = next(
            (
                element
                for element in interval
                if element.tag == f"{{{W_NS}}}p" and _element_text(element).strip()
            ),
            heading,
        )
        for position_in_interval, element in enumerate(interval):
            if element.tag == f"{{{W_NS}}}p" and not keep_when_section_is_generated(interval, position_in_interval):
                body.remove(element)

        anchor = heading
        for kind, block in _structured_blocks(generated):
            new_paragraph = _paragraph_element(style_source, block, kind, bullet)
            anchor.addnext(new_paragraph)
            anchor = new_paragraph


def _clean_name(name: str) -> str:
    """Patient name for substitution — parentheticals like "(test)" removed."""
    name = re.sub(r"\s*\(.*?\)\s*", " ", name or "").strip()
    if _normalize(name) in {"", "patient name"}:
        return ""
    return name


def _replace_placeholder_names(root, full_name: str) -> None:
    """Swap the template's "Jane/Joe Lastname" placeholders for the real name
    throughout the document, preserving ALL-CAPS styling where used."""
    if not full_name:
        return
    parts = full_name.split()
    first, last = parts[0], (parts[-1] if len(parts) > 1 else "")

    def _cased(match, replacement):
        return replacement.upper() if match.group(0).isupper() else replacement

    for node in root.iter(f"{{{W_NS}}}t"):
        if not node.text:
            continue
        text = re.sub(r"(?i)\b(?:jane|joe)\s+lastname\b", lambda m: _cased(m, full_name), node.text)
        text = re.sub(r"(?i)\b(?:jane|joe)\b", lambda m: _cased(m, first), text)
        if last:
            text = re.sub(r"(?i)\blastname\b", lambda m: _cased(m, last), text)
        if text != node.text:
            node.text = text


def _strip_highlighting(root) -> None:
    """Remove text highlighting and run-level shading (the yellow placeholder marks)."""
    for highlight in list(root.iter(f"{{{W_NS}}}highlight")):
        parent = highlight.getparent()
        if parent is not None:
            parent.remove(highlight)
    for shading in list(root.iter(f"{{{W_NS}}}shd")):
        parent = shading.getparent()
        if parent is not None and parent.tag == f"{{{W_NS}}}rPr":
            parent.remove(shading)


def _extract_labeled_values(text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in (text or "").splitlines():
        match = re.match(r"^\s*([^:#]{2,80}?):\s*(.+?)\s*$", line)
        if match and match.group(2).strip():
            values[_normalize(match.group(1))] = match.group(2).strip()
    return values


def _first_value(values: Mapping[str, str], aliases: Iterable[str]) -> Optional[str]:
    for alias in aliases:
        value = values.get(_normalize(alias))
        if value:
            return value
    return None


def _find_paragraph(paragraphs: Iterable, aliases: Iterable[str]):
    expected = {_normalize(alias) for alias in aliases}
    for paragraph in paragraphs:
        if _normalize(_element_text(paragraph)) in expected:
            return paragraph
    return None


def _element_text(element) -> str:
    return "".join(element.xpath(".//w:t/text()", namespaces=NS))


def _set_element_text(element, text: str) -> None:
    paragraph_properties = element.find(f"{{{W_NS}}}pPr")
    run_properties = element.find(f".//{{{W_NS}}}rPr")
    for child in list(element):
        if child is not paragraph_properties:
            element.remove(child)

    run = etree.Element(f"{{{W_NS}}}r")
    if run_properties is not None:
        run.append(deepcopy(run_properties))
    for index, part in enumerate(text.split("\t")):
        if index:
            etree.SubElement(run, f"{{{W_NS}}}tab")  # a tab character inside w:t is not a Word tab
        if part:
            text_element = etree.SubElement(run, f"{{{W_NS}}}t")
            if part.startswith(" ") or part.endswith(" "):
                text_element.set(f"{{{XML_NS}}}space", "preserve")
            text_element.text = part
    element.append(run)


def _set_cell_text(cell, text: str) -> None:
    paragraphs = cell.xpath("./w:p", namespaces=NS)
    if paragraphs:
        _set_element_text(paragraphs[0], text)
        for paragraph in paragraphs[1:]:
            cell.remove(paragraph)
        return

    paragraph = etree.SubElement(cell, f"{{{W_NS}}}p")
    _set_element_text(paragraph, text)


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


_PLAIN_DROP = ("i", "iCs", "ins", "del", "rPrChange")


def _plain_run_properties(properties, *, drop=_PLAIN_DROP):
    """A copy of run properties without italics or tracked-change marks: text we generate
    is never italic, whatever the template's placeholder paragraph looked like."""
    if properties is None:
        return None
    clean = deepcopy(properties)
    for tag in drop:
        for node in clean.findall(_w(tag)):
            clean.remove(node)
    return clean


def _plain_paragraph_properties(properties):
    clean = deepcopy(properties)
    for mark in clean.findall(_w("rPr")):
        clean.replace(mark, _plain_run_properties(mark))
    return clean


def _paragraph_element(style_source, text: str, kind: str = "para", bullet: Optional[dict] = None):
    """``kind``: "para", "heading" (a short bold line above bullets) or "bullet"
    (a real Word list item copied from the template's own bullets)."""
    paragraph = etree.Element(_w("p"))
    if kind == "bullet" and bullet is not None:
        paragraph.append(deepcopy(bullet["ppr"]))
        run_properties = _plain_run_properties(bullet["rpr"], drop=_PLAIN_DROP + ("b", "bCs"))
    else:
        paragraph_properties = style_source.find(_w("pPr"))
        if paragraph_properties is not None:
            paragraph.append(_plain_paragraph_properties(paragraph_properties))
        run_properties = _plain_run_properties(style_source.find(f".//{_w('rPr')}"))
        if kind == "bullet":
            text = "\u2022 " + text  # the template has no bullet list to copy
        elif kind == "heading":
            if run_properties is None:
                run_properties = etree.Element(_w("rPr"))
            if run_properties.find(_w("b")) is None:
                run_properties.append(etree.Element(_w("b")))
            ppr = paragraph.find(_w("pPr"))
            if ppr is None:
                ppr = etree.Element(_w("pPr"))
                paragraph.insert(0, ppr)
            if ppr.find(_w("keepNext")) is None:
                ppr.insert(1 if ppr.find(_w("pStyle")) is not None else 0, etree.Element(_w("keepNext")))

    run = etree.SubElement(paragraph, f"{{{W_NS}}}r")
    if run_properties is not None:
        run.append(run_properties)
    text_element = etree.SubElement(run, f"{{{W_NS}}}t")
    if text.startswith(" ") or text.endswith(" "):
        text_element.set(f"{{{XML_NS}}}space", "preserve")
    text_element.text = text
    return paragraph


def _content_blocks(text: str) -> List[str]:
    cleaned = unescape(text or "")
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</(?:p|div|tr|li)>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    blocks = [
        re.sub(r"\s+", " ", block).strip()
        for block in re.split(r"\n\s*\n|\n", cleaned)
    ]
    return [block for block in blocks if block]


_BULLET_LINE = re.compile(r"^\s*[-*\u2022\u2013]\s+(.*\S)\s*$")


def _structured_blocks(text: str) -> List[Tuple[str, str]]:
    """Generated text as (kind, text) blocks: "bullet" for "- item" lines, "heading"
    for a short line that introduces bullets (or a markdown heading), else "para"."""
    cleaned = unescape(text or "")
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)<li[^>]*>", "\n- ", cleaned)
    cleaned = re.sub(r"(?i)</(?:p|div|tr|li|ul|ol)>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)

    blocks: List[Tuple[str, str]] = []
    for line in cleaned.split("\n"):
        if not line.strip():
            continue
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        bullet = _BULLET_LINE.match(line)
        heading = re.match(r"^\s*#{1,6}\s+(.*\S)\s*$", line)
        if bullet and bullet.group(1).rstrip().endswith(":") and len(bullet.group(1)) <= 80:
            # "- Attention:" is how a model writes a heading above its sub-bullets
            blocks.append(("heading", bullet.group(1).strip().rstrip(":").strip()))
        elif bullet:
            blocks.append(("bullet", re.sub(r"\s+", " ", bullet.group(1)).strip()))
        elif heading:
            blocks.append(("heading", heading.group(1).strip().rstrip(":")))
        else:
            blocks.append(("para", re.sub(r"\s+", " ", line).strip()))

    for index, (kind, text_value) in enumerate(blocks[:-1]):
        if (
            kind == "para"
            and blocks[index + 1][0] == "bullet"
            and len(text_value) <= 60
            and not re.search(r"[.!?;,]$", text_value)
        ):
            blocks[index] = ("heading", text_value.rstrip(":"))
    return blocks


def _set_spacing_after(properties, after: str = "0") -> None:
    spacing = properties.find(_w("spacing"))
    if spacing is None:
        spacing = etree.Element(_w("spacing"))
        later = next(
            (properties.find(_w(tag)) for tag in ("ind", "contextualSpacing", "jc", "textAlignment", "outlineLvl", "rPr")
             if properties.find(_w(tag)) is not None),
            None,
        )
        if later is not None:
            later.addprevious(spacing)
        else:
            properties.append(spacing)
    spacing.set(_w("after"), after)
    spacing.set(_w("before"), "0")


def _bullet_prototype(root, template_path: Path) -> Optional[dict]:
    """The template's own bullet-list look: the paragraph properties of one of its
    bullet items (so generated bullets match the clinic's list style and indents).
    None if the template has no bullet list at all."""
    try:
        with ZipFile(template_path, "r") as package:
            numbering = etree.fromstring(package.read("word/numbering.xml"))
    except (KeyError, etree.XMLSyntaxError):
        return None
    abstract = {a.get(_w("abstractNumId")): a for a in numbering.findall(_w("abstractNum"))}
    bullet_ids = set()
    for num in numbering.findall(_w("num")):
        link = num.find(_w("abstractNumId"))
        definition = abstract.get(link.get(_w("val"))) if link is not None else None
        level = definition.find(_w("lvl")) if definition is not None else None
        fmt = level.find(_w("numFmt")) if level is not None else None
        if fmt is not None and fmt.get(_w("val")) == "bullet":
            bullet_ids.add(num.get(_w("numId")))
    if not bullet_ids:
        return None

    exemplars = []
    for paragraph in root.iter(_w("p")):
        ppr = paragraph.find(_w("pPr"))
        num_pr = ppr.find(_w("numPr")) if ppr is not None else None
        if num_pr is None or not _element_text(paragraph).strip():
            continue
        num_id, level = num_pr.find(_w("numId")), num_pr.find(_w("ilvl"))
        if num_id is None or num_id.get(_w("val")) not in bullet_ids:
            continue
        if level is not None and level.get(_w("val")) != "0":
            continue
        exemplars.append(paragraph)
    if exemplars:
        def is_bold(paragraph) -> bool:
            run = paragraph.find(_w("r"))
            properties = run.find(_w("rPr")) if run is not None else None
            return properties is not None and properties.find(_w("b")) is not None

        paragraph = next((p for p in exemplars if not is_bold(p)), exemplars[0])
        proto = deepcopy(paragraph.find(_w("pPr")))
        for mark in proto.findall(_w("rPr")):
            proto.remove(mark)
        _set_spacing_after(proto)
        run = paragraph.find(_w("r"))
        return {"ppr": proto, "rpr": run.find(_w("rPr")) if run is not None else None}

    # No bullet item in the body to copy: build a standard one on a bullet list the template defines.
    num_id = sorted(bullet_ids, key=lambda value: int(value) if value.isdigit() else 0)[0]
    ppr = etree.Element(_w("pPr"))
    num_pr = etree.SubElement(ppr, _w("numPr"))
    etree.SubElement(num_pr, _w("ilvl")).set(_w("val"), "0")
    etree.SubElement(num_pr, _w("numId")).set(_w("val"), num_id)
    _set_spacing_after(ppr)
    indent = etree.SubElement(ppr, _w("ind"))
    indent.set(_w("left"), "720")
    indent.set(_w("hanging"), "360")
    return {"ppr": ppr, "rpr": None}


def _normalize(value: str) -> str:
    folded = (value or "").replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", folded.strip().casefold())
