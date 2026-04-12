"""XSD parser using xmlschema for schema extraction."""

import logging
from pathlib import Path

from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType

logger = logging.getLogger(__name__)


class XSDParser:
    def parse(self, file_path: str) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        path = Path(file_path)

        try:
            import xmlschema

            schema = xmlschema.XMLSchema(str(path))

            # Extract type definitions
            for type_name, type_obj in schema.types.items():
                if isinstance(type_name, str) and not type_name.startswith("{"):
                    content_parts = [f"Type: {type_name}"]
                    if hasattr(type_obj, "content") and type_obj.content:
                        content_parts.append(f"Content model: {type(type_obj.content).__name__}")
                    chunks.append(
                        DocumentChunk(
                            content=f"[Source: {path.name}, Schema Type: {type_name}]\n" + "\n".join(content_parts),
                            source_file=path.name,
                            file_type=FileType.XSD,
                            chunk_type=ChunkType.SCHEMA,
                            metadata=ChunkMetadata(schema_element=type_name),
                        )
                    )

            # Extract element definitions
            for elem_name, elem_obj in schema.elements.items():
                content_parts = [
                    f"Element: {elem_name}",
                    f"Type: {elem_obj.type.name if hasattr(elem_obj.type, 'name') else str(elem_obj.type)}",
                ]
                if hasattr(elem_obj, "min_occurs"):
                    content_parts.append(f"minOccurs: {elem_obj.min_occurs}")
                if hasattr(elem_obj, "max_occurs"):
                    content_parts.append(f"maxOccurs: {elem_obj.max_occurs}")

                # Extract child elements if complex type
                if hasattr(elem_obj.type, "content") and elem_obj.type.content:
                    try:
                        child_elems = []
                        for child in elem_obj.type.content.iter_elements():
                            child_info = f"  - {child.name}: {child.type.name if hasattr(child.type, 'name') else 'complex'}"
                            if hasattr(child, "min_occurs"):
                                child_info += f" (min={child.min_occurs}, max={child.max_occurs})"
                            child_elems.append(child_info)
                        if child_elems:
                            content_parts.append("Child elements:\n" + "\n".join(child_elems))
                    except Exception:
                        pass

                chunks.append(
                    DocumentChunk(
                        content=f"[Source: {path.name}, Schema Element: {elem_name}]\n" + "\n".join(content_parts),
                        source_file=path.name,
                        file_type=FileType.XSD,
                        chunk_type=ChunkType.SCHEMA,
                        metadata=ChunkMetadata(schema_element=elem_name),
                    )
                )

        except ImportError:
            logger.warning("xmlschema not installed, falling back to XML parsing for %s", path.name)
            from src.parsers.xml_parser import XMLParser
            return XMLParser().parse(file_path)
        except Exception as e:
            logger.error("Failed to parse XSD %s: %s", path.name, e)

        return chunks
