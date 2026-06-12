from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.tools.embedding_client import EmbeddingClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Qwen3 embedding endpoint.")
    parser.add_argument("--text", default="ทดสอบ embedding สำหรับ FahMai")
    args = parser.parse_args()

    settings = Settings.from_env()
    result = EmbeddingClient(settings).embed(args.text)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
