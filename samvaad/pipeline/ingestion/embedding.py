from typing import List, Tuple, Union
from samvaad.pipeline.vectorstore.vectorstore import get_collection
from samvaad.utils.hashing import generate_chunk_id
from samvaad.utils.onnx_embedding import ONNXEmbeddingModel
import contextlib

# Global model instance to avoid reloading
_model = None


def embed_chunks_with_dedup(
    chunks: List[str], filename: str = None
) -> Tuple[List[List[float]], List[int]]:
    """
    Embed chunks with deduplication - only compute embeddings for chunks that don't already exist in ChromaDB.
    Uses content-based IDs to avoid re-embedding identical chunks that may have shifted position.
    Returns: (embeddings_list, indices_embedded) where indices_embedded shows which chunks were actually embedded.
    """

    # Generate content-based IDs for all chunks (SHA256 hash only)
    chunk_ids = [generate_chunk_id(chunk) for chunk in chunks]

    # Deduplicate within the current batch first
    unique_chunks_map = {}  # chunk_id -> (original_index, chunk_content)
    for i, (chunk, chunk_id) in enumerate(zip(chunks, chunk_ids)):
        if chunk_id not in unique_chunks_map:
            unique_chunks_map[chunk_id] = (i, chunk)

    unique_chunk_ids = list(unique_chunks_map.keys())

    # Check which chunks already exist in ChromaDB
    existing = set()
    if len(unique_chunk_ids) > 0:
        try:
            collection = get_collection()
            get_res = collection.get(ids=unique_chunk_ids)
        except Exception as exc:
            print(
                f"Warning: unable to query existing chunk IDs from Chroma ({exc}). Treating all as new."
            )
            get_res = None
        if get_res and "ids" in get_res:
            existing = set(get_res["ids"])

    # Find chunks that need embedding
    to_embed = []
    for chunk_id, (original_idx, chunk_content) in unique_chunks_map.items():
        if chunk_id not in existing:
            to_embed.append((original_idx, chunk_content))

    if not to_embed:
        print(
            "All chunks for this file already exist in ChromaDB. No embeddings needed."
        )
        return [], []

    # Extract chunks that need embedding
    embed_indices, chunks_to_embed = zip(*to_embed)
    embed_indices = list(embed_indices)
    chunks_to_embed = list(chunks_to_embed)

   

    # Compute embeddings only for new chunks
    global _model
    if _model is None:
        _model = ONNXEmbeddingModel()

    embeddings = _model.encode_document(chunks_to_embed)

    return embeddings.tolist(), embed_indices
