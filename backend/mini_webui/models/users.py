import time
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, Boolean

from ..internal.db import Base, JSONField


####################
# User DB Schema
####################


class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    role = Column(String, default="user")  # user, admin
    profile_image_url = Column(Text, nullable=True)
    
    # Additional user info
    bio = Column(Text, nullable=True)
    settings = Column(JSONField, nullable=True)
    
    # API key for authentication
    api_key = Column(String, nullable=True, unique=True)
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    last_active_at = Column(BigInteger, nullable=True)
    
    # Timestamps
    created_at = Column(BigInteger, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))


####################
# Pydantic Models
####################


class UserSettings(BaseModel):
    """User settings model"""
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")


class UserModel(BaseModel):
    """User response model"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    email: str
    
    role: str = "user"
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    settings: Optional[UserSettings] = None
    
    api_key: Optional[str] = None
    is_active: bool = True
    last_active_at: Optional[int] = None
    
    created_at: int
    updated_at: int


class UserCreate(BaseModel):
    """User creation model"""
    name: str
    email: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    """User update model"""
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    settings: Optional[UserSettings] = None
    is_active: Optional[bool] = None


class UserLogin(BaseModel):
    """User login model"""
    email: str
    password: str


class UserResponse(BaseModel):
    """User response without sensitive data"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    email: str
    role: str
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    created_at: int
    updated_at: int