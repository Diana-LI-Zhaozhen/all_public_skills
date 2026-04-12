"""Data models for the Financial Report RAG system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd


class FileType(str, Enum):
    PDF = "pdf"
    HTML = "html"
    XML = "xml"
    TXT = "txt"
    XSD = "xsd"
    XLSX = "xlsx"
    JSON = "json"


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    SCHEMA = "schema"
    CODE = "code"


@dataclass
class ChunkMetadata:
    page: Optional[int] = None
    sheet: Optional[str] = None
    table_name: Optional[str] = None
    headers: list[str] = field(default_factory=list)
    row_count: int = 0
    schema_element: Optional[str] = None


@dataclass
class DocumentChunk:
    content: str
    source_file: str
    file_type: FileType
    chunk_type: ChunkType
    metadata: ChunkMetadata = field(default_factory=ChunkMetadata)
    dataframe: Optional[pd.DataFrame] = None
    embedding: Optional[list[float]] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class TableRecord:
    id: str
    source_file: str
    sheet_name: Optional[str]
    table_data: str  # JSON-serialized DataFrame
    numerical_columns: list[str] = field(default_factory=list)
    min_max_values: dict = field(default_factory=dict)
