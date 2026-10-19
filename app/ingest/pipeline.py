"""Ingestion pipeline."""
import json
from pathlib import Path
from typing import Dict, List, Any

from app.config import settings
from app.ingest.loaders import load_markdown
from app.ingest.clean import clean_text
from app.ingest.chunker import chunk_text
from app.rag.embed import get_embed_model
from app.rag.store import (
    compute_doc_id,
    compute_chunk_id,
    compute_content_hash,
    upsert_chunks,
    delete_chunks_by_doc_id,
    ensure_collections,
    get_existing_doc_hashes,
)


def ingest_documents(manifest_path: Path, corpus_base_path: Path) -> Dict[str, int]:
    """Ingest documents from a manifest.

    Returns:
        Dict with counts: added, updated, deleted, skipped
    """
    # Load manifest
    manifest_entries = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                manifest_entries.append(json.loads(line))

    # Load current doc_id -> content_hash state from Qdrant for idempotency
    ensure_collections()
    existing_docs: Dict[str, str] = get_existing_doc_hashes()

    embed_model = get_embed_model(settings.embed_model)

    stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0}

    for entry in manifest_entries:
        doc_id = compute_doc_id(entry["tenant_id"], entry["path"])
        file_path = corpus_base_path / entry["path"]

        # Load and clean
        if entry["format"] == "md":
            raw_text = load_markdown(file_path)
        else:
            raise ValueError(f"Unsupported format: {entry['format']}")

        cleaned_text = clean_text(raw_text)

        # Compute content hash
        content_hash = compute_content_hash(
            cleaned_text,
            entry["tenant_id"],
            entry["department"],
            entry["min_role_level"],
        )

        # Check if changed
        if doc_id in existing_docs and existing_docs[doc_id] == content_hash:
            stats["skipped"] += 1
            continue

        # Chunk
        chunks = chunk_text(cleaned_text, entry["title"])

        # Prepare chunks for embedding
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = embed_model.embed_documents(chunk_texts)

        # Build chunk records
        chunk_records = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = compute_chunk_id(doc_id, i, content_hash)
            chunk_records.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "tenant_id": entry["tenant_id"],
                "department": entry["department"],
                "min_role_level": entry["min_role_level"],
                "title": entry["title"],
                "heading_path": chunk["heading_path"],
                "source_path": entry["path"],
                "page": None,
                "chunk_index": i,
                "content_hash": content_hash,
                "text": chunk["text"],
                "dense_embedding": embedding,
                "kind": entry.get("kind", "normal"),
            })

        # Delete old chunks if this is an update
        if doc_id in existing_docs:
            delete_chunks_by_doc_id(doc_id)
            stats["updated"] += 1
        else:
            stats["added"] += 1

        # Upsert new chunks
        upsert_chunks(chunk_records)

        # Track this doc
        existing_docs[doc_id] = content_hash

    return stats
