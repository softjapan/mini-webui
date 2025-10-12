# User roles
USER_ROLE_ADMIN = "admin"
USER_ROLE_USER = "user"

# Default models
DEFAULT_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo-preview"
]

# Message types
MESSAGE_TYPE_USER = "user"
MESSAGE_TYPE_ASSISTANT = "assistant"
MESSAGE_TYPE_SYSTEM = "system"

# API endpoints
API_PREFIX = "/api"
AUTH_PREFIX = f"{API_PREFIX}/auth"
CHATS_PREFIX = f"{API_PREFIX}/chats"
ADMIN_PREFIX = f"{API_PREFIX}/admin"
RAG_PREFIX = f"{API_PREFIX}/rag"
