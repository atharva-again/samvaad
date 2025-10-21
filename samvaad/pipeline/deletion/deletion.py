"""
delete a file and its embeddings from both metadata tables and ChromaDB
"""
from samvaad.utils.filehash_db import delete_file_and_cleanup
from samvaad.utils.hashing import generate_file_id
from samvaad.pipeline.vectorstore.vectorstore import get_collection


def delete_file_and_embeddings(file_path: str):
    """
    Deletes file metadata and all unique embeddings for the file from ChromaDB.
    Returns the list of deleted chunk IDs.
    """
    with open(file_path, "rb") as f:
        contents = f.read()
    file_id = generate_file_id(contents)
    orphaned_chunks = delete_file_and_cleanup(file_id)
    if orphaned_chunks:
        collection = get_collection()
        collection.delete(ids=orphaned_chunks)
    return orphaned_chunks
