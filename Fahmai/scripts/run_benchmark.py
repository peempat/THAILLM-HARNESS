from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.evaluator import score_answer, summarize_scores
from agent.pipeline import run_pipeline
from agent.tools.csv_loader import read_questions


def main() -> int:
    parser = argparse.ArgumentParser(description="Run harness planning over benchmark questions.")
    parser.add_argument("--questions-csv", help="Questions CSV path.")
    parser.add_argument("--ground-truth-csv", help="Ground truth CSV path.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of questions.")
    parser.add_argument("--execute-rag", action="store_true", help="Run markdown RAG for routed RAG tasks.")
    parser.add_argument("--use-llm", action="store_true", help="Use configured LLM for final composing.")
    parser.add_argument("--use-local-llm", action="store_true", help="Alias for --use-llm.")
    parser.add_argument("--out", default="artifacts/benchmark_routes.csv", help="CSV output path.")
    parser.add_argument("--jsonl", default="artifacts/benchmark_states.jsonl", help="Full state JSONL output path.")
    parser.add_argument("--summary", default="artifacts/benchmark_summary.json", help="Summary JSON output path.")
    args = parser.parse_args()

    settings = Settings.from_env()
    questions_csv = Path(args.questions_csv) if args.questions_csv else settings.workspace_root / "data" / "questions.csv"
    ground_truth_csv = (
        Path(args.ground_truth_csv) if args.ground_truth_csv else settings.workspace_root / "data" / "ground_truth.csv"
    )
    rows = read_questions(questions_csv)
    truth_by_id = {row.get("id"): row for row in read_questions(ground_truth_csv)} if ground_truth_csv.exists() else {}
    if args.limit:
        rows = rows[: args.limit]

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = settings.project_root / out_path
    jsonl_path = Path(args.jsonl)
    if not jsonl_path.is_absolute():
        jsonl_path = settings.project_root / jsonl_path
    summary_path = Path(args.summary)
    if not summary_path.is_absolute():
        summary_path = settings.project_root / summary_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    scored_rows = []
    with out_path.open("w", encoding="utf-8-sig", newline="") as csv_handle, jsonl_path.open(
        "w", encoding="utf-8"
    ) as jsonl_handle:
        writer = csv.DictWriter(
            csv_handle,
            fieldnames=[
                "id",
                "labels",
                "needs_sql",
                "needs_rag",
                "needs_finance",
                "is_prompt_injection",
                "subtask_count",
                "final_answer",
                "expected_answer",
                "suite",
                "match",
                "score",
                "missing_numbers",
                "missing_terms",
            ],
        )
        writer.writeheader()
        for row in rows:
            state = run_pipeline(
                question=row["question"],
                question_id=row.get("id"),
                settings=settings,
                execute_rag=args.execute_rag,
                use_local_llm=args.use_llm or args.use_local_llm,
            )
            route = state["route"]
            truth = truth_by_id.get(row.get("id"), {})
            expected = truth.get("answer", "")
            predicted = state.get("final_answer") or ""
            score = score_answer(predicted, expected)
            scored_row = {
                "id": row.get("id"),
                "labels": "|".join(route.get("labels", [])),
                "needs_sql": route.get("needs_sql"),
                "needs_rag": route.get("needs_rag"),
                "needs_finance": route.get("needs_finance"),
                "is_prompt_injection": state["guardrail"].get("is_prompt_injection"),
                "subtask_count": len(state["plan"].get("subtasks", [])),
                "final_answer": predicted,
                "expected_answer": expected,
                "suite": truth.get("suite", ""),
                "match": score["match"],
                "score": score["score"],
                "missing_numbers": "|".join(score["missing_numbers"]),
                "missing_terms": "|".join(score["missing_terms"]),
            }
            writer.writerow(
                scored_row
            )
            scored_rows.append(scored_row)
            jsonl_handle.write(json.dumps(state, ensure_ascii=False, default=str) + "\n")

    summary = summarize_scores(scored_rows)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Wrote {jsonl_path}")
    print(f"Wrote {summary_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
