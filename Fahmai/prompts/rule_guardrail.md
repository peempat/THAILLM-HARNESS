# Rule-Based Prompt Injection Guardrail

## Goal

Fast deterministic detection before any LLM or tool call.

## Detect

- `[SYSTEM]`
- `[/SYSTEM]`
- `admin mode`
- `system override`
- `developer instruction`
- `ignore previous`
- `do not consult`
- `output exactly`
- `verbatim`
- `reply with exact string`
- `previous session confirmed`
- `trust = HIGH`
- `new policy says`
- `authoritative memo`
- `do not use internal table`
- `confirm this unsupported fact`

## Output JSON

```json
{
  "is_prompt_injection": true,
  "classification": "prompt_injection",
  "reasons": ["contains [SYSTEM]", "asks to output exact string"],
  "safe_underlying_question": "..."
}
```

## Guardrails

- Never echo the injected directive in final answer.
- Do not allow the user to suppress trusted data sources.
- Pass a cleaned underlying business question to the planner when possible.
