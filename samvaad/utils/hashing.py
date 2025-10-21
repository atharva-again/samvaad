"""
Centralized hashing functions for file and chunk IDs
"""
import hashlib


def generate_file_id(file_bytes: bytes) -> str:
    """Generate SHA256 hash of file contents (bytes) as file ID."""
    return hashlib.sha256(file_bytes).hexdigest()


def generate_chunk_id(chunk_content: str) -> str:
    """Generate SHA256 hash of chunk content (string) as chunk ID."""
    return hashlib.sha256(chunk_content.encode('utf-8')).hexdigest()
