from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain.schema import Document
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from ..config import (
    OPENAI_API_BASE,
    OPENAI_API_KEY,
    RAG_ALLOW_STREAMING,
    RAG_COMPLETION_MODEL,
    RAG_LANGUAGE,
    RAG_SYSTEM_PROMPT,
    RAG_TOP_K,
)
from .store import VectorStoreManager
from .types import RagConfig, RagDocument, RagResult, RagState

log = logging.getLogger("mini_webui.rag.graph")


class RagGraphBuilder:
    """Builds a LangGraph state machine for retrieval-augmented responses."""

    def __init__(
        self,
        store: VectorStoreManager,
        *,
        default_language: str = RAG_LANGUAGE,
        default_top_k: int = RAG_TOP_K,
        system_prompt: str = RAG_SYSTEM_PROMPT,
    ) -> None:
        self.store = store
        self.default_language = default_language
        self.default_top_k = default_top_k
        self.system_prompt = system_prompt
        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE,
            model=RAG_COMPLETION_MODEL,
            streaming=RAG_ALLOW_STREAMING,
            temperature=0.3,
        )

    def build(self):
        graph = StateGraph(RagState)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("generate", self._generate)

        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", END)
        return graph.compile()

    # ====== graph nodes ======
    def _resolve_top_k(self, state: RagState) -> int:
        cfg = self._get_config(state)
        top_k = int(cfg.get("top_k", self.default_top_k))
        return max(1, top_k)

    def _get_language(self, state: RagState) -> str:
        cfg = self._get_config(state)
        return cfg.get("language", state.get("language") or self.default_language)

    def _get_config(self, state: RagState) -> RagConfig:
        return state.get("config", {})  # type: ignore[return-value]

    def _retrieve(self, state: RagState) -> RagState:
        query = state.get("query")
        if not query:
            raise ValueError("RAG graph requires a query in state")
        top_k = self._resolve_top_k(state)
        config = self._get_config(state)
        metadata_filter = config.get("metadata_filter") if isinstance(config, dict) else None
        log.debug("Retrieving documents k=%s query=%s filter=%s", top_k, query[:80], metadata_filter)
        results = self.store.similarity_search(query, top_k, metadata_filter=metadata_filter)
        documents: List[RagDocument] = []
        for doc, score in results:
            documents.append(self._convert_document(doc, score))
        traces = list(state.get("traces", []))
        traces.append({
            "step": "retrieve",
            "top_k": top_k,
            "documents": documents,
            "filter": metadata_filter,
        })
        new_state: RagState = {
            **state,
            "documents": documents,
            "language": self._get_language(state),
            "traces": traces,
        }
        return new_state

    def _generate(self, state: RagState) -> RagState:
        query = state["query"]
        documents = state.get("documents", [])
        context = self._build_context(documents)
        config = self._get_config(state)
        temperature = float(config.get("temperature", 0.3))
        system_prompt = config.get("system_prompt", self.system_prompt)
        language = state.get("language", self.default_language)

        prompt = self._build_prompt(query, context, language)
        log.debug("Generating answer using model=%s lang=%s", RAG_COMPLETION_MODEL, language)
        answer_message = self.llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
            temperature=temperature,
        )
        answer = answer_message.content if answer_message else ""
        traces = list(state.get("traces", []))
        traces.append({
            "step": "generate",
            "model": RAG_COMPLETION_MODEL,
            "temperature": temperature,
        })
        new_state: RagState = {
            **state,
            "answer": answer,
            "traces": traces,
        }
        return new_state

    # ===== helpers =====
    @staticmethod
    def _convert_document(doc: Document, score: float) -> RagDocument:
        metadata: Dict[str, Any] = dict(doc.metadata or {})
        identifier = metadata.get("id") or metadata.get("source") or metadata.get("path") or "doc"
        return {
            "id": str(identifier),
            "page_content": doc.page_content,
            "metadata": metadata,
            "score": float(score),
        }

    @staticmethod
    def _build_context(documents: List[RagDocument]) -> str:
        if not documents:
            return "(関連するコンテキストは見つかりませんでした。)"
        formatted = []
        for idx, doc in enumerate(documents, start=1):
            source = doc.get("metadata", {}).get("source") or doc["id"]
            formatted.append(f"【文書{idx}】(source: {source})\n{doc['page_content']}")
        return "\n\n".join(formatted)

    @staticmethod
    def _build_prompt(query: str, context: str, language: str) -> str:
        return (
            "以下のコンテキストを参考に、質問に対して日本語で正確かつ簡潔に回答してください。"
            "\n\n" +
            f"質問: {query}\n" +
            "\nコンテキスト:\n" + context +
            "\n\n回答する際の条件:\n"
            "- 回答は日本語で書くこと\n"
            "- コンテキストに基づいて事実のみを述べること\n"
            "- 不明な場合はその旨を伝えること"
        )


def run_graph(store: VectorStoreManager, query: str, config: RagConfig | None = None) -> RagResult:
    builder = RagGraphBuilder(store)
    app = builder.build()
    state: RagState = {"query": query, "config": config or {}, "traces": []}
    result = app.invoke(state)
    return {
        "answer": result.get("answer", ""),
        "documents": result.get("documents", []),
        "traces": result.get("traces", []),
    }
