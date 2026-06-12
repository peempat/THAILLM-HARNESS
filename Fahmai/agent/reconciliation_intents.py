from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationIntent:
    name: str
    confidence: float
    required_sources: list[str]
    compute_steps: list[str]
    answer_shape: str
    reason: str


INTENT_RULES = [
    {
        "name": "promo_roi_dedup",
        "keywords": ["campaign", "promo", "redemption", "duplicate", "phantom", "roi", "discount"],
        "required_sources": ["FACT_PROMO_REDEMPTION", "FACT_SALES", "FACT_BANK_TRANSACTION", "dim_promo_mechanic"],
        "compute_steps": [
            "count raw redemption rows",
            "deduplicate by transaction/customer grain",
            "compare redemption discount to sales header discount",
            "compute net revenue and ROI",
            "check whether phantom rows created real cash outflow",
        ],
        "answer_shape": "ordered_tuple",
    },
    {
        "name": "vendor_invoice_bitemporal",
        "keywords": ["vendor", "invoice", "duplicate", "contract", "posting", "event", "bitemporal"],
        "required_sources": ["FACT_VENDOR_PAYMENT", "DIM_VENDOR_CONTRACT_VERSION", "FACT_BANK_TRANSACTION"],
        "compute_steps": [
            "identify duplicated vendor invoice IDs",
            "compare event date and posting date",
            "resolve contract version as of each payment date",
            "sum cash outflow and determine over-payment",
        ],
        "answer_shape": "row_by_row_reconciliation",
    },
    {
        "name": "recall_cost_reconciliation",
        "keywords": ["recall", "warranty", "refund", "reimbursement", "vendor", "routing", "net cost"],
        "required_sources": [
            "dim_product_recall_history",
            "FACT_RETURN",
            "FACT_REFUND_PAID",
            "FACT_BANK_TRANSACTION",
            "FACT_WARRANTY_CLAIM",
            "DIM_POLICY_VERSION",
        ],
        "compute_steps": [
            "resolve recall active/completed window",
            "count affected returns or warranty claims",
            "sum refund or claim outflow",
            "look for vendor reimbursement inflow",
            "compute net cost and policy routing",
        ],
        "answer_shape": "ordered_tuple",
    },
    {
        "name": "refund_authority_reconciliation",
        "keywords": ["refund", "approver", "cosig", "co-signer", "signing authority", "ladder", "ceiling", "pm1"],
        "required_sources": ["FACT_REFUND_PAID", "DIM_EMPLOYEE", "dim_signing_authority_ladder", "DIM_POLICY_VERSION"],
        "compute_steps": [
            "resolve employee role and department",
            "resolve effective approval ladder per refund date",
            "classify rows before and after policy cutover",
            "sum violating rows and amounts",
        ],
        "answer_shape": "policy_violation_breakdown",
    },
    {
        "name": "sales_dip_attribution",
        "keywords": ["sales dip", "gap", "baseline", "operating-day", "songkran", "renovation", "root cause"],
        "required_sources": ["FACT_SALES", "DIM_BRANCH", "docs/minutes", "docs/memo"],
        "compute_steps": [
            "construct baseline from comparable dates or branches",
            "compute observed period sales",
            "split loss by event windows",
            "check overlap between causes",
            "state root cause and demand-side check",
        ],
        "answer_shape": "attribution_tuple",
    },
    {
        "name": "pos_schema_reconciliation",
        "keywords": ["pos", "schema", "cutover", "discount_amt", "discount_total", "logs"],
        "required_sources": ["logs/pos_*.tsv", "pos_logs", "FACT_SALES", "FACT_SALES_LINE_ITEM"],
        "compute_steps": [
            "detect schema version cutover date",
            "map old columns to new columns",
            "count lines before and after cutover",
            "reconcile gross amounts against table facts",
        ],
        "answer_shape": "schema_tuple",
    },
    {
        "name": "warranty_anomaly_reconciliation",
        "keywords": ["warranty", "claim", "batch", "phantom", "prior purchase", "vendor batch defect", "lift"],
        "required_sources": ["FACT_WARRANTY_CLAIM", "FACT_SALES_LINE_ITEM", "DIM_PRODUCT", "DIM_VENDOR"],
        "compute_steps": [
            "extract batch identifier",
            "count claims in anomaly window",
            "compare to baseline claim rate",
            "check prior matching purchases",
            "summarize anomaly signature",
        ],
        "answer_shape": "anomaly_case_file",
    },
    {
        "name": "b2b_ar_reconciliation",
        "keywords": ["b2b", "open ar", "unpaid", "cross-fiscal", "payment_due", "payment_received"],
        "required_sources": ["FACT_SALES", "DIM_CUSTOMER", "DIM_EMPLOYEE"],
        "compute_steps": [
            "filter unpaid B2B sales as of requested date",
            "rank by net_total_thb",
            "attach account manager and customer name",
            "sum total cross-fiscal AR",
        ],
        "answer_shape": "entity_tuple",
    },
    {
        "name": "discount_outlier_reconciliation",
        "keywords": ["outlier", "deep discount", "msrp", "foregone", "volume", "revenue per unit"],
        "required_sources": ["FACT_SALES_LINE_ITEM", "FACT_SALES", "DIM_PRODUCT"],
        "compute_steps": [
            "build monthly SKU unit baseline",
            "detect lift outlier",
            "compare unit price to MSRP",
            "compute foregone revenue",
        ],
        "answer_shape": "outlier_summary",
    },
    {
        "name": "executive_transition_reconciliation",
        "keywords": ["ceo", "transition", "founder", "incoming", "cutover", "anachronistic", "authority"],
        "required_sources": ["DIM_EMPLOYEE", "DIM_POLICY_VERSION", "FACT_REFUND_PAID", "FACT_VENDOR_PAYMENT", "docs/memo"],
        "compute_steps": [
            "resolve canonical leaders",
            "resolve transition evidence date",
            "compare policy cutover dates",
            "scan post-transition approvals for stale authority usage",
        ],
        "answer_shape": "timeline_and_flag",
    },
]


def classify_reconciliation_intent(question: str, question_parts: list[dict]) -> dict:
    text = " ".join([question] + [str(part.get("text", "")) for part in question_parts]).lower()
    ranked: list[ReconciliationIntent] = []
    for rule in INTENT_RULES:
        hits = [keyword for keyword in rule["keywords"] if keyword.lower() in text]
        if not hits:
            continue
        confidence = min(1.0, 0.35 + (len(hits) / max(len(rule["keywords"]), 1)))
        ranked.append(
            ReconciliationIntent(
                name=rule["name"],
                confidence=round(confidence, 3),
                required_sources=list(rule["required_sources"]),
                compute_steps=list(rule["compute_steps"]),
                answer_shape=rule["answer_shape"],
                reason=f"matched keywords: {', '.join(hits)}",
            )
        )
    ranked.sort(key=lambda item: item.confidence, reverse=True)
    if ranked:
        best = ranked[0]
    else:
        best = ReconciliationIntent(
            name="generic_multi_part",
            confidence=0.25 if len(question_parts) > 1 else 0.0,
            required_sources=[],
            compute_steps=["answer each part in order", "reuse earlier evidence when later parts depend on it"],
            answer_shape="ordered_answer" if len(question_parts) > 1 else "single_answer",
            reason="no specialized reconciliation pattern matched",
        )
    return {
        "intent": best.name,
        "confidence": best.confidence,
        "required_sources": best.required_sources,
        "compute_steps": best.compute_steps,
        "answer_shape": best.answer_shape,
        "reason": best.reason,
        "related_parts": _related_parts(question_parts),
    }


def _related_parts(question_parts: list[dict]) -> list[dict]:
    related = []
    for part in question_parts:
        depends_on = part.get("depends_on") or []
        if depends_on:
            related.append({"part_id": part.get("id"), "depends_on": depends_on, "reason": "derived or comparative part"})
    return related
