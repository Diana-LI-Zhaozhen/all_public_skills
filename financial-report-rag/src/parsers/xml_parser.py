"""XML parser using xml.etree.ElementTree."""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType

logger = logging.getLogger(__name__)


class XMLParser:
    def parse(self, file_path: str) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        path = Path(file_path)

        try:
            tree = ET.parse(path)
            root = tree.getroot()
            self._extract_elements(root, chunks, path.name, depth=0)
        except Exception as e:
            logger.error("Failed to parse XML %s: %s", path.name, e)

        return chunks

    def _extract_elements(
        self,
        element: ET.Element,
        chunks: list[DocumentChunk],
        filename: str,
        depth: int,
        parent_path: str = "",
    ) -> None:
        # Strip namespace for readability
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        current_path = f"{parent_path}/{tag}" if parent_path else tag

        # Collect text content
        text_parts: list[str] = []
        if element.text and element.text.strip():
            text_parts.append(element.text.strip())
        if element.tail and element.tail.strip():
            text_parts.append(element.tail.strip())

        # Include attributes
        attrs = element.attrib
        attr_text = ", ".join(f"{k}={v}" for k, v in attrs.items()) if attrs else ""

        # Build content for leaf or shallow elements
        children = list(element)
        if not children and (text_parts or attr_text):
            content_parts = [f"Path: {current_path}"]
            if attr_text:
                content_parts.append(f"Attributes: {attr_text}")
            if text_parts:
                content_parts.append(f"Content: {' '.join(text_parts)}")

            content = "\n".join(content_parts)
            chunks.append(
                DocumentChunk(
                    content=f"[Source: {filename}, Element: {current_path}]\n{content}",
                    source_file=filename,
                    file_type=FileType.XML,
                    chunk_type=ChunkType.TEXT,
                    metadata=ChunkMetadata(schema_element=current_path),
                )
            )
        elif depth < 2 and children:
            # For high-level structural elements, create a summary chunk
            summary = f"Element: {current_path}"
            if attr_text:
                summary += f"\nAttributes: {attr_text}"
            child_tags = [
                c.tag.split("}")[-1] if "}" in c.tag else c.tag for c in children
            ]
            summary += f"\nChildren: {', '.join(child_tags)}"
            if text_parts:
                summary += f"\nText: {' '.join(text_parts)}"

            chunks.append(
                DocumentChunk(
                    content=f"[Source: {filename}, Element: {current_path}]\n{summary}",
                    source_file=filename,
                    file_type=FileType.XML,
                    chunk_type=ChunkType.TEXT,
                    metadata=ChunkMetadata(schema_element=current_path),
                )
            )

        # Recurse into children
        for child in children:
            self._extract_elements(child, chunks, filename, depth + 1, current_path)
