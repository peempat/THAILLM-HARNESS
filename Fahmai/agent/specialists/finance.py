from __future__ import annotations

from decimal import Decimal, DivisionByZero


def roi(incremental_revenue: str | int | float, cost: str | int | float) -> dict:
    revenue = Decimal(str(incremental_revenue))
    cost_value = Decimal(str(cost))
    try:
        value = (revenue - cost_value) / cost_value
    except DivisionByZero:
        return {"status": "error", "warnings": ["cost is zero"], "result": None}
    return {
        "status": "success",
        "formula": "ROI = (incremental_revenue - cost) / cost",
        "inputs": {"incremental_revenue": str(revenue), "cost": str(cost_value)},
        "result": {"roi": str(value), "roi_percent": str(value * Decimal("100"))},
        "warnings": [],
    }


def percent_share(part: str | int | float, total: str | int | float) -> dict:
    part_value = Decimal(str(part))
    total_value = Decimal(str(total))
    try:
        value = part_value / total_value
    except DivisionByZero:
        return {"status": "error", "warnings": ["total is zero"], "result": None}
    return {
        "status": "success",
        "formula": "share = part / total",
        "inputs": {"part": str(part_value), "total": str(total_value)},
        "result": {"share": str(value), "share_percent": str(value * Decimal("100"))},
        "warnings": [],
    }
