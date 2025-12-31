"""
Ingestion pipeline module for processing files into the RAG system.
This module encapsulates the common ingestion logic used by test.py and main.py.
"""

import os
import time

from samvaad.db.service import DBService
from samvaad.pipeline.ingestion.chunking import (
    parse_file,
    structural_chunk,
)
from samvaad.pipeline.ingestion.embedding import generate_embeddings
from samvaad.utils.hashing import generate_file_id


def ingest_file_pipeline(filename, content_type, contents, user_id: str = None):
    """
    Process a file: parse, chunk, embed, and store in the database.

    Args:
        filename (str): Name of the file.
        content_type (str): MIME type of the file.
        contents (bytes): Raw file contents.

    Returns:
        dict: Result containing processing details and any errors.
    """
    return ingest_file_pipeline_with_progress(filename, content_type, contents, user_id=user_id)


def ingest_file_pipeline_with_progress(
    filename, content_type, contents, progress_callback=None, user_id: str = None
):
    """
    Process a file: parse, chunk, embed, and store in the database with progress reporting.

    Args:
        filename (str): Name of the file.
        content_type (str): MIME type of the file.
        contents (bytes): Raw file contents.
        progress_callback (callable): Optional callback for progress updates.

    Returns:
        dict: Result containing processing details and any errors.
    """

    def progress(step: str, current: int = None, total: int = None):
        if progress_callback:
            progress_callback(step, current, total)

    # Generate file ID / Hash
    progress("Checking for duplicates...")
    content_hash = generate_file_id(contents)

    # 1. Check if content exists globally
    if DBService.check_content_exists(content_hash):
        print(f"Content hash {content_hash} exists globally. Linking to user {user_id}.")
        result = DBService.link_existing_content(user_id, filename, content_hash)

        progress("File linked successfully!", 100, 100)
        return {
            "file_id": result.get("file_id"), # Critical for Frontend
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(contents),
            "num_chunks": 0,
            "new_chunks_embedded": 0,
            "chunk_preview": [],
            "error": None,
            "status": "linked"
        }

    # 2. Check if user already has this specific file (Wait, logic in UI handles this, but backend safety ok)
    # The global check above handles the 'content' check.
    # If user uploads same content with diff name -> linked.
    # If user uploads same content same name -> linked (and duplication in UI sources list? Allowed).

    # Parse the file
    progress("Parsing file...")
    pages, error = parse_file(filename, content_type, contents)
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

    from samvaad.utils.hashing import generate_chunk_id

    # Chunk the text structurally
    progress("Chunking text based on structure...")
    chunks_obj = structural_chunk(pages)
    chunks = [c.content for c in chunks_obj]
    chunk_metadatas = [c.metadata for c in chunks_obj]

    if not chunks:
         return {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(contents),
            "num_chunks": 0,
            "new_chunks_embedded": 0,
            "chunk_preview": [],
            "error": "No text extracted",
        }

    # Smart Deduplication Logic
    progress("Checking chunk duplicates...")

    # 1. Calculate hashes for all chunks
    chunk_hashes = [generate_chunk_id(c) for c in chunks]

    # 2. Check which exist in DB
    existing_hashes = DBService.get_existing_chunk_hashes(chunk_hashes)

    # 3. Identify chunks that need embedding
    chunks_to_embed = [] # List of text
    chunks_to_embed_indices = [] # Indices to map back

    for i, h in enumerate(chunk_hashes):
        if h not in existing_hashes:
            chunks_to_embed.append(chunks[i])
            chunks_to_embed_indices.append(i)

    num_new = len(chunks_to_embed)
    num_skipped = len(chunks) - num_new
    print(f"Deduplication: {num_skipped} existing, {num_new} new chunks.")

    # 4. Embed only new chunks
    new_embeddings_map = {} # Hash -> Vector

    if num_new > 0:
        progress(f"Embedding {num_new} new chunks...", 0, num_new)
        embed_start_time = time.time()

        new_embeddings = generate_embeddings(chunks_to_embed)

        # Map back to hashes
        for idx_in_subset, embedding in enumerate(new_embeddings):
            original_idx = chunks_to_embed_indices[idx_in_subset]
            h = chunk_hashes[original_idx]
            new_embeddings_map[h] = embedding

        embed_end_time = time.time()
        print(
            f"Finished embedding {num_new} chunks in {embed_end_time - embed_start_time:.2f} sec."
        )
    else:
        progress("All chunks reused!", 100, 100)

    # Store in Postgres
    progress("Storing in database...")
    store_start_time = time.time()

    # Use the SMART method
    result = DBService.add_smart_dedup_content(
        filename=os.path.basename(filename),
        content=contents,
        chunks=chunks,
        chunk_hashes=chunk_hashes,
        new_embeddings_map=new_embeddings_map,
        user_id=user_id,
        chunk_metadatas=chunk_metadatas
    )

    store_end_time = time.time()
    print(
        f"Finished storing in Postgres in {store_end_time - store_start_time:.2f} sec."
    )

    return {
        "file_id": result.get("file_id"), # Critical for Frontend
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(contents),
        "num_chunks": len(chunks),
        "new_chunks_embedded": num_new,
        "chunk_preview": chunks[:3],
        "error": None,
    }
