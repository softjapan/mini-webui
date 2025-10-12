import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .config import FRONTEND_BUILD_DIR
from .internal.db import init_db
from . import models  # Import models to register them with Base
from .routers.auths import router as auth_router
from .routers.openai_api import router as openai_router
from .routers.chats import router as chats_router
from .routers.admin import router as admin_router
from .routers.rag import router as rag_router

app = FastAPI(
    title="mini-webui",
    description="delivers a streamlined AI chat console for teams that need rapid iteration, reliable integrations, and production-ready guardrails",
    version="0.1.0"
)

# Basic logging configuration (console)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mini_webui")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up: initializing database")
    init_db()
    logger.info("Startup complete")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# API routes will be added here
@app.get("/api/health")
async def api_health():
    return {"status": "ok", "message": "mini-webui API is running"}

# Routers
app.include_router(auth_router)
app.include_router(openai_router)
app.include_router(chats_router)
app.include_router(admin_router)
app.include_router(rag_router)

# Serve static files and SPA
if os.path.exists(FRONTEND_BUILD_DIR):
    # Mount SvelteKit's _app directory for assets
    app_dir = os.path.join(FRONTEND_BUILD_DIR, "_app")
    if os.path.exists(app_dir):
        app.mount("/_app", StaticFiles(directory=app_dir), name="app-assets")
    
    # Serve other static files (favicon, etc.)
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        # Handle root path
        if path == "":
            return FileResponse(os.path.join(FRONTEND_BUILD_DIR, "index.html"))
        
        file_path = os.path.join(FRONTEND_BUILD_DIR, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # For all other paths, serve the SPA
        return FileResponse(os.path.join(FRONTEND_BUILD_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mini_webui.main:app", host="0.0.0.0", port=8080, reload=True)
