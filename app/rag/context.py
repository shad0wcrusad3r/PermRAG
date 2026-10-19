"""Context assembly with token budget."""
import tiktoken
from typing import List, Dict, Any

from app.config import settings


def assemble_context(chunks: List[Dict[str, Any]], max_tokens: int = None) -> tuple[str, List[Dict[str, Any]]]:
    """Assemble context from chunks within token budget.

    Args:
        chunks: List of retrieved chunks (ordered by score)
        max_tokens: Token budget (default from config)

    Returns:
        (context_text, sources_metadata)
    """
    if max_tokens is None:
        max_tokens = settings.max_context_tokens

    # Per-document cap
    doc_chunk_count = {}
    max_per_doc = 3

    encoder = tiktoken.get_encoding("cl100k_base")
    context_parts = []
    sources = []
    total_tokens = 0

    for i, chunk in enumerate(chunks):
        doc_id = chunk["doc_id"]

        # Check per-doc limit
        if doc_chunk_count.get(doc_id, 0) >= max_per_doc:
            continue

        # Format chunk
        ref = f"S{len(context_parts) + 1}"
        formatted = f"[{ref}] (doc: {chunk['title']}, section: {chunk['heading_path']})\n{chunk['text']}\n"

        # Check token budget
        chunk_tokens = len(encoder.encode(formatted))
        if total_tokens + chunk_tokens > max_tokens:
            break

        context_parts.append(formatted)
        sources.append({
            "ref": ref,
            "doc_id": doc_id,
            "title": chunk["title"],
            "heading_path": chunk["heading_path"],
            "chunk_id": chunk["chunk_id"],
        })

        total_tokens += chunk_tokens
        doc_chunk_count[doc_id] = doc_chunk_count.get(doc_id, 0) + 1

    context_text = "\n".join(context_parts)
    return context_text, sources
