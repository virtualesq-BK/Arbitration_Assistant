"""Checks that rule/article references in AI output are grounded in retrieved sources.

A reference such as "ICC Art. 23", "SIAC Rule 29" or "Article 26" is considered valid only if
a retrieved chunk carries the same number (and, when the reference names an institution,
belongs to that institution). Anything else is flagged so a human can check it — the model
must never fabricate citations.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from services.rag_service import RetrievedChunk

INSTITUTIONS = ("ICC", "SIAC", "LCIA", "HKIAC", "ICDR", "ICSID", "UNCITRAL")

_INST = r"(?:(?P<inst>ICC|SIAC|LCIA|HKIAC|ICDR|ICSID|UNCITRAL)(?:\s+Rules?)?(?:\s+\d{4})?(?:\s+Rules)?[,\s]+)?"
_KIND = r"(?P<kind>Articles?|Arts?\.?|Rules?)"
_NUM = r"(?P<num>\d{1,3})(?:\.\d+)?(?:\s*(?P<sep>-|–|to|and|&|,)\s*(?P<end>\d{1,3})(?!\d))?"
REFERENCE_RE = re.compile(rf"\b{_INST}{_KIND}\s+{_NUM}\b", re.IGNORECASE)

Ref = tuple[str | None, int]


def _expand(start: int, end: int | None) -> list[int]:
    if end is None or end < start or end - start > 30:
        return [start]
    return list(range(start, end + 1))


def extract_references(text: str) -> list[tuple[str, Ref]]:
    """Return [(matched_text, (institution|None, number)), ...] for each number referenced."""
    refs: list[tuple[str, Ref]] = []
    for m in REFERENCE_RE.finditer(text or ""):
        inst = m.group("inst").upper() if m.group("inst") else None
        start = int(m.group("num"))
        end = int(m.group("end")) if m.group("end") else None
        if end is not None and m.group("sep") in ("and", "&", ","):
            numbers = [start, end]  # an enumeration, not a range
        else:
            numbers = _expand(start, end)
        for n in numbers:
            refs.append((m.group(0).strip(), (inst, n)))
    return refs


def _chunk_refs(chunk: RetrievedChunk) -> set[Ref]:
    owner = chunk.institution.upper() if chunk.institution else None
    refs: set[Ref] = set()
    for _, (inst, num) in extract_references(f"{chunk.source_name}\n{chunk.text}"):
        refs.add((inst or owner, num))
        refs.add((None, num))
    return refs


def validate_citations(response_text: str, retrieved_chunks: list[RetrievedChunk]) -> tuple[bool, list[str]]:
    """Check that rule/article references in response_text appear in retrieved chunks.
    Returns (is_valid, list_of_warnings)."""
    available: set[Ref] = set()
    for chunk in retrieved_chunks:
        available |= _chunk_refs(chunk)

    warnings: list[str] = []
    seen: set[Ref] = set()
    for matched, ref in extract_references(response_text):
        if ref in seen:
            continue
        seen.add(ref)
        inst, num = ref
        grounded = ref in available if inst else (None, num) in available
        if not grounded:
            label = f"{inst} {num}" if inst else str(num)
            warnings.append(
                f"REQUIRES_HUMAN_REVIEW: citation '{matched}' (ref {label}) was not found in the retrieved "
                "sources and may be inaccurate. Source not found."
            )
    return (not warnings), warnings


def validate_many(texts: Iterable[str], retrieved_chunks: list[RetrievedChunk]) -> tuple[bool, list[str]]:
    ok = True
    all_warnings: list[str] = []
    for t in texts:
        valid, w = validate_citations(t, retrieved_chunks)
        ok = ok and valid
        for item in w:
            if item not in all_warnings:
                all_warnings.append(item)
    return ok, all_warnings
