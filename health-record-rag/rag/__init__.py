"""Offline ingest and online retrieval for the local Chroma knowledge base."""

from .store import (
    CHROMA_DIR,
    COLLECTION_NAME,
    PROJECT_ROOT,
    get_knowledge_status,
    ingest_pdf,
    list_chunks,
    search_chunks,
)

__all__ = [
    "CHROMA_DIR",
    "COLLECTION_NAME",
    "PROJECT_ROOT",
    "get_knowledge_status",
    "ingest_pdf",
    "list_chunks",
    "search_chunks",
]
