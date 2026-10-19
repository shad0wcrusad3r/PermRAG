"""Embeddings using fastembed."""
from typing import List
import numpy as np
from fastembed import TextEmbedding


class EmbeddingModel:
    """Dense embedding model using fastembed."""

    def __init__(self, model_name: str):
        self.model = TextEmbedding(model_name=model_name)
        self.model_name = model_name

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query with the BGE query instruction prefix."""
        prefixed = f"Represent this sentence for searching relevant passages: {text}"
        embeddings = list(self.model.embed([prefixed]))
        return embeddings[0].tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document texts."""
        embeddings = list(self.model.embed(texts))
        return [emb.tolist() for emb in embeddings]


# Global singleton - loaded once at startup
_embed_model: EmbeddingModel | None = None


def get_embed_model(model_name: str) -> EmbeddingModel:
    """Get or create the global embedding model."""
    global _embed_model
    if _embed_model is None:
        _embed_model = EmbeddingModel(model_name)
    return _embed_model
