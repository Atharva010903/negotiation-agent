"""
ChromaDB retriever for procurement benchmark documents.
Loads the synthetic CSV into a persistent Chroma collection and exposes
a LangChain-compatible retriever for top-k similarity search.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.config import (
    BENCHMARK_CSV,
    CHROMA_COLLECTION,
    CHROMA_DIR,
    RAG_TOP_K,
)
from app.rag.embedder import get_embeddings
from app.rag.generator import generate_benchmark_csv

logger = logging.getLogger(__name__)

_vectorstore: Optional[Chroma] = None


def _load_csv_as_documents(csv_path: Path) -> list[Document]:
    """
    Read the benchmark CSV and convert each row into a LangChain Document.
    The full row is serialised as human-readable text in page_content,
    and all fields are stored in metadata for filtering.
    """
    documents: list[Document] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (
                f"Industry: {row['industry']} | "
                f"Average Discount: {row['average_discount_pct']}% | "
                f"Payment Terms: {row['payment_terms']} | "
                f"Delivery: {row['delivery_period']} | "
                f"MOQ: {row['moq']} units | "
                f"Contract Size: ${row['contract_size_usd']} | "
                f"Outcome: {row['negotiated_outcome']} | "
                f"Supplier Rating: {row['supplier_rating']}/5.0"
            )
            documents.append(
                Document(
                    page_content=text,
                    metadata={k: v for k, v in row.items()},
                )
            )
    logger.info("Loaded %d benchmark documents from %s", len(documents), csv_path)
    return documents


def get_vectorstore(force_reload: bool = False) -> Chroma:
    """
    Return (or create) the persistent ChromaDB vectorstore.

    On first call the benchmark CSV is ingested and embedded.
    Subsequent calls return the cached singleton.

    Parameters
    ----------
    force_reload : bool
        If True, re-ingest documents even if collection already exists.
    """
    global _vectorstore

    if _vectorstore is not None and not force_reload:
        return _vectorstore

    embeddings = get_embeddings()

    # Attempt to load existing collection
    _vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION,
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )

    # Check if collection is empty — if so, ingest
    existing = _vectorstore._collection.count()
    if existing == 0 or force_reload:
        logger.info("Ingesting benchmark documents into ChromaDB …")
        # Ensure CSV exists
        if not BENCHMARK_CSV.exists():
            generate_benchmark_csv()

        docs = _load_csv_as_documents(BENCHMARK_CSV)
        _vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            collection_name=CHROMA_COLLECTION,
            persist_directory=str(CHROMA_DIR),
        )
        logger.info("Ingested %d documents into ChromaDB.", len(docs))

    return _vectorstore


def retrieve_benchmarks(query: str, top_k: int | None = None) -> list[str]:
    """
    Retrieve the top-k most relevant benchmark documents for a given query.

    Parameters
    ----------
    query : str
        The search query (e.g. product category or negotiation context).
    top_k : int, optional
        Number of documents to retrieve. Defaults to config.RAG_TOP_K.

    Returns
    -------
    list[str]
        A list of benchmark text strings.
    """
    top_k = top_k or RAG_TOP_K
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=top_k)
    return [doc.page_content for doc in results]
