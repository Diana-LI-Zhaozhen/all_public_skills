"""Unit tests for file parsers."""

import json
import os
import tempfile

import pandas as pd
import pytest

from src.models import ChunkType, FileType
from src.parsers.dispatcher import FileDispatcher
from src.parsers.html_parser import HTMLParser
from src.parsers.json_parser import JSONParser
from src.parsers.txt_parser import TXTParser
from src.parsers.xlsx_parser import XLSXParser
from src.parsers.xml_parser import XMLParser


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestTXTParser:
    def test_parse_paragraphs(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("First paragraph about revenue.\n\nSecond paragraph about expenses.\n\nThird paragraph about profit.")

        parser = TXTParser()
        chunks = parser.parse(path)

        assert len(chunks) == 3
        assert chunks[0].file_type == FileType.TXT
        assert chunks[0].chunk_type == ChunkType.TEXT
        assert "revenue" in chunks[0].content
        assert "expenses" in chunks[1].content

    def test_parse_empty_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "empty.txt")
        with open(path, "w") as f:
            f.write("")

        parser = TXTParser()
        chunks = parser.parse(path)
        assert len(chunks) == 0


class TestHTMLParser:
    def test_parse_text_and_tables(self, tmp_dir):
        html = """
        <html>
        <body>
            <p>Annual revenue was $10 billion in 2024.</p>
            <table>
                <tr><th>Year</th><th>Revenue</th><th>Profit</th></tr>
                <tr><td>2023</td><td>9500000000</td><td>1200000000</td></tr>
                <tr><td>2024</td><td>10000000000</td><td>1500000000</td></tr>
            </table>
        </body>
        </html>
        """
        path = os.path.join(tmp_dir, "test.html")
        with open(path, "w") as f:
            f.write(html)

        parser = HTMLParser()
        chunks = parser.parse(path)

        text_chunks = [c for c in chunks if c.chunk_type == ChunkType.TEXT]
        table_chunks = [c for c in chunks if c.chunk_type == ChunkType.TABLE]

        assert len(text_chunks) >= 1
        assert len(table_chunks) == 1
        assert table_chunks[0].dataframe is not None
        assert "Revenue" in table_chunks[0].metadata.headers


class TestXMLParser:
    def test_parse_elements(self, tmp_dir):
        xml = """<?xml version="1.0"?>
        <financials>
            <company name="TestCorp">
                <revenue year="2024">10000000000</revenue>
                <profit year="2024">1500000000</profit>
            </company>
        </financials>
        """
        path = os.path.join(tmp_dir, "test.xml")
        with open(path, "w") as f:
            f.write(xml)

        parser = XMLParser()
        chunks = parser.parse(path)

        assert len(chunks) >= 2
        assert any("revenue" in c.content.lower() for c in chunks)


class TestJSONParser:
    def test_parse_nested(self, tmp_dir):
        data = {
            "company": "TestCorp",
            "financials": {
                "revenue": 10000000000,
                "profit": 1500000000,
                "year": 2024,
            },
            "divisions": [
                {"name": "Tech", "revenue": 5000000000},
                {"name": "Services", "revenue": 5000000000},
            ],
        }
        path = os.path.join(tmp_dir, "test.json")
        with open(path, "w") as f:
            json.dump(data, f)

        parser = JSONParser()
        chunks = parser.parse(path)

        assert len(chunks) >= 1
        assert chunks[0].file_type == FileType.JSON


class TestXLSXParser:
    def test_parse_sheets(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.xlsx")
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df1 = pd.DataFrame({"Year": [2023, 2024], "Revenue": [9.5e9, 10e9]})
            df1.to_excel(writer, sheet_name="Q4", index=False)
            df2 = pd.DataFrame({"Item": ["A", "B"], "Value": [100, 200]})
            df2.to_excel(writer, sheet_name="Summary", index=False)

        parser = XLSXParser()
        chunks = parser.parse(path)

        assert len(chunks) == 2
        assert all(c.chunk_type == ChunkType.TABLE for c in chunks)
        assert chunks[0].metadata.sheet == "Q4"
        assert chunks[0].dataframe is not None
        assert "Revenue" in chunks[0].metadata.headers


class TestFileDispatcher:
    def test_supported_extensions(self):
        dispatcher = FileDispatcher()
        exts = dispatcher.supported_extensions
        assert ".pdf" in exts
        assert ".html" in exts
        assert ".xml" in exts
        assert ".txt" in exts
        assert ".xsd" in exts
        assert ".xlsx" in exts
        assert ".json" in exts

    def test_unsupported_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.xyz")
        with open(path, "w") as f:
            f.write("test")

        dispatcher = FileDispatcher()
        chunks = dispatcher.parse_file(path)
        assert len(chunks) == 0

    def test_parse_directory(self, tmp_dir):
        # Create a txt file
        with open(os.path.join(tmp_dir, "a.txt"), "w") as f:
            f.write("Some text content here.")

        # Create a json file
        with open(os.path.join(tmp_dir, "b.json"), "w") as f:
            json.dump({"key": "value"}, f)

        dispatcher = FileDispatcher()
        chunks = dispatcher.parse_directory(tmp_dir)
        assert len(chunks) >= 2
