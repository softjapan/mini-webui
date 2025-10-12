from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..constants import API_PREFIX
from ..utils.openai import chat_completion
from ..config import OPENAI_MODEL, OPENAI_API_BASE
from ..utils.auth import get_current_user, get_db
from sqlalchemy.orm import Session
from ..models.settings import Setting


router = APIRouter(prefix=f"{API_PREFIX}/openai", tags=["openai"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = None
    api_base: Optional[str] = None


class ChatResponse(BaseModel):
    content: str


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = req.model or OPENAI_MODEL

    # Resolve OpenAI settings from DB (if present)
    def get_setting(key: str) -> Optional[str]:
        s = db.query(Setting).filter(Setting.key == key).first()
        return (s.value if s and s.value else None)

    api_key = get_setting("openai_api_key")
    base_url = req.api_base or get_setting("openai_api_base") or OPENAI_API_BASE

    content = chat_completion(
        messages=[m.model_dump() for m in req.messages],
        model=model,
        temperature=req.temperature,
        api_key=api_key,
        base_url=base_url,
    )
    return ChatResponse(content=content)
