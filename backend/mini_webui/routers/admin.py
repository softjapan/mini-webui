from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..constants import ADMIN_PREFIX
from ..utils.auth import require_admin, get_db
from ..models.users import UserResponse, User, UserUpdate
from ..models.chats import Chat
from ..models.messages import Message
from ..utils.security import get_password_hash
from pydantic import BaseModel, EmailStr
from ..models.settings import Setting, SettingModel


router = APIRouter(prefix=ADMIN_PREFIX, tags=["admin"])


@router.get("/whoami", response_model=UserResponse)
def whoami(admin: User = Depends(require_admin)):
    """Confirm admin identity."""
    return UserResponse.model_validate(admin)


@router.get("/stats")
def stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Basic counts for admin dashboard."""
    return {
        "users": db.query(User).count(),
        "chats": db.query(Chat).count(),
        "messages": db.query(Message).count(),
    }


class UserCreateAdmin(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "user"  # default user; can be set to 'admin'


class UserList(BaseModel):
    items: List[UserResponse]
    total: int


@router.get("/users", response_model=UserList)
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    q: Optional[str] = Query(None, description="Search by name or email"),
    offset: int = 0,
    limit: int = Query(50, ge=1, le=200),
):
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter((User.name.ilike(like)) | (User.email.ilike(like)))
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return UserList(items=[UserResponse.model_validate(u) for u in users], total=total)


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user_admin(payload: UserCreateAdmin, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    # Check duplication
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        id=str(__import__("uuid").uuid4()),
        name=payload.name,
        email=str(payload.email),
        password_hash=get_password_hash(payload.password),
        role=payload.role or "user",
        is_active=True,
        created_at=__import__("time").time().__int__(),
        updated_at=__import__("time").time().__int__(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Email uniqueness check if email is changed
    if payload.email and payload.email != user.email:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already exists")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    user.updated_at = __import__("time").time().__int__()
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/activate", response_model=UserResponse)
def activate_user(user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    user.updated_at = __import__("time").time().__int__()
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    user.updated_at = __import__("time").time().__int__()
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: str, hard: bool = False, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not hard:
        user.is_active = False
        user.updated_at = __import__("time").time().__int__()
        db.commit()
        return {"status": "deactivated", "id": user_id}

    # Hard delete: remove messages -> chats -> user
    chat_ids = [c.id for c in db.query(Chat.id).filter(Chat.user_id == user_id).all()]
    if chat_ids:
        db.query(Message).filter(Message.chat_id.in_(chat_ids)).delete(synchronize_session=False)
        db.query(Chat).filter(Chat.id.in_(chat_ids)).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"status": "deleted", "id": user_id}


# ============ Settings management (admin) ============

class AdminSettings(BaseModel):
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    app_name: Optional[str] = None
    debug: Optional[bool] = None


def _get_setting(db: Session, key: str) -> Optional[Setting]:
    return db.query(Setting).filter(Setting.key == key).first()


def _set_setting(db: Session, key: str, value: Optional[str], description: Optional[str] = None, category: Optional[str] = None) -> Setting:
    import time as _t
    s = _get_setting(db, key)
    now = int(_t.time())
    if s is None:
        s = Setting(
            id=str(__import__("uuid").uuid4()),
            key=key,
            value=value or "",
            description=description,
            category=category,
            created_at=now,
            updated_at=now,
        )
        db.add(s)
    else:
        s.value = value or ""
        if description is not None:
            s.description = description
        if category is not None:
            s.category = category
        s.updated_at = now
    db.commit()
    db.refresh(s)
    return s


@router.get("/settings", response_model=AdminSettings)
def get_settings(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Return selected system settings for admin view."""
    def val(k: str) -> Optional[str]:
        s = _get_setting(db, k)
        return s.value if s else None

    def val_bool(k: str) -> Optional[bool]:
        s = _get_setting(db, k)
        if not s or s.value is None:
            return None
        return s.value.lower() in ("true", "1", "yes", "on")

    return AdminSettings(
        openai_api_key=val("openai_api_key"),
        openai_api_base=val("openai_api_base"),
        app_name=val("app_name"),
        debug=val_bool("debug"),
    )


@router.put("/settings", response_model=AdminSettings)
def update_settings(payload: AdminSettings, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Upsert selected system settings. Returns the updated values."""
    if payload.openai_api_key is not None:
        _set_setting(db, "openai_api_key", payload.openai_api_key, description="OpenAI API Key", category="openai")
    if payload.openai_api_base is not None:
        _set_setting(db, "openai_api_base", payload.openai_api_base, description="OpenAI API Base URL", category="openai")
    if payload.app_name is not None:
        _set_setting(db, "app_name", payload.app_name, description="Application Name", category="app")
    if payload.debug is not None:
        _set_setting(db, "debug", "true" if payload.debug else "false", description="Debug Mode", category="app")

    return get_settings(db, admin)


@router.get("/settings/all", response_model=List[SettingModel])
def list_all_settings(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """List all raw settings (for troubleshooting)."""
    rows = db.query(Setting).order_by(Setting.key.asc()).all()
    return [SettingModel.model_validate(r) for r in rows]
