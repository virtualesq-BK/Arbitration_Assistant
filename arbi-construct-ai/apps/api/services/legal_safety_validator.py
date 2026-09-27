"""Enforces the AI product boundary on generated text.

The system must never predict outcomes, give probabilities of success, or present
output as legal advice. Offending phrases are replaced by a REQUIRES_HUMAN_REVIEW marker.
"""
from __future__ import annotations

import re

FORBIDDEN_PATTERNS = [
    r"will win",
    r"guaranteed to",
    r"\d+\s*%\s*(chance|probability|likelihood)",
    r"you will succeed",
    r"definitely liable",
    r"I advise you to",
    r"my legal advice",
    r"legal conclusion is",
]

# Additional outcome-prediction phrasings, same treatment.
EXTRA_PATTERNS = [
    r"will (certainly|definitely) (lose|succeed|prevail)",
    r"(is|are) certain to (win|lose|prevail|succeed)",
    r"will be awarded",
    r"the tribunal will (find|rule|hold|award)",
    r"(chance|probability|likelihood) of (success|winning) is",
]

REPLACEMENT = "[REQUIRES_HUMAN_REVIEW: outcome prediction / legal advice removed]"

_COMPILED = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS + EXTRA_PATTERNS]


def validate(response_text: str) -> tuple[str, list[str]]:
    """Returns (safe_response, warnings). Replaces forbidden phrases with REQUIRES_HUMAN_REVIEW labels."""
    if not response_text:
        return response_text, []
    warnings: list[str] = []
    safe = response_text
    for pattern in _COMPILED:
        matches = [m.group(0) for m in pattern.finditer(safe)]
        if not matches:
            continue
        for phrase in dict.fromkeys(matches):
            warnings.append(
                f"REQUIRES_HUMAN_REVIEW: forbidden phrase '{phrase}' (pattern '{pattern.pattern}') removed — "
                "outcome predictions and legal advice are outside the product boundary."
            )
        safe = pattern.sub(REPLACEMENT, safe)
    return safe, warnings


def is_safe(response_text: str) -> bool:
    return not validate(response_text)[1]
