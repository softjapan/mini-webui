from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class RagConfig(TypedDict, total=False):
    top_k: int
    language: str
    streaming: bool
    temperature: float
    metadata_filter: Dict[str, Any]
    system_prompt: str


class RagDocument(TypedDict, total=False):
    id: str
    page_content: str
    metadata: Dict[str, Any]
    score: float


class RagState(TypedDict, total=False):
    query: str
    language: str
    documents: List[RagDocument]
    answer: str
    traces: List[Dict[str, Any]]


class RagChunk(TypedDict):
    event: str
    data: Any


class RagResult(TypedDict):
    answer: str
    documents: List[RagDocument]
    traces: List[Dict[str, Any]]
