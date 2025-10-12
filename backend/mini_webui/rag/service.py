from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Generator, Optional

from fastapi import HTTPException, status

from ..config import (
    RAG_ALLOW_STREAMING,
    RAG_ENABLED,
    RAG_INDEX_PATH,
    RAG_LANGUAGE,
    RAG_TOP_K,
)
from .graph import RagGraphBuilder
from .store import VectorStoreManager
from .types import RagConfig, RagResult

log = logging.getLogger("mini_webui.rag.service")


class RagService:
    """Facade around LangGraph RAG workflow and vector store."""

    def __init__(
        self,
        *,
        index_path: Path | str = RAG_INDEX_PATH,
        default_top_k: int = RAG_TOP_K,
        default_language: str = RAG_LANGUAGE,
    ) -> None:
        if isinstance(index_path, str):
            index_path = Path(index_path)
        self._enabled = RAG_ENABLED
        self.store = VectorStoreManager(index_path)
        self.builder = RagGraphBuilder(
            self.store,
            default_top_k=default_top_k,
            default_language=default_language,
        )
        self.graph = self.builder.build()

    def ensure_enabled(self) -> None:
        if not self._enabled:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RAG is disabled")

    def ingest_path(self, path: Path | str, glob: str = "**/*") -> int:
        """Convenience ingestion helper (can be called from scripts or admin tasks)."""
        self.ensure_enabled()
        return self.store.ingest_directory(Path(path), glob=glob)

    def query(self, question: str, *, config: Optional[RagConfig] = None) -> RagResult:
        self.ensure_enabled()
        state = {
            "query": question,
            "traces": [],
            "config": config or {},
        }
        result = self.graph.invoke(state)
        return {
            "answer": result.get("answer", ""),
            "documents": result.get("documents", []),
            "traces": result.get("traces", []),
        }

    def stream(self, question: str, *, config: Optional[RagConfig] = None) -> Generator[Dict[str, str], None, None]:
        self.ensure_enabled()
        if not RAG_ALLOW_STREAMING:
            # Fallback to single answer event
            result = self.query(question, config=config)
            yield self._make_event("answer", result["answer"])
            yield self._make_event("documents", result["documents"])
            yield self._make_event("traces", result["traces"])
            return
        state = {
            "query": question,
            "traces": [],
            "config": config or {},
        }
        for event in self.graph.stream(state, stream_mode="updates"):
            kind = str(event.get("event"))
            data = event.get("data", {}) or {}
            documents = data.get("documents")
            answer = data.get("answer")
            if documents:
                yield self._make_event("documents", documents)
            if answer:
                yield self._make_event("answer", answer)
            if kind == "graph:end":
                final_state = data.get("state", {})
                if final_state.get("traces"):
                    yield self._make_event("traces", final_state["traces"])
                break

    @staticmethod
    def _make_event(event: str, payload) -> Dict[str, str]:
        return {
            "event": event,
            "data": json.dumps(payload, ensure_ascii=False),
        }


_rag_service: Optional[RagService] = None


def get_rag_service() -> RagService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service
