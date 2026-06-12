# Answer Checker Prompt

## Goal

Decide whether a proposed final answer is supported and grader-ready.

## SQL No Data / Schema Missing Checks

- `attempts.length >= max_sql_retries`, unless schema registry proves field absent immediately.
- At least one schema inspection occurred for schema errors.
- Empty-result retries used meaningful alternatives.
- `refusal_topic` is present.
- No unverified candidate numbers are included.

## RAG No Data Checks

- `attempts.length >= max_retries`.
- Query variants are meaningfully different.
- SQL was used if the topic could exist in structured data.
- `refusal_topic` is present.

## Output JSON

```json
{
  "status": "pass | fail | retry",
  "reasons": [],
  "retry_to": null,
  "final_answer": "..."
}
```
