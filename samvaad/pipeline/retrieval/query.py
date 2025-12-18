"""
RAG query pipeline module.
"""

from typing import Any, Dict, List

from samvaad.db.service import DBService
from samvaad.core.voyage import embed_query, rerank_documents
from samvaad.pipeline.generation.generation import generate_answer_with_groq


def search_similar_chunks(
    query_emb: List[float], query_text: str, top_k: int = 3, user_id: str = None
) -> List[Dict]:
    """Search for similar chunks using dense semantic search with reranking."""

    # Fetch top 6 from Postgres for reranking
    fetch_k = 6
    try:
        results = DBService.search_similar_chunks(query_emb, top_k=fetch_k, user_id=user_id)
    except Exception as e:
        print(f"Warning: DB search failed: {e}")
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
    model: str = "llama-3.3-70b-versatile",
    history_str: str = "",
    generate_answer: bool = True,
    user_id: str = None,
    persona: str = "default",
    strict_mode: bool = False,
) -> Dict[str, Any]:
    """
    Complete RAG pipeline: embed query, search, generate answer.

    Returns:
        dict: {
            'query': str,
            'answer': str,
            'sources': List[Dict],
            'success': bool,
            'retrieval_count': int,
        }
    """
    try:
        # Step 1: Embed the query
        query_emb = embed_query(query_text)

        # Step 2: Search for similar chunks (dense semantic search)
        chunks = search_similar_chunks(query_emb, query_text, top_k, user_id=user_id)

        if not chunks:
            if strict_mode and generate_answer:
                return {
                    "query": query_text,
                    "answer": "I don't know the answer as there is no relevant information in your documents.",
                    "sources": [],
                    "success": True,
                    "retrieval_count": 0,
                }
            elif not generate_answer:
                return {
                    "query": query_text,
                    "answer": "No relevant documents found.",
                    "sources": [],
                    "success": False,
                    "retrieval_count": 0,
                }
            
        if not chunks and not strict_mode: 
            return {
                "query": query_text,
                "answer": "No relevant documents found in the knowledge base.",
                "sources": [],
                "success": False,
                "retrieval_count": 0,
            }

        # Step 3: Build context and generate answer if needed
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"Document {i} ({chunk['filename']}):\n{chunk.get('content', '')}\n"
            )
        context = "\n".join(context_parts)

        if generate_answer:
            answer = generate_answer_with_groq(
                query_text, 
                chunks, 
                model, 
                history_str,
                persona=persona,
                strict_mode=strict_mode
            )
        else:
            answer = context

        # Step 4: Format sources for display
        sources = []
        for chunk in chunks:
            sources.append(
                {
                    "filename": chunk["filename"],
                    "content_preview": chunk.get("content", ""),
                    "rerank_score": float(chunk.get("rerank_score"))
                    if chunk.get("rerank_score") is not None
                    else None,
                }
            )

        return {
            "query": query_text,
            "answer": answer,
            "sources": sources,
            "success": True,
            "retrieval_count": len(chunks),
        }

    except Exception as e:
        import traceback

        print(f"❌ Error in RAG pipeline: {str(e)}")
        print(traceback.format_exc())
        return {
            "query": query_text,
            "answer": f"Error processing query: {str(e)}",
            "sources": [],
            "success": False,
            "retrieval_count": 0,
        }
