"""BM25 keyword index using rank_bm25."""

import logging
import os
import pickle
import re
from pathlib import Path

from src.models import DocumentChunk

logger = logging.getLogger(__name__)

# Finance-specific stopwords in addition to common English ones
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "and", "but", "or", "nor",
    "not", "no", "so", "too", "very", "just", "about", "up", "down", "here",
    "there", "when", "where", "why", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "than", "that", "this",
    "these", "those", "it", "its", "he", "she", "they", "them", "their",
    "we", "our", "you", "your", "i", "me", "my",
}


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"\b[a-z0-9]+(?:\.[0-9]+)*\b", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


class KeywordIndex:
    def __init__(self, index_path: str = "./indexes/bm25.pkl"):
        self.index_path = index_path
        self.bm25 = None
        self.chunks: list[DocumentChunk] = []
        self._corpus: list[list[str]] = []

    def build(self, chunks: list[DocumentChunk]) -> None:
        from rank_bm25 import BM25Okapi

        self.chunks = list(chunks)
        self._corpus = [tokenize(c.content) for c in chunks]
        self.bm25 = BM25Okapi(self._corpus)
        logger.info("Built BM25 index with %d documents", len(self.chunks))

    def add(self, new_chunks: list[DocumentChunk]) -> None:
        from rank_bm25 import BM25Okapi

        self.chunks.extend(new_chunks)
        new_tokenized = [tokenize(c.content) for c in new_chunks]
        self._corpus.extend(new_tokenized)
        # Rebuild BM25 (rank_bm25 doesn't support incremental add)
        self.bm25 = BM25Okapi(self._corpus)
        logger.info("Rebuilt BM25 index with %d documents", len(self.chunks))

    def search(self, query: str, top_k: int = 20) -> list[tuple[DocumentChunk, float]]:
        if self.bm25 is None or not self.chunks:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Get top-k indices
        top_indices = scores.argsort()[-top_k:][::-1]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((self.chunks[idx], float(scores[idx])))
        return results

    def save(self) -> None:
        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "wb") as f:
            pickle.dump(
                {
                    "chunks": self.chunks,
                    "corpus": self._corpus,
                },
                f,
            )
        logger.info("Saved BM25 index to %s", self.index_path)

    def load(self) -> bool:
        from rank_bm25 import BM25Okapi

        if os.path.exists(self.index_path):
            with open(self.index_path, "rb") as f:
                data = pickle.load(f)
            self.chunks = data["chunks"]
            self._corpus = data["corpus"]
            self.bm25 = BM25Okapi(self._corpus)
            logger.info("Loaded BM25 index: %d documents", len(self.chunks))
            return True
        return False
