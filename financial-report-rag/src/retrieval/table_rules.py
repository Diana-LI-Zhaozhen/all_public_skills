"""Rule-based table query extraction and SQL condition generation (no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass

METRIC_ALIASES = {
    "revenue": ["revenue", "营业收入", "营收", "收入"],
    "profit": ["profit", "利润", "营业利润", "利润总额"],
    "net_income": ["net income", "net_income", "净利润", "归母净利润", "归属于上市公司股东的净利润"],
    "eps": ["eps", "每股收益", "基本每股收益", "稀释每股收益"],
    "operating_margin": ["operating margin", "operating_margin", "营业利润率", "经营利润率"],
}


@dataclass
class SQLConditions:
    metrics: list[str]
    years: list[int]
    operator: str | None
    value: float | None


def _normalize_metric(metric: str) -> str:
    return metric.strip().lower().replace(" ", "_")


def extract_sql_conditions(query: str) -> SQLConditions:
    q = query.lower()

    found_metrics: list[str] = []
    for canonical, aliases in METRIC_ALIASES.items():
        if any(alias.lower() in q for alias in aliases):
            found_metrics.append(canonical)

    year_pattern = re.compile(r"((?:19|20)\d{2})")
    years = [int(y) for y in year_pattern.findall(q)]

    op = None
    if ">=" in q:
        op = ">="
    elif "<=" in q:
        op = "<="
    elif ">" in q:
        op = ">"
    elif "<" in q:
        op = "<"
    elif "exceed" in q or "above" in q or "greater than" in q or "超过" in q or "高于" in q:
        op = ">"
    elif "below" in q or "less than" in q or "低于" in q or "小于" in q:
        op = "<"

    value = _extract_numeric_value(q)

    return SQLConditions(metrics=found_metrics, years=years, operator=op, value=value)


def _extract_numeric_value(query: str) -> float | None:
    # Supports: 10, 10.5, 10 billion, 500 million, 10b, 500m, 10亿元, 500万元
    pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(billion|million|b|m|亿元|亿|万元|万)?\b")
    matches = pattern.findall(query)
    if not matches:
        return None

    raw_num, unit = matches[-1]
    value = float(raw_num)

    unit = unit.lower() if unit else ""
    if unit in ("billion", "b"):
        value *= 1_000_000_000
    elif unit in ("million", "m"):
        value *= 1_000_000
    elif unit in ("亿元", "亿"):
        value *= 100_000_000
    elif unit in ("万元", "万"):
        value *= 10_000

    return value
