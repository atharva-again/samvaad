import chromadb
import pytest
from unittest.mock import patch

from samvaad.pipeline.ingestion.chunking import find_new_chunks, update_chunk_file_db
from samvaad.pipeline.vectorstore import vectorstore
from samvaad.utils import filehash_db, hashing


@pytest.mark.integration
def test_ingestion_persists_across_restart(tmp_path, monkeypatch):
    """Ensure chunk metadata and embeddings persist across client restarts."""
    # Point the hash database to a temporary location and initialise schema
    db_path = tmp_path / "filehashes.sqlite3"
    monkeypatch.setattr(filehash_db, "DB_PATH", str(db_path))
    filehash_db.init_db()

    # Use a temporary persistent directory for Chroma
    chroma_path = tmp_path / "chroma"
    try:
        client = chromadb.PersistentClient(path=str(chroma_path))
    except Exception as exc:
        pytest.skip(f"ChromaDB not available in test environment: {exc}")
    collection = client.get_or_create_collection("documents")
    monkeypatch.setattr(vectorstore, "_client", client)
    monkeypatch.setattr(vectorstore, "_collection", collection)

    # Simulate ingestion of a single chunk
    raw_bytes = b"Persistence test payload"
    filename = "persistence.txt"
    file_id = hashing.generate_file_id(raw_bytes)
    chunk_text = "This chunk should be queryable after restart."

    filehash_db.add_file(file_id, filename)
    new_chunks = find_new_chunks([chunk_text], file_id)
    assert new_chunks, "Expected the first chunk to be marked as new."
    update_chunk_file_db(new_chunks, file_id)

    chunk_id = new_chunks[0][1]
    embeddings = [[0.1] * 768]
    metadatas = [{"filename": filename, "chunk_id": chunk_id}]

    # Mock generate_chunk_id to return the consistent chunk_id
    with patch('samvaad.pipeline.vectorstore.vectorstore.generate_chunk_id', return_value=chunk_id):
        vectorstore.add_embeddings([chunk_text], embeddings, metadatas, filename)

    # Verify the data is queryable immediately
    stored = collection.get(ids=[chunk_id])
    assert stored["ids"] == [chunk_id]
    assert filehash_db.file_exists(file_id)
    assert filehash_db.chunk_exists(chunk_id, file_id)

    # Simulate a new process by creating a fresh client against the same path
    restarted_client = chromadb.PersistentClient(path=str(chroma_path))
    restarted_collection = restarted_client.get_or_create_collection("documents")
    stored_after_restart = restarted_collection.get(ids=[chunk_id])
    assert stored_after_restart["ids"] == [chunk_id]

    # Adding the same chunk again should be a no-op because of deduplication
    with patch('samvaad.pipeline.vectorstore.vectorstore.generate_chunk_id', return_value=chunk_id):
        vectorstore.add_embeddings([chunk_text], embeddings, metadatas, filename)
    dedup_check = restarted_collection.get(ids=[chunk_id])
    assert dedup_check["ids"] == [chunk_id]
