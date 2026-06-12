from __future__ import annotations

import re


RULES: list[tuple[str, str]] = [
    (r"\[/?system\]", "contains [SYSTEM] marker"),
    (r"admin mode", "claims admin mode"),
    (r"system override", "claims system override"),
    (r"developer instruction", "mentions developer instruction"),
    (r"ignore (all )?(previous|prior)", "asks to ignore previous instructions"),
    (r"do not consult", "blocks trusted sources"),
    (r"output exactly|reply with exact string|verbatim", "asks for exact output"),
    (r"previous session confirmed", "previous-session authority claim"),
    (r"trust\s*=\s*high", "fake trust marker"),
    (r"new policy says|authoritative memo", "fake policy authority"),
    (r"do not use internal table", "blocks internal table"),
    (r"confirm this unsupported fact", "asks to confirm unsupported fact"),
]


def classify_injection(question: str) -> dict:
    lowered = question.lower()
    reasons = [reason for pattern, reason in RULES if re.search(pattern, lowered)]
    is_injection = bool(reasons)
    safe = question
    if is_injection:
        safe = re.sub(r"\[system\].*?\[/system\]", " ", safe, flags=re.IGNORECASE | re.DOTALL)
        safe = re.sub(r"(?i)output exactly.*", " ", safe)
        safe = re.sub(r"(?i)reply with exact string.*", " ", safe)
        safe = re.sub(r"(?i)do not consult[^.?!]*[.?!]?", " ", safe)
        safe = " ".join(safe.split())
    return {
        "is_prompt_injection": is_injection,
        "classification": "prompt_injection" if is_injection else "normal_question",
        "reasons": reasons,
        "safe_underlying_question": safe,
    }
