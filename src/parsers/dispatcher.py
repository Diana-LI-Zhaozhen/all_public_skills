"""File dispatcher that routes files to the appropriate parser."""

import logging
from pathlib import Path

from src.models import DocumentChunk
from src.parsers.html_parser import HTMLParser
from src.parsers.json_parser import JSONParser
from src.parsers.pdf_parser import PDFParser
from src.parsers.txt_parser import TXTParser
from src.parsers.xsd_parser import XSDParser
from src.parsers.xlsx_parser import XLSXParser
from src.parsers.xml_parser import XMLParser

logger = logging.getLogger(__name__)

EXTENSION_MAP = {
    ".pdf": PDFParser,
    ".htm": HTMLParser,
    ".html": HTMLParser,
    ".xml": XMLParser,
    ".txt": TXTParser,
    ".xsd": XSDParser,
    ".xlsx": XLSXParser,
    ".json": JSONParser,
}


class FileDispatcher:
    def __init__(self):
        self._parsers = {ext: cls() for ext, cls in EXTENSION_MAP.items()}

    @property
    def supported_extensions(self) -> list[str]:
        return list(EXTENSION_MAP.keys())

    def parse_file(self, file_path: str) -> list[DocumentChunk]:
        path = Path(file_path)
        ext = path.suffix.lower()

        parser = self._parsers.get(ext)
        if parser is None:
            logger.warning("Unsupported file type '%s' for file %s", ext, path.name)
            return []

        logger.info("Parsing %s with %s", path.name, type(parser).__name__)
        try:
            return parser.parse(str(path))
        except Exception as e:
            logger.error("Parser failed for %s: %s", path.name, e)
            return []

    def parse_directory(self, dir_path: str) -> list[DocumentChunk]:
        path = Path(dir_path)
        all_chunks: list[DocumentChunk] = []

        if not path.is_dir():
            logger.error("Directory not found: %s", dir_path)
            return all_chunks

        files = sorted(
            f
            for f in path.rglob("*")
            if f.is_file() and f.suffix.lower() in EXTENSION_MAP
        )

        logger.info("Found %d supported files in %s", len(files), dir_path)
        for file in files:
            chunks = self.parse_file(str(file))
            all_chunks.extend(chunks)
            logger.info("  %s -> %d chunks", file.name, len(chunks))

        return all_chunks
