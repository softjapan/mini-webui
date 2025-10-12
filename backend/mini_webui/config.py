import os
from pathlib import Path
from dotenv import load_dotenv

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent

# Load environment variables from project .env
load_dotenv(BASE_DIR / ".env")
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_BUILD_DIR = BASE_DIR / "build"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/webui.db")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# App settings
APP_NAME = "mini-webui"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# RAG / LangGraph settings
RAG_ENABLED = os.getenv("RAG_ENABLED", "false").lower() == "true"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-large")
RAG_INDEX_PATH = os.getenv("RAG_INDEX_PATH", str(BASE_DIR / "data" / "rag_index"))
RAG_LANGUAGE = os.getenv("RAG_LANGUAGE", "ja")
RAG_ALLOW_STREAMING = os.getenv("RAG_ALLOW_STREAMING", "true").lower() == "true"
RAG_COMPLETION_MODEL = os.getenv("RAG_COMPLETION_MODEL", OPENAI_MODEL)
RAG_SYSTEM_PROMPT = os.getenv(
    "RAG_SYSTEM_PROMPT",
    (
        "あなたは資料回答専用のアシスタントです。与えられたコンテキスト以外の知識は絶対に使わず、"
        "表データが含まれる場合は『表名』『行番号』『列名: 値』の形式で根拠を引用してください。"
        "回答は必ず日本語で簡潔にまとめ、数値や料金はそのままの表記（例: ¥100,000）で示します。"
        "情報が見つからないときはその旨を率直に伝え、推測はしません。"
    ),
)
