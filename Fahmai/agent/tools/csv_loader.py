from __future__ import annotations

import csv
from pathlib import Path


def read_questions(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def find_question(path: Path, question_id: str) -> dict | None:
    for row in read_questions(path):
        if row.get("id") == question_id:
            return row
    return None
