"""Unit tests for indexing components."""

import os
import tempfile

import pandas as pd
import pytest

from src.indexing.keyword_index import KeywordIndex, tokenize
from src.indexing.metadata_index import MetadataIndex
from src.indexing.table_store import TableStore
from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType
from src.retrieval.table_rules import extract_sql_conditions


def make_chunk(content: str, chunk_type=ChunkType.TEXT, df=None, **meta_kw) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        source_file="test.txt",
        file_type=FileType.TXT,
        chunk_type=chunk_type,
        metadata=ChunkMetadata(**meta_kw),
        dataframe=df,
    )


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestTokenize:
    def test_basic(self):
        tokens = tokenize("The revenue was 10 billion dollars")
        assert "revenue" in tokens
        assert "billion" in tokens
        assert "dollars" in tokens
        assert "the" not in tokens

    def test_stopword_removal(self):
        tokens = tokenize("The a an is are was were")
        assert len(tokens) == 0


class TestKeywordIndex:
    def test_build_and_search(self, tmp_dir):
        idx = KeywordIndex(index_path=os.path.join(tmp_dir, "bm25.pkl"))
        chunks = [
            make_chunk("Revenue for Q4 2024 was 10 billion dollars"),
            make_chunk("Operating expenses increased by 5 percent year over year"),
            make_chunk("Net income was 1.5 billion after tax adjustments"),
        ]
        idx.build(chunks)
        results = idx.search("revenue Q4", top_k=2)
        assert len(results) > 0
        assert "revenue" in results[0][0].content.lower()

    def test_save_and_load(self, tmp_dir):
        path = os.path.join(tmp_dir, "bm25.pkl")
        idx = KeywordIndex(index_path=path)
        chunks = [make_chunk("test content about financial data")]
        idx.build(chunks)
        idx.save()

        idx2 = KeywordIndex(index_path=path)
        assert idx2.load() is True
        assert len(idx2.chunks) == 1


class TestTableStore:
    def test_insert_and_search(self, tmp_dir):
        db_path = os.path.join(tmp_dir, "tables.duckdb")
        store = TableStore(db_path=db_path)

        df = pd.DataFrame({"Year": [2023, 2024], "Revenue": [9.5e9, 10e9]})
        chunk = make_chunk(
            "Revenue table",
            chunk_type=ChunkType.TABLE,
            df=df,
            sheet="Q4",
            headers=["Year", "Revenue"],
            row_count=2,
        )

        count = store.insert_chunks([chunk])
        assert count == 1

        tables = store.search_tables(source="test.txt")
        assert len(tables) == 1
        assert tables[0]["source"] == "test.txt"

        store.close()

    def test_sql_query(self, tmp_dir):
        db_path = os.path.join(tmp_dir, "tables.duckdb")
        store = TableStore(db_path=db_path)

        df = pd.DataFrame({"Year": [2023, 2024], "Revenue": [9.5e9, 10e9]})
        chunk = make_chunk("Revenue table", chunk_type=ChunkType.TABLE, df=df)
        store.insert_chunks([chunk])

        result = store.query_sql("SELECT COUNT(*) as cnt FROM tables")
        assert result is not None
        assert result.iloc[0]["cnt"] == 1

        store.close()

    def test_metric_row_query(self, tmp_dir):
        db_path = os.path.join(tmp_dir, "tables.duckdb")
        store = TableStore(db_path=db_path)

        df = pd.DataFrame(
            {
                "Year": [2023, 2024],
                "Revenue": [9.5e9, 10e9],
                "Profit": [1.2e9, 1.5e9],
            }
        )
        chunk = make_chunk("Financial metrics", chunk_type=ChunkType.TABLE, df=df)
        store.insert_chunks([chunk])

        rows = store.query_metric_rows(
            metrics=["revenue"],
            years=[2024],
            operator=">=",
            value=9.9e9,
        )
        assert len(rows) == 1
        assert rows[0]["metric"] == "revenue"
        assert rows[0]["year"] == 2024

        store.close()


class TestMetadataIndex:
    def test_insert_and_filter(self, tmp_dir):
        db_path = os.path.join(tmp_dir, "metadata.db")
        idx = MetadataIndex(db_path=db_path)

        chunks = [
            make_chunk("text chunk", page=1),
            make_chunk("table chunk", chunk_type=ChunkType.TABLE, sheet="Q4"),
        ]
        idx.insert_chunks(chunks)

        stats = idx.get_stats()
        assert stats["total_chunks"] == 2

        ids = idx.filter_by_source("test.txt")
        assert len(ids) == 2

        ids = idx.filter_by_type(chunk_type="table")
        assert len(ids) == 1

        idx.close()


class TestTableRuleExtraction:
    def test_extract_metric_year_and_value(self):
        cond = extract_sql_conditions("Net income in 2024 exceeded 5 billion")
        assert "net_income" in cond.metrics
        assert 2024 in cond.years
        assert cond.operator == ">"
        assert cond.value == 5_000_000_000

    def test_extract_chinese_metric_year_and_value(self):
        cond = extract_sql_conditions("2023年营业收入超过10亿元吗？")
        assert "revenue" in cond.metrics
        assert 2023 in cond.years
        assert cond.operator == ">"
        assert cond.value == 1_000_000_000
