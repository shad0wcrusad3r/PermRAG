"""Retrieval metrics."""
from typing import List, Dict, Any


def recall_at_k(retrieved_doc_ids: List[str], gold_doc_ids: List[str], k: int) -> float:
    """Recall@k: proportion of gold docs in top k results."""
    if not gold_doc_ids:
        return 0.0

    retrieved_set = set(retrieved_doc_ids[:k])
    gold_set = set(gold_doc_ids)

    matches = len(retrieved_set & gold_set)
    return matches / len(gold_set)


def hit_rate_at_k(retrieved_doc_ids: List[str], gold_doc_ids: List[str], k: int) -> float:
    """Hit rate@k: 1 if any gold doc in top k, 0 otherwise."""
    retrieved_set = set(retrieved_doc_ids[:k])
    gold_set = set(gold_doc_ids)

    return 1.0 if (retrieved_set & gold_set) else 0.0


def mrr_at_k(retrieved_doc_ids: List[str], gold_doc_ids: List[str], k: int) -> float:
    """Mean Reciprocal Rank@k."""
    gold_set = set(gold_doc_ids)

    for i, doc_id in enumerate(retrieved_doc_ids[:k]):
        if doc_id in gold_set:
            return 1.0 / (i + 1)

    return 0.0
