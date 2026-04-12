"""Main pipeline orchestrating ingestion, indexing, and querying."""

import logging
from pathlib import Path
from typing import Any, Optional

from src.chunker import TextChunker
from src.config import load_config
from src.generation.llm_wrapper import LLMWrapper
from src.indexing.keyword_index import KeywordIndex
from src.indexing.metadata_index import MetadataIndex
from src.indexing.table_store import TableStore
from src.indexing.vector_index import VectorIndex
from src.models import DocumentChunk
from src.parsers.dispatcher import FileDispatcher
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        paths = self.config.get("paths", {})

        # Initialize components
        self.dispatcher = FileDispatcher()
        self.chunker = TextChunker(
            chunk_size=self.config.get("chunk_size_tokens", 512),
            overlap=self.config.get("chunk_overlap_tokens", 50),
        )

        self.vector_index = VectorIndex(
            model_name=self.config.get("embedding_model", "BAAI/bge-large-en-v1.5"),
            index_path=paths.get("faiss_index_path", "./indexes/faiss.index"),
        )
        self.keyword_index = KeywordIndex(
            index_path=paths.get("bm25_index_path", "./indexes/bm25.pkl"),
        )
        self.table_store = TableStore(
            db_path=paths.get("duckdb_path", "./indexes/tables.duckdb"),
        )
        self.metadata_index = MetadataIndex(
            db_path=paths.get("db_path", "./indexes/metadata.db"),
        )

        reranker_model = self.config.get("reranker_model", "BAAI/bge-reranker-base")
        self.reranker = Reranker(model_name=reranker_model)

        retrieval_cfg = self.config.get("retrieval", {})
        self.retriever = HybridRetriever(
            vector_index=self.vector_index,
            keyword_index=self.keyword_index,
            table_store=self.table_store,
            reranker=self.reranker,
            rrf_k=retrieval_cfg.get("rrf_k", 60),
            top_k_initial=retrieval_cfg.get("top_k_initial", 20),
            top_k_final=retrieval_cfg.get("top_k_final", 5),
        )

        self.llm = LLMWrapper(self.config.get("llm", {}))
        self._all_chunks: list[DocumentChunk] = []

    def ingest_file(self, file_path: str) -> int:
        logger.info("Ingesting file: %s", file_path)
        raw_chunks = self.dispatcher.parse_file(file_path)
        if not raw_chunks:
            logger.warning("No chunks produced from %s", file_path)
            return 0

        chunks = self.chunker.chunk_documents(raw_chunks)
        self._index_chunks(chunks)
        return len(chunks)

    def ingest_directory(self, dir_path: str) -> int:
        logger.info("Ingesting directory: %s", dir_path)
        raw_chunks = self.dispatcher.parse_directory(dir_path)
        if not raw_chunks:
            logger.warning("No chunks produced from %s", dir_path)
            return 0

        chunks = self.chunker.chunk_documents(raw_chunks)
        self._index_chunks(chunks)
        return len(chunks)

    def _index_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return

        logger.info("Indexing %d chunks...", len(chunks))

        # Build or add to vector index
        if not self._all_chunks:
            self.vector_index.build(chunks)
        else:
            self.vector_index.add(chunks)

        # Build or add to keyword index
        if not self._all_chunks:
            self.keyword_index.build(chunks)
        else:
            self.keyword_index.add(chunks)

        # Insert tables into table store
        self.table_store.insert_chunks(chunks)

        # Insert metadata
        self.metadata_index.insert_chunks(chunks)

        self._all_chunks.extend(chunks)
        logger.info("Total indexed chunks: %d", len(self._all_chunks))

    def query(self, question: str) -> dict[str, Any]:
        logger.info("Query: %s", question)

        # Retrieve relevant chunks
        results = self.retriever.retrieve(question)

        if not results:
            return {
                "answer": "No relevant documents found for your query.",
                "sources": [],
                "num_chunks": 0,
            }

        # Generate answer
        answer = self.llm.generate(question, results)

        # Collect source citations
        sources = []
        for chunk, score in results:
            source = {"file": chunk.source_file, "score": round(score, 4)}
            if chunk.metadata.page:
                source["page"] = chunk.metadata.page
            if chunk.metadata.sheet:
                source["sheet"] = chunk.metadata.sheet
            if chunk.metadata.table_name:
                source["table"] = chunk.metadata.table_name
            sources.append(source)

        return {
            "answer": answer,
            "sources": sources,
            "num_chunks": len(results),
        }

    def save_indexes(self) -> None:
        self.vector_index.save()
        self.keyword_index.save()
        logger.info("All indexes saved")

    def load_indexes(self) -> bool:
        v = self.vector_index.load()
        k = self.keyword_index.load()
        if v:
            self._all_chunks = list(self.vector_index.chunks)
        if v and k:
            logger.info("Loaded existing indexes")
            return True
        return False

    def get_stats(self) -> dict:
        stats = self.metadata_index.get_stats()
        stats["vector_index_size"] = (
            self.vector_index.index.ntotal if self.vector_index.index else 0
        )
        stats["keyword_index_size"] = len(self.keyword_index.chunks)
        return stats

    def close(self) -> None:
        self.table_store.close()
        self.metadata_index.close()
