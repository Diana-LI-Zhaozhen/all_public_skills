"""Unit tests for the text chunker."""

import pytest

from src.chunker import TextChunker
from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType


class TestTextChunker:
    def test_small_chunk_no_split(self):
        chunker = TextChunker(chunk_size=512, overlap=50)
        chunk = DocumentChunk(
            content="Short text content.",
            source_file="test.txt",
            file_type=FileType.TXT,
            chunk_type=ChunkType.TEXT,
        )
        result = chunker.chunk_documents([chunk])
        assert len(result) == 1
        assert result[0].content == "Short text content."

    def test_large_chunk_split(self):
        chunker = TextChunker(chunk_size=50, overlap=10)
        long_text = " ".join(["word"] * 200)
        chunk = DocumentChunk(
            content=long_text,
            source_file="test.txt",
            file_type=FileType.TXT,
            chunk_type=ChunkType.TEXT,
        )
        result = chunker.chunk_documents([chunk])
        assert len(result) > 1

    def test_table_not_split(self):
        chunker = TextChunker(chunk_size=50, overlap=10)
        long_text = " ".join(["data"] * 200)
        chunk = DocumentChunk(
            content=long_text,
            source_file="test.xlsx",
            file_type=FileType.XLSX,
            chunk_type=ChunkType.TABLE,
        )
        result = chunker.chunk_documents([chunk])
        assert len(result) == 1  # Tables should not be split
