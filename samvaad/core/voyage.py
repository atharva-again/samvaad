"""
Voyage AI client singleton.
Centralizes Voyage AI client creation for embeddings and reranking.
"""

import os
import voyageai
from tenacity import retry, stop_after_attempt, wait_random_exponential
from typing import List

_client = None


def get_voyage_client() -> voyageai.Client:
    """Get or create a singleton Voyage AI client."""
    global _client
    if _client is None:
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise ValueError("VOYAGE_API_KEY environment variable not set")
        _client = voyageai.Client(api_key=api_key)
    return _client


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def embed_texts(texts: List[str], input_type: str = "document") -> List[List[float]]:
    """
    Embed a list of texts using Voyage AI.
    
    Args:
        texts: List of text strings to embed
        input_type: Either "document" or "query"
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    client = get_voyage_client()
    return client.embed(texts=texts, model="voyage-3.5-lite", input_type=input_type).embeddings


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def embed_query(query: str) -> List[float]:
    """Embed a single query string."""
    client = get_voyage_client()
    return client.embed(texts=[query], model="voyage-3.5-lite", input_type="query").embeddings[0]


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def rerank_documents(query: str, documents: List[str]):
    """Rerank documents using Voyage AI rerank model."""
    client = get_voyage_client()
    return client.rerank(query=query, documents=documents, model="rerank-2.5")


async def get_voyage_embeddings(texts: List[str], input_type: str = "query") -> List[List[float]]:
    """
    Async wrapper for embedding (runs sync function in executor).
    Used by memory tools for semantic search.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: embed_texts(texts, input_type))

