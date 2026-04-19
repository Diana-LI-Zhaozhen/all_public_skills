from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(r"C:/Users/zhaozhen/Desktop/financial-report-rag/financial-report-rag")
OUT_DIR = Path(r"C:/Users/zhaozhen/Desktop/financial-report-rag/indexes-smoke")
INPUT_FILE = OUT_DIR / "baba_20250331_20F.html"

sys.path.insert(0, str(ROOT))

from src.parsers.dispatcher import FileDispatcher  # noqa: E402


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    dispatcher = FileDispatcher()
    chunks = dispatcher.parse_file(str(INPUT_FILE))

    # Save all parsed chunks in JSONL.
    chunks_path = OUT_DIR / "parsed_chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            payload = {
                "id": c.id,
                "source_file": c.source_file,
                "file_type": c.file_type.value,
                "chunk_type": c.chunk_type.value,
                "table_name": c.metadata.table_name,
                "headers": c.metadata.headers,
                "row_count": c.metadata.row_count,
                "content": c.content,
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    table_chunks = [c for c in chunks if c.chunk_type.value == "table"]

    # Save extracted table previews as markdown files.
    table_files = []
    for idx, c in enumerate(table_chunks):
        name = c.metadata.table_name or f"table_{idx}"
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
        out_file = OUT_DIR / f"table_{idx:03d}_{safe_name}.md"
        out_file.write_text(c.content, encoding="utf-8")
        table_files.append(out_file.name)

    summary = {
        "input_file": str(INPUT_FILE),
        "total_chunks": len(chunks),
        "text_chunks": sum(1 for c in chunks if c.chunk_type.value == "text"),
        "table_chunks": len(table_chunks),
        "table_preview_files": table_files,
        "outputs": [
            "parsed_chunks.jsonl",
            "parse_summary.json",
            "parse_summary.txt",
            *table_files,
        ],
    }

    (OUT_DIR / "parse_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "parse_summary.txt").write_text(
        "\n".join([
            f"input_file={summary['input_file']}",
            f"total_chunks={summary['total_chunks']}",
            f"text_chunks={summary['text_chunks']}",
            f"table_chunks={summary['table_chunks']}",
            f"table_preview_files={len(table_files)}",
        ]),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
