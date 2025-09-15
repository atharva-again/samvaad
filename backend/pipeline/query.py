import os
from dotenv import load_dotenv
import pathlib
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from pipeline.vectorstore import collection
from google import genai
from google.genai import types

 # Load .env.local first (if present), then .env
env_path = pathlib.Path(__file__).parent.parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent.parent / ".env", override=False)

# Use same embedding model as for documents
_MODEL_NAME = "BAAI/bge-m3"
_INSTRUCTION = "Represent this sentence for retrieval: "

# Global model instance to avoid reloading
_embedding_model = None

def get_embedding_model():
    """Get or create the embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(_MODEL_NAME)
    return _embedding_model

def embed_query(query: str) -> List[float]:
    """Embed a query using the same model as documents."""
    model = get_embedding_model()
    inputs = [_INSTRUCTION + query]
    embeddings = model.encode(inputs, show_progress_bar=False, convert_to_numpy=True)
    return embeddings[0].tolist()


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

def search_similar_chunks(query_embedding: List[float], top_k: int = 3) -> List[Dict]:
    """Search for similar chunks in the vectorstore."""
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "content": doc,
            "metadata": meta,
            "distance": dist,
            "filename": meta.get("filename", "unknown") if meta else "unknown"
        })

    return chunks

def generate_answer_with_gemini(query: str, chunks: List[Dict], model: str = "gemini-2.5-flash") -> str:
    """Generate answer using Google Gemini with retrieved chunks as context."""
    # DEBUG: Print GEMINI_API_KEY (masked)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print(f"[DEBUG] GEMINI_API_KEY loaded")
    else:
        print("[DEBUG] GEMINI_API_KEY is NOT loaded (None or empty)")

    # Build context from chunks (use summaries/truncated content to reduce token usage)
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        content = chunk.get('content', '')
        # Truncate to a short preview to save tokens (prefer sentence boundary)
        short = summarize_chunk(content, max_chars=200)
        context_parts.append(f"Document {i} ({chunk['filename']}):\n{short}\n")

    context = "\n".join(context_parts)

    # Create the prompt
    prompt = f"""You are a helpful assistant that answers questions based on the provided context.

Context:
{context}

Question: {query}

Instructions:
- Answer the question based only on the information provided in the context above.
- If the context doesn't contain enough information to answer the question, say so.
- Be concise but comprehensive.
- Cite the specific documents you used in your answer.
- If multiple documents are relevant, mention them all.

Answer:"""

    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    # Generate response
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,  # Slightly higher to encourage concise responses
            max_output_tokens=1024,  # Limit response length to reduce token usage
            thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disable thinking for speed
        )
    )

    return response.text

def rag_query_pipeline(query_text: str, top_k: int = 3, model: str = "gemini-2.5-flash") -> Dict[str, Any]:
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
        print("🔍 Embedding query...")
        query_embedding = embed_query(query_text)

        # Step 2: Search for similar chunks (default fewer chunks to save tokens)
        print(f"🔎 Searching for top-{top_k} similar chunks...")
        chunks = search_similar_chunks(query_embedding, top_k)

        if not chunks:
            return {
                'query': query_text,
                'answer': "No relevant documents found in the knowledge base.",
                'sources': [],
                'success': False,
                'retrieval_count': 0,
                'rag_prompt': ""
            }

        # Step 3: Generate answer with Gemini
        print("🤖 Generating answer with Gemini...")
        answer = generate_answer_with_gemini(query_text, chunks, model)

        # Step 4: Format sources for display
        sources = []
        for chunk in chunks:
            sources.append({
                'filename': chunk['filename'],
                'content_preview': summarize_chunk(chunk.get('content', ''), max_chars=200),
                'distance': chunk['distance']
            })

        # Build the RAG prompt for debugging (use truncated content to avoid huge prompts)
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"Document {i} ({chunk['filename']}):\n{summarize_chunk(chunk.get('content', ''), max_chars=200)}\n")
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