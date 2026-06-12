from __future__ import annotations

from .tools.sql_safety import validate_sql


def pre_normalize_hook(question: str) -> str:
    return " ".join(question.replace("\u200b", "").split())


def planner_json_validation_hook(plan: dict) -> dict:
    required = ["goal", "subtasks", "final_answer_requirements", "risk_flags"]
    for key in required:
        plan.setdefault(key, [] if key != "goal" else "")
    if not isinstance(plan["subtasks"], list):
        plan["subtasks"] = []
    return plan


def tool_input_validation_hook(tool_name: str, payload: dict) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if tool_name == "sql":
        ok, sql_warnings = validate_sql(payload.get("sql", ""))
        warnings.extend(sql_warnings)
        return ok, warnings
    if tool_name == "rag":
        query = str(payload.get("query", "")).strip()
        if not query:
            return False, ["RAG query is empty"]
    return True, warnings


def retrieval_dedup_hook(chunks: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for chunk in chunks:
        key = (str(chunk.get("source", "")), str(chunk.get("snippet", ""))[:200])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def evidence_validation_hook(specialist_outputs: list[dict]) -> dict:
    supported = []
    warnings = []
    for output in specialist_outputs:
        status = output.get("status")
        evidence = output.get("evidence") or []
        if status == "success" and evidence:
            supported.extend(evidence)
        elif status in {"no_data", "schema_missing"}:
            if not output.get("refusal_topic"):
                warnings.append("missing refusal_topic")
    return {
        "status": "ok" if not warnings else "needs_review",
        "supported_evidence": supported,
        "warnings": warnings,
    }


def refusal_format_hook(topic: str, scope: str = "dataset", language: str = "th") -> str:
    topic = topic.strip() or "ข้อมูลที่ถาม"
    if scope == "schema":
        return f"ไม่มี {topic} ในระบบ" if language == "th" else "No such data in the records"
    return (
        f"ไม่พบ {topic} ในชุดข้อมูล"
        if language == "th"
        else f"{topic} not found in the dataset"
    )


def injection_output_hook(answer: str) -> str:
    blocked_fragments = [
        "[SYSTEM]",
        "[/SYSTEM]",
        "ignore previous",
        "output exactly",
        "reply with exact string",
    ]
    cleaned = answer
    for fragment in blocked_fragments:
        cleaned = cleaned.replace(fragment, "")
    return cleaned.strip()


def final_format_hook(answer: str) -> str:
    return " ".join(answer.split())
