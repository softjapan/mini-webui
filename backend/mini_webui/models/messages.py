import time
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, ForeignKey, Index

from ..internal.db import Base, JSONField


####################
# Message DB Schema
####################


class Message(Base):
    __tablename__ = "message"

    id = Column(String, primary_key=True)
    chat_id = Column(String, ForeignKey("chat.id"), nullable=False)
    
    # Message content
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    
    # Additional message data
    data = Column(JSONField, nullable=True)
    meta = Column(JSONField, nullable=True)
    
    # Timestamps
    created_at = Column(BigInteger, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))

    # Performance indexes
    __table_args__ = (
        Index("chat_id_idx", "chat_id"),
        Index("chat_id_created_at_idx", "chat_id", "created_at"),
    )


####################
# Pydantic Models
####################


class MessageModel(BaseModel):
    """Message response model"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    role: str
    content: str
    
    data: Optional[dict] = None
    meta: Optional[dict] = None
    
    created_at: int
    updated_at: int


class MessageCreate(BaseModel):
    """Message creation model"""
    role: str
    content: str
    data: Optional[dict] = None
    meta: Optional[dict] = None


class MessageUpdate(BaseModel):
    """Message update model"""
    content: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None


class MessageResponse(BaseModel):
    """Message response model"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    role: str
    content: str
    created_at: int
    updated_at: int