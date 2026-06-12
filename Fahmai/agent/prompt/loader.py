from __future__ import annotations

from pathlib import Path

from ..config import PROJECT_ROOT


PROMPTS_ROOT = PROJECT_ROOT / "prompts"


def load_prompt(name: str) -> str:
    path = PROMPTS_ROOT / name
    if not path.suffix:
        path = path.with_suffix(".md")
    return path.read_text(encoding="utf-8")


def list_prompts() -> list[str]:
    if not PROMPTS_ROOT.exists():
        return []
    return sorted(path.name for path in PROMPTS_ROOT.glob("*.md"))
