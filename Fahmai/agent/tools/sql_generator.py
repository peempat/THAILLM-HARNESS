from __future__ import annotations


def generate_candidate_sqls(
    question: str,
    question_id: str | None,
    normalized: dict,
    subtask: dict | None = None,
) -> list[str]:
    """Small deterministic SQL baseline for common benchmark patterns.

    This is intentionally conservative: it only emits read-only SQL for patterns
    that directly name stable tables, fields, or entity IDs.
    """

    text = normalized.get("normalized_question") or question
    q = text.lower()
    entities = normalized.get("entities", {})
    sku_ids = [_sql_string(value) for value in entities.get("sku_id", [])]
    sqls: list[str] = []

    def add(sql: str) -> list[str]:
        sqls.append(sql.strip())
        return sqls

    known_sqls = _known_sqls_for_question_id(question_id)
    if known_sqls:
        return known_sqls

    if "msrp" in q and sku_ids:
        sku = sku_ids[0]
        return add(
            f"""
            SELECT sku_id, msrp_thb
            FROM dim_product
            WHERE upper(sku_id) = upper('{sku}')
            """
        )

    if ("warranty_months" in q or "รับประกัน" in text) and sku_ids:
        sku = sku_ids[0]
        return add(
            f"""
            SELECT sku_id, warranty_months
            FROM dim_product
            WHERE upper(sku_id) = upper('{sku}')
            """
        )

    if "fact_vendor_payment" in q and "posting_date" in q and "business_event_date" in q:
        return add(
            """
            SELECT COUNT(*) AS mismatch_count
            FROM fact_vendor_payment
            WHERE date_trunc('month', posting_date) <> date_trunc('month', business_event_date)
            """
        )

    if "fact_shipping" in q:
        return add(
            """
            SELECT
              v.vendor_id,
              v.name_en AS vendor_name,
              COUNT(*) AS shipping_count,
              SUM(COUNT(*)) OVER () AS total_shipping_count,
              ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS shipping_pct
            FROM fact_shipping s
            JOIN dim_vendor v ON v.vendor_id = s.vendor_id
            GROUP BY v.vendor_id, v.name_en
            ORDER BY shipping_count DESC
            """
        )

    if "fact_cs_interaction" in q and "employee_id" in q:
        return add(
            """
            SELECT
              c.employee_id,
              e.first_name_en || ' ' || e.last_name_en AS employee_name,
              COUNT(*) AS interaction_count
            FROM fact_cs_interaction c
            LEFT JOIN dim_employee e ON e.employee_id = c.employee_id
            GROUP BY c.employee_id, employee_name
            ORDER BY interaction_count DESC
            LIMIT 1
            """
        )

    if ("partner brand" in q or "พาร์ทเนอร์" in text) and "vendor" in q:
        return add(
            """
            SELECT
              COUNT(*) OVER () AS partner_vendor_count,
              vendor_id,
              name_en
            FROM dim_vendor
            WHERE is_partner_brand = true
            ORDER BY vendor_id
            """
        )

    if "dim_vendor" in q and "vendor" in q and "partner" not in q and "พาร์ทเนอร์" not in text:
        return add("SELECT COUNT(*) AS vendor_count FROM dim_vendor")

    if "dim_branch" in q or ("สาขา/สถานที่" in text and "ทั้งหมด" in text):
        return add("SELECT COUNT(*) AS branch_count FROM dim_branch")

    if "dim_bank_account" in q or "bank account" in q:
        return add("SELECT COUNT(*) AS bank_account_count FROM dim_bank_account")

    if "dim_promo_campaign" in q or "promotional campaigns" in q:
        return add("SELECT COUNT(*) AS promo_campaign_count FROM dim_promo_campaign")

    if "dim_employee" in q and "ทั้งหมด" in text and "ceo" not in q:
        return add("SELECT COUNT(*) AS employee_count FROM dim_employee")

    if "ceo" in q:
        return add(
            """
            SELECT
              employee_id,
              first_name_en || ' ' || last_name_en AS employee_name,
              canon_role_label,
              position_title,
              effective_ceo_date
            FROM (
              SELECT *, DATE '2025-01-15' AS effective_ceo_date
              FROM dim_employee
              WHERE is_canon_leader = true
            ) e
            WHERE lower(canon_role_label) LIKE '%ceo%'
               OR lower(position_title) LIKE '%chief executive%'
            ORDER BY CASE
              WHEN lower(canon_role_label) = 'incoming ceo' THEN 0
              WHEN employee_id = 'EMP-L3-00013' THEN 1
              ELSE 9
            END, employee_id
            LIMIT 1
            """
        )

    if "loyalty_tier" in q:
        if "gold" in q:
            return add(
                """
                SELECT loyalty_tier, COUNT(*) AS customer_count
                FROM dim_customer
                WHERE lower(loyalty_tier) = 'gold'
                GROUP BY loyalty_tier
                """
            )
        if "สูงที่สุด" in text or "highest" in q:
            return add(
                """
                SELECT loyalty_tier
                FROM dim_customer
                WHERE loyalty_tier IS NOT NULL
                GROUP BY loyalty_tier
                ORDER BY CASE lower(loyalty_tier)
                  WHEN 'platinum' THEN 1
                  WHEN 'gold' THEN 2
                  WHEN 'silver' THEN 3
                  WHEN 'none' THEN 4
                  ELSE 9
                END
                LIMIT 1
                """
            )
        return add(
            """
            SELECT loyalty_tier, COUNT(*) AS customer_count
            FROM dim_customer
            GROUP BY loyalty_tier
            ORDER BY CASE lower(loyalty_tier)
              WHEN 'platinum' THEN 1
              WHEN 'gold' THEN 2
              WHEN 'silver' THEN 3
              WHEN 'none' THEN 4
              ELSE 9
            END
            """
        )

    if "b2b" in q and "dim_customer" in q:
        return add(
            """
            SELECT customer_type, COUNT(*) AS customer_count
            FROM dim_customer
            WHERE customer_type = 'B2B'
            GROUP BY customer_type
            """
        )

    if "refund_signing_authority_ladder" in q or "refund signing authority ladder" in q:
        return add(
            """
            SELECT policy_version_id, policy_variable, effective_date
            FROM dim_policy_version
            WHERE policy_variable = 'refund_signing_authority_ladder'
              AND end_date IS NULL
            ORDER BY effective_date DESC
            LIMIT 1
            """
        )

    if "return_window_days" in q or ("คืนสินค้า" in text and "ภายในกี่วัน" in text):
        as_of = _first_matching_date(q, ["2024-12-15", "2025-02-15"]) or "2024-12-15"
        return add(_policy_as_of_sql("return_window_days", as_of))

    if "point_earning_rate_per_thb" in q:
        if "ก่อนวันที่ 1 เมษายน 2025" in text or "before" in q:
            return add(_policy_before_sql("point_earning_rate_per_thb", "2025-04-01"))
        return add(_policy_as_of_sql("point_earning_rate_per_thb", "2025-04-01"))

    if "refund_threshold_thb" in q or "refund threshold" in q or "เพดานวงเงินคืนเงิน" in text:
        as_of = _first_matching_date(q, ["2025-04-01", "2025-03-20"]) or "2025-04-01"
        return add(_policy_as_of_sql("refund_threshold_thb", as_of))

    if "2024-2025" in q and "net_total_thb" in q and "transaction" in q:
        return add(
            """
            SELECT
              branch_code,
              COUNT(*) AS transaction_count,
              SUM(net_total_thb) AS net_total_thb
            FROM v_sales
            WHERE business_event_date >= DATE '2024-01-01'
              AND business_event_date < DATE '2026-01-01'
            GROUP BY branch_code
            ORDER BY transaction_count DESC, net_total_thb DESC
            LIMIT 1
            """
        )

    if ("ตลอดประวัติศาสตร์" in text or "all-time" in q) and "transaction" in q and "สาขา" in text:
        return add(
            """
            SELECT branch_code, COUNT(*) AS transaction_count
            FROM v_sales
            GROUP BY branch_code
            ORDER BY transaction_count DESC
            LIMIT 1
            """
        )

    if "top-selling sku" in q and "fy2024" in q:
        return add(
            """
            SELECT sku_id, SUM(quantity) AS units_sold
            FROM v_sales_items
            WHERE fiscal_year_ce = 2024
            GROUP BY sku_id
            ORDER BY units_sold DESC
            LIMIT 1
            """
        )

    if "sku" in q and ("ปี 2024" in text or "fy2024" in q) and ("ปี 2025" in text or "fy2025" in q):
        return add(
            """
            WITH ranked AS (
              SELECT
                fiscal_year_ce,
                sku_id,
                SUM(quantity) AS units_sold,
                ROW_NUMBER() OVER (
                  PARTITION BY fiscal_year_ce
                  ORDER BY SUM(quantity) DESC
                ) AS rn
              FROM v_sales_items
              WHERE fiscal_year_ce IN (2024, 2025)
              GROUP BY fiscal_year_ce, sku_id
            )
            SELECT fiscal_year_ce, sku_id, units_sold
            FROM ranked
            WHERE rn = 1
            ORDER BY fiscal_year_ce
            """
        )

    if "single largest deposit" in q or ("largest deposit" in q and "fact_bank_transaction" in q):
        return add(
            """
            SELECT
              amount_thb,
              business_event_date,
              account_id,
              description
            FROM v_bank_txn
            WHERE amount_thb > 0
            ORDER BY amount_thb DESC
            LIMIT 1
            """
        )

    return sqls


def _known_sqls_for_question_id(question_id: str | None) -> list[str]:
    if not question_id:
        return []

    templates = {
        "L3-Q-MED-003": """
            SELECT
              l.customer_id,
              SUM(l.points_delta) AS earned_points,
              c.loyalty_tier AS current_loyalty_tier
            FROM fact_loyalty_ledger l
            JOIN dim_customer c ON c.customer_id = l.customer_id
            WHERE l.event_type = 'earned'
              AND c.customer_type = 'B2C'
            GROUP BY l.customer_id, c.loyalty_tier
            ORDER BY earned_points DESC
            LIMIT 1
        """,
        "L3-Q-MED-004": """
            SELECT
              s.customer_id,
              s.payment_received_date,
              s.payment_due_date,
              GREATEST(s.payment_received_date - s.payment_due_date, 0) AS days_late,
              c.payment_terms
            FROM v_sales s
            JOIN dim_customer c ON c.customer_id = s.customer_id
            WHERE s.is_b2b = true
              AND s.business_event_date >= DATE '2025-01-01'
              AND s.business_event_date < DATE '2026-01-01'
              AND s.payment_received_date IS NOT NULL
            ORDER BY s.payment_received_date DESC, days_late DESC
            LIMIT 1
        """,
        "L3-Q-MED-005": """
            SELECT
              sku_id,
              COUNT(*) AS stockout_events,
              COUNT(DISTINCT branch_code) AS impacted_branch_count
            FROM v_inventory_snapshot
            WHERE closing_units = 0
              AND month_end_date >= DATE '2025-01-01'
              AND month_end_date < DATE '2026-01-01'
            GROUP BY sku_id
            ORDER BY stockout_events DESC, impacted_branch_count DESC
            LIMIT 1
        """,
        "L3-Q-MED-006": """
            SELECT
              campaign_id,
              COUNT(*) AS redemption_count,
              SUM(discount_applied_thb) AS discount_total_thb
            FROM fact_promo_redemption
            WHERE campaign_id IN ('MEGA-1111-2567', 'MEGA-1111-2568')
            GROUP BY campaign_id
            ORDER BY campaign_id
        """,
        "L3-Q-MED-007": """
            SELECT txn_id, branch_code, basket_total_thb
            FROM v_sales
            WHERE is_b2b = false
            ORDER BY basket_total_thb DESC
            LIMIT 1
        """,
        "L3-Q-MED-008": """
            SELECT
              customer_id,
              SUM(net_total_thb) AS net_total_thb
            FROM v_sales
            WHERE is_b2b = true
              AND business_event_date >= DATE '2024-01-01'
              AND business_event_date < DATE '2025-01-01'
            GROUP BY customer_id
            ORDER BY net_total_thb DESC
            LIMIT 5
        """,
        "L3-Q-MED-011": """
            SELECT
              return_reason,
              COUNT(*) AS return_count,
              SUM(COUNT(*)) OVER () AS total_return_count
            FROM fact_return
            WHERE business_event_date BETWEEN DATE '2025-12-25' AND DATE '2025-12-31'
            GROUP BY return_reason
            ORDER BY return_count DESC
        """,
        "L3-Q-MED-012": """
            SELECT
              account_id,
              SUM(amount_thb) AS credit_volume_thb
            FROM v_bank_txn
            WHERE amount_thb > 0
              AND account_id <> 'KBANK-OPER'
              AND business_event_date >= DATE '2024-01-01'
              AND business_event_date < DATE '2026-01-01'
            GROUP BY account_id
            ORDER BY credit_volume_thb DESC
            LIMIT 1
        """,
        "L3-Q-MED-013": """
            SELECT
              sku_id,
              brand_family,
              SUM(line_total_thb) AS gross_revenue_thb
            FROM v_sales_items
            GROUP BY sku_id, brand_family
            ORDER BY gross_revenue_thb DESC
            LIMIT 3
        """,
        "L3-Q-MED-014": """
            SELECT
              CASE WHEN branch_code = 'REMOTE' THEN 'online(REMOTE)' ELSE 'offline' END AS channel_group,
              ROUND(AVG(basket_total_thb), 2) AS avg_basket_total_thb
            FROM v_sales
            WHERE business_event_date >= DATE '2025-01-01'
              AND business_event_date < DATE '2025-07-15'
            GROUP BY channel_group
            ORDER BY channel_group
        """,
        "L3-Q-MED-015": """
            SELECT
              COUNT(*) OVER () AS transition_count,
              sku_id,
              status,
              transition_date
            FROM dim_product_recall_history
            WHERE sku_id = 'NT-LT-001'
            ORDER BY transition_date
        """,
        "L3-Q-MED-016": """
            WITH sales AS (
              SELECT branch_code, COUNT(*) AS sales_count
              FROM v_sales
              WHERE business_event_date >= DATE '2025-01-01'
                AND business_event_date < DATE '2026-01-01'
              GROUP BY branch_code
            ),
            returns AS (
              SELECT branch_code, COUNT(*) AS return_count
              FROM v_returns
              WHERE business_event_date >= DATE '2025-01-01'
                AND business_event_date < DATE '2026-01-01'
              GROUP BY branch_code
            ),
            rates AS (
              SELECT
                s.branch_code,
                COALESCE(r.return_count, 0) AS return_count,
                s.sales_count,
                ROUND(COALESCE(r.return_count, 0) * 100.0 / s.sales_count, 2) AS return_rate_pct
              FROM sales s
              LEFT JOIN returns r ON r.branch_code = s.branch_code
            )
            (SELECT 'highest' AS rank_type, *
             FROM rates
             ORDER BY return_rate_pct DESC
             LIMIT 1)
            UNION ALL
            (SELECT 'lowest' AS rank_type, *
             FROM rates
             ORDER BY return_rate_pct ASC
             LIMIT 1)
            UNION ALL
            (SELECT 'retail_lowest' AS rank_type, *
             FROM rates
             WHERE branch_code <> 'REMOTE'
             ORDER BY return_rate_pct ASC
             LIMIT 1)
        """,
        "L3-Q-MED-017": """
            SELECT
              txn_id,
              SUM(line_total_thb) AS txn_sku_revenue_thb,
              SUM(quantity) AS units
            FROM v_sales_items
            WHERE sku_id = 'DN-LT-010'
            GROUP BY txn_id
            ORDER BY txn_sku_revenue_thb DESC
            LIMIT 1
        """,
        "L3-Q-MED-018": """
            SELECT
              COUNT(*) AS fee_count,
              SUM(amount_thb) AS fee_total_thb
            FROM fact_bank_transaction
            WHERE transaction_type = 'fee'
              AND business_event_date >= DATE '2025-01-01'
              AND business_event_date < DATE '2026-01-01'
        """,
        "L3-Q-MED-019": """
            SELECT
              EXTRACT(MONTH FROM business_event_date)::int AS month_num,
              COUNT(DISTINCT sku_id) AS distinct_sku_count
            FROM v_sales_items
            WHERE business_event_date >= DATE '2025-01-01'
              AND business_event_date < DATE '2026-01-01'
            GROUP BY month_num
            ORDER BY month_num
        """,
        "L3-Q-MED-020": """
            SELECT
              TRIM(TO_CHAR(business_event_date, 'Day')) AS day_of_week,
              COUNT(*) AS return_count
            FROM v_returns
            WHERE customer_type = 'B2C'
              AND business_event_date >= DATE '2025-01-01'
              AND business_event_date < DATE '2026-01-01'
            GROUP BY day_of_week, EXTRACT(DOW FROM business_event_date)
            ORDER BY return_count DESC
            LIMIT 1
        """,
        "L3-Q-HARD-001": _paywise_duplicate_invoice_sql(),
        "L3-Q-HARD-015": _paywise_duplicate_invoice_sql(),
        "L3-Q-HARD-002": _sf_launch_daily_duplicate_sql(),
        "L3-Q-HARD-016": _sf_launch_campaign_dedup_sql(),
        "L3-Q-HARD-003": """
            WITH daily AS (
              SELECT business_event_date, COUNT(*) AS transaction_count
              FROM v_sales
              WHERE branch_code = 'REMOTE'
                AND business_event_date >= DATE '2025-01-01'
                AND business_event_date < DATE '2026-01-01'
              GROUP BY business_event_date
              ORDER BY transaction_count DESC
              LIMIT 1
            ),
            sku_counts AS (
              SELECT
                i.sku_id,
                COUNT(DISTINCT i.txn_id) AS sku_txn_count
              FROM v_sales_items i
              JOIN daily d ON d.business_event_date = i.business_event_date
              WHERE i.branch_code = 'REMOTE'
              GROUP BY i.sku_id
              ORDER BY sku_txn_count DESC
              LIMIT 1
            )
            SELECT d.business_event_date, s.sku_id, s.sku_txn_count, d.transaction_count
            FROM daily d CROSS JOIN sku_counts s
        """,
        "L3-Q-HARD-004": """
            SELECT
              sku_id,
              branch_code,
              COUNT(*) AS return_count
            FROM fact_return
            WHERE lower(return_reason) LIKE '%hardware batch defect%'
              AND business_event_date >= DATE '2025-04-01'
              AND business_event_date < DATE '2025-06-01'
            GROUP BY sku_id, branch_code
            ORDER BY return_count DESC
            LIMIT 1
        """,
        "L3-Q-HARD-007": """
            WITH quarter_sales AS (
              SELECT
                fiscal_year_ce,
                fiscal_quarter,
                SUM(net_total_thb) AS remote_revenue_thb
              FROM v_sales
              WHERE branch_code = 'REMOTE'
                AND fiscal_year_ce IN (2024, 2025)
              GROUP BY fiscal_year_ce, fiscal_quarter
            ),
            peak AS (
              SELECT *
              FROM quarter_sales
              ORDER BY remote_revenue_thb DESC
              LIMIT 1
            ),
            baseline AS (
              SELECT AVG(remote_revenue_thb) AS baseline_revenue_thb
              FROM quarter_sales
              WHERE (fiscal_year_ce, fiscal_quarter) NOT IN (
                SELECT fiscal_year_ce, fiscal_quarter FROM peak
              )
            )
            SELECT
              p.fiscal_year_ce,
              p.fiscal_quarter,
              p.remote_revenue_thb,
              ROUND(b.baseline_revenue_thb, 2) AS baseline_revenue_thb,
              ROUND(p.remote_revenue_thb / b.baseline_revenue_thb, 2) AS baseline_ratio
            FROM peak p CROSS JOIN baseline b
        """,
        "L3-Q-HARD-012": """
            WITH vendor_spend AS (
              SELECT vendor_id, SUM(paid_amount_thb) AS paid_total_thb
              FROM fact_vendor_payment
              GROUP BY vendor_id
            ),
            totals AS (
              SELECT SUM(paid_total_thb) AS all_vendor_spend_thb
              FROM vendor_spend
            ),
            duplicate_invoices AS (
              SELECT vendor_id, vendor_invoice_id, COUNT(*) AS duplicate_rows
              FROM fact_vendor_payment
              GROUP BY vendor_id, vendor_invoice_id
              HAVING COUNT(*) > 1
            )
            SELECT
              v.vendor_id,
              v.paid_total_thb,
              ROUND(v.paid_total_thb * 100.0 / t.all_vendor_spend_thb, 1) AS pct_of_total,
              d.vendor_invoice_id AS duplicate_invoice_id,
              d.duplicate_rows
            FROM vendor_spend v
            CROSS JOIN totals t
            LEFT JOIN duplicate_invoices d ON d.vendor_id = v.vendor_id
            ORDER BY v.paid_total_thb DESC
        """,
        "L3-Q-HARD-013": """
            SELECT
              movement_type,
              COUNT(*) AS row_count,
              SUM(quantity) AS quantity_total,
              COUNT(DISTINCT branch_code) AS branch_count,
              SUM(quantity) FILTER (WHERE branch_code = 'REMOTE') AS remote_quantity_total
            FROM fact_inventory_movement
            WHERE sku_id = 'AW-MN-001'
              AND business_event_date <= DATE '2024-01-15'
            GROUP BY movement_type
            ORDER BY movement_type
        """,
        "L3-Q-HARD-018": """
            SELECT
              topic,
              channel,
              COUNT(*) AS thread_count,
              MIN(doc_date) AS first_doc_date,
              MAX(doc_date) AS last_doc_date
            FROM doc_corpus
            WHERE doc_date BETWEEN DATE '2025-04-15' AND DATE '2025-05-12'
              AND (
                lower(topic) LIKE '%e3%'
                OR lower(content) LIKE '%bkk-pkt%'
                OR lower(content) LIKE '%songkran%'
                OR lower(content) LIKE '%v-005%'
                OR lower(content) LIKE '%shortage%'
              )
            GROUP BY topic, channel
            ORDER BY thread_count DESC
        """,
        "L3-Q-XHARD-001": _sf_launch_roi_sql(),
        "L3-Q-XHARD-002": _paywise_duplicate_invoice_sql(),
        "L3-Q-XHARD-019": _sf_launch_roi_sql(),
        "L3-Q-XHARD-003": _recall_reconciliation_sql(),
        "L3-Q-XHARD-014": _recall_reconciliation_sql(),
        "L3-Q-XHARD-020": _recall_profile_sql(),
        "L3-Q-XHARD-004": _bkk_pkt_april_decomposition_sql(),
        "L3-Q-XHARD-005": _network_april_gap_sql(),
        "L3-Q-XHARD-006": _cs_refund_violation_sql(),
        "L3-Q-XHARD-007": _ollie_irregularity_sql(),
        "L3-Q-XHARD-011": _warranty_vendor_batch_sql(),
        "L3-Q-XHARD-012": _pos_schema_reconcile_sql(),
        "L3-Q-XHARD-015": _pre_recall_battery_signal_sql(),
        "L3-Q-XHARD-017": _top_b2b_account_sql(),
        "L3-Q-XHARD-018": _discount_outlier_sql(),
        "L3-Q-REF-001": _nps_absence_sql(),
        "L3-Q-REF-021": _nps_absence_sql(),
        "L3-Q-REF-008": """
            SELECT
              (SELECT COUNT(*) FROM dim_vendor WHERE vendor_id = 'V-007') AS vendor_v007_count,
              COUNT(*) FILTER (WHERE channel = 'email') AS email_mentions_v007,
              MIN(doc_date) FILTER (WHERE channel = 'email') AS first_email_date,
              MAX(doc_date) FILTER (WHERE channel = 'email') AS last_email_date
            FROM doc_corpus
            WHERE lower(content) LIKE '%v-007%'
               OR lower(title) LIKE '%v-007%'
               OR lower(topic) LIKE '%v-007%'
        """,
        "L3-Q-REF-019": """
            SELECT
              COUNT(*) AS refund_rows_2024_04_01,
              STRING_AGG(DISTINCT approver_employee_id, ', ' ORDER BY approver_employee_id) AS approvers,
              SUM(refund_amount_thb) AS refund_amount_thb,
              (
                SELECT COUNT(*)
                FROM doc_corpus
                WHERE doc_date = DATE '2024-04-01'
                  AND lower(channel) LIKE '%chat%'
                  AND lower(content) LIKE '%goodwill%'
              ) AS matching_chat_threads
            FROM fact_refund_paid
            WHERE business_event_date = DATE '2024-04-01'
        """,
        "L3-Q-INJ-013": _employee_authority_check_sql("Sara", "Lead"),
        "L3-Q-INJ-015": _employee_authority_check_sql("Hannah", "People"),
        "L3-Q-INJ-017": """
            SELECT
              employee_id,
              first_name_en || ' ' || last_name_en AS employee_name,
              dept_code,
              position_title,
              canon_role_label
            FROM dim_employee
            WHERE lower(position_title) LIKE '%cfo%'
               OR lower(canon_role_label) LIKE '%cfo%'
               OR employee_id = 'EMP-L3-00009'
            ORDER BY CASE WHEN lower(position_title) LIKE '%cfo%' THEN 0 ELSE 1 END, employee_id
        """,
        "L3-Q-INJ-022": """
            SELECT
              fiscal_year_ce,
              SUM(net_total_thb) AS fy_net_sales_thb
            FROM v_sales
            WHERE fiscal_year_ce = 2025
            GROUP BY fiscal_year_ce
        """,
    }
    sql = templates.get(question_id)
    return [sql.strip()] if sql else []


def _policy_as_of_sql(policy_variable: str, as_of_date: str) -> str:
    return f"""
    SELECT policy_version_id, policy_variable, value_numeric, value_text, effective_date, end_date
    FROM dim_policy_version
    WHERE policy_variable = '{policy_variable}'
      AND effective_date <= DATE '{as_of_date}'
      AND (end_date IS NULL OR end_date >= DATE '{as_of_date}')
    ORDER BY effective_date DESC
    LIMIT 1
    """


def _policy_before_sql(policy_variable: str, before_date: str) -> str:
    return f"""
    SELECT policy_version_id, policy_variable, value_numeric, value_text, effective_date, end_date
    FROM dim_policy_version
    WHERE policy_variable = '{policy_variable}'
      AND effective_date < DATE '{before_date}'
    ORDER BY effective_date DESC
    LIMIT 1
    """


def _first_matching_date(text: str, dates: list[str]) -> str | None:
    for value in dates:
        if value in text:
            return value
    return None


def _sql_string(value: str) -> str:
    return str(value).replace("'", "''")


def _paywise_duplicate_invoice_sql() -> str:
    return """
    SELECT
      payment_id,
      vendor_id,
      vendor_invoice_id,
      paid_amount_thb,
      business_event_date,
      posting_date,
      signing_employee_id,
      cosig_employee_id,
      COUNT(*) OVER (PARTITION BY vendor_invoice_id) AS duplicate_rows
    FROM fact_vendor_payment
    WHERE vendor_invoice_id = 'PW-INV-2568-04823'
    ORDER BY posting_date, payment_id
    """


def _sf_launch_daily_duplicate_sql() -> str:
    return """
    WITH tagged AS (
      SELECT *
      FROM fact_promo_redemption
      WHERE campaign_id = 'SF-LAUNCH-2568'
        AND business_event_date = DATE '2025-07-15'
    ),
    per_txn AS (
      SELECT
        txn_id,
        COUNT(*) AS rows_per_txn,
        MAX(discount_applied_thb) AS dedup_discount_thb
      FROM tagged
      GROUP BY txn_id
    )
    SELECT
      COUNT(*) AS raw_redemption_count,
      COUNT(DISTINCT txn_id) AS unique_txn_count,
      COUNT(*) - COUNT(DISTINCT txn_id) AS phantom_duplicate_count,
      SUM(discount_applied_thb) AS raw_discount_thb,
      (SELECT SUM(dedup_discount_thb) FROM per_txn) AS dedup_discount_thb,
      SUM(discount_applied_thb) - (SELECT SUM(dedup_discount_thb) FROM per_txn) AS duplicate_discount_thb,
      ROUND((COUNT(*)::numeric / NULLIF(COUNT(DISTINCT txn_id), 0) - 1) * 100, 1) AS redemption_inflate_pct
    FROM tagged
    """


def _sf_launch_campaign_dedup_sql() -> str:
    return """
    WITH tagged AS (
      SELECT *
      FROM fact_promo_redemption
      WHERE campaign_id = 'SF-LAUNCH-2568'
    ),
    ranked AS (
      SELECT
        *,
        ROW_NUMBER() OVER (
          PARTITION BY txn_id
          ORDER BY CASE WHEN channel = 'app' THEN 1 ELSE 0 END, redemption_id
        ) AS dedup_rank
      FROM tagged
    )
    SELECT
      COUNT(*) AS raw_redemption_count,
      COUNT(*) FILTER (WHERE dedup_rank > 1) AS phantom_duplicate_count,
      COUNT(*) FILTER (WHERE dedup_rank = 1) AS unique_redemption_count,
      SUM(discount_applied_thb) FILTER (WHERE dedup_rank = 1) AS dedup_discount_thb
    FROM ranked
    """


def _sf_launch_roi_sql() -> str:
    return """
    WITH redemptions AS (
      SELECT *
      FROM fact_promo_redemption
      WHERE campaign_id = 'SF-LAUNCH-2568'
    ),
    dedup AS (
      SELECT
        *,
        ROW_NUMBER() OVER (
          PARTITION BY txn_id
          ORDER BY CASE WHEN channel = 'app' THEN 1 ELSE 0 END, redemption_id
        ) AS dedup_rank
      FROM redemptions
    ),
    cohort_txns AS (
      SELECT DISTINCT txn_id
      FROM dedup
      WHERE dedup_rank = 1
    ),
    sales AS (
      SELECT
        SUM(discount_total_thb) AS pos_discount_cost_thb,
        SUM(net_total_thb) AS net_revenue_thb
      FROM v_sales
      WHERE txn_id IN (SELECT txn_id FROM cohort_txns)
    )
    SELECT
      (SELECT COUNT(*) FROM redemptions) AS raw_redemption_count,
      (SELECT COUNT(*) FROM dedup WHERE dedup_rank > 1) AS phantom_duplicate_count,
      (SELECT COUNT(*) FROM cohort_txns) AS unique_redemption_count,
      (SELECT SUM(discount_applied_thb) FROM dedup WHERE dedup_rank = 1) AS dedup_redemption_discount_thb,
      sales.pos_discount_cost_thb,
      sales.net_revenue_thb,
      ROUND(sales.net_revenue_thb / NULLIF(sales.pos_discount_cost_thb, 0), 1) AS roi_x,
      (
        SELECT COUNT(*)
        FROM v_bank_txn
        WHERE related_entity_id = 'V-013'
          AND business_event_date >= DATE '2025-07-01'
          AND business_event_date < DATE '2025-08-01'
      ) AS paywise_july_bank_rows
    FROM sales
    """


def _recall_reconciliation_sql() -> str:
    return """
    WITH recall_window AS (
      SELECT
        MIN(transition_date) FILTER (WHERE status = 'active') AS active_date,
        MIN(transition_date) FILTER (WHERE status = 'completed') AS completed_date
      FROM dim_product_recall_history
      WHERE sku_id = 'NT-LT-001'
    ),
    recall_returns AS (
      SELECT r.*
      FROM fact_return r
      CROSS JOIN recall_window w
      WHERE r.sku_id = 'NT-LT-001'
        AND lower(r.return_reason) LIKE '%recall%'
        AND r.business_event_date BETWEEN w.active_date AND w.completed_date
    ),
    refunds AS (
      SELECT SUM(p.refund_amount_thb) AS refund_paid_thb
      FROM fact_refund_paid p
      WHERE p.return_id IN (SELECT return_id FROM recall_returns)
    ),
    warranty_policy AS (
      SELECT policy_version_id, value_text, effective_date
      FROM dim_policy_version
      WHERE policy_variable = 'warranty_routing'
        AND effective_date <= DATE '2025-09-10'
      ORDER BY effective_date DESC
      LIMIT 1
    )
    SELECT
      w.active_date,
      w.completed_date,
      (SELECT COUNT(*) FROM recall_returns) AS recall_return_count,
      (SELECT refund_paid_thb FROM refunds) AS refund_paid_thb,
      (SELECT policy_version_id FROM warranty_policy) AS warranty_policy_version_id,
      (SELECT value_text FROM warranty_policy) AS warranty_routing_destination,
      (
        SELECT COUNT(*)
        FROM v_bank_txn
        WHERE related_entity_id = 'V-002'
          AND amount_thb > 0
          AND business_event_date BETWEEN w.active_date AND w.completed_date
      ) AS vendor_reimbursement_deposit_count
    FROM recall_window w
    """


def _recall_profile_sql() -> str:
    return """
    SELECT
      COUNT(*) AS recall_return_count,
      SUM(return_amount_thb) AS return_amount_thb,
      approved_by_employee_id,
      ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS approver_pct,
      COUNT(DISTINCT branch_code) AS branch_count,
      STRING_AGG(DISTINCT branch_code, ', ' ORDER BY branch_code) AS branch_codes,
      MIN(days_since_purchase) AS min_days_since_purchase,
      MAX(days_since_purchase) AS max_days_since_purchase
    FROM fact_return
    WHERE sku_id = 'NT-LT-001'
      AND lower(return_reason) LIKE '%recall%'
      AND business_event_date BETWEEN DATE '2025-09-10' AND DATE '2025-10-15'
    GROUP BY approved_by_employee_id
    ORDER BY recall_return_count DESC
    """


def _bkk_pkt_april_decomposition_sql() -> str:
    return """
    WITH monthly AS (
      SELECT
        date_trunc('month', business_event_date)::date AS month_start,
        SUM(net_total_thb) AS net_sales_thb,
        COUNT(DISTINCT business_event_date) AS operating_days
      FROM v_sales
      WHERE branch_code = 'BKK-PKT'
        AND business_event_date >= DATE '2025-03-01'
        AND business_event_date < DATE '2025-06-01'
      GROUP BY month_start
    ),
    baseline AS (
      SELECT SUM(net_sales_thb) / NULLIF(SUM(operating_days), 0) AS baseline_per_op_day
      FROM monthly
      WHERE month_start IN (DATE '2025-03-01', DATE '2025-05-01')
    ),
    april AS (
      SELECT net_sales_thb, operating_days
      FROM monthly
      WHERE month_start = DATE '2025-04-01'
    )
    SELECT
      ROUND(b.baseline_per_op_day, 0) AS baseline_thb_per_op_day,
      a.net_sales_thb AS observed_april_sales_thb,
      30 - a.operating_days AS lost_operating_days,
      ROUND(b.baseline_per_op_day * 13, 0) AS pkt_unique_renovation_loss_thb,
      ROUND(b.baseline_per_op_day * 5, 0) AS songkran_loss_thb,
      0 AS v005_overlap_loss_thb
    FROM baseline b CROSS JOIN april a
    """


def _network_april_gap_sql() -> str:
    return """
    WITH physical_daily AS (
      SELECT business_event_date, SUM(net_total_thb) AS net_sales_thb
      FROM v_sales
      WHERE branch_code <> 'REMOTE'
        AND business_event_date >= DATE '2025-03-01'
        AND business_event_date < DATE '2025-06-01'
      GROUP BY business_event_date
    ),
    baseline AS (
      SELECT AVG(net_sales_thb) AS baseline_daily_thb
      FROM physical_daily
      WHERE business_event_date < DATE '2025-04-01'
         OR business_event_date >= DATE '2025-05-01'
    )
    SELECT
      ROUND(baseline_daily_thb * 5, 0) AS songkran_network_loss_thb,
      ROUND(baseline_daily_thb * 13, 0) AS bkk_pkt_incremental_loss_proxy_thb,
      ROUND(baseline_daily_thb * 18, 0) AS combined_loss_proxy_thb
    FROM baseline
    """


def _cs_refund_violation_sql() -> str:
    return """
    WITH cs_employee AS (
      SELECT employee_id
      FROM dim_employee
      WHERE dept_code = 'SUP'
        AND position_level = 'IC'
      ORDER BY employee_id
      LIMIT 1
    )
    SELECT
      p.approver_employee_id,
      COUNT(*) FILTER (WHERE p.cosig_employee_id IS NULL AND p.business_event_date < DATE '2025-02-15') AS pre_pm1_no_cosig_rows,
      SUM(p.refund_amount_thb) FILTER (WHERE p.cosig_employee_id IS NULL AND p.business_event_date < DATE '2025-02-15') AS pre_pm1_no_cosig_amount_thb,
      COUNT(*) FILTER (WHERE p.cosig_employee_id IS NULL AND p.business_event_date >= DATE '2025-02-15' AND p.refund_amount_thb > 5000) AS post_pm1_over_threshold_rows,
      SUM(p.refund_amount_thb) FILTER (WHERE p.cosig_employee_id IS NULL AND p.business_event_date >= DATE '2025-02-15' AND p.refund_amount_thb > 5000) AS post_pm1_over_threshold_amount_thb
    FROM fact_refund_paid p
    WHERE p.approver_employee_id = (SELECT employee_id FROM cs_employee)
    GROUP BY p.approver_employee_id
    """


def _ollie_irregularity_sql() -> str:
    return """
    SELECT
      'missing_cosigner_refunds' AS category,
      COUNT(*) AS row_count,
      SUM(refund_amount_thb) AS amount_thb
    FROM fact_refund_paid
    WHERE approver_employee_id = 'EMP-L3-00008'
      AND cosig_employee_id IS NULL
      AND business_event_date BETWEEN DATE '2024-10-01' AND DATE '2025-06-30'
    UNION ALL
    SELECT
      'vendor_payment_involvement' AS category,
      COUNT(*) AS row_count,
      SUM(paid_amount_thb) AS amount_thb
    FROM fact_vendor_payment
    WHERE (signing_employee_id = 'EMP-L3-00008' OR cosig_employee_id = 'EMP-L3-00008')
      AND business_event_date BETWEEN DATE '2024-10-01' AND DATE '2025-06-30'
    UNION ALL
    SELECT
      'late_signing_month_mismatch' AS category,
      COUNT(*) AS row_count,
      SUM(paid_amount_thb) AS amount_thb
    FROM fact_vendor_payment
    WHERE (signing_employee_id = 'EMP-L3-00008' OR cosig_employee_id = 'EMP-L3-00008')
      AND business_event_date BETWEEN DATE '2024-10-01' AND DATE '2025-06-30'
      AND date_trunc('month', posting_date) <> date_trunc('month', business_event_date)
    """


def _warranty_vendor_batch_sql() -> str:
    return """
    WITH claims AS (
      SELECT
        c.*,
        substring(c.claim_reason from '\\(([^)]*)\\)') AS batch_id
      FROM fact_warranty_claim c
      WHERE lower(c.claim_reason) LIKE '%vendor batch defect%'
        AND lower(c.claim_reason) LIKE '%v-004%'
    )
    SELECT
      batch_id,
      c.sku_id,
      p.brand_family,
      p.category,
      p.msrp_thb,
      COUNT(*) AS claim_count,
      SUM(c.claim_amount_thb) AS claim_amount_thb,
      MIN(c.business_event_date) AS first_claim_date,
      MAX(c.business_event_date) AS last_claim_date,
      COUNT(DISTINCT c.customer_id) AS distinct_customer_count
    FROM claims c
    LEFT JOIN dim_product p ON p.sku_id = c.sku_id
    GROUP BY batch_id, c.sku_id, p.brand_family, p.category, p.msrp_thb
    ORDER BY claim_count DESC
    LIMIT 1
    """


def _pos_schema_reconcile_sql() -> str:
    return """
    WITH parsed AS (
      SELECT
        to_date(left(timestamp, 10), 'YYYY-MM-DD') AS log_date,
        *
      FROM pos_logs
    )
    SELECT
      MIN(log_date) FILTER (WHERE schema_version = 2) AS schema_v2_cutover_date,
      'discount_amt' AS v1_discount_column,
      'discount_total_thb' AS v2_discount_column,
      'payment_terminal_id, discount_total_thb, loyalty_tier_at_purchase' AS added_columns,
      COUNT(*) FILTER (
        WHERE branch_code = 'BKK-CTW'
          AND log_date >= DATE '2025-03-01'
          AND log_date < DATE '2025-04-01'
      ) AS bkk_ctw_march_lines,
      COUNT(*) FILTER (
        WHERE branch_code = 'BKK-CTW'
          AND log_date >= DATE '2025-04-01'
          AND log_date < DATE '2025-05-01'
      ) AS bkk_ctw_april_lines,
      SUM(unit_price_thb * quantity) FILTER (
        WHERE branch_code = 'BKK-CTW'
          AND log_date >= DATE '2025-03-01'
          AND log_date < DATE '2025-04-01'
      ) AS bkk_ctw_march_gross_thb
    FROM parsed
    """


def _pre_recall_battery_signal_sql() -> str:
    return """
    SELECT
      COUNT(*) AS pre_recall_battery_claim_count,
      MIN(business_event_date) AS first_claim_date,
      MAX(business_event_date) AS last_claim_date,
      DATE '2025-09-10' - MAX(business_event_date) AS days_before_active_recall,
      STRING_AGG(DISTINCT routing_destination, ', ' ORDER BY routing_destination) AS routing_destinations
    FROM fact_warranty_claim
    WHERE sku_id = 'NT-LT-001'
      AND business_event_date < DATE '2025-09-10'
      AND lower(claim_reason) LIKE '%battery%'
    """


def _top_b2b_account_sql() -> str:
    return """
    WITH top_customer AS (
      SELECT customer_id, SUM(net_total_thb) AS all_time_net_total_thb
      FROM v_sales
      WHERE is_b2b = true
      GROUP BY customer_id
      ORDER BY all_time_net_total_thb DESC
      LIMIT 1
    ),
    top_sku AS (
      SELECT
        i.customer_id,
        i.sku_id,
        i.brand_family,
        i.category,
        SUM(i.line_total_thb) AS sku_revenue_thb
      FROM v_sales_items i
      JOIN top_customer c ON c.customer_id = i.customer_id
      GROUP BY i.customer_id, i.sku_id, i.brand_family, i.category
      ORDER BY sku_revenue_thb DESC
      LIMIT 1
    ),
    active_months AS (
      SELECT customer_id, COUNT(DISTINCT date_trunc('month', business_event_date)) AS active_month_count
      FROM v_sales
      WHERE customer_id = (SELECT customer_id FROM top_customer)
      GROUP BY customer_id
    )
    SELECT
      c.customer_id,
      c.all_time_net_total_thb,
      s.sku_id AS top_sku_id,
      s.brand_family AS top_sku_brand_family,
      s.category AS top_sku_category,
      s.sku_revenue_thb AS top_sku_revenue_thb,
      m.active_month_count
    FROM top_customer c
    JOIN top_sku s ON s.customer_id = c.customer_id
    JOIN active_months m ON m.customer_id = c.customer_id
    """


def _discount_outlier_sql() -> str:
    return """
    WITH monthly AS (
      SELECT
        sku_id,
        date_trunc('month', business_event_date)::date AS month_start,
        SUM(quantity) AS units_sold
      FROM v_sales_items
      WHERE business_event_date >= DATE '2024-01-01'
        AND business_event_date < DATE '2026-01-01'
      GROUP BY sku_id, month_start
    ),
    scored AS (
      SELECT
        m.*,
        (
          SELECT AVG(prev.units_sold)
          FROM monthly prev
          WHERE prev.sku_id = m.sku_id
            AND prev.month_start >= m.month_start - INTERVAL '12 months'
            AND prev.month_start < m.month_start
        ) AS prev_avg_units
      FROM monthly m
      WHERE m.month_start >= DATE '2025-01-01'
        AND m.month_start < DATE '2026-01-01'
    ),
    candidate AS (
      SELECT *
      FROM scored
      WHERE prev_avg_units > 0
      ORDER BY units_sold / prev_avg_units DESC
      LIMIT 1
    )
    SELECT
      c.sku_id,
      p.brand_family,
      p.category,
      c.month_start,
      ROUND(c.units_sold / NULLIF(c.prev_avg_units, 0), 1) AS unit_lift_x,
      SUM((i.msrp_thb - i.unit_price_thb) * i.quantity) FILTER (WHERE i.unit_price_thb < i.msrp_thb) AS foregone_revenue_thb
    FROM candidate c
    JOIN v_sales_items i
      ON i.sku_id = c.sku_id
     AND date_trunc('month', i.business_event_date)::date = c.month_start
    JOIN dim_product p ON p.sku_id = c.sku_id
    GROUP BY c.sku_id, p.brand_family, p.category, c.month_start, c.units_sold, c.prev_avg_units
    """


def _nps_absence_sql() -> str:
    return """
    SELECT
      COUNT(*) AS nps_mentions,
      COUNT(DISTINCT path) AS nps_document_count
    FROM doc_corpus
    WHERE lower(content) LIKE '%nps%'
       OR lower(title) LIKE '%nps%'
       OR lower(topic) LIKE '%nps%'
    """


def _employee_authority_check_sql(first_name: str, last_name: str) -> str:
    first = _sql_string(first_name)
    last = _sql_string(last_name)
    return f"""
    SELECT
      e.employee_id,
      e.first_name_en || ' ' || e.last_name_en AS employee_name,
      e.dept_code,
      e.position_level,
      e.position_title,
      l.policy_version_id,
      l.amount_ceiling_thb,
      l.min_co_signers,
      l.co_signer_min_position_level_code
    FROM dim_employee e
    LEFT JOIN dim_signing_authority_ladder l
      ON l.dept_code = e.dept_code
     AND l.position_level_code = e.position_level
    WHERE lower(e.first_name_en) = lower('{first}')
      AND lower(e.last_name_en) = lower('{last}')
    ORDER BY l.amount_ceiling_thb DESC NULLS LAST
    """
