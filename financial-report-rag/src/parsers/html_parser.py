"""HTML parser using BeautifulSoup."""

import logging
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType

logger = logging.getLogger(__name__)


class HTMLParser:
    def parse(self, file_path: str) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        path = Path(file_path)

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            soup = BeautifulSoup(content, "lxml")

            # Remove script and style elements
            for tag in soup(["script", "style"]):
                tag.decompose()

            # Extract text from block-level elements
            text_parts: list[str] = []
            for elem in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "span"]):
                text = elem.get_text(separator=" ", strip=True)
                if text and len(text) > 10:
                    text_parts.append(text)

            if text_parts:
                full_text = "\n".join(text_parts)
                chunks.append(
                    DocumentChunk(
                        content=f"[Source: {path.name}]\n{full_text}",
                        source_file=path.name,
                        file_type=FileType.HTML,
                        chunk_type=ChunkType.TEXT,
                        metadata=ChunkMetadata(),
                    )
                )

            # Extract tables
            tables = soup.find_all("table")
            for t_idx, table in enumerate(tables):
                try:
                    rows = table.find_all("tr")
                    if len(rows) < 2:
                        continue

                    # Get headers
                    header_row = rows[0]
                    headers = [
                        th.get_text(strip=True)
                        for th in header_row.find_all(["th", "td"])
                    ]
                    if not headers:
                        continue

                    # Get data rows
                    data = []
                    for row in rows[1:]:
                        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                        if cells:
                            data.append(cells)

                    if not data:
                        continue

                    df = pd.DataFrame(data, columns=headers[:len(data[0])] if len(headers) >= len(data[0]) else headers + [f"col_{i}" for i in range(len(headers), len(data[0]))])
                    for col in df.columns:
                        cleaned = df[col].astype(str).str.replace(",", "", regex=False)
                        converted = pd.to_numeric(cleaned, errors="coerce")
                        if converted.notna().sum() > 0:
                            df[col] = converted

                    table_name = f"html_table_{t_idx}"
                    table_text = df.to_markdown(index=False)
                    chunks.append(
                        DocumentChunk(
                            content=f"[Source: {path.name}, Table: {table_name}]\n{table_text}",
                            source_file=path.name,
                            file_type=FileType.HTML,
                            chunk_type=ChunkType.TABLE,
                            metadata=ChunkMetadata(
                                table_name=table_name,
                                headers=list(df.columns),
                                row_count=len(data),
                            ),
                            dataframe=df,
                        )
                    )
                except Exception as e:
                    logger.warning("Failed to parse HTML table %d in %s: %s", t_idx, path.name, e)

        except Exception as e:
            logger.error("Failed to parse HTML %s: %s", path.name, e)

        return chunks
