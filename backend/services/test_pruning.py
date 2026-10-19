"""Remove the template's tests that were not administered.

The clinic templates list every test the clinic ever uses (the "Tests Administered"
lists) and carry a result block for each (heading, description, blank score tables,
graph placeholder). A report only needs the tests that were actually given, so once
we know which those are, the rest is taken out:

* list entries in the "Tests Administered" lists, and
* result blocks, found from the template's own structure: a short heading or table
  caption naming a test starts a block, which runs until the next test's heading, a
  section heading, or something that is clearly not part of a block (a signature).

Deleting content is worse than leaving it, so everything here errs on the side of
keeping: nothing is removed unless we know which tests were given; a block is only
removed if we are sure which test it belongs to; a list entry we can't place stays;
section anchors and anything holding a section/page break are never removed.
Tests are matched by family only (WIAT-III and WIAT-4 are the same test to us), the
same way a score report's tests are matched to the template.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from docx.oxml.ns import qn

from services.docx_test_results import (
    HEADING_MAX_CHARS,
    KNOWN_FAMILIES,
    P,
    RESULTS_END_EXACT,
    RESULTS_END_PREFIXES,
    RESULTS_START_HEADINGS,
    TBL,
    _norm,
    _text,
)

# Names the clinic uses that are not (or not only) a known family token.
_ALIASES = (
    (re.compile(r"\bbbcs\b|bracken"), "bracken"),
    (re.compile(r"\brcft\b|rey[\s–-]*osterrieth|rey complex"), "rey"),
    (re.compile(r"\bvabs\b|vineland"), "vineland"),
    (re.compile(r"d[\s–-]*kefs|delis[\s–-]*kaplan"), "dkefs"),
    (re.compile(r"colou?r trails|\bcctt\b"), "cctt"),
    (re.compile(r"adhd[\s-]*(?:5\s*)?rating|adhd[\s-]*5"), "adhdrs"),
    (re.compile(r"feifer"), "feifer"),
    (re.compile(r"vanderbilt"), "vanderbilt"),
    (re.compile(r"\bcefi\b|comprehensive executive function"), "cefi"),
    (re.compile(r"\bcsrpi\b|self-report and projective"), "csrpi"),
    (re.compile(r"\bwnv\b|wechsler nonverbal"), "wnv"),
    (re.compile(r"beck youth"), "beck"),
    (re.compile(r"sensory profile"), "sensoryprofile"),
    (re.compile(r"movement abc"), "movementabc"),
    (re.compile(r"achenbach|\baseba\b|\bcbcl\b|\btrf\b"), "aseba"),
    (re.compile(r"weiss|\bwsr\b"), "wsr"),
    (re.compile(r"autism spectrum rating|\basrs\b"), "asrs"),
    (re.compile(r"scales of independent behaviou?r|\bsib[\s-]*r\b"), "sib"),
    (re.compile(r"conners"), "conners"),
    # the same tests written out in full (some headings never use the abbreviation)
    (re.compile(r"multidimensional anxiety"), "masc"),
    (re.compile(r"screen for child anxiety"), "scared"),
    (re.compile(r"wide range assessment of (?:memory|learning)"), "wraml"),
    (re.compile(r"wechsler intelligence scale for children"), "wisc"),
    (re.compile(r"wechsler adult intelligence"), "wais"),
    (re.compile(r"wechsler individual achievement"), "wiat"),
    (re.compile(r"wechsler preschool"), "wppsi"),
    (re.compile(r"wechsler abbreviated"), "wasi"),
    (re.compile(r"california verbal learning"), "cvlt"),
    (re.compile(r"behaviou?r rating inventory"), "brief"),
    (re.compile(r"behaviou?r assessment system for children"), "basc"),
    (re.compile(r"adaptive behaviou?r assessment"), "abas"),
    (re.compile(r"bayley scales"), "bayley"),
    (re.compile(r"peabody picture"), "ppvt"),
    (re.compile(r"differential ability scales"), "das"),
    (re.compile(r"developmental neuropsychological"), "nepsy"),
    (re.compile(r"comprehensive test of phonological"), "ctopp"),
    (re.compile(r"kaufman test of educational"), "ktea"),
    (re.compile(r"gray oral reading"), "gort"),
    (re.compile(r"autism diagnostic observation"), "ados"),
    (re.compile(r"social responsiveness scale"), "srs"),
    (re.compile(r"social communication questionnaire"), "scq"),
    (re.compile(r"children's depression inventory|children’s depression inventory"), "cdi"),
)
_FAMILY_PATTERNS = {
    family: re.compile(r"(?<![a-z0-9])" + re.escape(family) + r"(?![a-z])") for family in KNOWN_FAMILIES
}
HEAD_WINDOW = 160  # a description names its test near the start


def _matches(text: str) -> List[Tuple[int, str]]:
    raw = re.sub(r"\s+", " ", (text or "").lower())
    hyphenless = _norm(text)
    found: Dict[str, int] = {}
    for family, pattern in _FAMILY_PATTERNS.items():
        for haystack in (hyphenless, raw):
            match = pattern.search(haystack)
            if match:
                found[family] = min(found.get(family, 10**9), match.start())
    for pattern, family in _ALIASES:
        match = pattern.search(raw)
        if match:
            found[family] = min(found.get(family, 10**9), match.start())
    return sorted((pos, family) for family, pos in found.items())


def families_in(text: str) -> Set[str]:
    return {family for _, family in _matches(text)}


def first_family(text: str) -> Optional[str]:
    matches = _matches(text)
    return matches[0][1] if matches else None


# --------------------------------------------------------------------------- #
def _is_bold_or_heading(paragraph) -> bool:
    properties = paragraph.find(qn("w:pPr"))
    style = properties.find(qn("w:pStyle")) if properties is not None else None
    if style is not None and "heading" in (style.get(qn("w:val")) or "").lower():
        return True
    return any(
        run.find(qn("w:rPr")) is not None and run.find(qn("w:rPr")).find(qn("w:b")) is not None and _text(run)
        for run in paragraph.iter(qn("w:r"))
    )


_CAPTION_WORDS = re.compile(r"table|summary|scores?|profile", re.IGNORECASE)


def _is_caption(paragraph) -> bool:
    return _is_bold_or_heading(paragraph) and bool(_CAPTION_WORDS.search(_text(paragraph)))


def _keeps_layout(paragraph) -> bool:
    """A section break lives in a paragraph's properties; deleting it would merge sections."""
    properties = paragraph.find(qn("w:pPr"))
    return properties is not None and properties.find(qn("w:sectPr")) is not None


def _region(children) -> Tuple[int, int]:
    start = None
    for index, element in enumerate(children):
        if element.tag != P:
            continue
        norm = _norm(_text(element))
        if start is None:
            if norm in RESULTS_START_HEADINGS:
                start = index
        elif norm.startswith(RESULTS_END_PREFIXES) or norm in RESULTS_END_EXACT:
            return start, index
    return (start, len(children)) if start is not None else (len(children), len(children))


def _next_nonempty(children, index: int, stop: int):
    for follower in children[index + 1:stop]:
        if follower.tag == TBL or _text(follower):
            return follower
    return None


def _is_note(text: str) -> bool:
    lowered = text.lstrip().lower()
    return lowered.startswith(("*", "(", "note")) or "insert" in lowered[:12]


def prune_unadministered(root, administered: Iterable[str], protected: Iterable[str] = (), _debug: Optional[dict] = None) -> Optional[dict]:
    """Delete list entries and result blocks for tests not in ``administered`` from the
    template tree. Returns {"removed": [...]} (what went), or None if nothing was
    removed or we can't tell which tests were given."""
    given: Set[str] = set()
    for name in administered:
        given |= families_in(name)
    if not given:
        return None
    body = root.find(qn("w:body"))
    if body is None:
        return None
    children = list(body)
    start, end = _region(children)
    if start >= end:
        return None
    protected_norm = {_norm(p) for p in protected}

    # ---- classify the paragraphs of the results region ---------------------
    kinds: Dict[int, str] = {}
    fam: Dict[int, Optional[str]] = {}
    named_short: List[int] = []
    for index in range(start + 1, end):
        element = children[index]
        if element.tag != P or not _text(element):
            continue
        text = _text(element)
        if len(text) <= HEADING_MAX_CHARS and not _is_note(text) and families_in(text):
            named_short.append(index)

    list_members: Set[int] = set()
    ordered = [i for i in range(start + 1, end) if children[i].tag == TBL or _text(children[i])]
    position = {i: n for n, i in enumerate(ordered)}
    for index in named_short:
        n = position[index]
        neighbours = [ordered[n - 1]] if n else []
        neighbours += [ordered[n + 1]] if n + 1 < len(ordered) else []
        if any(m in named_short for m in neighbours):
            list_members.add(index)

    for index in range(start + 1, end):
        element = children[index]
        if element.tag == TBL:
            kinds[index] = "table"
            continue
        if element.tag != P:
            kinds[index] = "other"
            continue
        text = _text(element)
        if not text:
            kinds[index] = "empty"
        elif index in list_members:
            kinds[index] = "list"
        elif _is_note(text):
            kinds[index] = "note"
        elif len(text) <= HEADING_MAX_CHARS and families_in(text):
            kinds[index], fam[index] = "head", first_family(text)
        elif len(text) > HEADING_MAX_CHARS and first_family(text[:HEAD_WINDOW]):
            kinds[index], fam[index] = "desc", first_family(text[:HEAD_WINDOW])
        elif len(text) <= HEADING_MAX_CHARS:
            follower = _next_nonempty(children, index, end)
            if follower is not None and follower.tag == TBL:
                kinds[index] = "caption"
            elif _is_bold_or_heading(element) and _norm(text) not in protected_norm:
                kinds[index] = "container"
            elif _is_bold_or_heading(element):
                kinds[index] = "anchor"
            else:
                kinds[index] = "terminator"  # e.g. a signature line
        else:
            kinds[index] = "body"

    # ---- who owns each element ------------------------------------------------
    owner_of: Dict[int, Optional[str]] = {}
    soft: Set[int] = set()
    owner: Optional[str] = None
    heads_ahead = sorted(i for i, k in kinds.items() if k == "head")
    for index in range(start + 1, end):
        kind = kinds.get(index, "other")
        if kind == "head":
            caption = _is_caption(children[index])
            # A table caption never takes a block away from a test that was given: some templates label
            # one test's table with another test's name ("Academic Scores - KTEA-3" under the WIAT text).
            if not (caption and owner in given and fam[index] != owner):
                owner = fam[index]
        elif kind == "desc":
            named = families_in(_text(children[index])[:HEAD_WINDOW])
            upcoming = next((h for h in heads_ahead if h > index), None)
            if named & given:
                # it introduces a test that was given (a paragraph may name several): keep it and what follows
                owner = fam[index] if fam[index] in given else sorted(named & given)[0]
            elif owner is None or (upcoming is not None and fam.get(upcoming) == fam[index]):
                owner = fam[index]
            else:
                soft.add(index)  # an intro for a test we are not keeping, inside another block: it goes, that block's end is unchanged
        elif kind in ("container", "terminator", "anchor"):
            owner = None
        owner_of[index] = owner if kind not in ("container", "terminator", "anchor", "list") else None
        if index in soft:
            owner_of[index] = fam[index]

    if _debug is not None:
        _debug.update(kinds=kinds, owner_of=owner_of, fam=fam, children=children, start=start, end=end)

    # ---- what goes -------------------------------------------------------------
    removed_labels: List[str] = []
    doomed: List[int] = []
    for index in range(start + 1, end):
        kind = kinds.get(index)
        text = _text(children[index]) if children[index].tag == P else ""
        if kind == "list":
            families = families_in(text)
            if families and not (families & given):
                doomed.append(index)
                removed_labels.append(text)
        elif owner_of.get(index) and owner_of[index] not in given:
            doomed.append(index)
            if kind == "head" and text not in removed_labels:
                removed_labels.append(text)
    doomed = [i for i in doomed if not (children[i].tag == P and _keeps_layout(children[i]))]
    if not doomed:
        return None
    doomed_set = set(doomed)

    # ---- section headings that are left with nothing under them -------------
    def nonempty(index: int) -> bool:
        return children[index].tag == TBL or bool(_text(children[index]))

    empty_headings = []
    for index in range(start + 1, end):
        if kinds.get(index) != "container" or index in doomed_set:
            continue
        after = next((j for j in range(index + 1, end) if nonempty(j)), None)
        if after is None or after not in doomed_set:
            continue  # nothing of ours was taken out right under it
        survivor = next((j for j in range(index + 1, end) if nonempty(j) and j not in doomed_set), None)
        if survivor is None or kinds.get(survivor) in ("container", "terminator", "anchor"):
            empty_headings.append(index)
    for index in doomed:
        body.remove(children[index])
    for index in empty_headings:
        body.remove(children[index])
    return {"removed": removed_labels}
