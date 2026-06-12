from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = WORKSPACE_ROOT / "fah-mai-the-finale-enterprise-data-agentic-showdown"
TABLES_DIR = DATASET_ROOT / "tables"
KB_TABLES_DIR = DATASET_ROOT / "knowledge_base" / "folders" / "tables"


@dataclass(frozen=True)
class TableInfo:
    name: str
    source_path: Path
    guide_path: Path
    columns: list[str]
    row_count: int
    primary_key: str
    layer: str
    purpose: str
    route_clues: list[str]
    avoid: list[str]
    related_evidence: list[str]


TABLE_PURPOSES: dict[str, tuple[str, list[str], list[str], list[str]]] = {
    "DIM_BANK_ACCOUNT": (
        "Bank account master data for account IDs, bank names, account roles, branch association, opening balances, and statement cadence.",
        ["bank account", "account_id", "cash account", "settlement account", "statement cadence"],
        ["Line-level bank postings; use FACT_BANK_TRANSACTION for movements and balances after each transaction."],
        ["renders/bank_statement/", "FACT_BANK_TRANSACTION"],
    ),
    "DIM_BRANCH": (
        "Branch/store master data, including Thai and English names, branch type, service-center flag, and allocation coefficients.",
        ["branch", "store", "service center", "branch_code", "traffic share", "headcount share"],
        ["Sales, inventory, or staffing events by themselves; join to fact tables for activity."],
        ["docs/l1_kb/store_info/", "reports/"],
    ),
    "dim_care_plus_sku_tier": (
        "Care Plus plan price, coverage months, and Thai description by policy version and SKU/category.",
        ["Care Plus", "care_plus_price", "coverage", "policy version", "SKU tier"],
        ["Actual warranty claims or sales attachment rates; use FACT_WARRANTY_CLAIM or sales line items."],
        ["DIM_POLICY_VERSION", "DIM_PRODUCT", "docs/l1_kb/policies/"],
    ),
    "DIM_CUSTOMER": (
        "Customer profile master data, including contact fields, province/region, B2B subtype, loyalty tier, channel preference, and LINE OA usage.",
        ["customer", "customer_id", "loyalty tier", "B2B", "province", "LINE OA"],
        ["Customer support conversation content; use docs/chat_line_oa/ and FACT_CS_INTERACTION."],
        ["FACT_SALES", "FACT_LOYALTY_LEDGER", "docs/chat_line_oa/"],
    ),
    "DIM_DATE": (
        "Calendar reference data with Thai Buddhist-era string, day of week, public holiday flag/name, fiscal year, and fiscal quarter.",
        ["calendar", "holiday", "fiscal quarter", "fiscal year", "date_iso", "BE date"],
        ["Business metrics without joining to a fact table."],
        ["reports/"],
    ),
    "DIM_DEPARTMENT": (
        "Department master data with department code, Thai/English names, and department type.",
        ["department", "dept_code", "dept type", "function"],
        ["Employee or product records by themselves; join through employee/product tables."],
        ["DIM_EMPLOYEE", "DIM_PRODUCT"],
    ),
    "DIM_EMPLOYEE": (
        "Employee master and organization structure data, including branch, department, position level, manager, dates, status, and canonical roles.",
        ["employee", "staff", "manager", "approver", "cosigner", "position", "reports_to"],
        ["Payroll amounts by period; use FACT_PAYROLL for pay and deductions."],
        ["FACT_PAYROLL", "dim_signing_authority_ladder", "docs/minutes/"],
    ),
    "DIM_POLICY_VERSION": (
        "Dated policy variables and values, including policy class, scope, effective/end dates, and source policy document filename.",
        ["policy", "effective date", "policy_version_id", "rule", "threshold", "as of date"],
        ["Narrative policy wording by itself; pair with memo or L1 KB docs when wording is requested."],
        ["docs/memo/", "docs/l1_kb/policies/", "dim_signing_authority_ladder"],
    ),
    "DIM_POSITION_LEVEL": (
        "Position-level reference data with rank and default signing authority amount.",
        ["position level", "rank", "signing authority", "approval ceiling"],
        ["Department-specific or policy-version-specific approval ladders; use dim_signing_authority_ladder."],
        ["dim_signing_authority_ladder", "DIM_EMPLOYEE"],
    ),
    "DIM_PRODUCT": (
        "Product/SKU master data, including brand family, department, category, MSRP, vendor, launch/EOL dates, warranty months, and Care Plus eligibility.",
        ["SKU", "product", "MSRP", "warranty", "vendor", "category", "launch", "end of life"],
        ["Customer-facing product copy; use docs/l1_kb/products/ for prose, but keep this table authoritative for structured values."],
        ["docs/l1_kb/products/", "FACT_SALES_LINE_ITEM", "dim_product_recall_history"],
    ),
    "dim_product_recall_history": (
        "Recall status transitions for SKUs over time.",
        ["recall", "product recall", "SKU status", "transition date"],
        ["Warranty claim amounts; use FACT_WARRANTY_CLAIM."],
        ["DIM_PRODUCT", "FACT_WARRANTY_CLAIM", "docs/memo/"],
    ),
    "DIM_PROMO_CAMPAIGN": (
        "Promotion campaign master data with campaign window, scope filter, and Thai/English descriptions.",
        ["campaign", "promotion", "promo", "scope", "start", "end"],
        ["Actual redemption counts or sales impact; use FACT_PROMO_REDEMPTION and FACT_SALES."],
        ["dim_promo_mechanic", "FACT_PROMO_REDEMPTION", "renders/e7_banner/"],
    ),
    "dim_promo_mechanic": (
        "Promotion mechanics by campaign, including discount type/value, point multiplier, minimum basket, and Thai description.",
        ["promo mechanic", "discount", "point multiplier", "min basket", "campaign rule"],
        ["Campaign date windows; use DIM_PROMO_CAMPAIGN."],
        ["DIM_PROMO_CAMPAIGN", "FACT_PROMO_REDEMPTION"],
    ),
    "dim_signing_authority_ladder": (
        "Approval ladder rules by policy version, position level, department, amount ceiling, and co-signer requirements.",
        ["approval", "signing authority", "cosigner", "amount ceiling", "policy_version_id"],
        ["Actual approved payments/refunds; use FACT_VENDOR_PAYMENT or FACT_REFUND_PAID."],
        ["DIM_POLICY_VERSION", "DIM_POSITION_LEVEL", "DIM_EMPLOYEE"],
    ),
    "DIM_VENDOR": (
        "Vendor master data, including Thai/English names, category, role, payment terms, invoice cadence, partner/component flags, and active dates.",
        ["vendor", "supplier", "payment terms", "invoice cadence", "partner brand"],
        ["Payment facts or invoices; use FACT_VENDOR_PAYMENT and rendered invoice evidence."],
        ["FACT_VENDOR_PAYMENT", "DIM_VENDOR_CONTRACT_VERSION", "renders/vendor_invoice/"],
    ),
    "DIM_VENDOR_CONTRACT_VERSION": (
        "Vendor contract version history with effective dates, PDF filename, and amendment summary.",
        ["vendor contract", "contract version", "amendment", "effective date"],
        ["Actual payment amounts; use FACT_VENDOR_PAYMENT."],
        ["DIM_VENDOR", "FACT_VENDOR_PAYMENT", "renders/vendor_invoice/"],
    ),
    "FACT_BANK_TRANSACTION": (
        "Bank posting fact table for cash movement, transaction type, counterparty, related entity references, amounts, and balance after posting.",
        ["bank transaction", "cash movement", "deposit", "fee", "balance", "bank_txn_id"],
        ["Bank account metadata; join DIM_BANK_ACCOUNT."],
        ["DIM_BANK_ACCOUNT", "renders/bank_statement/", "logs/paywise_fee_log_*.csv"],
    ),
    "FACT_CS_INTERACTION": (
        "Customer-support interaction fact table connecting customers, employees, branches, channels, interaction/resolution types, and related refund/warranty/chat IDs.",
        ["CS", "support", "interaction", "chat", "resolution", "customer service"],
        ["Full chat transcript text; use docs/chat_line_oa/."],
        ["docs/chat_line_oa/", "FACT_REFUND_PAID", "FACT_WARRANTY_CLAIM"],
    ),
    "FACT_INVENTORY_MONTHLY_SNAPSHOT": (
        "Month-end inventory snapshot by SKU and branch, with closing units.",
        ["inventory snapshot", "month end", "stock on hand", "closing units"],
        ["Intra-month movement reasons; use FACT_INVENTORY_MOVEMENT."],
        ["DIM_PRODUCT", "DIM_BRANCH", "reports/"],
    ),
    "FACT_INVENTORY_MOVEMENT": (
        "Inventory movement fact table by SKU, branch, movement type, quantity, and related transaction.",
        ["inventory movement", "stock movement", "quantity", "WMS", "related transaction"],
        ["Month-end closing stock; use FACT_INVENTORY_MONTHLY_SNAPSHOT."],
        ["DIM_PRODUCT", "DIM_BRANCH", "logs/wms_*.jsonl"],
    ),
    "FACT_LOYALTY_LEDGER": (
        "Loyalty points ledger with event type, points delta, resulting balance, and resulting tier by customer and transaction.",
        ["loyalty", "points", "tier", "points_delta", "ledger"],
        ["Customer profile/contact details; join DIM_CUSTOMER."],
        ["DIM_CUSTOMER", "FACT_SALES", "docs/l1_kb/policies/"],
    ),
    "FACT_PAYROLL": (
        "Payroll fact table by employee and pay period, including gross pay, deductions, net pay, bank transaction, and period-end employment status.",
        ["payroll", "salary", "tax deduction", "social security", "net pay"],
        ["Employee organization metadata; join DIM_EMPLOYEE."],
        ["DIM_EMPLOYEE", "FACT_BANK_TRANSACTION"],
    ),
    "FACT_PROMO_REDEMPTION": (
        "Promotion redemption fact table by transaction, customer, campaign, discount applied, and channel.",
        ["promo redemption", "campaign ROI", "discount applied", "redeemed", "channel"],
        ["Campaign definitions/mechanics; join DIM_PROMO_CAMPAIGN and dim_promo_mechanic."],
        ["DIM_PROMO_CAMPAIGN", "dim_promo_mechanic", "FACT_SALES"],
    ),
    "FACT_REFUND_PAID": (
        "Refund payout fact table linking returns, CS interactions, customers, approvers/cosigners, refund amounts, request dates, and bank transactions.",
        ["refund", "refund paid", "approver", "cosig", "bank payout"],
        ["Original return reason/details; join FACT_RETURN."],
        ["FACT_RETURN", "FACT_CS_INTERACTION", "FACT_BANK_TRANSACTION", "renders/bank_statement/"],
    ),
    "FACT_RETURN": (
        "Return fact table linking original sale/line item, SKU, branch, customer, return reason, approver, days since purchase, and return amount.",
        ["return", "return reason", "days since purchase", "return amount", "original transaction"],
        ["Refund payout status; use FACT_REFUND_PAID."],
        ["FACT_SALES", "FACT_SALES_LINE_ITEM", "FACT_REFUND_PAID", "docs/chat_line_oa/"],
    ),
    "FACT_SALES": (
        "Sales transaction header fact table with dates, branch, customer, employee, channel, basket totals, discounts, shipping, promo, payment status, bank settlement, logs, schema version, and B2B marker.",
        ["sales", "transaction", "revenue", "basket", "payment status", "txn_id", "B2B"],
        ["SKU-level item detail; join FACT_SALES_LINE_ITEM."],
        ["FACT_SALES_LINE_ITEM", "DIM_BRANCH", "DIM_CUSTOMER", "logs/pos_*.tsv", "reports/"],
    ),
    "FACT_SALES_LINE_ITEM": (
        "Sales line item fact table by transaction and SKU, including quantity, unit price, line discount, line total, Care Plus flag, and POS log link.",
        ["line item", "SKU sold", "quantity sold", "unit price", "line total", "Care Plus attachment"],
        ["Transaction-level payment, customer, or branch fields; join FACT_SALES."],
        ["FACT_SALES", "DIM_PRODUCT", "logs/pos_*.tsv"],
    ),
    "FACT_SHIPPING": (
        "Shipping fact table by transaction, shipping vendor, tracking number, origin branch, destination province, and confirmation status.",
        ["shipping", "tracking", "delivery", "confirmation", "destination province"],
        ["Shipping charge on the sale; join FACT_SALES."],
        ["FACT_SALES", "DIM_VENDOR", "logs/"],
    ),
    "FACT_VENDOR_PAYMENT": (
        "Vendor payment fact table with invoice period, amount paid, contract version, request date, signing/cosigning employees, and bank transaction.",
        ["vendor payment", "invoice", "paid amount", "signing employee", "cosig", "contract version"],
        ["Vendor master/payment terms; join DIM_VENDOR."],
        ["DIM_VENDOR", "DIM_VENDOR_CONTRACT_VERSION", "FACT_BANK_TRANSACTION", "renders/vendor_invoice/"],
    ),
    "FACT_WARRANTY_CLAIM": (
        "Warranty claim fact table by customer, SKU, original transaction, claim reason, claim amount, routing destination, and resolution type.",
        ["warranty", "claim", "repair", "routing", "claim amount"],
        ["Product warranty months and eligibility; join DIM_PRODUCT."],
        ["DIM_PRODUCT", "FACT_CS_INTERACTION", "renders/warranty_form/", "docs/chat_line_oa/"],
    ),
    "T2_DOC_INVENTORY": (
        "Inventory of generated T2 documents with document kind, template, body source, issue date, source table, and source primary key.",
        ["T2 document", "doc inventory", "template", "render source", "source_pk"],
        ["The rendered document body itself; open the file in renders/ when needed."],
        ["renders/t2_doc/", "renders/t3_doc/"],
    ),
}


EXACT_JOIN_TARGETS = {
    "account_id": "DIM_BANK_ACCOUNT.account_id",
    "associated_branch_code": "DIM_BRANCH.branch_code",
    "origin_branch_code": "DIM_BRANCH.branch_code",
    "branch_code": "DIM_BRANCH.branch_code",
    "customer_id": "DIM_CUSTOMER.customer_id",
    "account_manager_id": "DIM_EMPLOYEE.employee_id",
    "employee_id": "DIM_EMPLOYEE.employee_id",
    "reports_to_employee_id": "DIM_EMPLOYEE.employee_id",
    "approver_employee_id": "DIM_EMPLOYEE.employee_id",
    "approved_by_employee_id": "DIM_EMPLOYEE.employee_id",
    "cosig_employee_id": "DIM_EMPLOYEE.employee_id",
    "signing_employee_id": "DIM_EMPLOYEE.employee_id",
    "sku_id": "DIM_PRODUCT.sku_id",
    "vendor_id": "DIM_VENDOR.vendor_id",
    "campaign_id": "DIM_PROMO_CAMPAIGN.campaign_id",
    "promo_campaign_id": "DIM_PROMO_CAMPAIGN.campaign_id",
    "policy_version_id": "DIM_POLICY_VERSION.policy_version_id",
    "position_level_code": "DIM_POSITION_LEVEL.position_level_code",
    "co_signer_min_position_level_code": "DIM_POSITION_LEVEL.position_level_code",
    "dept_code": "DIM_DEPARTMENT.dept_code",
    "bank_txn_id": "FACT_BANK_TRANSACTION.bank_txn_id",
    "settlement_bank_txn_id": "FACT_BANK_TRANSACTION.bank_txn_id",
    "txn_id": "FACT_SALES.txn_id",
    "original_txn_id": "FACT_SALES.txn_id",
    "related_txn_id": "FACT_SALES.txn_id",
    "line_item_id": "FACT_SALES_LINE_ITEM.line_item_id",
    "return_id": "FACT_RETURN.return_id",
    "refund_id": "FACT_REFUND_PAID.refund_id",
    "related_refund_id": "FACT_REFUND_PAID.refund_id",
    "claim_id": "FACT_WARRANTY_CLAIM.claim_id",
    "related_warranty_claim_id": "FACT_WARRANTY_CLAIM.claim_id",
    "contract_version_id": "DIM_VENDOR_CONTRACT_VERSION.contract_version_id",
    "vendor_contract_version_id": "DIM_VENDOR_CONTRACT_VERSION.contract_version_id",
    "promo_mechanic_id": "dim_promo_mechanic.promo_mechanic_id",
    "chat_session_id": "docs/chat_line_oa/ transcript IDs and FACT_CS_INTERACTION.chat_session_id",
    "vendor_invoice_id": "renders/vendor_invoice/ and FACT_VENDOR_PAYMENT.vendor_invoice_id",
    "web_log_line_id": "logs/web_*.jsonl",
    "pos_log_line_id": "logs/pos_*.tsv",
}


SPECIAL_COLUMN_NOTES = {
    "business_event_date": "Best date for real-world event timing unless the question asks for posting/effective/as-of semantics.",
    "posting_date": "System posting date; use when the question is about ledger/system recognition.",
    "effective_date": "Rule or record effective date; use for as-of policy and contract logic.",
    "as_of_date": "Snapshot/audit as-of date.",
    "date_iso": "Canonical ISO date.",
    "amount_thb": "Money amount in Thai baht.",
    "net_total_thb": "Net sale total in Thai baht after discounts.",
    "basket_total_thb": "Basket gross total in Thai baht before discounts.",
    "discount_total_thb": "Header-level total discount in Thai baht.",
    "line_total_thb": "Line total in Thai baht.",
    "line_discount_thb": "Line discount in Thai baht.",
    "unit_price_thb": "Unit price in Thai baht.",
    "paid_amount_thb": "Paid amount in Thai baht.",
    "refund_amount_thb": "Refund payout amount in Thai baht.",
    "claim_amount_thb": "Warranty claim amount in Thai baht.",
    "points_delta": "Positive or negative points movement.",
    "resulting_balance_points": "Points balance after this ledger event.",
}


def read_csv_profile(path: Path) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        row_count = sum(1 for _ in reader)
    return header, row_count


def layer_for(name: str) -> str:
    upper = name.upper()
    if upper.startswith("DIM_") or name.startswith("dim_"):
        return "Dimension / reference"
    if upper.startswith("FACT_"):
        return "Fact / event"
    return "Supporting / document index"


def primary_key_for(name: str, columns: list[str]) -> str:
    lower_name = name.lower()
    exact = {
        "dim_date": "date_iso",
        "dim_signing_authority_ladder": "ladder_row_id",
        "dim_promo_mechanic": "promo_mechanic_id",
        "dim_care_plus_sku_tier": "tier_row_id",
        "dim_product_recall_history": "history_id",
    }
    if lower_name in exact and exact[lower_name] in columns:
        return exact[lower_name]
    for column in columns:
        c = column.lower()
        if c.endswith("_id") or c.endswith("_code"):
            return column
    return columns[0] if columns else "(none)"


def purpose_for(name: str) -> tuple[str, list[str], list[str], list[str]]:
    return TABLE_PURPOSES.get(
        name,
        (
            "Structured table in the FahMai dataset. Use the schema and joins below to decide whether it is the right source.",
            [name, name.lower()],
            ["Narrative explanation without supporting evidence from docs/reports."],
            [],
        ),
    )


def role_for_column(column: str, primary_key: str) -> str:
    c = column.lower()
    if column == primary_key:
        return "Primary key"
    if c in EXACT_JOIN_TARGETS or c.endswith("_id") or c.endswith("_code"):
        return "Identifier / join key"
    if "date" in c or "timestamp" in c or "period" in c:
        return "Date/time"
    if any(token in c for token in ["status", "type", "category", "method", "channel", "reason", "scope", "tier", "version", "flag", "is_", "terms", "role"]):
        return "Category/status"
    if any(token in c for token in ["thb", "amount", "total", "discount", "price", "tax", "balance", "ceiling", "charge"]):
        return "Measure"
    if any(token in c for token in ["quantity", "units", "points", "pct", "coefficient", "rank", "months", "multiplier", "headcount"]):
        return "Measure"
    if any(token in c for token in ["name", "description", "title", "email", "phone", "filename", "summary", "body"]):
        return "Descriptive attribute"
    return "Attribute"


def notes_for_column(column: str) -> str:
    c = column.lower()
    if c in SPECIAL_COLUMN_NOTES:
        return SPECIAL_COLUMN_NOTES[c]
    if c in EXACT_JOIN_TARGETS:
        return f"Join to `{EXACT_JOIN_TARGETS[c]}` when the answer needs related attributes."
    if c.endswith("_thb"):
        return "Money value in Thai baht."
    if c.endswith("_date") or c == "date_iso":
        return "Date field; clarify date semantics before filtering."
    if c.endswith("_timestamp"):
        return "Timestamp field; use for time-window filtering."
    if c.startswith("is_"):
        return "Boolean flag."
    return ""


def join_target_for(column: str) -> str | None:
    c = column.lower()
    if c in EXACT_JOIN_TARGETS:
        return EXACT_JOIN_TARGETS[c]
    if c.endswith("_employee_id"):
        return "DIM_EMPLOYEE.employee_id"
    if c.endswith("_customer_id"):
        return "DIM_CUSTOMER.customer_id"
    if c.endswith("_vendor_id"):
        return "DIM_VENDOR.vendor_id"
    if c.endswith("_sku_id"):
        return "DIM_PRODUCT.sku_id"
    if c.endswith("_branch_code"):
        return "DIM_BRANCH.branch_code"
    return None


def escape_cell(value: object) -> str:
    text = str(value).replace("|", "\\|").replace("\n", " ").strip()
    return text if text else "-"


def table_info(path: Path) -> TableInfo:
    columns, row_count = read_csv_profile(path)
    name = path.stem
    primary_key = primary_key_for(name, columns)
    purpose, route_clues, avoid, related_evidence = purpose_for(name)
    return TableInfo(
        name=name,
        source_path=path,
        guide_path=KB_TABLES_DIR / f"{name}.md",
        columns=columns,
        row_count=row_count,
        primary_key=primary_key,
        layer=layer_for(name),
        purpose=purpose,
        route_clues=route_clues,
        avoid=avoid,
        related_evidence=related_evidence,
    )


def render_table_doc(info: TableInfo) -> str:
    date_columns = [c for c in info.columns if "date" in c.lower() or "timestamp" in c.lower() or "period" in c.lower()]
    measure_columns = [c for c in info.columns if role_for_column(c, info.primary_key) == "Measure"]
    joins = [(c, join_target_for(c)) for c in info.columns if join_target_for(c)]
    joins = [(c, target) for c, target in joins if target and not target.startswith(f"{info.name}.")]

    column_rows = [
        f"| `{escape_cell(column)}` | {escape_cell(role_for_column(column, info.primary_key))} | {escape_cell(notes_for_column(column))} |"
        for column in info.columns
    ]
    join_rows = [
        f"| `{escape_cell(column)}` | `{escape_cell(target)}` | Pull related attributes or validate referenced events/entities. |"
        for column, target in joins
    ]
    if not join_rows:
        join_rows = ["| - | - | No obvious foreign-key style columns inferred. |"]

    related = ", ".join(f"`{item}`" for item in info.related_evidence) if info.related_evidence else "`knowledge_base/README.md`"
    date_list = ", ".join(f"`{c}`" for c in date_columns) if date_columns else "No dedicated date/time columns."
    measure_list = ", ".join(f"`{c}`" for c in measure_columns) if measure_columns else "No obvious numeric measure columns."
    route_list = ", ".join(f"`{clue}`" for clue in info.route_clues)
    avoid_lines = "\n".join(f"- {item}" for item in info.avoid)

    return "\n".join(
        [
            f"# {info.name}",
            "",
            f"Source CSV: `tables/{info.source_path.name}`",
            f"Layer: {info.layer}",
            f"Rows: {info.row_count}",
            f"Primary key: `{info.primary_key}`",
            "",
            "## What This Table Knows",
            "",
            info.purpose,
            "",
            "## Route Here When",
            "",
            f"- The question mentions or implies: {route_list}.",
            "- The answer needs exact structured values, filters, joins, counts, sums, rankings, or date-window calculations.",
            "- Use SQL/Supabase first when available; use the CSV as a local mirror or schema reference.",
            "",
            "## Do Not Use This Table Alone For",
            "",
            avoid_lines,
            "",
            "## Important Fields",
            "",
            f"- Date/time fields: {date_list}",
            f"- Measure fields: {measure_list}",
            f"- Related evidence or context: {related}",
            "",
            "## Columns",
            "",
            "| Column | Role | Notes |",
            "|---|---|---|",
            *column_rows,
            "",
            "## Join Hints",
            "",
            "| Column | Likely target | Why join |",
            "|---|---|---|",
            *join_rows,
            "",
            "## Agent Notes",
            "",
            "- Extract explicit IDs, dates, branch/SKU/vendor/customer clues, and requested metric before querying.",
            "- Keep date semantics explicit: `business_event_date`, `posting_date`, `effective_date`, and `as_of_date` can answer different questions.",
            "- When a narrative explanation is needed, pair this table with the related evidence listed above instead of replacing the structured result.",
            "",
        ]
    )


def common_join_summary(info: TableInfo) -> str:
    targets = []
    for column in info.columns:
        target = join_target_for(column)
        if target and target not in targets and not target.startswith(f"{info.name}."):
            targets.append(target)
    if not targets:
        return "-"
    return ", ".join(f"`{target}`" for target in targets[:4])


def render_index(infos: list[TableInfo]) -> str:
    rows = []
    for info in infos:
        rows.append(
            "| "
            f"[`{escape_cell(info.name)}`]({escape_cell(info.guide_path.name)}) | "
            f"{escape_cell(info.layer)} | "
            f"{info.row_count} | "
            f"`{escape_cell(info.primary_key)}` | "
            f"{escape_cell(info.purpose)} | "
            f"{common_join_summary(info)} |"
        )

    return "\n".join(
        [
            "# Tables Knowledge Base",
            "",
            "This folder is the structured knowledge-base layer for FahMai tables. Each table guide below explains what the table knows, when an agent should route to it, important fields, and likely joins.",
            "",
            "Generated from the CSV files in `tables/` by `Fahmai/scripts/build_table_knowledge_base.py`.",
            "",
            "## Routing Rule",
            "",
            "Use these table guides when a question needs exact counts, sums, averages, ratios, rankings, IDs, dates, payment/refund status, inventory quantities, policy thresholds, or joins across business entities.",
            "",
            "Prefer Supabase/SQL execution for final numeric answers. Use these markdown files to choose the right tables and joins before querying.",
            "",
            "## Topic Shortcuts",
            "",
            "| Topic | Start with |",
            "|---|---|",
            "| Product master, MSRP, warranty | [`DIM_PRODUCT`](DIM_PRODUCT.md), [`dim_product_recall_history`](dim_product_recall_history.md) |",
            "| Sales and baskets | [`FACT_SALES`](FACT_SALES.md), [`FACT_SALES_LINE_ITEM`](FACT_SALES_LINE_ITEM.md) |",
            "| Customers and loyalty | [`DIM_CUSTOMER`](DIM_CUSTOMER.md), [`FACT_LOYALTY_LEDGER`](FACT_LOYALTY_LEDGER.md) |",
            "| Returns, refunds, warranty | [`FACT_RETURN`](FACT_RETURN.md), [`FACT_REFUND_PAID`](FACT_REFUND_PAID.md), [`FACT_WARRANTY_CLAIM`](FACT_WARRANTY_CLAIM.md) |",
            "| Vendor payments and contracts | [`DIM_VENDOR`](DIM_VENDOR.md), [`FACT_VENDOR_PAYMENT`](FACT_VENDOR_PAYMENT.md), [`DIM_VENDOR_CONTRACT_VERSION`](DIM_VENDOR_CONTRACT_VERSION.md) |",
            "| Bank/cash | [`DIM_BANK_ACCOUNT`](DIM_BANK_ACCOUNT.md), [`FACT_BANK_TRANSACTION`](FACT_BANK_TRANSACTION.md) |",
            "| Inventory | [`FACT_INVENTORY_MOVEMENT`](FACT_INVENTORY_MOVEMENT.md), [`FACT_INVENTORY_MONTHLY_SNAPSHOT`](FACT_INVENTORY_MONTHLY_SNAPSHOT.md) |",
            "| Policy-as-of-date and approvals | [`DIM_POLICY_VERSION`](DIM_POLICY_VERSION.md), [`dim_signing_authority_ladder`](dim_signing_authority_ladder.md), [`DIM_POSITION_LEVEL`](DIM_POSITION_LEVEL.md) |",
            "| Campaigns/promotions | [`DIM_PROMO_CAMPAIGN`](DIM_PROMO_CAMPAIGN.md), [`dim_promo_mechanic`](dim_promo_mechanic.md), [`FACT_PROMO_REDEMPTION`](FACT_PROMO_REDEMPTION.md) |",
            "| Support interactions | [`FACT_CS_INTERACTION`](FACT_CS_INTERACTION.md), `docs/chat_line_oa/` |",
            "",
            "## Table Guides",
            "",
            "| Table | Layer | Rows | Primary key | What it knows | Common joins |",
            "|---|---|---:|---|---|---|",
            *rows,
            "",
            "## Agent Hints",
            "",
            "- Route by strongest entity clue first: table name, SKU, vendor ID, employee ID, customer ID, campaign ID, transaction ID, date, branch code, or document ID.",
            "- For date questions, identify whether the user means business event date, posting date, effective date, as-of date, or fiscal calendar date.",
            "- For questions asking why something happened, use SQL for the numeric/entity facts and then add supporting evidence from docs, logs, renders, or reports.",
            "",
        ]
    )


def main() -> int:
    KB_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    csv_paths = sorted(TABLES_DIR.glob("*.csv"), key=lambda p: p.stem.lower())
    infos = [table_info(path) for path in csv_paths]

    for info in infos:
        info.guide_path.write_text(render_table_doc(info), encoding="utf-8")

    (KB_TABLES_DIR / "README.md").write_text(render_index(infos), encoding="utf-8")
    print(f"Generated {len(infos)} table guides in {KB_TABLES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
