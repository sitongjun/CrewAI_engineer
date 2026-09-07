"""Online-only knowledge search tool.

This is not PDF parsing and not ingest. Documents must already be in local
Chroma. Call ``python ingest.py`` or POST /v1/documents first.
"""

from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from rag.store import search_chunks


class KnowledgeSearchInput(BaseModel):
    query: str = Field(..., description="要在已灌库的健康档案中检索的问题或关键词")


class KnowledgeSearchTool(BaseTool):
    name: str = "Search ingested health records"
    description: str = (
        "Search the already-ingested local health-record knowledge base. "
        "This tool only retrieves. It never uploads, parses, or indexes a PDF."
    )
    args_schema: type[BaseModel] = KnowledgeSearchInput

    def _run(self, query: str) -> str:
        hits = search_chunks(query, limit=5)
        if not hits:
            return "No relevant content found."
        parts = ["Relevant Content:"]
        for index, hit in enumerate(hits, 1):
            source = (hit.get("metadata") or {}).get("source", "")
            distance = hit.get("distance")
            header = f"[{index}] source={source} distance={distance}"
            parts.append(header)
            parts.append(hit["content"])
        return "\n\n".join(parts)


def create_pdf_search_tool() -> KnowledgeSearchTool:
    """Return the online retrieval tool. Name kept for the existing crew import."""
    return KnowledgeSearchTool()
