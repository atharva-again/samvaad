"""
Voyage AI client singleton.
Centralizes Voyage AI client creation for embeddings and reranking.
"""

import os
import re

import voyageai
from tenacity import retry, stop_after_attempt, wait_random_exponential

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


# [SECURITY-FIX #95] Scrub PII before sending to 3rd party embedding service


def scrub_pii(text: str) -> str:
    """Scrub PII from text using regex."""
    # Email
    text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_REDACTED]", text)
    # Phone: Matches (123) 456-7890, 123-456-7890, 123 456 7890
    text = re.sub(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]", text)
    # SSN-like: 000-00-0000
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]", text)
    # Credit Card-like: 16 digits (simple)
    text = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD_REDACTED]", text)
    return text


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def embed_texts(texts: list[str], input_type: str = "document") -> list[list[float]]:
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

    scrubbed_texts = [scrub_pii(t) for t in texts]

    client = get_voyage_client()
    # Use scrubbed text for embedding
    return client.embed(
        texts=scrubbed_texts, model="voyage-3.5-lite", input_type=input_type
    ).embeddings


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    client = get_voyage_client()
    return client.embed(texts=[query], model="voyage-3.5-lite", input_type="query").embeddings[0]


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def rerank_documents(query: str, documents: list[str]):
    """Rerank documents using Voyage AI rerank model."""
    client = get_voyage_client()
    return client.rerank(query=query, documents=documents, model="rerank-2.5")


async def get_voyage_embeddings(texts: list[str], input_type: str = "query") -> list[list[float]]:
    """
    Async wrapper for embedding (runs sync function in executor).
    Used by memory tools for semantic search.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: embed_texts(texts, input_type))
