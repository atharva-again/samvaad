from utils.filehash_db import chunk_exists, add_chunk
from utils.hashing import generate_file_id, generate_chunk_id
from .docling_wrapper import get_docling_converter, get_docling_chunker
from typing import Tuple, List

def find_new_chunks(chunks, file_id):
    """
    For each chunk, check deduplication.
    Returns a list of (chunk, chunk_id) that are new for this file.
    """
    new_chunks = []
    seen_in_batch = set()  # Track IDs already seen in this batch
    
    for chunk in chunks:
        chunk_id = generate_chunk_id(chunk)
        
        # Skip if we've already seen this chunk_id in this batch
        if chunk_id in seen_in_batch:
            continue
            
        # Check if chunk exists globally (not per file)
        if not chunk_exists(chunk_id):
            new_chunks.append((chunk, chunk_id))
            seen_in_batch.add(chunk_id)
    return new_chunks

def update_chunk_file_db(new_chunks, file_id):
    """
    Add new (chunk_id, file_id) pairs to the DB.
    Returns a list of (chunk, chunk_id) that were newly added.
    """
    
    for chunk in new_chunks:
        # chunk may be a string or a tuple (chunk, chunk_id)
        if isinstance(chunk, tuple):
            chunk_id = chunk[1]
        else:
            chunk_id = generate_chunk_id(chunk)
        # Only add the (chunk_id, file_id) mapping if it doesn't exist
        if not chunk_exists(chunk_id, file_id):
            add_chunk(chunk_id, file_id)
    return new_chunks


def parse_file(filename: str, content_type: str, contents: bytes) -> Tuple[str, str]:
    """
    Parse PDF or text file contents and return extracted text and error (if any).
    Uses Docling for PDF parsing and maintains .txt file support.
    """
    text = ""
    error = None
    
    if filename.lower().endswith(".pdf") or content_type == "application/pdf":
        # Use Docling for PDF parsing
        try:
            converter = get_docling_converter()
            text, error = converter.convert_pdf(contents)
        except Exception as e:
            error = f"Docling PDF parsing error: {e}"
    elif filename.lower().endswith(".txt") or content_type.startswith("text/"):
        # Keep existing text file support
        try:
            text = contents.decode("utf-8")
        except Exception as e:
            error = f"Text parsing error: {e}"
    else:
        error = "Unsupported file type. Only PDF and text files are supported."
    
    return text, error


def chunk_text(text: str, chunk_size: int = 200) -> List[str]:
    """
    Split text into chunks using Docling's hierarchical chunker.
    Uses hierarchical separators with token-based splitting.
    Chunk size: 200 tokens, no overlaps.
    """
    chunker = get_docling_chunker(chunk_size=chunk_size)
    return chunker.chunk_text(text)



