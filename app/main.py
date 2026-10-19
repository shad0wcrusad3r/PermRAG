"""FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, query
from app.rag.store import ensure_collections
from app.rag.embed import get_embed_model
from app.config import settings

app = FastAPI(title="PermRAG API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(query.router)


@app.on_event("startup")
def startup_event():
    """Initialize on startup."""
    # Ensure collections exist
    ensure_collections()

    # Load embedding model
    get_embed_model(settings.embed_model)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
