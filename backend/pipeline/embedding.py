from typing import List, Tuple
from sentence_transformers import SentenceTransformer
from pipeline.vectorstore import collection
from pipeline.vectorstore import generate_chunk_id

# Use BGE-M3: strong English + multilingual support
_MODEL_NAME = "BAAI/bge-m3"
_INSTRUCTION = "Represent this sentence for retrieval: "

# Global model instance to avoid reloading
_model = None

def embed_chunks_with_dedup(chunks: List[str], filename: str = None) -> Tuple[List[List[float]], List[int]]:
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
        get_res = collection.get(ids=unique_chunk_ids)
        if get_res and "ids" in get_res:
            existing = set(get_res["ids"])
    
    # Find chunks that need embedding
    to_embed = []
    for chunk_id, (original_idx, chunk_content) in unique_chunks_map.items():
        if chunk_id not in existing:
            to_embed.append((original_idx, chunk_content))
    
    if not to_embed:
        print("All chunks for this file already exist in ChromaDB. No embeddings needed.")
        return [], []
    
    # Extract chunks that need embedding
    embed_indices, chunks_to_embed = zip(*to_embed)
    embed_indices = list(embed_indices)
    chunks_to_embed = list(chunks_to_embed)
    
    print(f"Embedding {len(chunks_to_embed)} new chunks out of {len(chunks)} total chunks.")
    
    # Compute embeddings only for new chunks
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    
    inputs = [_INSTRUCTION + chunk for chunk in chunks_to_embed]
    embeddings = _model.encode(inputs, show_progress_bar=True, convert_to_numpy=True)
    
    return embeddings.tolist(), embed_indices
