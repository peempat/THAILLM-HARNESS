from __future__ import annotations

import re
from datetime import date

from .hooks import pre_normalize_hook


THAI_RE = re.compile(r"[\u0E00-\u0E7F]")
TABLE_RE = re.compile(r"\b(?:FACT|DIM|V)_[A-Z0-9_]+\b", re.IGNORECASE)
VENDOR_RE = re.compile(r"\bV-\d{3}\b", re.IGNORECASE)
EMPLOYEE_RE = re.compile(r"\bEMP-[A-Z0-9-]+\b", re.IGNORECASE)
SKU_RE = re.compile(r"\b[A-Z]{2,5}(?:-[A-Z0-9]{2,8})+-\d{3,4}\b", re.IGNORECASE)
DOC_ID_RE = re.compile(
    r"\b(?:MEMO|MIN|FIN|OPS|CHAT|EMAIL|POL|SF|PM|T[0-9])-?[A-Z0-9_-]*\d{2,}\b",
    re.IGNORECASE,
)


FIELD_HINTS = [
    "msrp_thb",
    "net_total_thb",
    "business_event_date",
    "posting_date",
    "loyalty_tier",
    "employee_id",
    "vendor_id",
    "sku_id",
    "campaign_id",
]


def detect_language(question: str) -> str:
    return "th" if THAI_RE.search(question) else "en"


def _unique_upper(matches: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in matches:
        value = match.upper()
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _date_range_from_year(year: int) -> dict:
    return {
        "start": date(year, 1, 1).isoformat(),
        "end": date(year, 12, 31).isoformat(),
        "date_type": "business_event_date",
    }


def extract_date_constraints(question: str) -> dict:
    lowered = question.lower()
    if "posting_date" in lowered and "business_event_date" in lowered:
        date_type = "business_event_date+posting_date"
    elif "posting_date" in lowered:
        date_type = "posting_date"
    else:
        date_type = "business_event_date"

    fy = re.search(r"\bFY\s*(20\d{2}|25\d{2})\b", question, re.IGNORECASE)
    if fy:
        year = int(fy.group(1))
        if year >= 2400:
            year -= 543
        result = _date_range_from_year(year)
        result["date_type"] = date_type
        return result

    year_range = re.search(r"\b(20\d{2}|25\d{2})\s*[-–]\s*(20\d{2}|25\d{2})\b", question)
    if year_range:
        start_year = int(year_range.group(1))
        end_year = int(year_range.group(2))
        if start_year >= 2400:
            start_year -= 543
        if end_year >= 2400:
            end_year -= 543
        return {
            "start": date(start_year, 1, 1).isoformat(),
            "end": date(end_year, 12, 31).isoformat(),
            "date_type": date_type,
        }

    years = [int(y) for y in re.findall(r"\b(20\d{2}|25\d{2})\b", question)]
    if years:
        year = years[0] - 543 if years[0] >= 2400 else years[0]
        result = _date_range_from_year(year)
        result["date_type"] = date_type
        return result

    quarter = re.search(r"\bQ([1-4])\s*(20\d{2}|25\d{2})\b", question, re.IGNORECASE)
    if quarter:
        q = int(quarter.group(1))
        year = int(quarter.group(2))
        if year >= 2400:
            year -= 543
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        end_day = 31 if end_month in {3, 12} else 30
        return {
            "start": date(year, start_month, 1).isoformat(),
            "end": date(year, end_month, end_day).isoformat(),
            "date_type": date_type,
        }

    return {"start": None, "end": None, "date_type": date_type}


def normalize_question(question: str) -> dict:
    normalized_question = pre_normalize_hook(question)
    table_terms = _unique_upper(TABLE_RE.findall(normalized_question))
    sku_ids = _unique_upper(SKU_RE.findall(normalized_question))
    vendor_ids = _unique_upper(VENDOR_RE.findall(normalized_question))
    employee_ids = _unique_upper(EMPLOYEE_RE.findall(normalized_question))
    doc_ids = _unique_upper(DOC_ID_RE.findall(normalized_question))

    sql_terms = table_terms[:]
    lowered = normalized_question.lower()
    for hint in FIELD_HINTS:
        if hint.lower() in lowered:
            sql_terms.append(hint)

    rag_keywords = doc_ids[:]
    if any(term in lowered for term in ["memo", "email", "chat", "line", "report", "policy", "minutes"]):
        rag_keywords.extend(re.findall(r"[A-Za-z0-9_-]{3,}", normalized_question))

    return {
        "normalized_question": normalized_question,
        "language": detect_language(normalized_question),
        "entities": {
            "sku_id": sku_ids,
            "campaign_id": [x for x in doc_ids if x.startswith(("SF", "PM", "PROMO"))],
            "vendor_id": vendor_ids,
            "employee_id": employee_ids,
            "document_id": doc_ids,
        },
        "date_constraints": extract_date_constraints(normalized_question),
        "sql_terms": list(dict.fromkeys(sql_terms)),
        "rag_keywords": list(dict.fromkeys(rag_keywords)),
        "warnings": [],
    }
