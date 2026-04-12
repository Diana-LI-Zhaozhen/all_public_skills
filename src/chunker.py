"""Text chunker that splits large text chunks according to token limits."""

import logging
import re

from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType

logger = logging.getLogger(__name__)


class TextChunker:
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_documents(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        result: list[DocumentChunk] = []
        for chunk in chunks:
            if chunk.chunk_type in (ChunkType.TABLE, ChunkType.SCHEMA):
                # Tables and schemas are kept as single chunks
                result.append(chunk)
            else:
                split = self._split_text_chunk(chunk)
                result.extend(split)
        return result

    def _split_text_chunk(self, chunk: DocumentChunk) -> list[DocumentChunk]:
        words = chunk.content.split()
        # Rough token estimate: 1 word ~ 1.3 tokens
        estimated_tokens = len(words) * 1.3

        if estimated_tokens <= self.chunk_size:
            return [chunk]

        # Split by words respecting token budget
        words_per_chunk = int(self.chunk_size / 1.3)
        overlap_words = int(self.overlap / 1.3)

        sub_chunks: list[DocumentChunk] = []
        start = 0

        while start < len(words):
            end = min(start + words_per_chunk, len(words))
            segment = " ".join(words[start:end])

            sub_chunks.append(
                DocumentChunk(
                    content=segment,
                    source_file=chunk.source_file,
                    file_type=chunk.file_type,
                    chunk_type=chunk.chunk_type,
                    metadata=ChunkMetadata(
                        page=chunk.metadata.page,
                        sheet=chunk.metadata.sheet,
                        table_name=chunk.metadata.table_name,
                        headers=chunk.metadata.headers,
                        row_count=chunk.metadata.row_count,
                        schema_element=chunk.metadata.schema_element,
                    ),
                )
            )

            if end >= len(words):
                break
            start = end - overlap_words

        return sub_chunks
