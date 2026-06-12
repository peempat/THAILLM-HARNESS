from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.pipeline import run_pipeline
from agent.tools.csv_loader import find_question


def _load_question(args, settings: Settings) -> tuple[str | None, str]:
    if args.question:
        return args.id, args.question
    if not args.id:
        raise SystemExit("Provide --question or --id")
    csv_path = Path(args.questions_csv) if args.questions_csv else settings.workspace_root / "data" / "questions.csv"
    row = find_question(csv_path, args.id)
    if not row:
        raise SystemExit(f"Question id not found: {args.id}")
    return row.get("id"), row["question"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FahMai harness for one question.")
    parser.add_argument("--id", help="Question id from data/questions.csv.")
    parser.add_argument("--question", help="Raw question text.")
    parser.add_argument("--questions-csv", help="Override questions CSV path.")
    parser.add_argument("--execute-rag", action="store_true", help="Run markdown keyword RAG specialist.")
    parser.add_argument("--use-llm", action="store_true", help="Use configured LLM for final composing.")
    parser.add_argument("--use-local-llm", action="store_true", help="Alias for --use-llm.")
    parser.add_argument(
        "--sql",
        action="append",
        default=[],
        help="Candidate read-only SQL to execute. Can be passed multiple times.",
    )
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")
    args = parser.parse_args()

    settings = Settings.from_env()
    question_id, question = _load_question(args, settings)
    state = run_pipeline(
        question=question,
        question_id=question_id,
        settings=settings,
        execute_rag=args.execute_rag,
        candidate_sqls=args.sql,
        use_local_llm=args.use_llm or args.use_local_llm,
    )
    print(json.dumps(state, ensure_ascii=False, indent=None if args.compact else 2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
