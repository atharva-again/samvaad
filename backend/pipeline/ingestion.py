from utils.filehash_db import chunk_exists, add_chunk
from utils.hashing import generate_file_id, generate_chunk_id
import fitz  # PyMuPDF
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
    """
    text = ""
    error = None
    if filename.lower().endswith(".pdf") or content_type == "application/pdf":
        try:
            with fitz.open(stream=contents, filetype="pdf") as doc:
                text = "\n".join(page.get_text() for page in doc)
        except Exception as e:
            error = f"PDF parsing error: {e}"
    elif filename.lower().endswith(".txt") or content_type.startswith("text/"):
        try:
            text = contents.decode("utf-8")
        except Exception as e:
            error = f"Text parsing error: {e}"
    else:
        error = "Unsupported file type. Only PDF and text files are supported."
    return text, error


def chunk_text(text: str, chunk_size: int = 200) -> List[str]:
    """
    Split text into chunks using recursive character text splitter.
    Uses separators in order: ["\n\n", "\n", ".", "?", "!", " ", ""]
    Chunk size: 200 characters, no overlaps.
    """
    separators = ["\n\n", "\n", ".", "?", "!", " ", ""]
    
    def split_text_recursive(text: str, separators: List[str]) -> List[str]:
        """Recursively split text using the provided separators."""
        if not text.strip():
            return []
        
        # If text is already small enough, return it
        if len(text) <= chunk_size:
            return [text.strip()] if text.strip() else []
        
        # Try each separator in order
        for separator in separators:
            if separator in text:
                splits = text.split(separator)
                result = []
                current_chunk = ""
                
                for split in splits:
                    # Add separator back except for empty string separator
                    split_with_sep = split + (separator if separator != "" else "")
                    
                    # If adding this split would exceed chunk size
                    if len(current_chunk) + len(split_with_sep) > chunk_size:
                        # Save current chunk if it has content
                        if current_chunk.strip():
                            result.append(current_chunk.strip())
                        
                        # If this split is still too large, recursively split it
                        if len(split_with_sep) > chunk_size:
                            # Remove the separator we just added for recursive call
                            split_for_recursion = split if separator != "" else split_with_sep
                            recursive_splits = split_text_recursive(split_for_recursion, separators[separators.index(separator)+1:])
                            result.extend(recursive_splits)
                            current_chunk = ""
                        else:
                            current_chunk = split_with_sep
                    else:
                        current_chunk += split_with_sep
                
                # Add any remaining content
                if current_chunk.strip():
                    result.append(current_chunk.strip())
                
                return result
        
        # If no separators worked, force split at chunk_size
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks
    
    return split_text_recursive(text, separators)



