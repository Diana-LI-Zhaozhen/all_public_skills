"""Unit tests for retrieval components."""

import pytest

from src.retrieval.router import QueryRouter


class TestQueryRouter:
    def setup_method(self):
        self.router = QueryRouter()

    def test_numerical_query(self):
        assert self.router.route("What was the revenue in Q4 2024?") == "table_sql"
        assert self.router.route("Net income exceeded 5 billion") == "table_sql"
        assert self.router.route("Show me profit margin ratio") == "table_sql"
        assert self.router.route("2023年营业收入是多少？") == "table_sql"
        assert self.router.route("比较2022和2023年的净利润") == "table_sql"

    def test_keyword_query(self):
        assert self.router.route('Find the "operating agreement" clause') == "keyword_only"
        assert self.router.route("Exact text from the schema definition") == "keyword_only"
        assert self.router.route("精确查找证券代码") == "keyword_only"

    def test_hybrid_query(self):
        assert self.router.route("What were the risk factors?") == "hybrid"
        assert self.router.route("Summarize the annual report") == "hybrid"
