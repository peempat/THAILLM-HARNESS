# Normalizer Prompt

## Goal

Normalize FahMai questions into stable JSON for routing, planning, SQL, and RAG.

## Input JSON

```json
{
  "question_id": "L3-Q-EASY-001",
  "raw_question": "..."
}
```

## Output JSON

```json
{
  "normalized_question": "...",
  "language": "th",
  "entities": {
    "sku_id": ["NT-LT-001"],
    "campaign_id": [],
    "vendor_id": [],
    "employee_id": [],
    "document_id": []
  },
  "date_constraints": {
    "start": "2025-01-01",
    "end": "2025-12-31",
    "date_type": "business_event_date"
  },
  "sql_terms": [],
  "rag_keywords": [],
  "warnings": []
}
```

## Rules

- Convert Buddhist years such as 2568 to Gregorian 2025.
- Normalize FY, quarter, month, and year ranges.
- Extract table names, IDs, field names, and document IDs.
- Use `business_event_date` for business event timing.
- Use `posting_date` for accounting/ledger timing.
- Use both only for mismatch/backposting questions.

## Failure Modes

- Ambiguous date window.
- Thai/English mixed entity alias.
- User-provided candidate value that must be verified later.
