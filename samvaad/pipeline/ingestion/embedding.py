"""
Embedding generation module using Voyage AI.
"""

from typing import List
from samvaad.core.voyage import embed_texts


def generate_embeddings(chunks: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of chunks using Voyage AI.
    Handles retry logic internally via the voyage singleton.
    """
    if not chunks:
        return []
    return embed_texts(chunks, input_type="document")
