"""JSON parser with nested structure flattening."""

import json
import logging
from pathlib import Path

from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType

logger = logging.getLogger(__name__)


class JSONParser:
    def parse(self, file_path: str) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        path = Path(file_path)

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            flat = self._flatten(data)

            if not flat:
                chunks.append(
                    DocumentChunk(
                        content=f"[Source: {path.name}]\n{json.dumps(data, indent=2, default=str)[:5000]}",
                        source_file=path.name,
                        file_type=FileType.JSON,
                        chunk_type=ChunkType.TEXT,
                        metadata=ChunkMetadata(),
                    )
                )
            else:
                # Group flattened keys into reasonable chunks
                lines = [f"{k}: {v}" for k, v in flat.items()]
                chunk_size = 50  # lines per chunk
                for i in range(0, len(lines), chunk_size):
                    batch = lines[i : i + chunk_size]
                    content = "\n".join(batch)
                    chunks.append(
                        DocumentChunk(
                            content=f"[Source: {path.name}, Keys: {i}-{i + len(batch)}]\n{content}",
                            source_file=path.name,
                            file_type=FileType.JSON,
                            chunk_type=ChunkType.TEXT,
                            metadata=ChunkMetadata(),
                        )
                    )

        except Exception as e:
            logger.error("Failed to parse JSON %s: %s", path.name, e)

        return chunks

    def _flatten(self, data, parent_key: str = "", sep: str = ".") -> dict:
        items: dict[str, str] = {}
        if isinstance(data, dict):
            for k, v in data.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                items.update(self._flatten(v, new_key, sep))
        elif isinstance(data, list):
            for i, v in enumerate(data):
                new_key = f"{parent_key}[{i}]"
                items.update(self._flatten(v, new_key, sep))
        else:
            items[parent_key] = str(data)
        return items
