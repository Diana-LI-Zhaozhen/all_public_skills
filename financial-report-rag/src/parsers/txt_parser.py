"""TXT parser with paragraph splitting."""

import logging
from pathlib import Path

from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType

logger = logging.getLogger(__name__)


class TXTParser:
    def parse(self, file_path: str) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        path = Path(file_path)

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if not content.strip():
                return chunks

            # Split by double newlines (paragraphs)
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

            if not paragraphs:
                paragraphs = [content.strip()]

            for i, para in enumerate(paragraphs):
                chunks.append(
                    DocumentChunk(
                        content=f"[Source: {path.name}, Section: {i + 1}]\n{para}",
                        source_file=path.name,
                        file_type=FileType.TXT,
                        chunk_type=ChunkType.TEXT,
                        metadata=ChunkMetadata(page=i + 1),
                    )
                )

        except Exception as e:
            logger.error("Failed to parse TXT %s: %s", path.name, e)

        return chunks
