"""Query API endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import List, Optional

from app.security.acl import User
from app.rag.pipeline import answer
from app.api.deps import get_current_user

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=1000)


class Source(BaseModel):
    ref: str
    doc_id: str
    title: str
    heading_path: str
    chunk_id: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    refused: bool
    cache_hit: bool
    latency_ms: dict
    request_id: str


@router.post("", response_model=QueryResponse)
def query(
    request: QueryRequest,
    user: User = Depends(get_current_user),
):
    """Query the RAG system."""
    result = answer(user, request.question, access_mode="pre")

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        refused=result["refused"],
        cache_hit=result["cache_hit"],
        latency_ms=result["latency_ms"],
        request_id=result["request_id"],
    )
