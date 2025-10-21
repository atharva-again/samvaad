import pathlib
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import numpy as np
from samvaad.pipeline.vectorstore.vectorstore import get_collection
from samvaad.utils.gpu_utils import get_device
from samvaad.pipeline.generation.generation import generate_answer_with_gemini
from samvaad.pipeline.ingestion.embedding import GGUFEmbeddingModel

# Use same GGUF quantized embedding model as for documents
_MODEL_REPO = "unsloth/embeddinggemma-300m-GGUF"
_QUANTIZATION = "Q8_0"

# Global model instance to avoid reloading
_embedding_model = None
_cross_encoder = None

def get_embedding_model():
    """Get or create the GGUF embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = GGUFEmbeddingModel(_MODEL_REPO, _QUANTIZATION)
    return _embedding_model

def get_cross_encoder():
    """Get or create the cross-encoder model instance."""
    global _cross_encoder
    if _cross_encoder is None:
        device = get_device()
        _cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device=device)
    return _cross_encoder

def embed_query(query: str) -> List[float]:
    """Embed a query using the same GGUF model as documents."""
    model = get_embedding_model()
    embedding = model.encode_query(query)
    return embedding.tolist()


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
    cutoff = text.rfind('.', 0, max_chars)
    if cutoff == -1:
        cutoff = text.rfind('\n', 0, max_chars)
    if cutoff == -1:
        # fallback hard cut but avoid cutting mid-word
        snippet = text[:max_chars]
        if ' ' in snippet:
            snippet = snippet.rsplit(' ', 1)[0]
        return snippet + '...'
    return text[: cutoff + 1].strip() + '...'

def reciprocal_rank_fusion(ranks1: List[Dict], ranks2: List[Dict], k: int = 60) -> List[Dict]:
    """Fuse two ranked lists using Reciprocal Rank Fusion."""
    scores = {}
    
    # Process first list
    for rank, item in enumerate(ranks1, 1):
        key = item.get('chunk_id', item.get('content', str(item)))
        scores[key] = scores.get(key, 0) + 1.0 / (k + rank)
    
    # Process second list
    for rank, item in enumerate(ranks2, 1):
        key = item.get('chunk_id', item.get('content', str(item)))
        scores[key] = scores.get(key, 0) + 1.0 / (k + rank)
    
    # Sort by fused score
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Return top items with their scores
    result = []
    for key, score in fused:
        # Find the original item (prefer from ranks1, then ranks2)
        item = next((item for item in ranks1 if item.get('chunk_id', item.get('content', str(item))) == key), None)
        if not item:
            item = next((item for item in ranks2 if item.get('chunk_id', item.get('content', str(item))) == key), None)
        if item:
            item_copy = item.copy()
            item_copy['rrf_score'] = float(score)  # Convert numpy to float
            result.append(item_copy)
    
    return result

def search_similar_chunks(query_embedding: List[float], query_text: str, top_k: int = 3) -> List[Dict]:
    """Search for similar chunks using hybrid BM25 + Embedding + Cross-Encoder reranking."""
    
    # Get ChromaDB collection (lazy initialization)
    collection = get_collection()
    
    # Get all chunks from ChromaDB (for BM25 indexing)
    all_results = collection.get(include=['documents', 'metadatas'])
    all_chunks = []
    for doc, meta in zip(all_results['documents'], all_results['metadatas']):
        all_chunks.append({
            "content": doc,
            "metadata": meta,
            "filename": meta.get("filename", "unknown") if meta else "unknown",
            "chunk_id": meta.get("chunk_id") if meta else None
        })
    
    if not all_chunks:
        return []
    
    # BM25 Search
    corpus = [chunk['content'] for chunk in all_chunks]
    tokenized_corpus = [doc.split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query_text.split()
    bm25_scores = bm25.get_scores(tokenized_query)
    
    # Get top 5 from BM25
    bm25_top_indices = np.argsort(bm25_scores)[::-1][:5]
    bm25_chunks = []
    for idx in bm25_top_indices:
        chunk = all_chunks[idx].copy()
        chunk['bm25_score'] = float(bm25_scores[idx])  # Convert numpy to float
        chunk['distance'] = 1.0  # High distance for BM25 chunks (low similarity)
        bm25_chunks.append(chunk)
    
    # Embedding Search - top 5
    embedding_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=['documents', 'metadatas', 'distances']
    )
    
    embedding_chunks = []
    for doc, meta, dist in zip(
        embedding_results["documents"][0],
        embedding_results["metadatas"][0],
        embedding_results["distances"][0]
    ):
        chunk = {
            "content": doc,
            "metadata": meta,
            "distance": float(dist),  # Convert numpy to float
            "filename": meta.get("filename", "unknown") if meta else "unknown",
            "chunk_id": meta.get("chunk_id") if meta else None
        }
        embedding_chunks.append(chunk)
    
    # Fuse using RRF
    fused_chunks = reciprocal_rank_fusion(bm25_chunks, embedding_chunks)
    
    # Take top 10 from fused for reranking (or all if less)
    candidates = fused_chunks[:10]
    
    if not candidates:
        return []
    
    # Cross-Encoder Reranking
    cross_encoder = get_cross_encoder()
    query_chunk_pairs = [[query_text, chunk['content']] for chunk in candidates]
    rerank_scores = cross_encoder.predict(query_chunk_pairs)
    
    # Add scores and sort
    for i, chunk in enumerate(candidates):
        chunk['rerank_score'] = float(rerank_scores[i])  # Convert numpy to float
    
    reranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
    
    # Return top 3
    return reranked[:top_k]

def rag_query_pipeline(query_text: str, top_k: int = 3, model: str = "gemini-2.5-flash", conversation_manager=None) -> Dict[str, Any]:
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
        query_embedding = embed_query(query_text)

        # Step 2: Search for similar chunks (hybrid retrieval with reranking)
        chunks = search_similar_chunks(query_embedding, query_text, top_k)

        if not chunks:
            return {
                'query': query_text,
                'answer': "No relevant documents found in the knowledge base.",
                'sources': [],
                'success': False,
                'retrieval_count': 0,
                'rag_prompt': ""
            }

        # Step 3: Generate answer with an LLM
    
        conversation_context = ""
        if conversation_manager:
            conversation_context = conversation_manager.get_context()
        
        answer = generate_answer_with_gemini(query_text, chunks, model, conversation_context)
        from samvaad.utils.clean_markdown import strip_markdown
        answer = strip_markdown(answer)

        # Step 4: Format sources for display
        sources = []
        for chunk in chunks:
            sources.append({
                'filename': chunk['filename'],
                'content_preview': chunk.get('content', ''),
                'distance': float(chunk.get('distance')) if chunk.get('distance') is not None else None,  # Ensure float
                'rerank_score': float(chunk.get('rerank_score')) if chunk.get('rerank_score') is not None else None  # Ensure float
            })

        # Build the RAG prompt for debugging (use full content)
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"Document {i} ({chunk['filename']}):\n{chunk.get('content', '')}\n")
        context = "\n".join(context_parts)
        rag_prompt = f"""Context:
{context}

Question: {query_text}

Answer:"""

        return {
            'query': query_text,
            'answer': answer,
            'sources': sources,
            'success': True,
            'retrieval_count': len(chunks),
            'rag_prompt': rag_prompt
        }

    except Exception as e:
        print(f"❌ Error in RAG pipeline: {str(e)}")
        return {
            'query': query_text,
            'answer': f"Error processing query: {str(e)}",
            'sources': [],
            'success': False,
            'retrieval_count': 0,
            'rag_prompt': ""
        }

