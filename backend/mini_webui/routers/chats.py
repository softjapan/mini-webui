import time
import uuid
import json
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..constants import CHATS_PREFIX
from ..models.chats import Chat, ChatCreate, ChatModel, ChatResponse
from ..models.messages import Message, MessageModel, MessageCreate
from ..utils.auth import get_current_user, get_db, GuestUser
from ..utils.openai import chat_completion, stream_chat_completion
from ..config import OPENAI_MODEL, OPENAI_API_BASE, RAG_ALLOW_STREAMING
from ..rag import get_rag_service
from ..models.settings import Setting
from ..internal.db import SessionLocal


router = APIRouter(prefix=CHATS_PREFIX, tags=["chats"])
log = logging.getLogger("mini_webui.chats")


class CreateChatRequest(ChatCreate):
    pass


class SendMessageRequest(BaseModel):
    content: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    api_base: Optional[str] = None
    use_rag: bool = False
    rag_top_k: Optional[int] = None
    rag_temperature: Optional[float] = None


class GuestChatRequest(BaseModel):
    content: str
    messages: List[dict] = []  # Previous conversation history
    model: Optional[str] = None
    temperature: Optional[float] = None
    api_base: Optional[str] = None
    use_rag: bool = False
    rag_top_k: Optional[int] = None
    rag_temperature: Optional[float] = None


class GuestChatResponse(BaseModel):
    response: str
    messages: List[dict]  # Updated conversation history
    data: Optional[dict] = None


def ensure_owner_or_admin(chat: Chat, current_user: Any):
    # Allow owners; admins can bypass for moderation/assistance
    if chat.user_id == getattr(current_user, 'id', None):
        return
    if getattr(current_user, 'role', 'user') == 'admin':
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def is_guest_user(user: Any) -> bool:
    """Check if the user is a guest user"""
    return isinstance(user, GuestUser)


@router.get("", response_model=List[ChatResponse])
def list_chats(db: Session = Depends(get_db), user: Any = Depends(get_current_user)):
    log.info("List chats: user=%s role=%s", getattr(user, 'id', '?'), getattr(user, 'role', '?'))
    
    # Guest users don't have saved chats
    if is_guest_user(user):
        return []
    
    query = db.query(Chat)
    # Admins can view all chats; regular users only their own
    if getattr(user, 'role', 'user') != 'admin':
        query = query.filter(Chat.user_id == user.id)
    chats = query.order_by(Chat.updated_at.desc()).all()
    return [ChatResponse.model_validate(c) for c in chats]


@router.post("", response_model=ChatModel, status_code=201)
def create_chat(payload: CreateChatRequest, db: Session = Depends(get_db), user: Any = Depends(get_current_user)):
    now = int(time.time())
    log.info("Create chat: user=%s title=%s", getattr(user, 'id', '?'), payload.title)
    
    # Guest users can't create persistent chats
    if is_guest_user(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guest users cannot create persistent chats")
    
    chat = Chat(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=payload.title,
        chat=payload.chat or [],
        meta=payload.meta or {},
        archived=False,
        pinned=False,
        created_at=now,
        updated_at=now,
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return ChatModel.model_validate(chat)


@router.get("/{chat_id}", response_model=ChatModel)
def get_chat(chat_id: str, db: Session = Depends(get_db), user: Any = Depends(get_current_user)):
    log.info("Get chat: user=%s chat_id=%s", getattr(user, 'id', '?'), chat_id)
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    ensure_owner_or_admin(chat, user)
    return ChatModel.model_validate(chat)


@router.delete("/{chat_id}")
def delete_chat(chat_id: str, db: Session = Depends(get_db), user: Any = Depends(get_current_user)):
    log.info("Delete chat: user=%s chat_id=%s", getattr(user, 'id', '?'), chat_id)
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    ensure_owner_or_admin(chat, user)

    # Delete related messages first
    db.query(Message).filter(Message.chat_id == chat_id).delete()
    db.delete(chat)
    db.commit()
    return {"status": "deleted", "id": chat_id}


@router.post("/{chat_id}/messages")
def send_message(
    chat_id: str,
    req: SendMessageRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    log.info(
        "Send message: user=%s chat_id=%s len=%d rag=%s",
        getattr(user, 'id', '?'),
        chat_id,
        len(req.content or ""),
        req.use_rag,
    )
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    ensure_owner_or_admin(chat, user)

    ts = int(time.time())

    # Persist user message
    user_data: Optional[dict[str, Any]] = None
    rag_config_payload: Optional[Dict[str, Any]] = None
    if req.use_rag:
        rag_config_payload = {}
        if req.rag_top_k is not None:
            rag_config_payload["top_k"] = max(1, int(req.rag_top_k))
        if req.rag_temperature is not None:
            rag_config_payload["temperature"] = float(req.rag_temperature)
        user_data = {"mode": "rag"}
        if rag_config_payload:
            user_data["config"] = rag_config_payload

    user_msg = Message(
        id=str(uuid.uuid4()),
        chat_id=chat_id,
        role="user",
        content=req.content,
        data=user_data,
        created_at=ts,
        updated_at=ts,
    )
    db.add(user_msg)

    # Update chat JSON transcript
    transcript = list(chat.chat or [])
    transcript_entry: dict[str, Any] = {"role": "user", "content": req.content, "timestamp": ts}
    if user_data:
        transcript_entry["data"] = user_data
    transcript.append(transcript_entry)

    # Build messages for OpenAI call (include history)
    messages_for_api = [
        {"role": m.get("role"), "content": m.get("content")} for m in transcript
    ]

    # Resolve OpenAI config (DB overrides)
    def get_setting(key: str) -> Optional[str]:
        s = db.query(Setting).filter(Setting.key == key).first()
        return (s.value if s and s.value else None)

    model = req.model or OPENAI_MODEL
    api_key = get_setting("openai_api_key")
    base_url = req.api_base or get_setting("openai_api_base") or OPENAI_API_BASE
    assistant_content: str
    assistant_data: Optional[dict[str, Any]] = None

    if req.use_rag:
        rag_service = get_rag_service()
        log.info("Calling RAG service for chat %s", chat_id)
        rag_result = rag_service.query(req.content, config=rag_config_payload or None)
        assistant_content = rag_result.get("answer", "")
        assistant_data = {
            "mode": "rag",
            "documents": rag_result.get("documents", []),
            "traces": rag_result.get("traces", []),
        }
        if rag_config_payload:
            assistant_data["config"] = rag_config_payload
    else:
        log.info("Calling OpenAI (non-stream) model=%s", model)
        assistant_content = chat_completion(
            messages=messages_for_api,
            model=model,
            temperature=req.temperature,
            api_key=api_key,
            base_url=base_url,
        )

    ts2 = int(time.time())
    # Persist assistant message
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        chat_id=chat_id,
        role="assistant",
        content=assistant_content,
        data=assistant_data,
        created_at=ts2,
        updated_at=ts2,
    )
    db.add(assistant_msg)

    # Update chat record
    assistant_entry: dict[str, Any] = {
        "role": "assistant",
        "content": assistant_content,
        "timestamp": ts2,
    }
    if assistant_data:
        assistant_entry["data"] = assistant_data
    transcript.append(assistant_entry)
    chat.chat = transcript
    chat.updated_at = ts2

    db.commit()

    return {
        "chat_id": chat_id,
        "message": {
            "role": "assistant",
            "content": assistant_content,
            "created_at": ts2,
            "data": assistant_data,
        },
    }


# ======== Guest Chat Endpoints (must be declared BEFORE /{chat_id}/stream to avoid route conflicts) ========

@router.post("/guest/chat", response_model=GuestChatResponse)
def guest_chat(
    req: GuestChatRequest,
    db: Session = Depends(get_db),
):
    """Guest chat endpoint - no persistence, memory-only conversation"""
    log.info("Guest chat: content_len=%d messages_count=%d", len(req.content or ""), len(req.messages or []))

    # Build messages for OpenAI call (include history + new user message)
    ts = int(time.time())
    messages_for_api = list(req.messages or [])
    messages_for_api.append({"role": "user", "content": req.content})

    # Resolve OpenAI config (DB overrides)
    def get_setting(key: str) -> Optional[str]:
        s = db.query(Setting).filter(Setting.key == key).first()
        return (s.value if s and s.value else None)

    model = req.model or OPENAI_MODEL
    api_key = get_setting("openai_api_key")
    base_url = req.api_base or get_setting("openai_api_base") or OPENAI_API_BASE
    assistant_content: str
    assistant_data: Optional[dict[str, Any]] = None

    if req.use_rag:
        rag_service = get_rag_service()
        log.info("Calling RAG service for guest chat")
        rag_config: Dict[str, Any] = {}
        if req.rag_top_k is not None:
            rag_config["top_k"] = max(1, int(req.rag_top_k))
        if req.rag_temperature is not None:
            rag_config["temperature"] = float(req.rag_temperature)
        rag_result = rag_service.query(req.content, config=rag_config)
        assistant_content = rag_result.get("answer", "")
        assistant_data = {
            "mode": "rag",
            "documents": rag_result.get("documents", []),
            "traces": rag_result.get("traces", []),
        }
        if rag_config:
            assistant_data["config"] = rag_config
    else:
        log.info("Calling OpenAI (non-stream) model=%s", model)
        assistant_content = chat_completion(
            messages=messages_for_api,
            model=model,
            temperature=req.temperature,
            api_key=api_key,
            base_url=base_url,
        )

    updated_messages = list(req.messages or [])
    updated_messages.append({"role": "user", "content": req.content, "timestamp": ts})
    updated_messages.append({
        "role": "assistant",
        "content": assistant_content,
        "timestamp": int(time.time()),
        "data": assistant_data,
    })

    return GuestChatResponse(response=assistant_content, messages=updated_messages, data=assistant_data)


@router.get("/guest/stream")
@router.get("/guest-stream")
def guest_chat_stream(
    content: str = Query(..., description="User message content"),
    messages: str = Query("[]", description="Previous conversation history as JSON string"),
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    api_base: Optional[str] = None,
    use_rag: bool = Query(False, description="Use LangGraph RAG pipeline"),
    rag_top_k: Optional[int] = Query(None, ge=1, le=20),
    rag_temperature: Optional[float] = Query(None, ge=0.0, le=2.0),
    db: Session = Depends(get_db),
):
    """Guest chat streaming endpoint - no persistence, memory-only conversation"""
    log.info("Guest chat stream: content_len=%d", len(content or ""))

    if use_rag and not RAG_ALLOW_STREAMING:
        raise HTTPException(status_code=400, detail="RAG streaming is not enabled")

    try:
        prev_messages = json.loads(messages) if messages else []
    except json.JSONDecodeError:
        prev_messages = []

    messages_for_api = list(prev_messages)
    messages_for_api.append({"role": "user", "content": content})

    if use_rag:
        raise HTTPException(status_code=400, detail="Streaming with RAG is not supported yet")

    used_model = model or OPENAI_MODEL

    def get_setting(key: str) -> Optional[str]:
        s = db.query(Setting).filter(Setting.key == key).first()
        return (s.value if s and s.value else None)

    api_key = get_setting("openai_api_key")
    base_url_final = api_base or get_setting("openai_api_base") or OPENAI_API_BASE

    def sse_gen():
        assistant_text_parts: list[str] = []
        try:
            for chunk in stream_chat_completion(
                messages=messages_for_api,
                model=used_model,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url_final,
            ):
                assistant_text_parts.append(chunk)
                for line in chunk.splitlines() or [""]:
                    log.debug("SSE chunk line len=%d", len(line))
                    yield f"data: {line}\n\n"
        except Exception:
            log.warning("Streaming failed, falling back to non-streaming", exc_info=True)
            try:
                full = chat_completion(
                    messages=messages_for_api,
                    model=used_model,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url_final,
                )
                assistant_text_parts.append(full)
                for line in full.splitlines() or [""]:
                    yield f"data: {line}\n\n"
            except Exception as e:
                log.error("Non-streaming fallback also failed: %s", e, exc_info=True)
                yield f"data: Error: {str(e)}\n\n"
        finally:
            full_text = "".join(assistant_text_parts)
            ts = int(time.time())
            updated_messages = list(prev_messages)
            updated_messages.append({"role": "user", "content": content, "timestamp": ts})
            updated_messages.append({"role": "assistant", "content": full_text, "timestamp": int(time.time())})
            yield f"data: {json.dumps({'type': 'messages', 'data': updated_messages})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("/{chat_id}/stream")
def stream_message(
    chat_id: str,
    content: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    api_base: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
    use_rag: bool = Query(False, description="Use LangGraph RAG pipeline"),
    rag_top_k: Optional[int] = Query(None, ge=1, le=20),
    rag_temperature: Optional[float] = Query(None, ge=0.0, le=2.0),
):
    """SSE stream of assistant response. Persists both user and assistant messages on completion.

    Query params:
    - content: user message content to send
    - model, temperature, api_base: optional overrides
    """
    log.info("Stream start: user=%s chat_id=%s len=%d model=%s", getattr(user, 'id', '?'), chat_id, len(content or ""), model or OPENAI_MODEL)
    if use_rag and not RAG_ALLOW_STREAMING:
        raise HTTPException(status_code=400, detail="RAG streaming is not enabled")

    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    ensure_owner_or_admin(chat, user)

    # Prepare transcript and persist user message immediately
    ts = int(time.time())
    user_data: Optional[dict[str, Any]] = None
    rag_stream_config: Optional[Dict[str, Any]] = None
    if use_rag:
        rag_stream_config = {}
        if rag_top_k is not None:
            rag_stream_config["top_k"] = int(rag_top_k)
        if rag_temperature is not None:
            rag_stream_config["temperature"] = float(rag_temperature)
        user_data = {"mode": "rag"}
        if rag_stream_config:
            user_data["config"] = rag_stream_config

    user_msg = Message(
        id=str(uuid.uuid4()),
        chat_id=chat_id,
        role="user",
        content=content,
        data=user_data,
        created_at=ts,
        updated_at=ts,
    )
    db.add(user_msg)
    transcript = list(chat.chat or [])
    user_entry: dict[str, Any] = {"role": "user", "content": content, "timestamp": ts}
    if user_data:
        user_entry["data"] = user_data
    transcript.append(user_entry)
    chat.chat = transcript
    chat.updated_at = ts
    db.commit()
    log.info("Persisted user message and updated transcript (len=%d)", len(transcript))

    # Build messages for OpenAI
    messages_for_api = [
        {"role": m.get("role"), "content": m.get("content")} for m in transcript
    ]

    if use_rag:
        raise HTTPException(status_code=400, detail="Streaming with RAG is not supported yet")

    used_model = model or OPENAI_MODEL

    def get_setting(key: str) -> Optional[str]:
        s = db.query(Setting).filter(Setting.key == key).first()
        return (s.value if s and s.value else None)

    api_key = get_setting("openai_api_key")
    base_url_final = api_base or get_setting("openai_api_base") or OPENAI_API_BASE

    def sse_gen():
        assistant_text_parts: list[str] = []
        try:
            for chunk in stream_chat_completion(
                messages=messages_for_api,
                model=used_model,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url_final,
            ):
                assistant_text_parts.append(chunk)
                # Follow SSE spec: each line must be prefixed by 'data: '
                for line in chunk.splitlines() or [""]:
                    log.debug("SSE chunk line len=%d", len(line))
                    yield f"data: {line}\n\n"
        except Exception:
            # Fallback to non-streaming if streaming fails
            log.warning("Streaming failed, falling back to non-streaming", exc_info=True)
            try:
                full = chat_completion(
                    messages=messages_for_api,
                    model=used_model,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url_final,
                )
                assistant_text_parts.append(full)
                for line in full.splitlines() or [""]:
                    log.debug("SSE fallback line len=%d", len(line))
                    yield f"data: {line}\n\n"
            except Exception as e:
                # Send error as SSE data for visibility
                log.error("Non-streaming fallback also failed: %s", e, exc_info=True)
                yield f"data: Error: {str(e)}\n\n"
        finally:
            # Persist assistant message at the end (even if fallback)
            full_text = "".join(assistant_text_parts)
            ts2 = int(time.time())
            try:
                with SessionLocal() as persist_session:
                    chat_row = persist_session.query(Chat).filter(Chat.id == chat_id).first()
                    if not chat_row:
                        log.warning("Chat %s missing when persisting assistant stream", chat_id)
                    else:
                        transcript2 = list(chat_row.chat or [])
                        transcript_entry_assistant: dict[str, Any] = {
                            "role": "assistant",
                            "content": full_text,
                            "timestamp": ts2,
                        }
                        transcript2.append(transcript_entry_assistant)
                        chat_row.chat = transcript2
                        chat_row.updated_at = ts2

                        assistant_msg = Message(
                            id=str(uuid.uuid4()),
                            chat_id=chat_id,
                            role="assistant",
                            content=full_text,
                            created_at=ts2,
                            updated_at=ts2,
                        )
                        persist_session.add(assistant_msg)
                        persist_session.commit()
                        log.info("Persisted assistant message (chars=%d). Sending [DONE]", len(full_text))
            except Exception:
                log.error("Failed to persist assistant message for chat %s", chat_id, exc_info=True)
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # for proxies like nginx
        },
    )


# ============ Guest Chat Endpoints ============

@router.post("/guest/chat", response_model=GuestChatResponse)
def guest_chat(
    req: GuestChatRequest,
    db: Session = Depends(get_db),
):
    """Guest chat endpoint - no persistence, memory-only conversation"""
    log.info("Guest chat: content_len=%d messages_count=%d", len(req.content or ""), len(req.messages or []))
    
    # Create a guest user for this request
    from ..utils.auth import GuestUser
    user = GuestUser()
    
    ts = int(time.time())
    
    # Build messages for OpenAI call (include history + new user message)
    messages_for_api = list(req.messages or [])
    messages_for_api.append({"role": "user", "content": req.content})
    
    # Resolve OpenAI config (DB overrides)
    def get_setting(key: str) -> Optional[str]:
        s = db.query(Setting).filter(Setting.key == key).first()
        return (s.value if s and s.value else None)
    
    model = req.model or OPENAI_MODEL
    api_key = get_setting("openai_api_key")
    base_url = req.api_base or get_setting("openai_api_base") or OPENAI_API_BASE
    assistant_content: str
    assistant_data: Optional[dict[str, Any]] = None
    
    if req.use_rag:
        rag_service = get_rag_service()
        log.info("Calling RAG service for guest chat")
        rag_config = {}
        if req.rag_top_k is not None:
            rag_config["top_k"] = max(1, int(req.rag_top_k))
        if req.rag_temperature is not None:
            rag_config["temperature"] = float(req.rag_temperature)
        
        rag_result = rag_service.query(req.content, config=rag_config)
        assistant_content = rag_result.get("answer", "")
        assistant_data = {
            "mode": "rag",
            "documents": rag_result.get("documents", []),
            "traces": rag_result.get("traces", []),
        }
        if rag_config:
            assistant_data["config"] = rag_config
    else:
        log.info("Calling OpenAI (non-stream) model=%s", model)
        assistant_content = chat_completion(
            messages=messages_for_api,
            model=model,
            temperature=req.temperature,
            api_key=api_key,
            base_url=base_url,
        )
    
    # Update conversation history
    updated_messages = list(req.messages or [])
    updated_messages.append({"role": "user", "content": req.content, "timestamp": ts})
    updated_messages.append({
        "role": "assistant", 
        "content": assistant_content, 
        "timestamp": int(time.time()),
        "data": assistant_data
    })
    
    return GuestChatResponse(
        response=assistant_content,
        messages=updated_messages,
        data=assistant_data
    )


@router.get("/guest/stream")
@router.get("/guest-stream")
def guest_chat_stream(
    content: str = Query(..., description="User message content"),
    messages: str = Query("[]", description="Previous conversation history as JSON string"),
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    api_base: Optional[str] = None,
    use_rag: bool = Query(False, description="Use LangGraph RAG pipeline"),
    rag_top_k: Optional[int] = Query(None, ge=1, le=20),
    rag_temperature: Optional[float] = Query(None, ge=0.0, le=2.0),
    db: Session = Depends(get_db),
):
    """Guest chat streaming endpoint - no persistence, memory-only conversation"""
    log.info("Guest chat stream: content_len=%d", len(content or ""))
    
    # Create a guest user for this request
    from ..utils.auth import GuestUser
    user = GuestUser()
    
    if use_rag and not RAG_ALLOW_STREAMING:
        raise HTTPException(status_code=400, detail="RAG streaming is not enabled")
    
    # Parse previous messages
    try:
        prev_messages = json.loads(messages) if messages else []
    except json.JSONDecodeError:
        prev_messages = []
    
    # Build messages for OpenAI
    messages_for_api = list(prev_messages)
    messages_for_api.append({"role": "user", "content": content})
    
    if use_rag:
        raise HTTPException(status_code=400, detail="Streaming with RAG is not supported yet")
    
    used_model = model or OPENAI_MODEL
    
    def get_setting(key: str) -> Optional[str]:
        s = db.query(Setting).filter(Setting.key == key).first()
        return (s.value if s and s.value else None)
    
    api_key = get_setting("openai_api_key")
    base_url_final = api_base or get_setting("openai_api_base") or OPENAI_API_BASE
    
    def sse_gen():
        assistant_text_parts: list[str] = []
        try:
            for chunk in stream_chat_completion(
                messages=messages_for_api,
                model=used_model,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url_final,
            ):
                assistant_text_parts.append(chunk)
                # Follow SSE spec: each line must be prefixed by 'data: '
                for line in chunk.splitlines() or [""]:
                    log.debug("SSE chunk line len=%d", len(line))
                    yield f"data: {line}\n\n"
        except Exception:
            # Fallback to non-streaming if streaming fails
            log.warning("Streaming failed, falling back to non-streaming", exc_info=True)
            try:
                full = chat_completion(
                    messages=messages_for_api,
                    model=used_model,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url_final,
                )
                assistant_text_parts.append(full)
                for line in full.splitlines() or [""]:
                    log.debug("SSE fallback line len=%d", len(line))
                    yield f"data: {line}\n\n"
            except Exception as e:
                # Send error as SSE data for visibility
                log.error("Non-streaming fallback also failed: %s", e, exc_info=True)
                yield f"data: Error: {str(e)}\n\n"
        finally:
            # Send updated conversation history as final event
            full_text = "".join(assistant_text_parts)
            ts = int(time.time())
            updated_messages = list(prev_messages)
            updated_messages.append({"role": "user", "content": content, "timestamp": ts})
            updated_messages.append({"role": "assistant", "content": full_text, "timestamp": int(time.time())})
            
            # Send updated messages as JSON
            yield f"data: {json.dumps({'type': 'messages', 'data': updated_messages})}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        sse_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
