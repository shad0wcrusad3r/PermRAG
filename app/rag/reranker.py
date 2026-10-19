"""Reranker stub (not implemented in Phase 1)."""
from typing import List, Dict, Any


def rerank(chunks: List[Dict[str, Any]], question: str, top_k: int) -> List[Dict[str, Any]]:
    """Reranker stub - returns chunks as-is for Phase 1.

    In Phase 2 this will use a cross-encoder to rerank.
    """
    return chunks[:top_k]
