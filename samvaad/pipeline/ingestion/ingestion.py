"""
Ingestion pipeline module for processing files into the RAG system.
This module encapsulates the common ingestion logic used by test.py and main.py.
"""

import os
from samvaad.pipeline.ingestion.chunking import parse_file, chunk_text, find_new_chunks, update_chunk_file_db
from samvaad.pipeline.ingestion.embedding import embed_chunks_with_dedup
from samvaad.pipeline.vectorstore.vectorstore import add_embeddings
from samvaad.pipeline.ingestion.preprocessing import preprocess_file
from samvaad.utils.hashing import generate_file_id
from samvaad.utils.filehash_db import add_file


def ingest_file_pipeline(filename, content_type, contents):
    """
    Process a file: parse, chunk, embed, and store in the database.
    
    Args:
        filename (str): Name of the file.
        content_type (str): MIME type of the file.
        contents (bytes): Raw file contents.
    
    Returns:
        dict: Result containing processing details and any errors.
    """
    # Generate file ID
    file_id = generate_file_id(contents)
    
    # Preprocessing: check for duplicates
    if preprocess_file(contents, filename):
        return {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(contents),
            "num_chunks": 0,
            "new_chunks_embedded": 0,
            "chunk_preview": [],
            "error": "File already processed",
        }
    
    # Parse the file
    text, error = parse_file(filename, content_type, contents)
    if error:
        return {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(contents),
            "num_chunks": 0,
            "new_chunks_embedded": 0,
            "chunk_preview": [],
            "error": error,
        }
    
    # Chunk the text
    chunks = chunk_text(text)
    
    # Find new chunks after deduplication
    new_chunks = find_new_chunks(chunks, file_id)
    
    if not new_chunks:
        return {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(contents),
            "num_chunks": len(chunks),
            "new_chunks_embedded": 0,
            "chunk_preview": chunks[:3],
            "error": "No new chunks to process",
        }
    
    # Extract chunk texts for embedding
    chunks_to_embed = [chunk for chunk, chunk_id in new_chunks]
    
    # Embed chunks with deduplication
    embeddings, embed_indices = embed_chunks_with_dedup(chunks_to_embed, filename=filename)
    
    if not embeddings:
        return {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(contents),
            "num_chunks": len(chunks),
            "new_chunks_embedded": 0,
            "chunk_preview": chunks[:3],
            "error": "No new embeddings",
        }
    
    # Store embeddings in ChromaDB (store only basename in metadata)
    new_chunks_to_store = [chunks_to_embed[i] for i in embed_indices]
    new_metadatas = [{"filename": os.path.basename(filename), "chunk_id": chunk_id, "file_id": file_id} for chunk, chunk_id in new_chunks]
    add_embeddings(new_chunks_to_store, embeddings, new_metadatas, filename=os.path.basename(filename))
    
    # Update file metadata (store only basename, not full path)
    add_file(file_id, os.path.basename(filename))
    
    # Update chunk-file mapping
    update_chunk_file_db(chunks, file_id)
    
    return {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(contents),
        "num_chunks": len(chunks),
        "new_chunks_embedded": len(embeddings),
        "chunk_preview": chunks[:3],
        "error": None,
    }