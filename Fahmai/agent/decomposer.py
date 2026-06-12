from __future__ import annotations

import re


ENUM_RE = re.compile(r"\((\d{1,2})\)")


DERIVED_CUES = {
    "roi",
    "รวม",
    "net",
    "gap",
    "baseline",
    "เทียบ",
    "correction",
    "dedup",
    "reconcile",
    "outflow",
    "refund",
    "window",
    "lift",
}


def decompose_question(question: str) -> list[dict]:
    """Split explicit numbered multi-part questions into ordered parts.

    HARD/XHARD prompts often contain tuples such as (1)..(6). The planner keeps
    those as first-class parts so downstream reconcilers can answer each part in
    order and mark derived parts as depending on earlier evidence.
    """

    matches = list(ENUM_RE.finditer(question))
    if len(matches) < 2:
        return [
            {
                "id": "part_1",
                "ordinal": 1,
                "text": question.strip(),
                "depends_on": [],
                "is_derived": False,
            }
        ]

    parts: list[dict] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(question)
        text = " ".join(question[start:end].strip(" :\n\t").split())
        ordinal = int(match.group(1))
        lower = text.lower()
        is_derived = any(cue in lower for cue in DERIVED_CUES)
        depends_on = [part["id"] for part in parts] if is_derived else []
        parts.append(
            {
                "id": f"part_{ordinal}",
                "ordinal": ordinal,
                "text": text,
                "depends_on": depends_on,
                "is_derived": is_derived,
            }
        )
    return parts
