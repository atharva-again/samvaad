import os
from typing import List, Tuple, Union

import voyageai
from tenacity import retry, stop_after_attempt, wait_random_exponential

from samvaad.utils.hashing import generate_chunk_id


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
def _embed_with_backoff(texts, model, input_type):
    vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    return vo.embed(texts=texts, model=model, input_type=input_type).embeddings



def generate_embeddings(chunks: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of chunks using Voyage AI.
    Handles retry logic internally.
    """
    if not chunks:
        return []

    vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

    @retry(
        wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6)
    )
    def _embed_with_backoff():
        return vo.embed(
            texts=chunks, model="voyage-3.5-lite", input_type="document"
        ).embeddings

    return _embed_with_backoff()
