"""
RAG query pipeline module.
"""

from typing import Any

from samvaad.core.voyage import embed_query, rerank_documents
from samvaad.db.service import DBService
from samvaad.utils.logger import logger


def search_similar_chunks(
    query_emb: list[float], query_text: str, top_k: int = 3, user_id: str = None, file_ids: list[str] = None
) -> list[dict]:
    """Search for similar chunks using dense semantic search with reranking.

    Args:
        query_emb: Query embedding vector
        query_text: Original query text for reranking
        top_k: Number of results to return
        user_id: User ID for access control
        file_ids: Optional list of file IDs to filter by (RAG source whitelist)
    """

    # Fetch top 6 from Postgres for reranking
    fetch_k = 6
    try:
        results = DBService.search_similar_chunks(query_emb, top_k=fetch_k, user_id=user_id, file_ids=file_ids)
    except Exception as e:
        logger.warning(f"DB search failed: {e}")
        return []

    chunks = []
    for res in results:
        chunks.append(
            {
                "content": res["document"],
                "metadata": res["metadata"],
                "distance": res["distance"],
                "filename": res["metadata"].get("filename", "unknown"),
                "chunk_id": res["id"],
            }
        )

    if not chunks:
        return []

    # Rerank using Voyage AI rerank-2.5
    documents = [chunk["content"] for chunk in chunks]
    rerank_results = rerank_documents(query_text, documents)

    # Sort chunks by rerank score descending
    reranked_chunks = []
    for rerank_res in rerank_results.results:
        idx = rerank_res.index
        score = rerank_res.relevance_score
        chunk = chunks[idx].copy()
        chunk["rerank_score"] = score
        reranked_chunks.append(chunk)

    # Sort by rerank score descending and take top_k
    reranked_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
    return reranked_chunks[:top_k]


def rag_query_pipeline(
    query_text: str,
    top_k: int = 3,
    user_id: str = None,
    file_ids: list[str] = None,
) -> dict[str, Any]:
    """
    Search-only RAG pipeline: embed query, search documents.
    Used by agents as a tool to fetch context.

    Args:
        query_text: The user's query
        top_k: Number of chunks to retrieve
        user_id: User ID for access control
        file_ids: Optional list of file IDs to filter by

    Returns:
        dict: {
            'query': str,
            'chunks': List[Dict],
            'success': bool,
        }
    """
    import time

    start_time = time.time()

    try:
        # Step 1: Embed the query
        query_emb = embed_query(query_text)

        # Step 2: Search for similar chunks (dense semantic search)
        chunks = search_similar_chunks(query_emb, query_text, top_k, user_id=user_id, file_ids=file_ids)

        total_ms = (time.time() - start_time) * 1000
        logger.info(f"[RAG] Search completed in {total_ms:.0f}ms, found {len(chunks)} chunks")

        return {
            "query": query_text,
            "chunks": chunks,
            "success": True,
        }

    except Exception as e:
        logger.error(f"[RAG] Search error: {e}")
        return {
            "query": query_text,
            "chunks": [],
            "success": False,
        }
