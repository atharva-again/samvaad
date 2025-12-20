"""
RAG query pipeline module.
"""

from typing import Any, Dict, List
import tiktoken

from samvaad.db.service import DBService
from samvaad.core.voyage import embed_query, rerank_documents
from samvaad.pipeline.generation.generation import generate_answer_with_groq

# Token counter (cl100k_base is compatible with GPT-4 and Groq's Llama models)
_encoder = None

def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken."""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return len(_encoder.encode(text)) if text else 0


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
    import time
    start_time = time.time()
    
    # Truncate query for logging
    query_preview = query_text[:60].replace('\n', ' ') + ('...' if len(query_text) > 60 else '')
    print(f"[RAG] ┌─ Query: \"{query_preview}\"")
    print(f"[RAG] │  user_id: {user_id[:8] if user_id else 'None'}..., strict: {strict_mode}, generate: {generate_answer}")
    
    try:
        # Step 1: Embed the query
        embed_start = time.time()
        query_emb = embed_query(query_text)
        embed_ms = (time.time() - embed_start) * 1000
        print(f"[RAG] │  ✓ Embed: {embed_ms:.0f}ms")

        # Step 2: Search for similar chunks (dense semantic search)
        search_start = time.time()
        chunks = search_similar_chunks(query_emb, query_text, top_k, user_id=user_id)
        search_ms = (time.time() - search_start) * 1000
        
        if chunks:
            top_scores = [f"{c.get('rerank_score', 0):.2f}" for c in chunks[:3]]
            filenames = list(set(c.get('filename', '?')[:20] for c in chunks))
            print(f"[RAG] │  ✓ Search: {search_ms:.0f}ms → {len(chunks)} chunks (scores: {', '.join(top_scores)})")
            print(f"[RAG] │    Sources: {', '.join(filenames)}")
        else:
            print(f"[RAG] │  ⚠ Search: {search_ms:.0f}ms → 0 chunks found")

        if not chunks:
            total_ms = (time.time() - start_time) * 1000
            print(f"[RAG] └─ No results ({total_ms:.0f}ms total)")
            
            if strict_mode and generate_answer:
                return {
                    "query": query_text,
                    "answer": "I don't know the answer as there is no relevant information in your documents.",
                    "sources": [],
                    "chunks": [],
                    "success": True,
                    "retrieval_count": 0,
                }
            else:
                return {
                    "query": query_text,
                    "answer": "No relevant documents found.",
                    "sources": [],
                    "chunks": [],
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
        
        # Token counting
        query_tokens = _count_tokens(query_text)
        context_tokens = _count_tokens(context)
        history_tokens = _count_tokens(history_str) if history_str else 0
        total_input_tokens = query_tokens + context_tokens + history_tokens
        print(f"[RAG] │  ⊕ Tokens: query={query_tokens}, context={context_tokens}, history={history_tokens} → total={total_input_tokens}")

        if generate_answer:
            gen_start = time.time()
            answer = generate_answer_with_groq(
                query_text, 
                chunks, 
                model, 
                history_str,
                persona=persona,
                strict_mode=strict_mode
            )
            gen_ms = (time.time() - gen_start) * 1000
            output_tokens = _count_tokens(answer)
            print(f"[RAG] │  ✓ Generate: {gen_ms:.0f}ms ({output_tokens} tokens out)")
        else:
            answer = context
            print(f"[RAG] │  ○ Generate: skipped (context-only mode)")

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

        total_ms = (time.time() - start_time) * 1000
        print(f"[RAG] └─ Done: {len(chunks)} chunks, {total_ms:.0f}ms total")
        
        return {
            "query": query_text,
            "answer": answer,
            "sources": sources,
            "chunks": chunks,
            "success": True,
            "retrieval_count": len(chunks),
        }

    except Exception as e:
        import traceback
        total_ms = (time.time() - start_time) * 1000
        print(f"[RAG] │  ✗ Error: {str(e)}")
        print(f"[RAG] └─ Failed after {total_ms:.0f}ms")
        print(traceback.format_exc())
        return {
            "query": query_text,
            "answer": f"Error processing query: {str(e)}",
            "sources": [],
            "chunks": [],
            "success": False,
            "retrieval_count": 0,
        }

