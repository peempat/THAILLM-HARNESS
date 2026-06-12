from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.tools.schema import get_schema_info, write_schema_cache


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect FahMai PostgreSQL schema with CSV fallback.")
    parser.add_argument("--table", help="Optional table or view name.")
    parser.add_argument("--out", help="Write schema JSON to this path.")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.out:
        schema = write_schema_cache(settings, Path(args.out), args.table)
    else:
        schema = get_schema_info(settings, args.table)
    print(json.dumps(schema, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
