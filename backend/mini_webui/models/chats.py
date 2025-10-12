import time
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, ForeignKey, Index

from ..internal.db import Base, JSONField


####################
# Chat DB Schema
####################


class Chat(Base):
    __tablename__ = "chat"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    title = Column(Text, nullable=False)
    
    # Chat messages stored as JSON
    chat = Column(JSONField, nullable=False, default=lambda: [])
    
    # Chat metadata
    meta = Column(JSONField, nullable=True, default=lambda: {})
    
    # Chat status
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False)
    
    # Share functionality
    share_id = Column(String, unique=True, nullable=True)
    
    # Timestamps
    created_at = Column(BigInteger, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))

    # Performance indexes
    __table_args__ = (
        Index("user_id_idx", "user_id"),
        Index("user_id_archived_idx", "user_id", "archived"),
        Index("user_id_pinned_idx", "user_id", "pinned"),
        Index("updated_at_idx", "updated_at"),
    )


####################
# Pydantic Models
####################


class ChatModel(BaseModel):
    """Chat response model"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    chat: list[dict]
    
    meta: Optional[dict] = {}
    archived: bool = False
    pinned: bool = False
    share_id: Optional[str] = None
    
    created_at: int
    updated_at: int


class ChatCreate(BaseModel):
    """Chat creation model"""
    title: str
    chat: Optional[list[dict]] = []
    meta: Optional[dict] = {}


class ChatUpdate(BaseModel):
    """Chat update model"""
    title: Optional[str] = None
    chat: Optional[list[dict]] = None
    meta: Optional[dict] = None
    archived: Optional[bool] = None
    pinned: Optional[bool] = None


class ChatMessage(BaseModel):
    """Individual chat message model"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[int] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = int(time.time())
        super().__init__(**data)


class ChatResponse(BaseModel):
    """Chat response without sensitive data"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    title: str
    archived: bool
    pinned: bool
    share_id: Optional[str] = None
    created_at: int
    updated_at: int