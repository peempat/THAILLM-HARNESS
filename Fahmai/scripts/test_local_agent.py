from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401
from agent.config import Settings
from agent.tools.local_agent import LocalAgentClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Test FahMai ModelHarbor local agent endpoints.")
    parser.add_argument("--message", default="Can you summarize the benefits of local LLMs?")
    parser.add_argument("--health-only", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args()

    settings = Settings.from_env()
    client = LocalAgentClient(settings)
    result = {"health": client.health()}

    if not args.health_only:
        chat = client.chat(
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": args.message},
            ],
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        result["chat"] = chat.to_dict()

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
