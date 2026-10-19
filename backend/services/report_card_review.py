"""The "Appendix 1: Report Card Review" section of the Sunny Hill / Psycho-Ed reports.

The clinic's template says how this appendix is filled: text is cut and pasted from the
file review document, in the template's own bullet format; a part with nothing in it
(no IEP, no learning support, a term with no report card) is simply left out, and if
the comments are not split by term the "Term" headers are left out too. So the form
collects the parts as typed and this module lays them out; there is no AI step, because
report-card comments must be reproduced exactly.

The template holds room for three school years, so the form has three.
"""
from __future__ import annotations

import re
from typing import List, Mapping, Tuple

YEARS = 3
SECTION_TITLE = "Appendix 1: Report Card Review"

# (key, form label without the "Year N: " prefix, field type, heading written in the report)
PARTS: Tuple[Tuple[str, str, str, str], ...] = (
    ("grade", "Grade, school (program if relevant, e.g. immersion, IB)", "text", ""),
    ("iep", "IEP (designation) major goals", "textarea", "IEP (Designation) Major Goals"),
    ("support", "Learning support programming", "textarea", "Learning Support Programming"),
    ("all", "Comments from report card(s), all terms together", "textarea", "Comments from Report Card(s)"),
    ("term1", "Comments from report card: Term 1", "textarea", "Term 1"),
    ("term2", "Comments from report card: Term 2", "textarea", "Term 2"),
    ("term3", "Comments from report card: Term 3/Final report", "textarea", "Term 3/Final Report"),
)


def field_label(year: int, key: str) -> str:
    label = next(p[1] for p in PARTS if p[0] == key)
    return f"Year {year}: {label}"


def is_report_card_section(section_name: str) -> bool:
    return (section_name or "").strip().lower().startswith("appendix 1: report card")


def _bullets(value: str) -> List[str]:
    """One bullet per line, keeping a pasted secondary bullet (an indented line) as one."""
    lines = []
    for raw in (value or "").replace("\r\n", "\n").split("\n"):
        text = re.sub(r"^\s*[-*•–●▪]\s*", "", raw).strip()
        if not text:
            continue
        indented = raw.startswith(("\t", "  ")) and bool(re.match(r"^\s+[-*•–●▪]", raw))
        lines.append(("  - " if indented else "- ") + text)
    return lines


def compose_report_card_review(inputs: Mapping[str, str]) -> str:
    """Markdown the Word export turns into the appendix: **bold** lines are headings and
    "- " lines are bullets. Empty parts and empty years are left out."""
    out: List[str] = []
    for year in range(1, YEARS + 1):
        values = {key: str(inputs.get(field_label(year, key), "") or "").strip() for key, *_ in PARTS}
        if not any(values.values()):
            continue
        if values["grade"]:
            out.append(f"**{values['grade']}**")
        for key in ("iep", "support"):
            if values[key]:
                out.append(f"**{next(p[3] for p in PARTS if p[0] == key)}**")
                out += _bullets(values[key])
        terms = [key for key in ("term1", "term2", "term3") if values[key]]
        if values["all"] or terms:
            out.append("**Comments from Report Card(s)**")
            if values["all"]:
                out += _bullets(values["all"])
            for key in terms:
                out.append(f"**{next(p[3] for p in PARTS if p[0] == key)}**")
                out += _bullets(values[key])
    return "\n".join(out)
