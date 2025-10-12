# mini-webui

mini-webui delivers a streamlined AI chat console for teams that need rapid iteration, reliable integrations, and production-ready guardrails. The application pairs a FastAPI backend with a SvelteKit front end, offering real-time conversations, LangGraph-powered retrieval, secure account management, and an operator-friendly admin console.

---

## Key Capabilities

| Area        | Highlights                                                                                     |
|-------------|------------------------------------------------------------------------------------------------|
| Chat        | Streaming completions, guest mode, transcript persistence, and LangGraph-based RAG             |
| Auth        | JWT login/register, profile editing, secure password hashing (bcrypt), session expiry control  |
| Admin       | Usage dashboard, user CRUD with activation toggle, runtime OpenAI setting overrides            |
| Integrations| OpenAI-compatible proxy endpoint, FAISS vector store ingestion pipeline, SSE endpoints         |
| UX          | Responsive SvelteKit interface, auto-resizing inputs, dark-mode aware styling                  |

---

## Architecture at a Glance

```
mini-webui_src/
├── backend/
│   └── mini_webui/
│       ├── main.py          # FastAPI entrypoint and router registration
│       ├── config.py        # Environment + runtime configuration
│       ├── models/          # SQLAlchemy ORM (users, chats, messages, settings)
│       ├── routers/         # REST & SSE endpoints (auth, chats, admin, openai, rag)
│       ├── rag/             # LangGraph orchestration & FAISS storage helpers
│       └── internal/db.py   # Engine/session helpers and JSON column type
├── src/
│   ├── lib/                 # Frontend API clients, stores, utilities
│   ├── routes/              # SvelteKit pages (app shell, auth, profile, admin)
│   └── app.css              # Tailwind base + custom design tokens
├── scripts/                 # CLI utilities (admin bootstrap, RAG ingest, DB checks)
├── requirements.txt         # Python dependencies (uv compatible)
└── package.json             # Node/Svelte workspace metadata
```

The backend exposes REST + Server-Sent Events; the SvelteKit client consumes the same interface for both guest and authenticated users. Admin tooling is served from `/admin`, with profile management under `/profile`.

---

## Technology Stack

| Layer          | Tools & Frameworks                                                                                         |
|----------------|------------------------------------------------------------------------------------------------------------|
| Language       | Python 3.11+, TypeScript                                                                                   |
| Backend        | FastAPI, SQLAlchemy 2.x, Alembic, Uvicorn                                                                   |
| Frontend       | SvelteKit 2.x, Svelte 4, Tailwind CSS, Vite                                                                 |
| Auth & Security| JWT (python-jose), bcrypt (passlib), CORS middleware                                                        |
| AI Integrations| OpenAI SDK, LangGraph, LangChain, FAISS, tiktoken                                                           |
| Dev Tooling    | `uv`, npm, ESLint, Prettier, svelte-check                                                                   |
| Infrastructure | SQLite (dev) / PostgreSQL-ready, Docker-friendly scripts, Server-Sent Events for streaming                  |

---

## Quick Start

### Prerequisites

- Python 3.11 or later
- Node.js 18 or later
- [`uv`](https://docs.astral.sh/uv/latest/) (preferred) or `pip`
- `npm` or `pnpm`

### Backend

```bash
cd mini-webui_src
uv env
uv pip install -r requirements.txt

cp .env.example .env          # Fill in OPENAI_API_KEY, SECRET_KEY, DATABASE_URL, etc.

uv run python -c "from backend.mini_webui.internal.db import init_db; init_db()"
uv run python -m uvicorn backend.mini_webui.main:app --reload --port 8080
```

### Frontend

```bash
npm install
npm run dev   # http://localhost:5173
```

Set `VITE_API_BASE` in a `.env` file (or shell) if the backend is hosted on a different origin.

---

## Configuration

Create a `.env` file in the project root:

```env
# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Database
DATABASE_URL=sqlite:///./data/webui.db

# Security
SECRET_KEY=replace-me
ACCESS_TOKEN_EXPIRE_MINUTES=30

# RAG
RAG_ENABLED=true
RAG_INDEX_PATH=./data/rag_index
RAG_TOP_K=4
RAG_EMBEDDING_MODEL=text-embedding-3-large
RAG_COMPLETION_MODEL=gpt-4o-mini
RAG_ALLOW_STREAMING=true
```

Admin users can override the OpenAI key/base, app name, and debug flag through the settings panel; overrides are written to the `settings` table.

---

## Retrieval-Augmented Generation

1. Toggle `RAG_ENABLED=true` and ensure the configured models are available to your API key.
2. Ingest documents into the FAISS index:
   ```bash
   uv run python ./scripts/ingest_rag.py ./data/rag_docs --glob "**/*.md"
   ```
3. Enable the RAG switch in the chat UI. Responses stream alongside inline citation cards referencing the retrieved documents.

Endpoints:
- `POST /api/rag/query` – synchronous answer + document payload
- `GET /api/rag/stream` – SSE stream with `documents`, `answer`, `traces`, `[DONE]`

---

## API Summary

- **Auth**: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `PUT /api/auth/me`
- **Chats**: `GET /api/chats`, `POST /api/chats`, `GET/DELETE /api/chats/{id}`, `POST /api/chats/{id}/messages`, `GET /api/chats/{id}/stream`
- **Guest Chat**: `POST /api/chats/guest/chat`, `GET /api/chats/guest/stream`
- **Admin**: `GET /api/admin/whoami`, `GET /api/admin/stats`, full CRUD on `/api/admin/users`, `/api/admin/settings`
- **OpenAI Proxy**: `POST /api/openai/chat`
- **Health**: `/health`, `/api/health`

The FastAPI app can optionally serve the built Svelte client for single-origin deployments.

---

## Development Workflow

| Task                             | Command                                                             |
|----------------------------------|---------------------------------------------------------------------|
| Backend tests / scripts          | `uv run pytest` (add tests as needed), `uv run python …`            |
| Frontend lint/check              | `npm run lint`, `npm run check`                                     |
| Build production bundle          | `npm run build`                                                     |
| Create admin user                | `uv run python scripts/create_admin.py`                             |
| Seed a test admin (dev)          | `uv run python scripts/create_test_admin.py`                        |
| Verify database schema           | `uv run python scripts/verify_database.py`                          |

Code style follows upstream FastAPI and Svelte conventions. Tailwind is used for rapid UI iteration with a thin layer of custom utility classes.

---

## Roadmap

- [x] JWT authentication, guest mode, profile editing
- [x] Chat CRUD with streaming and LangGraph RAG
- [x] Admin dashboard, usage metrics, OpenAI setting overrides
- [x] 2025 UI refresh (responsive layout, glassmorphism, toned depth)
- [ ] WebSocket live updates
- [ ] File attachment support and tool plugins
- [ ] Automated test suites (backend + e2e)
- [ ] Deployment recipes (Docker, Terraform modules)

---

## License

mini-webui is released under the MIT License. See [`LICENSE`](LICENSE) for full terms.

---

## Developer Notes

- Default test admin (if seeded): `admin@example.com` / `admin123`
- Commands assume project root is `mini-webui_src`
  - `uv run python mini-webui_src/scripts/create_test_admin.py`
  - `uv run python mini-webui_src/scripts/create_admin.py`
- Streaming uses SSE; inspect the Network tab for `text/event-stream` and `[DONE]` markers during debugging.

Enjoy building with **mini-webui**!
