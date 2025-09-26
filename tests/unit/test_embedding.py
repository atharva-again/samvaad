import pytest
from unittest.mock import patch, MagicMock

# Import modules to test
from backend.pipeline.embedding import embed_chunks_with_dedup


@pytest.fixture(autouse=True)
def reset_embedding_model():
    """Reset global embedding model between tests."""
    import backend.pipeline.embedding
    backend.pipeline.embedding._model = None


class TestEmbedding:
    """Test embedding functions."""

    @patch('backend.pipeline.embedding.collection')
    @patch('backend.pipeline.embedding.SentenceTransformer')
    @patch('backend.pipeline.embedding.get_device')
    @patch('backend.pipeline.embedding.generate_chunk_id')  # Mock for full isolation
    @patch('builtins.print')  # Suppress print statements
    def test_embed_chunks_with_dedup_all_new(self, mock_print, mock_generate_id, mock_get_device, mock_model_class, mock_collection):
        """Test embedding chunks when all are new."""
        # Mock chunk ID generation for predictable testing
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        mock_get_device.return_value = 'cpu'
        mock_model = MagicMock()
        # Mock numpy array with tolist() method
        mock_embeddings = MagicMock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_model.encode.return_value = mock_embeddings
        mock_model_class.return_value = mock_model

        mock_collection.get.return_value = {"ids": []}  # No existing chunks

        chunks = ["chunk1", "chunk2"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        assert len(embeddings) == 2
        assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
        assert indices == [0, 1]
        mock_model.encode.assert_called_once()
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 2

    @patch('backend.pipeline.embedding.collection')
    @patch('backend.pipeline.embedding.generate_chunk_id')  # Mock for full isolation
    @patch('builtins.print')  # Suppress print statements
    def test_embed_chunks_with_dedup_all_existing(self, mock_print, mock_generate_id, mock_collection):
        """Test embedding chunks when all already exist."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        # Mock collection to return the hashes that will be generated
        mock_collection.get.return_value = {"ids": ["chunk1_hash", "chunk2_hash"]}

        chunks = ["chunk1", "chunk2"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        assert embeddings == []
        assert indices == []
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 2

    @patch('backend.pipeline.embedding.collection')
    @patch('backend.pipeline.embedding.SentenceTransformer')
    @patch('backend.pipeline.embedding.get_device')
    @patch('backend.pipeline.embedding.generate_chunk_id')
    @patch('builtins.print')
    def test_embed_chunks_handles_collection_failure(self, mock_print, mock_generate_id, mock_get_device, mock_model_class, mock_collection):
        """If collection.get fails we should still embed new chunks."""
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        mock_collection.get.side_effect = RuntimeError("store unavailable")

        mock_get_device.return_value = 'cpu'
        mock_model = MagicMock()
        mock_embeddings = MagicMock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2]]
        mock_model.encode.return_value = mock_embeddings
        mock_model_class.return_value = mock_model

        chunks = ["chunk1"]

        embeddings, indices = embed_chunks_with_dedup(chunks, "test.txt")

        assert embeddings == [[0.1, 0.2]]
        assert indices == [0]
        mock_model.encode.assert_called_once()
        mock_generate_id.assert_called_once_with("chunk1")
        mock_print.assert_called()

    @patch('backend.pipeline.embedding.collection')
    @patch('backend.pipeline.embedding.SentenceTransformer')
    @patch('backend.pipeline.embedding.get_device')
    @patch('backend.pipeline.embedding.generate_chunk_id')  # Mock for full isolation
    @patch('builtins.print')  # Suppress print statements
    def test_embed_chunks_with_dedup_mixed_new_existing(self, mock_print, mock_generate_id, mock_get_device, mock_model_class, mock_collection):
        """Test embedding chunks when some are new and some already exist."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        mock_get_device.return_value = 'cpu'
        mock_model = MagicMock()
        # Mock numpy array with tolist() method - only 2 embeddings since only 2 chunks are new
        mock_embeddings = MagicMock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_model.encode.return_value = mock_embeddings
        mock_model_class.return_value = mock_model

        # Mock collection to show chunk2 already exists
        mock_collection.get.return_value = {"ids": ["chunk2_hash"]}

        chunks = ["chunk1", "chunk2", "chunk3"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        # Should return embeddings for chunk1 and chunk3 only
        assert len(embeddings) == 2
        assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
        # Should return indices [0, 2] for the positions of chunk1 and chunk3
        assert indices == [0, 2]
        mock_model.encode.assert_called_once()
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 3

    @patch('backend.pipeline.embedding.collection')
    @patch('backend.pipeline.embedding.SentenceTransformer')
    @patch('backend.pipeline.embedding.get_device')
    @patch('backend.pipeline.embedding.generate_chunk_id')  # Mock for full isolation
    @patch('builtins.print')  # Suppress print statements
    def test_embed_chunks_with_dedup_internal_deduplication(self, mock_print, mock_generate_id, mock_get_device, mock_model_class, mock_collection):
        """Test internal deduplication within the batch."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        mock_get_device.return_value = 'cpu'
        mock_model = MagicMock()
        # Mock numpy array with tolist() method - only 2 embeddings since only 2 unique chunks
        mock_embeddings = MagicMock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_model.encode.return_value = mock_embeddings
        mock_model_class.return_value = mock_model

        # Mock collection to return no existing chunks
        mock_collection.get.return_value = {"ids": []}

        # Provide chunks with duplicates within the batch
        chunks = ["same_chunk", "different_chunk", "same_chunk"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        # Should return embeddings for only 2 unique chunks
        assert len(embeddings) == 2
        assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
        # Should return indices for first occurrence of each unique chunk
        assert indices == [0, 1]  # "same_chunk" at index 0, "different_chunk" at index 1
        mock_model.encode.assert_called_once()
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 3

    @patch('backend.pipeline.embedding.collection')
    @patch('backend.pipeline.embedding.SentenceTransformer')
    @patch('backend.pipeline.embedding.get_device')
    @patch('backend.pipeline.embedding.generate_chunk_id')  # Mock for full isolation
    @patch('builtins.print')  # Suppress print statements
    def test_embed_chunks_model_reuse(self, mock_print, mock_generate_id, mock_get_device, mock_model_class, mock_collection):
        """Test that the model is reused across multiple calls."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        mock_get_device.return_value = 'cpu'
        mock_model = MagicMock()
        mock_embeddings = MagicMock()
        mock_embeddings.tolist.return_value = [[0.1, 0.2]]
        mock_model.encode.return_value = mock_embeddings
        mock_model_class.return_value = mock_model

        # Mock collection to return no existing chunks for both calls
        mock_collection.get.return_value = {"ids": []}

        # First call
        chunks1 = ["chunk1"]
        embeddings1, indices1 = embed_chunks_with_dedup(chunks1, "test1.txt")

        # Second call
        chunks2 = ["chunk2"]
        embeddings2, indices2 = embed_chunks_with_dedup(chunks2, "test2.txt")

        # SentenceTransformer should only be instantiated once due to model reuse
        assert mock_model_class.call_count == 1
        # But encode should be called twice
        assert mock_model.encode.call_count == 2

        assert embeddings1 == [[0.1, 0.2]]
        assert embeddings2 == [[0.1, 0.2]]
        assert indices1 == [0]
        assert indices2 == [0]
        # Verify generate_chunk_id was called for each chunk in each call
        assert mock_generate_id.call_count == 2