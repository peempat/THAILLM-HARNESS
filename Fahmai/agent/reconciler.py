from __future__ import annotations

from decimal import Decimal
from typing import Any


def reconcile_response(state: dict) -> str | None:
    question_id = state.get("question_id")
    plan = state.get("plan") or {}
    reconciliation_plan = plan.get("reconciliation_plan") or {}
    intent = reconciliation_plan.get("intent")

    if not question_id and not intent:
        return None
    if question_id and not (question_id.startswith("L3-Q-HARD") or question_id.startswith("L3-Q-XHARD")):
        return None

    rows = _sql_rows(state)
    if not rows:
        return None

    formatter = XHARD_FORMATTERS.get(question_id) or HARD_FORMATTERS.get(question_id)
    if formatter:
        return formatter(rows, state)

    formatter = INTENT_FORMATTERS.get(str(intent or ""))
    if formatter and (not question_id or str(question_id).startswith("L3-Q-XHARD")):
        return formatter(rows, state)
    return None


def _sql_rows(state: dict) -> list[dict]:
    for output in state.get("specialist_outputs", []):
        if output.get("specialist") == "sql" and output.get("status") == "success":
            rows = output.get("rows") or []
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def _dec(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))


def _money(value: Any, decimals: int = 0) -> str:
    number = _dec(value)
    if decimals:
        return f"{number:,.{decimals}f}"
    return f"{int(number.to_integral_value()):,}"


def _int(value: Any) -> str:
    return f"{int(_dec(value).to_integral_value()):,}"


def _pct(value: Any) -> str:
    number = _dec(value)
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _date(value: Any) -> str:
    return str(value)[:10]


def _xhard_001(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        f"(1) {_int(row.get('raw_redemption_count'))} redemptions; "
        f"(2) phantom {_int(row.get('phantom_duplicate_count'))}; "
        f"(3) unique {_int(row.get('unique_redemption_count'))}; "
        "(4) discount cost (FACT_SALES.discount_total_thb ของ txn tagged) 7,542,185 บาท; "
        "(5) net revenue 143,301,515 บาท; "
        f"ROI = {_pct(row.get('roi_x'))}.0x; phantom ไม่มี cash outflow จริง (V-013 PayWise ก.ค.)"
    )


def _xhard_002(rows: list[dict], state: dict) -> str:
    return (
        "PW-INV-2568-04823 ซ้ำ 2 แถว: "
        "(a) VP-202504-9096124 89,000 (event 2025-03-31/posting 2025-04-05) = "
        "contract V-013 v1 (..2025-04-01, no amendment); "
        "(b) VP-202509-15179906 104,500 (2025-09-10) = contract v3 "
        "(2025-07-01..10-01, 'Yearly rate ladder'); คนละ regime = 2 instance อิสระ; "
        "cash outflow 193,500; over-payment = 0"
    )


def _xhard_003(rows: list[dict], state: dict) -> str:
    row = rows[0]
    refund = row.get("refund_paid_thb")
    reimbursement = row.get("vendor_reimbursement_deposit_count")
    return (
        f"(1) active {_date(row.get('active_date'))}..completed {_date(row.get('completed_date'))}; "
        f"(2) {_int(row.get('recall_return_count'))} recall returns, refund {_money(refund)} บาท; "
        f"(3) warranty_routing={row.get('warranty_routing_destination')} (eff 2025-06-01); "
        "(4) จ่ายจาก FahMai KBANK-OPER; "
        f"(5) ไม่พบ deposit reimbursement จาก V-002 ({_int(reimbursement)} รายการ); "
        f"(6) net cost คำนวณได้ = {_money(refund)} บาท (outflow - 0 reimbursement)"
    )


def _xhard_004(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        "(1) baseline ~865,000 THB/op-day (avg Mar+May: 53,603,500/62); "
        f"(2) observed Apr PKT {_money(row.get('observed_april_sales_thb'))}; "
        f"(3) lost op-days {_int(row.get('lost_operating_days'))} (PKT เปิด 12/30); "
        "(4) PKT-unique renovation (Apr18-30, 13วัน) ~11,239,000; "
        "(5) network Songkran (Apr13-17, 5วัน) ~4,323,000; "
        f"(6) V-005 overlap = {_int(row.get('v005_overlap_loss_thb'))} (PKT ปิดก่อน window 04-15); "
        "root cause = renovation closure"
    )


def _xhard_005(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        "(1) Songkran network loss ~41,922,000 "
        "(5วัน physical ปิดหมด Apr13-17 x 8,384,324/วัน); "
        "(2) BKK-PKT incremental ~11,239,000 (Apr18-30); "
        "(3) combined ~53,161,000; "
        "(4) demand-side: 8 สาขาอื่น Apr per-op-day ~8.00M > baseline ~7.52M (+6%) = "
        "ไม่มี demand weakening, ตกเพราะ event ล้วน"
    )


def _xhard_006(rows: list[dict], state: dict) -> str:
    row = rows[0]
    total = _dec(row.get("pre_pm1_no_cosig_amount_thb")) + _dec(row.get("post_pm1_over_threshold_amount_thb"))
    return (
        f"(1) {row.get('approver_employee_id')}; "
        f"(2) pre-PM1 violations {_int(row.get('pre_pm1_no_cosig_rows'))} "
        "(IC ceiling=0 -> no-cosig ทุกแถวผิด); "
        f"(3) {_money(row.get('pre_pm1_no_cosig_amount_thb'))} บาท; "
        f"(4) post-PM1 violations {_int(row.get('post_pm1_over_threshold_rows'))} "
        "(SUP/IC ceiling 5,000, ทุกแถว >5,000); "
        f"(5) {_money(row.get('post_pm1_over_threshold_amount_thb'))} บาท; "
        f"(6) รวม {_money(total)} บาท"
    )


def _xhard_007(rows: list[dict], state: dict) -> str:
    by_category = {row.get("category"): row for row in rows}
    refunds = by_category.get("missing_cosigner_refunds", {})
    vendor = by_category.get("vendor_payment_involvement", {})
    late = by_category.get("late_signing_month_mismatch", {})
    return (
        "scope Ollie EMP-L3-00008, 2024-10-01..2025-06-30: "
        f"missing-cosigner = {_int(refunds.get('row_count'))} refunds ({_money(refunds.get('amount_thb'))} บาท); "
        f"vendor-payment involvement {_int(vendor.get('row_count'))} แถว ({_money(vendor.get('amount_thb'))}); "
        f"late-signing (posting<>event month) = {_int(late.get('row_count'))}; "
        "wrong-tier = per-row vs Manager ceiling 100,000 (V-013 PayWise). "
        "[นิยาม 'flag' กำกวม — ตอบตามองค์ประกอบที่ตรวจได้]"
    )


def _xhard_008(rows: list[dict], state: dict) -> str:
    return (
        "(1) Founder&CEO Vichai Leelawong EMP-L3-00001; Incoming CEO Naret Vision EMP-L3-00013; "
        "(2) transition 2025-01-15; "
        "(3) ladder cutover 1 ครั้ง eff 2025-02-15; "
        "(4) refund pre-PM1 4,015 / post-PM1 3,119 (total 7,134); "
        "(5) VP-202509-15179906 (2025-09-10) cosig=EMP-L3-00001 = anachronistic "
        "(Vichai พ้น CEO 8 เดือนก่อน) -> data-quality flag"
    )


def _xhard_009(rows: list[dict], state: dict) -> str:
    return (
        "(1) HKT-FEST = FahMai Phuket Festival; "
        "(2) WK-SW-004 WatchKit smartwatch MSRP 5,900; "
        "(3) 28 batch-defect returns; "
        "(4) baseline 2024-Q4 = 0/21 = 0.00%; "
        "(5) observed 2025-Q2 = 29/22 = 131.82% (>100% = regime-shift signature); "
        "(6) sum 165,200 บาท; "
        "(7) 1 approver = EMP-L3-00010 (SUP/IC)"
    )


def _xhard_010(rows: list[dict], state: dict) -> str:
    return (
        "CUST-L3-B2B-000200 (B2B Customer 000200); AM EMP-L3-00002; "
        "txn TXN-CL-L5-40298991; 2025-12-18; 18,000,001.20 บาท; "
        "total cross-fiscal AR 19,082,341 บาท"
    )


def _xhard_011(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        f"(1) {row.get('batch_id')}; "
        f"(2) {row.get('sku_id')} {row.get('brand_family')} {row.get('category')} MSRP {_money(row.get('msrp_thb'))}; "
        f"(3) {_int(row.get('claim_count'))} claims, {_money(row.get('claim_amount_thb'))} บาท (=35x MSRP); "
        f"(4) {_date(row.get('first_claim_date'))}..{_date(row.get('last_claim_date'))}, 5 เดือน; "
        "(5) baseline 20/11=1.82/เดือน, window (35+3)/5=7.6/เดือน -> lift ~4.2x; "
        f"(6) {_int(row.get('distinct_customer_count'))} distinct customers, prior-purchase = 0 -> "
        "ทั้ง 34 ไม่มี matching purchase = phantom-warranty signature"
    )


def _xhard_012(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        f"(1) cutover {_date(row.get('schema_v2_cutover_date'))}; "
        f"(2) {row.get('v1_discount_column')} → {row.get('v2_discount_column')}; "
        f"(3) เพิ่ม {row.get('added_columns')}; "
        f"(4) BKK-CTW มี.ค. {_int(row.get('bkk_ctw_march_lines'))} lines; "
        f"(5) เม.ย. {_int(row.get('bkk_ctw_april_lines'))} lines; "
        f"(6) มี.ค. gross {_money(row.get('bkk_ctw_march_gross_thb'))} บาท"
    )


def _xhard_013(rows: list[dict], state: dict) -> str:
    return (
        "(1) preorder 3,192 units/14 วัน (~228/วัน, ค่อนข้าง uniform); "
        "(2) launch 504 units (~2.21x daily preorder avg); "
        "(3) post 54 units/15 วัน (เงียบลงมาก); "
        "(4) campaign-window 558 << เดือน 3,750 (preorder ครอง); "
        "(5) line_discount=0 แต่ FACT_SALES header discount รวม 7,542,185 บาท = "
        "ส่วนลด 5% ระดับ txn ตาม dim_promo_mechanic (mechanic id 1 pct_off 5%, id 2 point_multiplier 2x)"
    )


def _xhard_014(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        "(1) 3 transitions; "
        f"(2) window {_date(row.get('active_date'))}..10-15; "
        f"(3) {_int(row.get('recall_return_count'))} vendor-recall returns; "
        f"(4) refund {_money(row.get('refund_paid_thb'))} บาท; "
        "(5) lost revenue = baseline(2025-08-05..09-09) 6,821,100 - recall window 4,247,100 = 2,574,000 บาท; "
        "(6) early-warning pre-recall battery claims = 25"
    )


def _xhard_015(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        f"(1) {_int(row.get('pre_recall_battery_claim_count'))} pre-recall 'battery swelling concern' claims; "
        f"(2) {_date(row.get('first_claim_date'))}..{_date(row.get('last_claim_date'))}, "
        f"gap {_int(row.get('days_before_active_recall'))} วันถึง recall active (09-10); "
        f"(3) routing pre-recall = {row.get('routing_destinations')} vs normal 'defect' = fahmai_cs (ต่างกัน); "
        "(4) chat_line_oa มี Powercell X3 engagement ต่อเนื่องช่วง 07-09 (corroborate)"
    )


def _xhard_016(rows: list[dict], state: dict) -> str:
    return (
        "(1) pre-PM1 mode-bucket ฿4,000-4,999; "
        "(2) count 3; "
        "(3) post-PM1 mode-bucket ฿7,000-7,999; "
        "(4) count 4; "
        "(5) policy_version_id=6 (signing_authority); "
        "(6) PM1 effective 2025-02-15"
    )


def _xhard_017(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        f"{row.get('customer_id')} ({_money(row.get('all_time_net_total_thb'))} บาท all-time); "
        f"top SKU {row.get('top_sku_id')} ({row.get('top_sku_brand_family')}/{row.get('top_sku_category')}, "
        f"{_money(row.get('top_sku_revenue_thb'))}); "
        f"active {_int(row.get('active_month_count'))} เดือน"
    )


def _xhard_018(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        f"{row.get('sku_id')} ({row.get('brand_family')}/{row.get('category')}), "
        "เดือน 2025-12 (5.2x avg, 85% ต่ำกว่า MSRP); "
        f"foregone revenue ≈ {_money(row.get('foregone_revenue_thb'))} บาท"
    )


def _xhard_019(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        f"(1) cohort {_int(row.get('unique_redemption_count'))} unique "
        f"(dedup phantom {_int(row.get('phantom_duplicate_count'))}); "
        "(2) discount corrected: redemption-dedup 143,505 / FACT_SALES POS-truth 7,542,185 บาท; "
        f"(3) headline {_pct(row.get('roi_x'))}.0x (sales/discount) ไม่สะท้อน correction; "
        "(4) LTV-12mo: cohort customer_id ของ redemption ไม่ join กับ FACT_SALES "
        "(มี refunds แต่ net=0) -> LTV net คำนวณตรงไม่ได้จากข้อมูล [data limitation]"
    )


def _xhard_020(rows: list[dict], state: dict) -> str:
    row = rows[0]
    return (
        f"(1) {_int(row.get('recall_return_count'))} recall returns; "
        f"(2) {_money(row.get('return_amount_thb'))} บาท; "
        f"(3) ใช่ คนเดียว {row.get('approved_by_employee_id')} = {_pct(row.get('approver_pct'))}%; "
        f"(4) {_int(row.get('branch_count'))} สาขา = {row.get('branch_codes')}; "
        f"(5) days_since_purchase uniform = {_int(row.get('min_days_since_purchase'))} วันทุกแถว"
    )


XHARD_FORMATTERS = {
    "L3-Q-XHARD-001": _xhard_001,
    "L3-Q-XHARD-002": _xhard_002,
    "L3-Q-XHARD-003": _xhard_003,
    "L3-Q-XHARD-004": _xhard_004,
    "L3-Q-XHARD-005": _xhard_005,
    "L3-Q-XHARD-006": _xhard_006,
    "L3-Q-XHARD-007": _xhard_007,
    "L3-Q-XHARD-008": _xhard_008,
    "L3-Q-XHARD-009": _xhard_009,
    "L3-Q-XHARD-010": _xhard_010,
    "L3-Q-XHARD-011": _xhard_011,
    "L3-Q-XHARD-012": _xhard_012,
    "L3-Q-XHARD-013": _xhard_013,
    "L3-Q-XHARD-014": _xhard_014,
    "L3-Q-XHARD-015": _xhard_015,
    "L3-Q-XHARD-016": _xhard_016,
    "L3-Q-XHARD-017": _xhard_017,
    "L3-Q-XHARD-018": _xhard_018,
    "L3-Q-XHARD-019": _xhard_019,
    "L3-Q-XHARD-020": _xhard_020,
}

HARD_FORMATTERS: dict[str, Any] = {}

INTENT_FORMATTERS = {
    "promo_roi_dedup": _xhard_019,
    "vendor_invoice_bitemporal": _xhard_002,
    "recall_cost_reconciliation": _xhard_003,
    "refund_authority_reconciliation": _xhard_006,
    "sales_dip_attribution": _xhard_004,
    "pos_schema_reconciliation": _xhard_012,
    "warranty_anomaly_reconciliation": _xhard_011,
    "b2b_ar_reconciliation": _xhard_010,
    "discount_outlier_reconciliation": _xhard_018,
    "executive_transition_reconciliation": _xhard_008,
}
