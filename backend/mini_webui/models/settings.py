import time
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text

from ..internal.db import Base


####################
# Settings DB Schema
####################


class Setting(Base):
    __tablename__ = "setting"

    id = Column(String, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(BigInteger, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))


####################
# Pydantic Models
####################


class SettingModel(BaseModel):
    """Setting response model"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    
    created_at: int
    updated_at: int


class SettingCreate(BaseModel):
    """Setting creation model"""
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class SettingUpdate(BaseModel):
    """Setting update model"""
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class SettingsResponse(BaseModel):
    """Settings response model"""
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    app_name: Optional[str] = None
    debug: Optional[bool] = None