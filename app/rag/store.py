"""Qdrant vector store interface."""
import hashlib
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter

from app.config import settings


# Global client singleton
_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Get or create the global Qdrant client."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=settings.qdrant_url)
    return _qdrant_client


def get_collection_name(collection_type: str) -> str:
    """Get collection name with environment prefix."""
    return f"{settings.env}_{collection_type}"


def ensure_collections() -> None:
    """Create collections if they don't exist."""
    client = get_qdrant_client()

    chunks_collection = get_collection_name("chunks")

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]

    if chunks_collection not in collection_names:
        client.create_collection(
            collection_name=chunks_collection,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

        # Create payload indexes for ACL fields
        client.create_payload_index(
            collection_name=chunks_collection,
            field_name="tenant_id",
            field_schema="keyword",
        )
        client.create_payload_index(
            collection_name=chunks_collection,
            field_name="department",
            field_schema="keyword",
        )
        client.create_payload_index(
            collection_name=chunks_collection,
            field_name="min_role_level",
            field_schema="integer",
        )
        client.create_payload_index(
            collection_name=chunks_collection,
            field_name="doc_id",
            field_schema="keyword",
        )


def upsert_chunks(chunks: List[Dict[str, Any]]) -> None:
    """Upsert chunk points to Qdrant."""
    client = get_qdrant_client()
    collection = get_collection_name("chunks")

    points = []
    for chunk in chunks:
        points.append(
            PointStruct(
                id=chunk["chunk_id"],
                vector=chunk["dense_embedding"],
                payload={
                    "chunk_id": chunk["chunk_id"],
                    "doc_id": chunk["doc_id"],
                    "tenant_id": chunk["tenant_id"],
                    "department": chunk["department"],
                    "min_role_level": chunk["min_role_level"],
                    "title": chunk["title"],
                    "heading_path": chunk["heading_path"],
                    "source_path": chunk["source_path"],
                    "page": chunk.get("page"),
                    "chunk_index": chunk["chunk_index"],
                    "content_hash": chunk["content_hash"],
                    "text": chunk["text"],
                    "kind": chunk.get("kind", "normal"),
                }
            )
        )

    client.upsert(collection_name=collection, points=points)


def delete_chunks_by_doc_id(doc_id: str) -> None:
    """Delete all chunks for a document."""
    client = get_qdrant_client()
    collection = get_collection_name("chunks")

    client.delete(
        collection_name=collection,
        points_selector=Filter(
            must=[{"key": "doc_id", "match": {"value": doc_id}}]
        ),
    )


def get_existing_doc_hashes() -> Dict[str, str]:
    """Return {doc_id: content_hash} for all docs currently in the chunks collection.

    If a doc's chunks carry more than one content_hash (e.g. stale leftovers),
    the value is set to "" so the caller treats it as changed and re-ingests it.
    """
    client = get_qdrant_client()
    collection = get_collection_name("chunks")

    hashes: Dict[str, str] = {}
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=256,
            offset=offset,
            with_payload=["doc_id", "content_hash"],
            with_vectors=False,
        )
        for p in points:
            doc_id = p.payload.get("doc_id")
            h = p.payload.get("content_hash", "")
            if doc_id in hashes and hashes[doc_id] != h:
                hashes[doc_id] = ""
            else:
                hashes.setdefault(doc_id, h)
        if offset is None:
            break
    return hashes


def compute_doc_id(tenant_id: str, path: str) -> str:
    """Compute deterministic doc_id using uuid5."""
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
    return str(uuid.uuid5(namespace, f"{tenant_id}:{path}"))


def compute_chunk_id(doc_id: str, chunk_index: int, content_hash: str) -> str:
    """Compute deterministic chunk_id using uuid5."""
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    return str(uuid.uuid5(namespace, f"{doc_id}:{chunk_index}:{content_hash}"))


def compute_content_hash(text: str, tenant_id: str, department: str, min_role_level: int) -> str:
    """Compute content hash including ACL metadata."""
    content = f"{text}|{tenant_id}|{department}|{min_role_level}"
    return hashlib.sha256(content.encode()).hexdigest()
