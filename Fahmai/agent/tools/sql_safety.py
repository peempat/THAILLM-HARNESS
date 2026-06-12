from __future__ import annotations

import re


FORBIDDEN_WORDS = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "replace",
    "grant",
    "revoke",
    "call",
    "copy",
    "execute",
    "vacuum",
    "analyze",
]

FORBIDDEN_FUNCTIONS = [
    "pg_read_file",
    "pg_ls_dir",
    "pg_sleep",
    "dblink",
    "lo_export",
    "lo_import",
]

SUSPICIOUS_COMMENT_RE = re.compile(
    r"--.*(?:ignore|system|developer|override|output exactly)|/\*.*?(?:ignore|system|developer|override|output exactly).*?\*/",
    re.IGNORECASE | re.DOTALL,
)


def _strip_trailing_semicolon(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def validate_sql(sql: str) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if not sql or not sql.strip():
        return False, ["SQL is empty"]

    stripped = sql.strip()
    normalized = stripped.lower()
    if not re.match(r"^\s*(select|with)\b", normalized):
        warnings.append("Only SELECT or WITH SELECT statements are allowed")

    if ";" in _strip_trailing_semicolon(stripped):
        warnings.append("Semicolon chaining is blocked")

    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", normalized):
            warnings.append(f"Forbidden SQL operation: {word}")

    for func in FORBIDDEN_FUNCTIONS:
        if re.search(rf"\b{re.escape(func)}\s*\(", normalized):
            warnings.append(f"Forbidden SQL function: {func}")

    if SUSPICIOUS_COMMENT_RE.search(stripped):
        warnings.append("SQL comment contains suspicious instruction text")

    return not warnings, warnings


def ensure_limit(sql: str, default_limit: int = 50) -> str:
    stripped = _strip_trailing_semicolon(sql)
    lowered = stripped.lower()
    if re.search(r"\blimit\s+\d+\b", lowered):
        return stripped
    if re.search(r"\b(count|sum|avg|min|max)\s*\(", lowered):
        return stripped
    return f"{stripped}\nLIMIT {default_limit}"
