from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass
class PipelineState:
    question: str
    question_id: str | None = None
    normalized: JsonDict = field(default_factory=dict)
    guardrail: JsonDict = field(default_factory=dict)
    route: JsonDict = field(default_factory=dict)
    plan: JsonDict = field(default_factory=dict)
    specialist_outputs: list[JsonDict] = field(default_factory=list)
    validation: JsonDict = field(default_factory=dict)
    final_answer: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "normalized": self.normalized,
            "guardrail": self.guardrail,
            "route": self.route,
            "plan": self.plan,
            "specialist_outputs": self.specialist_outputs,
            "validation": self.validation,
            "final_answer": self.final_answer,
            "warnings": self.warnings,
        }
