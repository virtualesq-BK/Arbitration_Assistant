from __future__ import annotations

import pytest

from services.legal_safety_validator import REPLACEMENT, validate


def test_will_win_triggers_forbidden_pattern() -> None:
    safe, warnings = validate("The contractor will win this case.")
    assert warnings, "outcome prediction must be flagged"
    assert "will win" not in safe.lower()
    assert REPLACEMENT in safe
    assert "REQUIRES_HUMAN_REVIEW" in safe


def test_cautious_source_based_language_passes() -> None:
    text = "Based on retrieved sources, the contractor's argument is potentially supported."
    safe, warnings = validate(text)
    assert warnings == []
    assert safe == text


@pytest.mark.parametrize(
    "text",
    [
        "There is a 70% chance of success on the EOT claim.",
        "The employer is definitely liable for the delay.",
        "I advise you to terminate the contract.",
        "My legal advice is to settle.",
        "The legal conclusion is that the notice was valid.",
        "The claimant is guaranteed to recover its costs.",
        "You will succeed on quantum.",
        "There is an 80 % probability the tribunal agrees.",
    ],
)
def test_other_forbidden_phrases(text: str) -> None:
    safe, warnings = validate(text)
    assert warnings
    assert "REQUIRES_HUMAN_REVIEW" in safe


def test_empty_text() -> None:
    assert validate("") == ("", [])
