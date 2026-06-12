from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.tools.vector_search import build_vector_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local JSONL vector index with Qwen3 embeddings.")
    parser.add_argument("--limit", type=int, default=0, help="Limit chunks for quick tests. 0 means all chunks.")
    parser.add_argument("--out", help="Output JSONL path.")
    args = parser.parse_args()

    settings = Settings.from_env()
    out = Path(args.out) if args.out else settings.vector_index_path
    if not out.is_absolute():
        out = settings.workspace_root / out
    result = build_vector_index(settings, output_path=out, limit=args.limit or None)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
