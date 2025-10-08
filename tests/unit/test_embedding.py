import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from numpy.testing import assert_allclose

# Import modules to test
from backend.pipeline.ingestion.embedding import (
    embed_chunks_with_dedup,
    GGUFEmbeddingModel,
)


@pytest.fixture(autouse=True)
def reset_embedding_model():
    """Reset global embedding model between tests."""
    import backend.pipeline.ingestion.embedding

    backend.pipeline.ingestion.embedding._model = None


class TestEmbedding:
    """Test embedding functions."""

    @patch("backend.pipeline.ingestion.embedding.collection")
    @patch("backend.pipeline.ingestion.embedding.GGUFEmbeddingModel")
    @patch("backend.pipeline.ingestion.embedding.get_device")
    @patch(
        "backend.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_with_dedup_all_new(
        self,
        mock_print,
        mock_generate_id,
        mock_get_device,
        mock_model_class,
        mock_collection,
    ):
        """Test embedding chunks when all are new."""
        # Mock chunk ID generation for predictable testing
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        mock_get_device.return_value = "cpu"
        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2], [0.3, 0.4]], dtype=np.float32
        )
        mock_model_class.return_value = mock_model

        mock_collection.get.return_value = {"ids": []}  # No existing chunks

        chunks = ["chunk1", "chunk2"]
        filename = "test.txt"

        embeddings, indices = embed_chunks_with_dedup(chunks, filename)

        assert len(embeddings) == 2
        assert_allclose(embeddings, [[0.1, 0.2], [0.3, 0.4]], rtol=1e-5)
        assert indices == [0, 1]
        mock_model.encode_document.assert_called_once()
        # Verify generate_chunk_id was called for each chunk
        assert mock_generate_id.call_count == 2

    @patch("backend.pipeline.ingestion.embedding.collection")
    @patch(
        "backend.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_with_dedup_all_existing(
        self, mock_print, mock_generate_id, mock_collection
    ):
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

    @patch("backend.pipeline.ingestion.embedding.collection")
    @patch("backend.pipeline.ingestion.embedding.GGUFEmbeddingModel")
    @patch("backend.pipeline.ingestion.embedding.get_device")
    @patch("backend.pipeline.ingestion.embedding.generate_chunk_id")
    @patch("builtins.print")
    def test_embed_chunks_handles_collection_failure(
        self,
        mock_print,
        mock_generate_id,
        mock_get_device,
        mock_model_class,
        mock_collection,
    ):
        """If collection.get fails we should still embed new chunks."""
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"
        mock_collection.get.side_effect = RuntimeError("store unavailable")

        mock_get_device.return_value = "cpu"
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

    @patch("backend.pipeline.ingestion.embedding.collection")
    @patch("backend.pipeline.ingestion.embedding.GGUFEmbeddingModel")
    @patch("backend.pipeline.ingestion.embedding.get_device")
    @patch(
        "backend.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_with_dedup_mixed_new_existing(
        self,
        mock_print,
        mock_generate_id,
        mock_get_device,
        mock_model_class,
        mock_collection,
    ):
        """Test embedding chunks when some are new and some already exist."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        mock_get_device.return_value = "cpu"
        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2], [0.3, 0.4]], dtype=np.float32
        )
        mock_model_class.return_value = mock_model

        # Mock collection to show chunk2 already exists
        mock_collection.get.return_value = {"ids": ["chunk2_hash"]}

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

    @patch("backend.pipeline.ingestion.embedding.collection")
    @patch("backend.pipeline.ingestion.embedding.GGUFEmbeddingModel")
    @patch("backend.pipeline.ingestion.embedding.get_device")
    @patch(
        "backend.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_with_dedup_internal_deduplication(
        self,
        mock_print,
        mock_generate_id,
        mock_get_device,
        mock_model_class,
        mock_collection,
    ):
        """Test internal deduplication within the batch."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        mock_get_device.return_value = "cpu"
        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2], [0.3, 0.4]], dtype=np.float32
        )
        mock_model_class.return_value = mock_model

        # Mock collection to return no existing chunks
        mock_collection.get.return_value = {"ids": []}

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

    @patch("backend.pipeline.ingestion.embedding.collection")
    @patch("backend.pipeline.ingestion.embedding.GGUFEmbeddingModel")
    @patch("backend.pipeline.ingestion.embedding.get_device")
    @patch(
        "backend.pipeline.ingestion.embedding.generate_chunk_id"
    )  # Mock for full isolation
    @patch("builtins.print")  # Suppress print statements
    def test_embed_chunks_model_reuse(
        self,
        mock_print,
        mock_generate_id,
        mock_get_device,
        mock_model_class,
        mock_collection,
    ):
        """Test that the model is reused across multiple calls."""
        # Mock chunk ID generation
        mock_generate_id.side_effect = lambda chunk: f"{chunk}_hash"

        mock_get_device.return_value = "cpu"
        mock_model = MagicMock()
        mock_model.encode_document.return_value = np.array(
            [[0.1, 0.2]], dtype=np.float32
        )
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
        assert mock_model.encode_document.call_count == 2

        assert_allclose(embeddings1, [[0.1, 0.2]], rtol=1e-5)
        assert_allclose(embeddings2, [[0.1, 0.2]], rtol=1e-5)
        assert indices1 == [0]
        assert indices2 == [0]
        # Verify generate_chunk_id was called for each chunk in each call
        assert mock_generate_id.call_count == 2


class TestGGUFEmbedding:
    """Test GGUF-based embedding model functionality."""

    @patch("backend.pipeline.ingestion.embedding.Llama")
    @patch("backend.pipeline.ingestion.embedding.get_device", return_value="cpu")
    def test_model_initialization_cpu(self, mock_get_device, mock_llama_class):
        """GGUF model should initialize with CPU defaults when CUDA unavailable."""
        mock_model = MagicMock()
        mock_llama_class.from_pretrained.return_value = mock_model

        GGUFEmbeddingModel()

        mock_llama_class.from_pretrained.assert_called_once()
        _, kwargs = mock_llama_class.from_pretrained.call_args
        assert kwargs["embedding"] is True
        # When running on CPU, n_gpu_layers defaults to 0 (no GPU offload)
        assert kwargs.get("n_gpu_layers", 0) == 0
        mock_get_device.assert_called_once()

    @patch("backend.pipeline.ingestion.embedding.Llama")
    @patch("backend.pipeline.ingestion.embedding.get_device", return_value="cuda")
    def test_model_initialization_gpu(self, mock_get_device, mock_llama_class):
        """GGUF model should enable GPU offload when CUDA is available."""
        mock_model = MagicMock()
        mock_llama_class.from_pretrained.return_value = mock_model

        GGUFEmbeddingModel()

        mock_llama_class.from_pretrained.assert_called_once()
        _, kwargs = mock_llama_class.from_pretrained.call_args
        assert kwargs["n_gpu_layers"] == -1
        assert kwargs["main_gpu"] == 0
        mock_get_device.assert_called_once()

    @patch("backend.pipeline.ingestion.embedding.Llama")
    def test_encode_document_batch_success(self, mock_llama_class):
        """encode_document should process texts and return numpy array."""
        mock_model = MagicMock()
        mock_model.embed.side_effect = [[0.1] * 768, [0.2] * 768]
        mock_llama_class.from_pretrained.return_value = mock_model

        model = GGUFEmbeddingModel()
        embeddings = model.encode_document(["text1", "text2"])

        assert mock_model.embed.call_count == 2
        call_args_list = mock_model.embed.call_args_list
        assert call_args_list[0][0][0] == "title: none | text: text1"
        assert call_args_list[1][0][0] == "title: none | text: text2"
        assert embeddings.shape == (2, 768)

    @patch("backend.pipeline.ingestion.embedding.Llama")
    def test_encode_query_prompt(self, mock_llama_class):
        """encode_query should apply the correct retrieval prompt."""
        mock_model = MagicMock()
        mock_model.embed.return_value = [0.3] * 768
        mock_llama_class.from_pretrained.return_value = mock_model

        model = GGUFEmbeddingModel()
        embedding = model.encode_query("example query")

        mock_model.embed.assert_called_once_with(
            "task: search result | query: example query"
        )
        assert embedding.shape == (768,)
