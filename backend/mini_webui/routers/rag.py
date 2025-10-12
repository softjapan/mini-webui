from __future__ import annotations

import json
import logging
from typing import Any, Dict, Generator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import RAG_ALLOW_STREAMING
from ..constants import API_PREFIX
from ..rag import get_rag_service
from ..rag.types import RagConfig, RagResult
from ..utils.auth import get_current_user

log = logging.getLogger("mini_webui.rag.router")

router = APIRouter(prefix=f"{API_PREFIX}/rag", tags=["rag"])


class RagQueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = None
    temperature: Optional[float] = None
    metadata_filter: Optional[Dict[str, Any]] = None
    streaming: Optional[bool] = False


class RagQueryResponse(BaseModel):
    answer: str
    documents: list[Dict[str, Any]]
    traces: list[Dict[str, Any]]


@router.post("/query", response_model=RagQueryResponse)
def rag_query(req: RagQueryRequest, user=Depends(get_current_user)):
    service = get_rag_service()
    if req.streaming:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /api/rag/stream for streaming responses",
        )
    config = _build_config(req.top_k, req.temperature, req.metadata_filter)
    result = service.query(req.question, config=config)
    return RagQueryResponse(**result)


def _build_config(top_k: Optional[int], temperature: Optional[float], metadata_filter: Optional[Dict[str, Any]]) -> RagConfig:
    config: RagConfig = {}
    if top_k is not None:
        config["top_k"] = max(1, min(int(top_k), 20))
    if temperature is not None:
        config["temperature"] = float(temperature)
    if metadata_filter:
        config["metadata_filter"] = metadata_filter
    return config


@router.get("/stream")
def rag_stream(
    question: str = Query(..., description="User question"),
    top_k: Optional[int] = Query(None, ge=1, le=20),
    temperature: Optional[float] = Query(None, ge=0.0, le=1.5),
    user=Depends(get_current_user),
):
    if not RAG_ALLOW_STREAMING:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RAG streaming disabled")
    service = get_rag_service()
    config = _build_config(top_k, temperature, metadata_filter=None)
    generator = service.stream(question, config=config)
    return StreamingResponse(
        _sse(generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(events: Generator[Dict[str, str], None, None]) -> Generator[str, None, None]:
    try:
        for event in events:
            name = event.get("event", "message")
            payload = event.get("data", "")
            yield f"event: {name}\n"
            for line in str(payload).splitlines() or [""]:
                yield f"data: {line}\n"
            yield "\n"
    finally:
        yield "event: done\n"
        yield "data: [DONE]\n\n"
