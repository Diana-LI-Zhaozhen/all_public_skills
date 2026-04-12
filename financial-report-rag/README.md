# Financial Report RAG System

A Retrieval-Augmented Generation (RAG) pipeline that ingests heterogeneous financial documents and answers user queries with citations. Supports tables, precise numbers, and mixed formats.

Revised architecture: no LLM in parsing/indexing/routing/retrieval/reranking. DeepSeek is used only at the final answer generation step.

## Supported File Formats

| Format | Parser | Output |
|--------|--------|--------|
| `.pdf` | pdfplumber + table extraction | Text chunks + DataFrame tables |
| `.htm`, `.html` | BeautifulSoup | Text from `<p>`, `<div>`; tables from `<table>` |
| `.xml` | xml.etree.ElementTree | Recursive text with tag hierarchy metadata |
| `.txt` | Native | Split by paragraphs |
| `.xsd` | xmlschema | Schema element definitions |
| `.xlsx` | pandas + openpyxl | Each sheet as a separate DataFrame |
| `.json` | json module | Flattened nested structures |

## Architecture

```
Input files -> Parsing + normalization -> Indexes (Vector + BM25 + DuckDB)
User query -> Rule router -> Hybrid retrieval or table SQL
-> Cross-Encoder rerank -> Top-5 context + query -> DeepSeek LLM
-> Final answer + citations
```

- **Hybrid Indexes**: Vector (FAISS) + Keyword (BM25) + Structured (DuckDB for tables)
- **Query Router**: Pure rule-based routing (no LLM)
- **Table Queries**: Rule extraction + SQL templates (no NL2SQL LLM)
- **Reranker**: Cross-Encoder for final context quality (not a generative model)
- **LLM**: DeepSeek only at final answer generation

## Installation

```bash
# Clone and enter directory
cd financial-report-rag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` to set:
- Embedding model (`BAAI/bge-large-en-v1.5` default)
- Reranker model (`BAAI/bge-reranker-base` default)
- LLM provider (`openai`, `anthropic`, or `local`)
- Retrieval parameters (top_k, RRF constant)

Set API keys via environment variables:
```bash
export DEEPSEEK_API_KEY="your-key"
```

## Usage

### Ingest Documents

```bash
# Ingest a single file
python main.py ingest path/to/report.pdf --save

# Ingest a directory of files
python main.py ingest ./data/ --save
```

### Query

```bash
# Single query
python main.py query "What were the risk factors in the 2024 annual report?" --load

# Interactive mode
python main.py interactive
```

### View Statistics

```bash
python main.py stats
```

### Python API

```python
from src.pipeline import RAGPipeline

pipeline = RAGPipeline("config.yaml")

# Ingest
pipeline.ingest_directory("./data/")
pipeline.save_indexes()

# Query
result = pipeline.query("What was the revenue in Q4 2024?")
print(result["answer"])
print(result["sources"])

pipeline.close()
```

## Docker

```bash
# Build
docker build -t financial-rag .

# Run interactive
docker run -it -v $(pwd)/data:/app/data -e OPENAI_API_KEY=$OPENAI_API_KEY financial-rag

# Ingest
docker run -v $(pwd)/data:/app/data financial-rag ingest /app/data --save
```

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
financial-report-rag/
├── config.yaml              # Configuration parameters
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container setup
├── src/
│   ├── config.py            # Config loader
│   ├── models.py            # Data models (DocumentChunk, TableRecord)
│   ├── chunker.py           # Text chunking with overlap
│   ├── pipeline.py          # Main orchestration
│   ├── parsers/
│   │   ├── dispatcher.py    # File type routing
│   │   ├── pdf_parser.py    # PDF text + tables
│   │   ├── html_parser.py   # HTML text + tables
│   │   ├── xml_parser.py    # XML elements
│   │   ├── txt_parser.py    # Plain text
│   │   ├── xsd_parser.py    # XML Schema
│   │   ├── xlsx_parser.py   # Excel spreadsheets
│   │   └── json_parser.py   # JSON documents
│   ├── indexing/
│   │   ├── vector_index.py  # FAISS vector index
│   │   ├── keyword_index.py # BM25 keyword index
│   │   ├── table_store.py   # DuckDB table store
│   │   └── metadata_index.py# SQLite metadata
│   ├── retrieval/
│   │   ├── router.py        # Query routing logic
│   │   ├── hybrid_retriever.py # RRF fusion retriever
│   │   └── reranker.py      # Cross-Encoder reranker
│   └── generation/
│       └── llm_wrapper.py   # LLM abstraction layer
└── tests/
    ├── test_parsers.py      # Parser unit tests
    ├── test_indexing.py      # Indexing unit tests
    ├── test_retrieval.py     # Retrieval unit tests
    └── test_chunker.py       # Chunker unit tests
```
