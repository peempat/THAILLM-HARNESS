from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.tools.vector_search import VectorSearch


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the local Qwen3 vector index.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    settings = Settings.from_env()
    results, warnings = VectorSearch(settings).search(args.query, top_k=args.top_k)
    print(json.dumps({"results": results, "warnings": warnings}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
