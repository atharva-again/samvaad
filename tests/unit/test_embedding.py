import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from numpy.testing import assert_allclose

# Import modules to test
from samvaad.pipeline.ingestion.embedding import (
    embed_chunks_with_dedup,
    ONNXEmbeddingModel,
)


@pytest.fixture(autouse=True)
def reset_embedding_model():
    """Reset global embedding model between tests."""
    import samvaad.pipeline.ingestion.embedding

    samvaad.pipeline.ingestion.embedding._model = None


class TestEmbedding:
    """Test embedding functions."""

    @patch("samvaad.pipeline.vectorstore.vectorstore.get_collection")
    @patch("samvaad.pipeline.ingestion.embedding.ONNXEmbeddingModel")
    @patch(
        "samvaad.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_with_dedup_all_new(
        self,
        mock_print,
        mock_generate_id,
        mock_model_class,
        mock_get_collection,
    ):
        """Test embedding chunks when all are new."""
        # Mock chunk ID generation for predictable testing
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2], [0.3, 0.4]], dtype=np.float32
        )
        mock_model_class.return_value = mock_model

        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}  # No existing chunks
        mock_get_collection.return_value = mock_collection

        chunks = ["chunk1", "chunk2"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        assert len(embeddings) == 2
        assert_allclose(embeddings, [[0.1, 0.2], [0.3, 0.4]], rtol=1e-5)
        assert indices == [0, 1]
        mock_model.encode_document.assert_called_once()
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 2

    @patch("samvaad.pipeline.ingestion.embedding.get_collection")
    @patch(
        "samvaad.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_with_dedup_all_existing(
        self, mock_print, mock_generate_id, mock_get_collection
    ):
        """Test embedding chunks when all already exist."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        # Mock collection to return the hashes that will be generated
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["chunk1_hash", "chunk2_hash"]}
        mock_get_collection.return_value = mock_collection

        chunks = ["chunk1", "chunk2"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        assert embeddings == []
        assert indices == []
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 2

    @patch("samvaad.pipeline.ingestion.embedding.get_collection")
    @patch("samvaad.pipeline.ingestion.embedding.ONNXEmbeddingModel")
    @patch("samvaad.pipeline.ingestion.embedding.generate_chunk_id")
    @patch("builtins.print")
    def test_embed_chunks_handles_collection_failure(
        self,
        mock_print,
        mock_generate_id,
        mock_model_class,
        mock_get_collection,
    ):
        """If collection.get fails we should still embed new chunks."""
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        
        mock_collection = MagicMock()
        mock_collection.get.side_effect = RuntimeError("store unavailable")
        mock_get_collection.return_value = mock_collection

        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2]], dtype=np.float32
        )
        mock_model_class.return_value = mock_model

        chunks = ["chunk1"]

        embeddings, indices = embed_chunks_with_dedup(chunks, "test.txt")

        assert_allclose(embeddings, [[0.1, 0.2]], rtol=1e-5)
        assert indices == [0]
        mock_model.encode_document.assert_called_once()
        mock_generate_id.assert_called_once_with("chunk1")
        mock_print.assert_called()

    @patch("samvaad.pipeline.ingestion.embedding.get_collection")
    @patch("samvaad.pipeline.ingestion.embedding.ONNXEmbeddingModel")
    @patch(
        "samvaad.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_with_dedup_mixed_new_existing(
        self,
        mock_print,
        mock_generate_id,
        mock_model_class,
        mock_get_collection,
    ):
        """Test embedding chunks when some are new and some already exist."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2], [0.3, 0.4]], dtype=np.float32
        )
        mock_model_class.return_value = mock_model

        # Mock collection to show chunk2 already exists
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["chunk2_hash"]}
        mock_get_collection.return_value = mock_collection

        chunks = ["chunk1", "chunk2", "chunk3"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        # Should return embeddings for chunk1 and chunk3 only
        assert len(embeddings) == 2
        assert_allclose(embeddings, [[0.1, 0.2], [0.3, 0.4]], rtol=1e-5)
        # Should return indices [0, 2] for the positions of chunk1 and chunk3
        assert indices == [0, 2]
        mock_model.encode_document.assert_called_once()
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 3

    @patch("samvaad.pipeline.ingestion.embedding.get_collection")
    @patch("samvaad.pipeline.ingestion.embedding.ONNXEmbeddingModel")
    @patch(
        "samvaad.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_with_dedup_internal_deduplication(
        self,
        mock_print,
        mock_generate_id,
        mock_model_class,
        mock_get_collection,
    ):
        """Test internal deduplication within the batch."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2], [0.3, 0.4]], dtype=np.float32
        )
        mock_model_class.return_value = mock_model

        # Mock collection to return no existing chunks
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_get_collection.return_value = mock_collection

        # Provide chunks with duplicates within the batch
        chunks = ["same_chunk", "different_chunk", "same_chunk"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        # Should return embeddings for only 2 unique chunks
        assert len(embeddings) == 2
        assert_allclose(embeddings, [[0.1, 0.2], [0.3, 0.4]], rtol=1e-5)
        # Should return indices for first occurrence of each unique chunk
        assert indices == [
            0,
            1,
        ]  # "same_chunk" at index 0, "different_chunk" at index 1
        mock_model.encode_document.assert_called_once()
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 3

    @patch("samvaad.pipeline.ingestion.embedding.get_collection")
    @patch("samvaad.pipeline.ingestion.embedding.ONNXEmbeddingModel")
    @patch(
        "samvaad.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_model_reuse(
        self,
        mock_print,
        mock_generate_id,
        mock_model_class,
        mock_get_collection,
    ):
        """Test that the model is reused across multiple calls."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2]], dtype=np.float32
        )
        mock_model_class.return_value = mock_model

        # Mock collection to return no existing chunks for both calls
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_get_collection.return_value = mock_collection

        # First call
        chunks1 = ["chunk1"]
        embeddings1, indices1 = embed_chunks_with_dedup(chunks1, "test1.txt")

        # Second call
        chunks2 = ["chunk2"]
        embeddings2, indices2 = embed_chunks_with_dedup(chunks2, "test2.txt")

        # SentenceTransformer should only be instantiated once due to model reuse
        assert mock_model_class.call_count == 1
        # But encode should be called twice
        assert mock_model.encode_document.call_count == 2

        assert_allclose(embeddings1, [[0.1, 0.2]], rtol=1e-5)
        assert_allclose(embeddings2, [[0.1, 0.2]], rtol=1e-5)
        assert indices1 == [0]
        assert indices2 == [0]
        # Verify generate_chunk_id was called for each chunk in each call
        assert mock_generate_id.call_count == 2


class TestEmbeddingErrorHandling:
    """Test error handling in embedding functions."""

    @patch("samvaad.pipeline.ingestion.embedding.get_collection")
    @patch("samvaad.pipeline.ingestion.embedding.ONNXEmbeddingModel")
    @patch("samvaad.pipeline.ingestion.embedding.generate_chunk_id")
    @patch("builtins.print")
    def test_embed_chunks_model_initialization_failure(
        self, mock_print, mock_generate_id, mock_model_class, mock_get_collection
    ):
        """Test handling of model initialization failure."""
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        mock_model_class.side_effect = Exception("Model download failed")
        
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_get_collection.return_value = mock_collection
        
        chunks = ["chunk1"]
        
        with pytest.raises(Exception, match="Model download failed"):
            embed_chunks_with_dedup(chunks, "test.txt")
    
    @patch("samvaad.pipeline.ingestion.embedding.get_collection")
    @patch("samvaad.pipeline.ingestion.embedding.ONNXEmbeddingModel")
    @patch("samvaad.pipeline.ingestion.embedding.generate_chunk_id")
    @patch("builtins.print")
    def test_embed_chunks_empty_input(
        self, mock_print, mock_generate_id, mock_model_class, mock_get_collection
    ):
        """Test handling of empty chunk list."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_get_collection.return_value = mock_collection
        
        chunks = []
        
        embeddings, indices = embed_chunks_with_dedup(chunks, "test.txt")
        
        assert embeddings == []
        assert indices == []
        mock_model.encode_document.assert_not_called()
    
    @patch("samvaad.pipeline.ingestion.embedding.get_collection")
    @patch("samvaad.pipeline.ingestion.embedding.ONNXEmbeddingModel")
    @patch("samvaad.pipeline.ingestion.embedding.generate_chunk_id")
    @patch("builtins.print")
    def test_embed_chunks_encoding_failure(
        self, mock_print, mock_generate_id, mock_model_class, mock_get_collection
    ):
        """Test handling of encoding failure."""
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        mock_model = MagicMock()
        mock_model.encode_document.side_effect = Exception("ONNX Runtime error")
        mock_model_class.return_value = mock_model
        
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_get_collection.return_value = mock_collection
        
        chunks = ["chunk1"]
        
        with pytest.raises(Exception, match="ONNX Runtime error"):
            embed_chunks_with_dedup(chunks, "test.txt")
