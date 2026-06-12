from __future__ import annotations

from .hooks import evidence_validation_hook


def validate_outputs(specialist_outputs: list[dict], normalized: dict, guardrail: dict) -> dict:
    validation = evidence_validation_hook(specialist_outputs)
    warnings = list(validation.get("warnings", []))

    if guardrail.get("is_prompt_injection"):
        for output in specialist_outputs:
            text = str(output)
            if "[SYSTEM]" in text or "output exactly" in text.lower():
                warnings.append("specialist output may echo injected instruction")

    for output in specialist_outputs:
        if output.get("specialist") == "rag" and output.get("status") == "no_data":
            attempts = output.get("attempts", [])
            max_retries = output.get("max_retries", 3)
            if len(attempts) < max_retries:
                warnings.append("RAG no_data before max_retries")
        if output.get("specialist") == "sql" and output.get("status") in {"no_data", "schema_missing"}:
            if not output.get("refusal_topic"):
                warnings.append("SQL refusal missing topic")

    validation["warnings"] = warnings
    validation["status"] = "ok" if not warnings else "needs_review"
    validation["language"] = normalized.get("language", "th")
    return validation
