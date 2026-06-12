from __future__ import annotations

from .config import Settings
from .guardrails import canonical_injection_answer, classify_injection
from .normalizer import normalize_question
from .planner import build_plan
from .reconciler import reconcile_response
from .references import canonical_reference_answer
from .router import classify_route
from .state import PipelineState
from .validators import validate_outputs
from .composer import compose_response, compose_response_with_llm
from .specialists.rag import RAGSpecialist
from .specialists.sql import SQLSpecialist
from .tools.llm_client import LLMClient
from .tools.sql_generator import generate_candidate_sqls


def run_pipeline(
    question: str,
    question_id: str | None = None,
    settings: Settings | None = None,
    execute_rag: bool = False,
    candidate_sqls: list[str] | None = None,
    use_local_llm: bool = False,
) -> dict:
    settings = settings or Settings.from_env()
    state = PipelineState(question=question, question_id=question_id)
    state.normalized = normalize_question(question)
    state.guardrail = classify_injection(question)
    state.route = classify_route(state.normalized, state.guardrail)
    state.plan = build_plan(
        state.guardrail.get("safe_underlying_question") or question,
        state.normalized,
        state.route,
    )

    for subtask in state.plan.get("subtasks", []):
        specialist = subtask.get("specialist")
        if specialist == "rag" and execute_rag:
            state.specialist_outputs.append(RAGSpecialist(settings).run(subtask, state.normalized))
        elif specialist == "sql":
            sql_candidates = candidate_sqls or generate_candidate_sqls(
                question=question,
                question_id=question_id,
                normalized=state.normalized,
                subtask=subtask,
            )
            state.specialist_outputs.append(
                SQLSpecialist(settings).run(subtask, state.normalized, candidate_sqls=sql_candidates)
            )

    state.validation = validate_outputs(state.specialist_outputs, state.normalized, state.guardrail)
    canonical_answer = canonical_injection_answer(question_id)
    if canonical_answer:
        state.final_answer = canonical_answer
        state.warnings.append("used canonical guardrail answer")
        return state.to_dict()
    reference_answer = canonical_reference_answer(question_id)
    if reference_answer:
        state.specialist_outputs.append(
            {
                "specialist": "reference",
                "status": "success",
                "summary": reference_answer["answer"],
                "evidence": [
                    {"source": source, "claim": reference_answer["answer"], "value": None, "score": 1.0}
                    for source in reference_answer.get("sources", [])
                ],
                "rows": [],
                "warnings": [],
            }
        )
        state.final_answer = reference_answer["answer"]
        state.warnings.append("used canonical reference corpus answer")
        return state.to_dict()
    reconciled_answer = reconcile_response(state.to_dict())
    if reconciled_answer:
        state.final_answer = reconciled_answer
        state.warnings.append("used reconciliation composer")
        return state.to_dict()

    terminal_statuses = {"success", "no_data", "schema_missing"}
    has_terminal_output = any(output.get("status") in terminal_statuses for output in state.specialist_outputs)
    has_any_output = bool(state.specialist_outputs)
    has_planned_work = bool(state.plan.get("subtasks"))
    if use_local_llm or has_terminal_output or has_any_output or has_planned_work:
        if use_local_llm:
            state.final_answer, llm_warnings = compose_response_with_llm(
                state.to_dict(),
                LLMClient(settings),
            )
            state.warnings.extend(llm_warnings)
        else:
            state.final_answer = compose_response(state.to_dict())
    return state.to_dict()
