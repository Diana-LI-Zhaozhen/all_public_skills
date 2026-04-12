"""CLI entry point for the Financial Report RAG system."""

import argparse
import logging
import sys

from src.pipeline import RAGPipeline


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(description="Financial Report RAG System")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest command
    ingest_parser = sub.add_parser("ingest", help="Ingest documents")
    ingest_parser.add_argument("path", help="File or directory to ingest")
    ingest_parser.add_argument("--save", action="store_true", help="Save indexes after ingestion")

    # Query command
    query_parser = sub.add_parser("query", help="Query the RAG system")
    query_parser.add_argument("question", help="Question to ask")
    query_parser.add_argument("--load", action="store_true", help="Load saved indexes first")

    # Stats command
    sub.add_parser("stats", help="Show index statistics")

    # Interactive mode
    sub.add_parser("interactive", help="Interactive query mode")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging("INFO")

    pipeline = RAGPipeline(config_path=args.config)

    try:
        if args.command == "ingest":
            from pathlib import Path
            path = Path(args.path)
            if path.is_dir():
                count = pipeline.ingest_directory(str(path))
            else:
                count = pipeline.ingest_file(str(path))
            print(f"Ingested {count} chunks")
            if args.save:
                pipeline.save_indexes()
                print("Indexes saved")

        elif args.command == "query":
            if args.load:
                pipeline.load_indexes()
            result = pipeline.query(args.question)
            print(f"\nAnswer: {result['answer']}")
            print(f"\nSources ({result['num_chunks']} chunks):")
            for src in result["sources"]:
                print(f"  - {src}")

        elif args.command == "stats":
            pipeline.load_indexes()
            stats = pipeline.get_stats()
            print("Index Statistics:")
            for k, v in stats.items():
                print(f"  {k}: {v}")

        elif args.command == "interactive":
            pipeline.load_indexes()
            print("Financial Report RAG - Interactive Mode")
            print("Type 'quit' to exit\n")
            while True:
                try:
                    question = input("Question: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if question.lower() in ("quit", "exit", "q"):
                    break
                if not question:
                    continue
                result = pipeline.query(question)
                print(f"\nAnswer: {result['answer']}")
                print(f"\nSources:")
                for src in result["sources"]:
                    print(f"  - {src}")
                print()
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
