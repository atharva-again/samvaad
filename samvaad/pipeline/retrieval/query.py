import os
from typing import Any, Dict, List

from samvaad.db.service import DBService

import voyageai
from tenacity import retry, stop_after_attempt, wait_random_exponential

from samvaad.pipeline.generation.generation import generate_answer_with_groq


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def _embed_query_with_backoff(query: str) -> List[float]:
    vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    return vo.embed(
        texts=[query], model="voyage-3.5-lite", input_type="query"
    ).embeddings[0]


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def _rerank_with_backoff(query_text: str, documents: List[str]):
    vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    return vo.rerank(query=query_text, documents=documents, model="rerank-2.5")


def embed_query(query: str) -> List[float]:
    """Embed a query using Voyage AI."""
    return _embed_query_with_backoff(query)


def summarize_chunk(text: str, max_chars: int = 200) -> str:
    """Return a short summary/truncation of `text` up to `max_chars` characters.

    This is a lightweight helper to reduce token usage by trimming to a
    sentence boundary when possible, otherwise returning a hard truncation.
    """
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # Try to break at the last sentence-ending punctuation before max_chars
    cutoff = text.rfind(".", 0, max_chars)
    if cutoff == -1:
        cutoff = text.rfind("\n", 0, max_chars)
    if cutoff == -1:
        # fallback hard cut but avoid cutting mid-word
        snippet = text[:max_chars]
        if " " in snippet:
            snippet = snippet.rsplit(" ", 1)[0]
        return snippet + "..."
    return text[: cutoff + 1].strip() + "..."


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
    rerank_results = _rerank_with_backoff(query_text, documents)

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
    conversation_manager=None, # Deprecated in favor of direct history_str
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
            'rag_prompt': str
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
                    "success": True, # It's a successful "I don't know"
                    "retrieval_count": 0,
                }
            elif not generate_answer: # Fetching context only
                 return {
                    "query": query_text,
                    "answer": "No relevant documents found.",
                    "sources": [],
                    "success": False,
                    "retrieval_count": 0,
                }
            # Else fall through to regular logic (which might just return empty sources or handle it in generation)
            # Actually, existing logic returns early. Let's keep it but modify for strict.
            # If strict mode and no chunks, we MUST fail early or say I don't know.
            
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
            conversation_context = history_str
            if conversation_manager and not conversation_context:
                conversation_context = conversation_manager.get_context()

            answer = generate_answer_with_groq(
                query_text, 
                chunks, 
                model, 
                conversation_context,
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
                    else None,  # Ensure float
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
