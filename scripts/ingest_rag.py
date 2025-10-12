"""Utility to ingest documents into the RAG vector store."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def _ensure_path() -> None:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_path()

from backend.mini_webui.rag import get_rag_service

log = logging.getLogger("ingest_rag")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest documents into the RAG index")
    parser.add_argument("path", type=Path, help="Directory containing documents (.txt/.md/.json)")
    parser.add_argument("--glob", default="**/*", help="Glob pattern for files (default: **/*)")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    args = parse_args()
    service = get_rag_service()
    count = service.ingest_path(args.path, glob=args.glob)
    log.info("Ingested %s chunks from %s", count, args.path)


if __name__ == "__main__":
    main()
