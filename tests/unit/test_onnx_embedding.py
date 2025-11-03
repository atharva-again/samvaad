"""Tests for ONNX embedding model."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch, Mock
from samvaad.utils.onnx_embedding import ONNXEmbeddingModel


@pytest.fixture
def mock_onnx_session():
    """Mock ONNX Runtime session."""
    mock_session = MagicMock()
    # Mock embedding output: (batch_size, 768)
    mock_session.run.return_value = [np.random.randn(1, 768).astype(np.float32)]
    return mock_session


@pytest.fixture
def mock_tokenizer():
    """Mock tokenizer."""
    mock_tok = MagicMock()
    mock_tok.return_value = {
        'input_ids': np.array([[1, 2, 3, 4, 5]]),
        'attention_mask': np.array([[1, 1, 1, 1, 1]])
    }
    return mock_tok


@pytest.mark.unit
class TestONNXEmbeddingModel:
    """Test ONNX embedding model functionality."""
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_initialization_cpu(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test initialization with CPU provider."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        model = ONNXEmbeddingModel()
        
        assert model is not None
        assert model.MAX_BATCH_SIZE == 32  # CPU batch size
        assert model.TARGET_TOKENS_PER_BATCH == 4096  # CPU token limit
        mock_session.assert_called_once()
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_initialization_gpu(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test initialization with GPU provider."""
        mock_provider.return_value = 'CUDAExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        model = ONNXEmbeddingModel()
        
        assert model is not None
        assert model.MAX_BATCH_SIZE == 64  # GPU batch size
        assert model.TARGET_TOKENS_PER_BATCH == 8192  # GPU token limit
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_encode_document_single_text(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test encoding a single document."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        # Create a mock tokenizer instance
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.return_value = {
            'input_ids': np.ones((1, 5), dtype=np.int32),
            'attention_mask': np.ones((1, 5), dtype=np.int32)
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer_instance
        
        mock_session = MagicMock()
        mock_session.run.return_value = [None, np.random.randn(1, 768).astype(np.float32)]
        mock_session_cls.return_value = mock_session
        
        model = ONNXEmbeddingModel()
        result = model.encode_document("Test document")
        
        assert result.shape == (1, 768)
        assert result.dtype == np.float32
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_encode_document_multiple_texts(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test encoding multiple documents."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.return_value = {
            'input_ids': np.ones((3, 3), dtype=np.int32),
            'attention_mask': np.ones((3, 3), dtype=np.int32)
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer_instance
        
        mock_session = MagicMock()
        mock_session.run.return_value = [None, np.random.randn(3, 768).astype(np.float32)]
        mock_session_cls.return_value = mock_session
        
        model = ONNXEmbeddingModel()
        texts = ["Doc 1", "Doc 2", "Doc 3"]
        result = model.encode_document(texts)
        
        assert result.shape == (3, 768)
        assert result.dtype == np.float32
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_encode_document_empty_list(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test encoding empty list returns empty array."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        model = ONNXEmbeddingModel()
        result = model.encode_document([])
        
        assert result.shape == (0, 768)
        assert result.dtype == np.float32
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_encode_query(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test encoding a query with proper prompt."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.return_value = {
            'input_ids': np.array([[1, 2, 3, 4, 5]]),
            'attention_mask': np.array([[1, 1, 1, 1, 1]])
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer_instance
        
        mock_session = MagicMock()
        mock_session.run.return_value = [None, np.random.randn(1, 768).astype(np.float32)]
        mock_session_cls.return_value = mock_session
        
        model = ONNXEmbeddingModel()
        result = model.encode_query("What is AI?")
        
        assert result.shape == (768,)
        assert result.dtype == np.float32
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_encode_document_batching(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test that large batches are properly split."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        num_texts = 50
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.return_value = {
            'input_ids': np.ones((num_texts, 100), dtype=np.int32),
            'attention_mask': np.ones((num_texts, 100), dtype=np.int32)
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer_instance
        
        # Session should be called multiple times for batching
        mock_session = MagicMock()
        
        def side_effect_run(output_names, inputs):
            batch_size = inputs['input_ids'].shape[0]
            return [None, np.random.randn(batch_size, 768).astype(np.float32)]
        
        mock_session.run.side_effect = side_effect_run
        mock_session_cls.return_value = mock_session
        
        model = ONNXEmbeddingModel()
        texts = [f"Document {i}" for i in range(num_texts)]
        result = model.encode_document(texts)
        
        assert result.shape == (num_texts, 768)
        assert mock_session.run.call_count > 1  # Should be batched
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_encode_document_inference_error(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test handling of inference errors."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.return_value = {
            'input_ids': np.ones((1, 3), dtype=np.int32),
            'attention_mask': np.ones((1, 3), dtype=np.int32)
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer_instance
        
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception("ONNX Runtime error")
        mock_session_cls.return_value = mock_session
        
        model = ONNXEmbeddingModel()
        result = model.encode_document("Test")
        
        # Should return zero embeddings on error
        assert result.shape == (1, 768)
        assert np.allclose(result, 0.0)
    
    @patch('samvaad.utils.onnx_embedding.ort.InferenceSession')
    @patch('samvaad.utils.onnx_embedding.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_embedding.hf_hub_download')
    @patch('samvaad.utils.onnx_embedding.get_ort_provider')
    def test_model_download(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test that model files are downloaded correctly."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.side_effect = lambda repo, **kwargs: f"/fake/{kwargs['filename']}"
        
        model = ONNXEmbeddingModel()
        
        # Should download both model and data files
        assert mock_download.call_count == 2
        calls = [call.kwargs['filename'] for call in mock_download.call_args_list]
        assert 'model_q4.onnx' in calls
        assert 'model_q4.onnx_data' in calls
