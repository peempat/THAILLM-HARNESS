from __future__ import annotations

import re
import unicodedata


TOKEN_RE = re.compile(r"[A-Za-z0-9ก-๙]+")
NUMBER_RE = re.compile(r"\d[\d,./-]*")

STOPWORDS = {
    "บาท",
    "รายการ",
    "ครั้ง",
    "ราย",
    "คือ",
    "และ",
    "ของ",
    "ใน",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "a",
    "an",
}


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower()
    text = text.replace("≈", "=").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def extract_terms(value: str | None) -> list[str]:
    text = normalize_text(value)
    terms: list[str] = []
    for token in TOKEN_RE.findall(text):
        cleaned = token.strip("_-")
        if not cleaned or cleaned in STOPWORDS:
            continue
        if len(cleaned) < 2 and not cleaned.isdigit():
            continue
        terms.append(cleaned)
    return list(dict.fromkeys(terms))


def extract_numbers(value: str | None) -> list[str]:
    numbers = []
    for raw in NUMBER_RE.findall(normalize_text(value)):
        number = raw.strip(".,;:")
        if number:
            numbers.append(number.replace(",", ""))
    return list(dict.fromkeys(numbers))


def score_answer(predicted: str | None, expected: str | None) -> dict:
    predicted_norm = normalize_text(predicted)
    expected_norm = normalize_text(expected)
    if not expected_norm:
        return {"match": False, "score": 0.0, "missing_terms": [], "missing_numbers": []}
    if expected_norm and expected_norm in predicted_norm:
        return {"match": True, "score": 1.0, "missing_terms": [], "missing_numbers": []}

    expected_numbers = extract_numbers(expected_norm)
    predicted_numbers = extract_numbers(predicted_norm)
    missing_numbers = [n for n in expected_numbers if n not in predicted_numbers]

    expected_terms = [t for t in extract_terms(expected_norm) if not t.isdigit()]
    predicted_terms = set(extract_terms(predicted_norm))
    missing_terms = [t for t in expected_terms if t not in predicted_terms]

    total = len(expected_numbers) + len(expected_terms)
    if total == 0:
        score = 0.0
    else:
        hit = (len(expected_numbers) - len(missing_numbers)) + (len(expected_terms) - len(missing_terms))
        score = max(0.0, hit / total)

    # Numeric answers are usually critical in this benchmark.
    match = score >= 0.85 and not missing_numbers
    return {
        "match": match,
        "score": round(score, 4),
        "missing_terms": missing_terms[:12],
        "missing_numbers": missing_numbers[:12],
    }


def summarize_scores(rows: list[dict]) -> dict:
    total = len(rows)
    matched = sum(1 for row in rows if str(row.get("match")).lower() == "true")
    by_suite: dict[str, dict] = {}
    for row in rows:
        suite = row.get("suite") or "UNKNOWN"
        bucket = by_suite.setdefault(suite, {"total": 0, "matched": 0})
        bucket["total"] += 1
        if str(row.get("match")).lower() == "true":
            bucket["matched"] += 1
    for bucket in by_suite.values():
        bucket["accuracy"] = round(bucket["matched"] / bucket["total"], 4) if bucket["total"] else 0.0
    return {
        "total": total,
        "matched": matched,
        "accuracy": round(matched / total, 4) if total else 0.0,
        "by_suite": by_suite,
    }
