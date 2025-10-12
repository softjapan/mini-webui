from datetime import timedelta
import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..constants import AUTH_PREFIX
from ..models.users import UserResponse, User
from ..utils.auth import (
    TokenResponse,
    authenticate_user,
    create_user,
    get_current_user,
    get_current_user_required,
    get_db,
)
from ..utils.security import create_access_token


router = APIRouter(prefix=AUTH_PREFIX, tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    profile_image_url: str | None = None
    bio: str | None = None


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    user = create_user(db, name=data.name, email=data.email, password=data.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token({"sub": user.id}, expires_delta=timedelta(minutes=30))
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
def update_me(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return UserResponse.model_validate(user)

    if "name" in updates and updates["name"] is not None:
        trimmed = updates["name"].strip()
        if not trimmed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")
        updates["name"] = trimmed

    for optional_field in ("profile_image_url", "bio"):
        if optional_field in updates and updates[optional_field] is not None:
            updates[optional_field] = updates[optional_field].strip() or None

    for field, value in updates.items():
        setattr(user, field, value)
    user.updated_at = int(time.time())
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
