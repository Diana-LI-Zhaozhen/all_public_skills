"""Hybrid retriever combining vector search, BM25, and table store with RRF fusion."""

import logging
import json
from typing import Optional

import pandas as pd

from src.indexing.keyword_index import KeywordIndex
from src.indexing.table_store import TableStore
from src.indexing.vector_index import VectorIndex
from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType
from src.retrieval.reranker import Reranker
from src.retrieval.router import QueryRouter
from src.retrieval.table_rules import extract_sql_conditions

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    result_lists: list[list[tuple[DocumentChunk, float]]],
    k: int = 60,
) -> list[tuple[DocumentChunk, float]]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    chunk_map: dict[str, DocumentChunk] = {}

    for result_list in result_lists:
        for rank, (chunk, _score) in enumerate(result_list):
            chunk_id = chunk.id
            chunk_map[chunk_id] = chunk
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    return [(chunk_map[cid], scores[cid]) for cid in sorted_ids]


class HybridRetriever:
    def __init__(
        self,
        vector_index: VectorIndex,
        keyword_index: KeywordIndex,
        table_store: TableStore,
        reranker: Optional[Reranker] = None,
        rrf_k: int = 60,
        top_k_initial: int = 20,
        top_k_final: int = 5,
    ):
        self.vector_index = vector_index
        self.keyword_index = keyword_index
        self.table_store = table_store
        self.reranker = reranker
        self.router = QueryRouter()
        self.rrf_k = rrf_k
        self.top_k_initial = top_k_initial
        self.top_k_final = top_k_final

    def retrieve(self, query: str) -> list[tuple[DocumentChunk, float]]:
        route = self.router.route(query)

        if route == "table_sql":
            results = self._table_retrieval(query)
            if results:
                return results
            # Fall back to hybrid if no table results
            logger.info("Table retrieval returned no results, falling back to hybrid")
            route = "hybrid"

        if route == "keyword_only":
            results = self.keyword_index.search(query, top_k=self.top_k_initial)
        else:
            # Hybrid: vector + keyword with RRF
            vector_results = self.vector_index.search(query, top_k=self.top_k_initial)
            keyword_results = self.keyword_index.search(query, top_k=self.top_k_initial)
            results = reciprocal_rank_fusion(
                [vector_results, keyword_results], k=self.rrf_k
            )

        # Limit to top_k_initial before reranking
        results = results[: self.top_k_initial]

        # Rerank if available
        if self.reranker and results:
            results = self.reranker.rerank(query, results, top_k=self.top_k_final)
        else:
            results = results[: self.top_k_final]

        return results

    def _table_retrieval(self, query: str) -> list[tuple[DocumentChunk, float]]:
        """Rule-based table retrieval without NL2SQL LLM conversion."""
        conditions = extract_sql_conditions(query)

        rows = self.table_store.query_metric_rows(
            metrics=conditions.metrics,
            years=conditions.years,
            operator=conditions.operator,
            value=conditions.value,
            limit=max(self.top_k_initial, 20),
        )

        if not rows:
            return []

        results: list[tuple[DocumentChunk, float]] = []
        for row in rows:
            try:
                row_dict = json.loads(row["row_data"]) if row.get("row_data") else {}
                row_df = pd.DataFrame([row_dict]) if row_dict else pd.DataFrame()
                table_text = row_df.to_markdown(index=False) if not row_df.empty else str(row_dict)
                chunk = DocumentChunk(
                    id=row["table_id"],
                    content=(
                        f"[Source: {row['source']}, Sheet: {row['sheet'] or 'N/A'}]\n"
                        f"Metric: {row['metric']}\n"
                        f"Year: {row['year']}\n"
                        f"Value: {row['numeric_value']}\n"
                        f"Row:\n{table_text}"
                    ),
                    source_file=row["source"],
                    file_type=FileType.XLSX,
                    chunk_type=ChunkType.TABLE,
                    metadata=ChunkMetadata(
                        sheet=row["sheet"],
                        table_name=row["table_id"],
                        headers=list(row_dict.keys()),
                        row_count=1,
                    ),
                    dataframe=row_df if not row_df.empty else None,
                )
                results.append((chunk, 1.0))
            except Exception as e:
                logger.warning("Failed to process metric row %s: %s", row.get("table_id"), e)

        # If we have a reranker, use it to select the most relevant tables
        if self.reranker and results:
            results = self.reranker.rerank(query, results, top_k=self.top_k_final)
        else:
            results = results[: self.top_k_final]

        return results
