"""XLSX parser using pandas + openpyxl."""

import logging
from pathlib import Path

import pandas as pd

from src.models import ChunkMetadata, ChunkType, DocumentChunk, FileType

logger = logging.getLogger(__name__)


class XLSXParser:
    def parse(self, file_path: str) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        path = Path(file_path)

        try:
            xls = pd.ExcelFile(path, engine="openpyxl")

            for sheet_name in xls.sheet_names:
                try:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    if df.empty:
                        continue

                    # Clean column names
                    df.columns = [str(c).strip() for c in df.columns]

                    # Drop completely empty rows
                    df = df.dropna(how="all").reset_index(drop=True)

                    if df.empty:
                        continue

                    table_text = df.to_markdown(index=False)
                    headers = list(df.columns)

                    chunks.append(
                        DocumentChunk(
                            content=f"[Source: {path.name}, Sheet: {sheet_name}]\n{table_text}",
                            source_file=path.name,
                            file_type=FileType.XLSX,
                            chunk_type=ChunkType.TABLE,
                            metadata=ChunkMetadata(
                                sheet=sheet_name,
                                table_name=f"{path.stem}_{sheet_name}",
                                headers=headers,
                                row_count=len(df),
                            ),
                            dataframe=df,
                        )
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to parse sheet '%s' in %s: %s",
                        sheet_name,
                        path.name,
                        e,
                    )

        except Exception as e:
            logger.error("Failed to parse XLSX %s: %s", path.name, e)

        return chunks
