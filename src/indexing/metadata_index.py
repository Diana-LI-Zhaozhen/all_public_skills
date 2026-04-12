"""Metadata index using SQLite for fast chunk metadata filtering."""

import json
import logging
import os
import sqlite3
from pathlib import Path

from src.models import DocumentChunk

logger = logging.getLogger(__name__)


class MetadataIndex:
    def __init__(self, db_path: str = "./indexes/metadata.db"):
        self.db_path = db_path
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        return self._conn

    def _init_schema(self):
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunk_metadata (
                id TEXT PRIMARY KEY,
                source_file TEXT NOT NULL,
                file_type TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                page INTEGER,
                sheet TEXT,
                table_name TEXT,
                headers TEXT,
                row_count INTEGER DEFAULT 0,
                schema_element TEXT,
                content_preview TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_meta_source ON chunk_metadata(source_file)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_meta_type ON chunk_metadata(file_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_meta_chunk_type ON chunk_metadata(chunk_type)")
        conn.commit()

    def insert_chunks(self, chunks: list[DocumentChunk]) -> int:
        conn = self._get_conn()
        count = 0
        for chunk in chunks:
            conn.execute(
                """
                INSERT OR REPLACE INTO chunk_metadata
                (id, source_file, file_type, chunk_type, page, sheet, table_name,
                 headers, row_count, schema_element, content_preview)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.id,
                    chunk.source_file,
                    chunk.file_type.value,
                    chunk.chunk_type.value,
                    chunk.metadata.page,
                    chunk.metadata.sheet,
                    chunk.metadata.table_name,
                    json.dumps(chunk.metadata.headers) if chunk.metadata.headers else None,
                    chunk.metadata.row_count,
                    chunk.metadata.schema_element,
                    chunk.content[:200],
                ),
            )
            count += 1
        conn.commit()
        logger.info("Inserted %d chunk metadata records", count)
        return count

    def filter_by_source(self, source_file: str) -> list[str]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id FROM chunk_metadata WHERE source_file = ?", (source_file,)
        ).fetchall()
        return [row["id"] for row in rows]

    def filter_by_type(self, file_type: str = None, chunk_type: str = None) -> list[str]:
        conn = self._get_conn()
        conditions = []
        params = []
        if file_type:
            conditions.append("file_type = ?")
            params.append(file_type)
        if chunk_type:
            conditions.append("chunk_type = ?")
            params.append(chunk_type)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(f"SELECT id FROM chunk_metadata{where}", params).fetchall()
        return [row["id"] for row in rows]

    def get_stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as cnt FROM chunk_metadata").fetchone()["cnt"]
        by_type = conn.execute(
            "SELECT file_type, COUNT(*) as cnt FROM chunk_metadata GROUP BY file_type"
        ).fetchall()
        by_chunk = conn.execute(
            "SELECT chunk_type, COUNT(*) as cnt FROM chunk_metadata GROUP BY chunk_type"
        ).fetchall()
        return {
            "total_chunks": total,
            "by_file_type": {row["file_type"]: row["cnt"] for row in by_type},
            "by_chunk_type": {row["chunk_type"]: row["cnt"] for row in by_chunk},
        }

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
