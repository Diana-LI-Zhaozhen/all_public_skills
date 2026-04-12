"""PDF parser using pdfplumber for text and camelot for tables."""

import logging
from pathlib import Path

import pandas as pd
import pdfplumber

from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType

logger = logging.getLogger(__name__)


class PDFParser:
    def parse(self, file_path: str) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        path = Path(file_path)

        try:
            with pdfplumber.open(path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text
                    text = page.extract_text()
                    if text and text.strip():
                        chunks.append(
                            DocumentChunk(
                                content=f"[Source: {path.name}, Page: {page_num}]\n{text}",
                                source_file=path.name,
                                file_type=FileType.PDF,
                                chunk_type=ChunkType.TEXT,
                                metadata=ChunkMetadata(page=page_num),
                            )
                        )

                    # Extract tables
                    tables = page.extract_tables()
                    for t_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue
                        try:
                            headers = [
                                str(h).strip() if h else f"col_{i}"
                                for i, h in enumerate(table[0])
                            ]
                            rows = table[1:]
                            df = pd.DataFrame(rows, columns=headers)
                            # Convert numeric columns
                            for col in df.columns:
                                converted = pd.to_numeric(df[col], errors="coerce")
                                if converted.notna().sum() > 0:
                                    df[col] = converted
                            table_text = df.to_markdown(index=False)
                            table_name = f"table_p{page_num}_{t_idx}"
                            chunks.append(
                                DocumentChunk(
                                    content=f"[Source: {path.name}, Page: {page_num}, Table: {table_name}]\n{table_text}",
                                    source_file=path.name,
                                    file_type=FileType.PDF,
                                    chunk_type=ChunkType.TABLE,
                                    metadata=ChunkMetadata(
                                        page=page_num,
                                        table_name=table_name,
                                        headers=headers,
                                        row_count=len(rows),
                                    ),
                                    dataframe=df,
                                )
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to parse table %d on page %d of %s: %s",
                                t_idx,
                                page_num,
                                path.name,
                                e,
                            )
        except Exception as e:
            logger.error("Failed to parse PDF %s: %s", path.name, e)

        return chunks
