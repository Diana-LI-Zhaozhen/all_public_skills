"""Cross-encoder reranker for improving retrieval quality."""

import logging
from typing import Optional

from src.models import DocumentChunk

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading reranker model: %s", self.model_name)
            self._model = CrossEncoder(self.model_name)

    def rerank(
        self,
        query: str,
        candidates: list[tuple[DocumentChunk, float]],
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        if not candidates:
            return []

        self._load_model()

        # Prepare pairs for cross-encoder
        pairs = [(query, chunk.content[:1024]) for chunk, _ in candidates]
        scores = self._model.predict(pairs)

        # Combine with original chunks
        scored = list(zip(candidates, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        results = [
            (chunk, float(rerank_score))
            for (chunk, _orig_score), rerank_score in scored[:top_k]
        ]

        logger.debug(
            "Reranked %d candidates -> top %d (scores: %.3f to %.3f)",
            len(candidates),
            len(results),
            results[0][1] if results else 0,
            results[-1][1] if results else 0,
        )
        return results
