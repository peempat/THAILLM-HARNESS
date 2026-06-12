from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.tools.schema import write_schema_cache


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local schema cache JSON file.")
    parser.add_argument("--table", help="Optional table/view to cache.")
    parser.add_argument("--out", default="artifacts/schema_cache.json")
    args = parser.parse_args()

    settings = Settings.from_env()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = settings.project_root / out_path
    schema = write_schema_cache(settings, out_path, args.table)
    print(f"Wrote {out_path} ({len(schema.get('tables', []))} tables)")
    for warning in schema.get("warnings", []):
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
