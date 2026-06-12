from __future__ import annotations

from ..hooks import refusal_format_hook


def build_refusal(topic: str, scope: str = "dataset", language: str = "th") -> dict:
    return {
        "specialist": "refusal",
        "status": "success",
        "topic": topic,
        "scope": scope,
        "answer": refusal_format_hook(topic, scope, language),
        "warnings": [],
    }
