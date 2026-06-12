from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.evaluator import score_answer, summarize_scores
from agent.tools.csv_loader import read_questions


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate an existing benchmark CSV against ground truth.")
    parser.add_argument("--predictions", default="artifacts/benchmark_routes.csv")
    parser.add_argument("--ground-truth-csv", help="Ground truth CSV path.")
    parser.add_argument("--out", default="artifacts/benchmark_eval.csv")
    parser.add_argument("--summary", default="artifacts/benchmark_eval_summary.json")
    args = parser.parse_args()

    settings = Settings.from_env()
    predictions_path = Path(args.predictions)
    if not predictions_path.is_absolute():
        predictions_path = settings.project_root / predictions_path
    ground_truth_path = (
        Path(args.ground_truth_csv) if args.ground_truth_csv else settings.workspace_root / "data" / "ground_truth.csv"
    )
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = settings.project_root / out_path
    summary_path = Path(args.summary)
    if not summary_path.is_absolute():
        summary_path = settings.project_root / summary_path

    truth_by_id = {row.get("id"): row for row in read_questions(ground_truth_path)}
    with predictions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        predictions = list(csv.DictReader(handle))

    rows = []
    for prediction in predictions:
        truth = truth_by_id.get(prediction.get("id"), {})
        score = score_answer(prediction.get("final_answer"), truth.get("answer"))
        row = {
            **prediction,
            "suite": truth.get("suite", prediction.get("suite", "")),
            "expected_answer": truth.get("answer", prediction.get("expected_answer", "")),
            "match": score["match"],
            "score": score["score"],
            "missing_numbers": "|".join(score["missing_numbers"]),
            "missing_terms": "|".join(score["missing_terms"]),
        }
        rows.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize_scores(rows)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Wrote {summary_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
