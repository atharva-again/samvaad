"""
Unified RAG Tooling for Samvaad Agents.

Consolidates RAG pipeline execution, formatting, and source extraction
to ensure consistent behavior across text and voice modes.
"""

import asyncio
from samvaad.pipeline.retrieval.query import rag_query_pipeline
from samvaad.utils.citations import format_rag_context
from samvaad.utils.logger import logger

RAG_TIMEOUT_SECONDS = 10.0


async def execute_unified_rag(
    query: str, user_id: str, file_ids: list[str] | None = None, limit_sources: int = 3
) -> dict:
    """
    Executes the RAG pipeline and returns formatted context and structured sources.

    Returns:
        dict: {
            "context": str,   # XML-formatted context for LLM
            "sources": list, # List of source dictionaries for UI/citations
            "raw_chunks": list # Original chunks from pipeline
        }
    """
    try:
        # Run blocking RAG code in thread to avoid blocking event loop
        result = await asyncio.wait_for(
            asyncio.to_thread(rag_query_pipeline, query, user_id=user_id, file_ids=file_ids or []),
            timeout=RAG_TIMEOUT_SECONDS,
        )

        chunks = result.get("chunks", [])
        rag_text = format_rag_context(chunks)

        sources = []
        for chunk in chunks[:limit_sources]:
            sources.append(
                {
                    "filename": chunk.get("filename", "document"),
                    "content_preview": chunk.get("content", "")[:1000],
                    "rerank_score": chunk.get("rerank_score"),
                    "chunk_id": chunk.get("chunk_id"),
                    "metadata": chunk.get("metadata", {}),
                }
            )

        return {"context": rag_text, "sources": sources, "raw_chunks": chunks}

    except asyncio.TimeoutError:
        logger.warning(f"[RAG] Timeout after {RAG_TIMEOUT_SECONDS}s for query: {query}")
        return {"context": "Search timed out. Please try your question again.", "sources": [], "raw_chunks": []}
    except Exception as e:
        logger.error(f"[RAG] Error during execution: {e}")
        return {"context": "An error occurred while searching. Please try again.", "sources": [], "raw_chunks": []}
