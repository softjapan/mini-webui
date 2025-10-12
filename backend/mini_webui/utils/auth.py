import uuid
from typing import Annotated, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..internal.db import SessionLocal
from ..models.users import User
from .security import verify_password, get_password_hash, create_access_token, decode_access_token


class GuestUser:
    """Guest user for unauthenticated chat sessions"""
    def __init__(self):
        self.id = "guest"
        self.name = "Guest"
        self.email = "guest@example.com"
        self.role = "guest"
        self.is_active = True
        self.created_at = 0
        self.updated_at = 0


http_bearer = HTTPBearer(auto_error=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, name: str, email: str, password: str) -> User:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        name=name,
        email=email,
        password_hash=get_password_hash(password),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(http_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> Union[User, GuestUser]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return GuestUser()

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        return GuestUser()

    sub = payload.get("sub")
    if not sub:
        return GuestUser()

    user = db.query(User).filter(User.id == sub).first()
    if not user or not getattr(user, "is_active", True):
        return GuestUser()
    return user


def get_current_user_required(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(http_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Dependency that requires authentication (no guest users)"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.query(User).filter(User.id == sub).first()
    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_admin(current_user: Annotated[Union[User, GuestUser], Depends(get_current_user)]) -> User:
    """Dependency that ensures the current user has admin role."""
    if isinstance(current_user, GuestUser):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if getattr(current_user, "role", "user") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privilege required")
    return current_user
