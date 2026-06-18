"""
Embedding wrapper using HuggingFace sentence-transformers (all-MiniLM-L6-v2).
Provides a LangChain-compatible embedding function for ChromaDB.
"""

from langchain_huggingface import HuggingFaceEmbeddings

from app.config import EMBEDDING_MODEL

_embeddings_instance: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Return a singleton HuggingFaceEmbeddings instance.

    Uses the model specified in config.EMBEDDING_MODEL
    (default: sentence-transformers/all-MiniLM-L6-v2).
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings_instance
