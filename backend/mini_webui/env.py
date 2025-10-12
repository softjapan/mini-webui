import os
from typing import Optional

def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default value."""
    return os.getenv(key, default)

def get_bool_env(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")

def get_int_env(key: str, default: int = 0) -> int:
    """Get integer environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

# Environment variables
ENV = get_env_var("ENV", "development")
DEBUG = get_bool_env("DEBUG", ENV == "development")
PORT = get_int_env("PORT", 8080)
HOST = get_env_var("HOST", "0.0.0.0")