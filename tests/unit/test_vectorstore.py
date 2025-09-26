import pytest
from unittest.mock import patch, MagicMock

# Import modules to test
from backend.pipeline.vectorstore import add_embeddings, query_embedding


class TestVectorstore:
    """Test vectorstore functions."""

    @patch('backend.pipeline.vectorstore.collection')
    @patch('backend.pipeline.vectorstore.generate_chunk_id')
    def test_add_embeddings_no_duplicates(self, mock_generate_id, mock_collection):
        """Test adding embeddings with no duplicates."""
        # Mock chunk ID generation for predictable testing
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        mock_collection.get.return_value = {"ids": []}  # No existing

        chunks = ["chunk1", "chunk2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        metadatas = [{"filename": "test.txt"}, {"filename": "test.txt"}]

        add_embeddings(chunks, embeddings, metadatas)

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert len(call_args[1]['embeddings']) == 2
        # Verify the correct IDs were used
        assert call_args[1]['ids'] == ["chunk1_hash", "chunk2_hash"]

    @patch('backend.pipeline.vectorstore.collection')
    @patch('backend.pipeline.vectorstore.generate_chunk_id')
    def test_add_embeddings_all_duplicates(self, mock_generate_id, mock_collection):
        """Test adding embeddings when all chunks are already duplicates."""
        # Mock chunk ID generation for predictable testing
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        mock_collection.get.return_value = {"ids": ["chunk1_hash", "chunk2_hash"]}  # All existing

        chunks = ["chunk1", "chunk2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        metadatas = [{"filename": "test.txt"}, {"filename": "test.txt"}]

        add_embeddings(chunks, embeddings, metadatas)

        # collection.add should not be called when all chunks are duplicates
        mock_collection.add.assert_not_called()

    @patch('backend.pipeline.vectorstore.collection')
    @patch('backend.pipeline.vectorstore.generate_chunk_id')
    def test_add_embeddings_mixed_duplicates(self, mock_generate_id, mock_collection):
        """Test adding embeddings when some chunks are new and some are duplicates."""
        # Mock chunk ID generation for predictable testing
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        # Mock collection to return only chunk2 as existing (chunk1 is new)
        mock_collection.get.return_value = {"ids": ["chunk2_hash"]}

        chunks = ["chunk1", "chunk2", "chunk3"]
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        metadatas = [{"filename": "test.txt"}, {"filename": "test.txt"}, {"filename": "test.txt"}]

        add_embeddings(chunks, embeddings, metadatas)

        # collection.add should be called once with only the new chunks
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        # Should only add chunk1 and chunk3 (indices 0 and 2)
        assert len(call_args[1]['embeddings']) == 2
        assert call_args[1]['documents'] == ["chunk1", "chunk3"]
        assert call_args[1]['ids'] == ["chunk1_hash", "chunk3_hash"]

    @patch('backend.pipeline.vectorstore.collection')
    @patch('backend.pipeline.vectorstore.generate_chunk_id')
    def test_add_embeddings_missing_metadata(self, mock_generate_id, mock_collection):
        """Test adding embeddings with missing or None metadata."""
        # Mock chunk ID generation for predictable testing
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        mock_collection.get.return_value = {"ids": []}  # No existing

        chunks = ["chunk1", "chunk2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        # Call without metadatas argument (defaults to None)

        add_embeddings(chunks, embeddings)

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        # Should generate default metadata when metadatas is None
        assert call_args[1]['metadatas'] == [{"dedup": True}, {"dedup": True}]

    @patch('backend.pipeline.vectorstore.collection')
    def test_query_embedding(self, mock_collection):
        """Test querying embeddings."""
        mock_collection.query.return_value = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"filename": "test.txt"}, {"filename": "test.txt"}]],
            "distances": [[0.1, 0.2]]
        }

        query_emb = [0.1, 0.2]
        results = query_embedding(query_emb, top_k=2)

        assert len(results) == 2
        assert results[0]['document'] == "doc1"
        assert results[0]['distance'] == 0.1