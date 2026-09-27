from __future__ import annotations

from services.citation_validator import extract_references, validate_citations
from services.rag_service import RetrievedChunk


def _icc_chunk(article: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        text=text,
        source_name=f"ICC Rules 2021 {article}",
        source_url="https://iccwbo.org/dispute-resolution/dispute-resolution-services/arbitration/rules-of-arbitration/",
        institution="ICC",
        rule_version="2021",
        document_id=None,
        chunk_index=0,
        confidence=0.9,
    )


ICC_ART4 = _icc_chunk("Art. 4", "Art. 4 — Request for Arbitration: a party wishing to have recourse to arbitration shall submit its Request to the Secretariat.")


def test_uncited_rule_number_produces_warning() -> None:
    ok, warnings = validate_citations("Under ICC Rule 99 the claimant must file a reply.", [ICC_ART4])
    assert not ok
    assert len(warnings) == 1
    assert "99" in warnings[0]
    assert "REQUIRES_HUMAN_REVIEW" in warnings[0]


def test_grounded_article_is_valid() -> None:
    ok, warnings = validate_citations("The Request for Arbitration is governed by ICC Art. 4.", [ICC_ART4])
    assert ok
    assert warnings == []


def test_institution_mismatch_is_flagged() -> None:
    ok, warnings = validate_citations("See SIAC Rule 4 on this point.", [ICC_ART4])
    assert not ok and warnings


def test_ranges_are_expanded() -> None:
    chunk = _icc_chunk("Arts. 11-13", "Arts. 11-13 — constitution of the arbitral tribunal.")
    ok, _ = validate_citations("Tribunal constitution is addressed in ICC Article 12.", [chunk])
    assert ok


def test_enumeration_is_not_a_range() -> None:
    refs = [r for _, r in extract_references("ICC Arts. 23 and 31")]
    assert refs == [("ICC", 23), ("ICC", 31)]


def test_extract_references() -> None:
    refs = [r for _, r in extract_references("ICC Rules 2021, Art. 23 and SIAC Rule 29; Article 5")]
    assert ("ICC", 23) in refs
    assert ("SIAC", 29) in refs
    assert (None, 5) in refs


def test_no_references_is_valid() -> None:
    assert validate_citations("No rule is referenced here.", []) == (True, [])
