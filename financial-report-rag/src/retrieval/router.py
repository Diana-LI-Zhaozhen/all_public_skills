"""Query router using deterministic rules (no LLM)."""

import logging

logger = logging.getLogger(__name__)

NUMERIC_TRIGGERS = [
    "revenue",
    "profit",
    "eps",
    "net income",
    "billion",
    "million",
    "growth",
    "ratio",
    ">=",
    "<=",
    ">",
    "<",
    "between",
    "table",
    "show me",
    "list",
    "compare",
    "total",
    "收入",
    "营收",
    "营业收入",
    "利润",
    "净利润",
    "净收入",
    "毛利率",
    "经营利润",
    "同比",
    "环比",
    "亿元",
    "万元",
    "表",
    "列出",
    "比较",
    "合计",
    "是多少",
]

EXACT_TRIGGERS = ['"', "exact", "code", "identifier", "精确", "代码", "编号"]


class QueryRouter:
    def route(self, query: str) -> str:
        q = query.lower()

        # 1) Numeric/table query -> direct table SQL route.
        if any(t in q for t in NUMERIC_TRIGGERS):
            logger.info("Query routed to: table_sql")
            return "table_sql"

        # 2) Exact keyword query -> BM25 only.
        if any(t in q for t in EXACT_TRIGGERS):
            logger.info("Query routed to: keyword_only")
            return "keyword_only"

        # 3) Default -> hybrid retrieval.
        logger.info("Query routed to: hybrid")
        return "hybrid"
