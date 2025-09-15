import chromadb
from utils.hashing import generate_chunk_id

# Initialize ChromaDB persistent client and collection
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("documents")

def add_embeddings(chunks, embeddings, metadatas=None, filename=None):
    """
    Add text chunks and their embeddings to ChromaDB, avoiding duplicates by content-based chunk IDs.
    filename: should be a string (e.g., file path or name) to uniquely identify the source file.
    """
    if filename is None:
        filename = "unknown"
    
    # Generate content-based IDs instead of position-based
    ids = [generate_chunk_id(chunk) for chunk in chunks]

    # Deduplication: check which IDs already exist
    existing = set()
    if len(ids) > 0:
        # ChromaDB allows batch get by IDs
        get_res = collection.get(ids=ids)
        if get_res and "ids" in get_res:
            existing = set(get_res["ids"])

    # Only add chunks/embeddings/metadata for IDs not already present
    to_add = [(i, id_) for i, id_ in enumerate(ids) if id_ not in existing]
    if not to_add:
        print("All chunks for this file are already in ChromaDB. Skipping add.")
        return
    # Extract indices and ids
    add_idxs, add_ids = zip(*to_add)
    add_idxs = list(add_idxs)
    add_ids = list(add_ids)
    
    add_chunks = [chunks[i] for i in add_idxs]
    add_embeddings_ = [embeddings[i] for i in add_idxs]
    
    # Robustly filter metadatas to match add_idxs
    if metadatas and isinstance(metadatas, list) and len(metadatas) == len(chunks):
        add_metadatas = [metadatas[i] for i in add_idxs]
    else:
        add_metadatas = [{"dedup": True} for _ in add_chunks]

    # All lists must be the same length
    assert len(add_ids) == len(add_chunks) == len(add_embeddings_) == len(add_metadatas), (
        f"add_ids: {len(add_ids)}, add_chunks: {len(add_chunks)}, add_embeddings_: {len(add_embeddings_)}, add_metadatas: {len(add_metadatas)}"
    )
    
    collection.add(
        embeddings=add_embeddings_,
        documents=add_chunks,
        metadatas=add_metadatas,
        ids=add_ids
    )

def query_embedding(query_embedding, top_k=3):
    """
    Query ChromaDB for the most similar chunks to the query embedding.
    Returns: List of dicts with 'document', 'metadata', and 'distance'.
    """
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return [
        {
            "document": doc,
            "metadata": meta,
            "distance": dist
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]
