"""
Delete a file and its embeddings using the DBService (pgvector in Supabase).
"""

from samvaad.db.service import DBService


def delete_file_by_id(file_id: str, user_id: str) -> bool:
    """
    Delete a file by ID for a specific user.
    Uses DBService which handles cleanup of orphaned chunks automatically.
    
    Returns True if successful, False otherwise.
    """
    return DBService.delete_file(file_id, user_id)
