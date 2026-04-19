"""Vector index using FAISS and sentence-transformers."""

import logging
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from src.models import DocumentChunk

logger = logging.getLogger(__name__)


class VectorIndex:
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5", index_path: str = "./indexes/faiss.index"):
        self.model_name = model_name
        self.index_path = index_path
        self._chunks_path = index_path + ".chunks.pkl"
        self.model = None
        self.index = None
        self.chunks: list[DocumentChunk] = []
        self.dimension: Optional[int] = None

    def _load_model(self):
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()

    def _init_index(self):
        if self.index is None:
            import faiss
            self._load_model()
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine with normalized vectors)

    def build(self, chunks: list[DocumentChunk], batch_size: int = 64) -> None:
        import faiss
        self._load_model()

        texts = [c.content for c in chunks]
        logger.info("Generating embeddings for %d chunks...", len(texts))

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embs = self.model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
            all_embeddings.append(embs)

        embeddings = np.vstack(all_embeddings).astype("float32")

        # Store embeddings in chunks
        for i, chunk in enumerate(chunks):
            chunk.embedding = embeddings[i].tolist()

        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        self.chunks = list(chunks)

        logger.info("Built vector index with %d vectors (dim=%d)", self.index.ntotal, self.dimension)

    def add(self, new_chunks: list[DocumentChunk], batch_size: int = 64) -> None:
        self._load_model()
        self._init_index()

        texts = [c.content for c in new_chunks]
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embs = self.model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
            all_embeddings.append(embs)

        embeddings = np.vstack(all_embeddings).astype("float32")
        for i, chunk in enumerate(new_chunks):
            chunk.embedding = embeddings[i].tolist()

        self.index.add(embeddings)
        self.chunks.extend(new_chunks)
        logger.info("Added %d vectors to index (total: %d)", len(new_chunks), self.index.ntotal)

    def search(self, query: str, top_k: int = 20) -> list[tuple[DocumentChunk, float]]:
        if self.index is None or self.index.ntotal == 0:
            return []

        self._load_model()
        query_vec = self.model.encode([query], normalize_embeddings=True).astype("float32")
        scores, indices = self.index.search(query_vec, min(top_k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                results.append((self.chunks[idx], float(score)))
        return results

    def save(self) -> None:
        import faiss
        if self.index is not None:
            Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, self.index_path)
            with open(self._chunks_path, "wb") as f:
                pickle.dump(self.chunks, f)
            logger.info("Saved vector index to %s", self.index_path)

    def load(self) -> bool:
        import faiss
        if os.path.exists(self.index_path) and os.path.exists(self._chunks_path):
            self.index = faiss.read_index(self.index_path)
            with open(self._chunks_path, "rb") as f:
                self.chunks = pickle.load(f)
            self.dimension = self.index.d
            logger.info("Loaded vector index: %d vectors", self.index.ntotal)
            return True
        return False
