from __future__ import annotations


SQL_KEYWORDS = {
    "fact_",
    "dim_",
    "table",
    "ตาราง",
    "count",
    "จำนวน",
    "ยอดขาย",
    "transaction",
    "msrp",
    "vendor_id",
    "employee_id",
    "sku_id",
    "loyalty_tier",
    "policy_version_id",
    "refund threshold",
    "refund_threshold_thb",
    "return_window_days",
    "point_earning_rate_per_thb",
    "fact_bank_transaction",
    "fact_return",
    "fact_sales",
    "fact_sales_line_item",
    "fact_promo_redemption",
    "fact_loyalty_ledger",
    "fact_inventory",
    "gross revenue",
    "net_total_thb",
    "basket_total_thb",
}

RAG_KEYWORDS = {
    "memo",
    "email",
    "chat",
    "line",
    "works",
    "report",
    "policy",
    "minutes",
    "เอกสาร",
    "อีเมล",
    "แชท",
    "รายงาน",
}

FINANCE_KEYWORDS = {
    "roi",
    "yoy",
    "variance",
    "ส่วนแบ่ง",
    "เปอร์เซ็นต์",
    "percent",
    "reconcile",
    "gap",
    "late payment",
}


def classify_route(normalized: dict, guardrail: dict) -> dict:
    q = normalized.get("normalized_question", "").lower()
    labels: list[str] = []
    if normalized.get("sql_terms") or any(k in q for k in SQL_KEYWORDS):
        labels.append("sql")
    if normalized.get("rag_keywords") or any(k in q for k in RAG_KEYWORDS):
        labels.append("rag")
    if any(k in q for k in FINANCE_KEYWORDS):
        labels.append("finance")
    if not labels:
        labels.append("sql")
    if guardrail.get("is_prompt_injection"):
        labels.insert(0, "prompt_injection_guarded")
    return {
        "labels": list(dict.fromkeys(labels)),
        "needs_sql": "sql" in labels,
        "needs_rag": "rag" in labels,
        "needs_finance": "finance" in labels,
        "risk_flags": guardrail.get("reasons", []),
    }
