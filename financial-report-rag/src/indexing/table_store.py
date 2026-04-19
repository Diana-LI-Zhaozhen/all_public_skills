"""Table store using DuckDB for structured queries on DataFrames."""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from src.models import ChunkType, DocumentChunk

logger = logging.getLogger(__name__)


class TableStore:
    def __init__(self, db_path: str = "./indexes/tables.duckdb"):
        self.db_path = db_path
        self._conn = None

    def _get_conn(self):
        if self._conn is None:
            import duckdb
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(self.db_path)
            self._init_schema()
        return self._conn

    def _init_schema(self):
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tables (
                id TEXT PRIMARY KEY,
                source TEXT,
                sheet TEXT,
                data JSON,
                numeric_cols TEXT[],
                headers TEXT[],
                row_count INTEGER
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tables_source ON tables(source)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS table_metrics (
                table_id TEXT,
                source TEXT,
                sheet TEXT,
                metric TEXT,
                year INTEGER,
                numeric_value DOUBLE,
                row_data JSON
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_metric ON table_metrics(metric)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_year ON table_metrics(year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_source ON table_metrics(source)")

    def insert_chunks(self, chunks: list[DocumentChunk]) -> int:
        conn = self._get_conn()
        count = 0
        for chunk in chunks:
            if chunk.chunk_type != ChunkType.TABLE or chunk.dataframe is None:
                continue

            df = chunk.dataframe
            numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
            headers = list(df.columns)

            # Serialize the DataFrame to JSON
            table_data = df.to_json(orient="records", default_handler=str)

            conn.execute(
                """
                INSERT OR REPLACE INTO tables (id, source, sheet, data, numeric_cols, headers, row_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    chunk.id,
                    chunk.source_file,
                    chunk.metadata.sheet,
                    table_data,
                    numeric_cols,
                    headers,
                    chunk.metadata.row_count,
                ],
            )

            self._insert_metric_rows(
                table_id=chunk.id,
                source=chunk.source_file,
                sheet=chunk.metadata.sheet,
                df=df,
            )
            count += 1

        logger.info("Inserted %d tables into table store", count)
        return count

    def query_sql(self, sql: str) -> Optional[pd.DataFrame]:
        conn = self._get_conn()
        try:
            result = conn.execute(sql).fetchdf()
            return result
        except Exception as e:
            logger.error("SQL query failed: %s - %s", sql, e)
            return None

    def search_tables(self, source: str = None, sheet: str = None) -> list[dict]:
        conn = self._get_conn()
        conditions = []
        params = []

        if source:
            conditions.append("source = ?")
            params.append(source)
        if sheet:
            conditions.append("sheet = ?")
            params.append(sheet)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT id, source, sheet, data, numeric_cols, headers, row_count FROM tables{where}"

        try:
            result = conn.execute(query, params).fetchall()
            columns = ["id", "source", "sheet", "data", "numeric_cols", "headers", "row_count"]
            return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error("Table search failed: %s", e)
            return []

    def _insert_metric_rows(
        self,
        table_id: str,
        source: str,
        sheet: str | None,
        df: pd.DataFrame,
    ) -> None:
        conn = self._get_conn()

        conn.execute("DELETE FROM table_metrics WHERE table_id = ?", [table_id])

        year_col = self._detect_year_column(df)
        metric_cols = [c for c in df.columns if self._is_metric_column(c)]
        if not metric_cols:
            metric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

        for _, row in df.iterrows():
            row_year = None
            if year_col and pd.notna(row.get(year_col)):
                try:
                    row_year = int(float(row.get(year_col)))
                except Exception:
                    row_year = None

            for col in metric_cols:
                raw_val = row.get(col)
                parsed = self._to_number(raw_val)
                if parsed is None:
                    continue

                metric = str(col).strip().lower().replace(" ", "_")
                row_json = json.dumps({k: self._to_jsonable(v) for k, v in row.to_dict().items()})
                conn.execute(
                    """
                    INSERT INTO table_metrics (table_id, source, sheet, metric, year, numeric_value, row_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [table_id, source, sheet, metric, row_year, parsed, row_json],
                )

    def query_metric_rows(
        self,
        metrics: list[str],
        years: list[int],
        operator: str | None,
        value: float | None,
        limit: int = 20,
    ) -> list[dict]:
        conn = self._get_conn()
        conditions: list[str] = []
        params: list = []

        if metrics:
            placeholders = ",".join(["?"] * len(metrics))
            conditions.append(f"metric IN ({placeholders})")
            params.extend(metrics)

        if years:
            placeholders = ",".join(["?"] * len(years))
            conditions.append(f"year IN ({placeholders})")
            params.extend(years)

        if operator and value is not None and operator in (">", "<", ">=", "<=", "="):
            conditions.append(f"numeric_value {operator} ?")
            params.append(value)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = (
            "SELECT table_id, source, sheet, metric, year, numeric_value, row_data "
            f"FROM table_metrics{where_clause} "
            "ORDER BY source, sheet, year NULLS LAST LIMIT ?"
        )
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        columns = ["table_id", "source", "sheet", "metric", "year", "numeric_value", "row_data"]
        return [dict(zip(columns, row)) for row in rows]

    def _detect_year_column(self, df: pd.DataFrame) -> str | None:
        for col in df.columns:
            col_norm = str(col).strip().lower()
            if col_norm in ("year", "fiscal_year", "fy"):
                return col
        return None

    def _is_metric_column(self, col_name: str) -> bool:
        col = str(col_name).strip().lower().replace(" ", "_")
        known = {
            "revenue",
            "profit",
            "net_income",
            "eps",
            "operating_margin",
            "gross_margin",
            "operating_income",
        }
        return col in known

    def _to_number(self, value) -> float | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().replace(",", "")
        text = text.replace("$", "")
        if not text:
            return None

        unit_factor = 1.0
        if text.lower().endswith("b"):
            unit_factor = 1_000_000_000
            text = text[:-1]
        elif text.lower().endswith("m"):
            unit_factor = 1_000_000
            text = text[:-1]

        if text.lower().endswith("billion"):
            unit_factor = 1_000_000_000
            text = text[:-7].strip()
        elif text.lower().endswith("million"):
            unit_factor = 1_000_000
            text = text[:-7].strip()

        try:
            return float(text) * unit_factor
        except Exception:
            return None

    def _to_jsonable(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float, str, bool)):
            return value
        if pd.isna(value):
            return None
        return str(value)

    def get_all_tables_as_dataframes(self) -> list[tuple[str, str, pd.DataFrame]]:
        tables = self.search_tables()
        results = []
        for t in tables:
            try:
                df = pd.read_json(t["data"])
                results.append((t["source"], t["sheet"] or "", df))
            except Exception as e:
                logger.warning("Failed to deserialize table %s: %s", t["id"], e)
        return results

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
