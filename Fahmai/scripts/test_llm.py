from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.tools.llm_client import LLMClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Test configured FahMai chat LLM.")
    parser.add_argument("--message", default="ตอบสั้นๆ ว่า OpenTyphoon พร้อมใช้งานไหม")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args()

    settings = Settings.from_env()
    client = LLMClient(settings)
    result = client.chat(
        [
            {"role": "system", "content": "You are a concise helpful assistant."},
            {"role": "user", "content": args.message},
        ],
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    output = result.to_dict()
    if settings.llm_api_key:
        output["api_key_loaded"] = True
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
