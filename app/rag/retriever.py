"""Retrieval with ACL filtering."""
from typing import List, Dict, Any
from qdrant_client.models import Filter

from app.rag.store import get_qdrant_client, get_collection_name
from app.rag.embed import get_embed_model
from app.security.acl import User, build_filter
from app.config import settings


def retrieve(user: User, question: str, top_k: int = None) -> List[Dict[str, Any]]:
    """Dense-only retrieval with ACL filter applied inside the vector search.

    Args:
        user: Authenticated user
        question: Query text
        top_k: Number of results (default from config)

    Returns:
        List of retrieved chunks with metadata
    """
    if top_k is None:
        top_k = settings.dense_top_k

    # Build ACL filter - THE CORE INVARIANT
    acl_filter = build_filter(user)

    # Embed query
    embed_model = get_embed_model(settings.embed_model)
    query_vector = embed_model.embed_query(question)

    # Search with filter applied inside HNSW traversal
    client = get_qdrant_client()
    collection = get_collection_name("chunks")

    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        query_filter=acl_filter,  # Filter BEFORE retrieval
        limit=top_k,
    ).points

    # Convert to list of dicts
    chunks = []
    for result in results:
        chunks.append({
            "chunk_id": result.payload["chunk_id"],
            "doc_id": result.payload["doc_id"],
            "tenant_id": result.payload["tenant_id"],
            "department": result.payload["department"],
            "min_role_level": result.payload["min_role_level"],
            "title": result.payload["title"],
            "heading_path": result.payload["heading_path"],
            "source_path": result.payload["source_path"],
            "text": result.payload["text"],
            "score": result.score,
        })

    return chunks
