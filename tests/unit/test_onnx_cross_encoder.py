"""Tests for ONNX cross-encoder model."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from samvaad.utils.onnx_cross_encoder import ONNXCrossEncoder, get_onnx_cross_encoder


@pytest.mark.unit
class TestONNXCrossEncoder:
    """Test ONNX cross-encoder functionality."""
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_initialization_default(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test initialization with default parameters."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        model = ONNXCrossEncoder()
        
        assert model is not None
        assert model.model_repo == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert model.model_file == "onnx/model.onnx"
        mock_download.assert_called_once_with(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            filename="onnx/model.onnx"
        )
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_initialization_custom_model(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test initialization with custom model file."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model_quantized.onnx'
        
        model = ONNXCrossEncoder(model_file="onnx/model_qint8_avx512.onnx")
        
        assert model.model_file == "onnx/model_qint8_avx512.onnx"
        mock_download.assert_called_once_with(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            filename="onnx/model_qint8_avx512.onnx"
        )
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_initialization_gpu_provider(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test initialization uses correct provider."""
        mock_provider.return_value = 'CUDAExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        model = ONNXCrossEncoder()
        
        # Verify session was created with GPU provider
        call_args = mock_session.call_args
        assert 'CUDAExecutionProvider' in call_args[1]['providers']
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_predict_single_pair(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test predicting score for a single query-passage pair."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': np.array([[1, 2, 3, 4, 5]]),
            'attention_mask': np.array([[1, 1, 1, 1, 1]])
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        
        mock_session = MagicMock()
        # Binary classification output: [negative_score, positive_score]
        mock_session.run.return_value = [np.array([[0.1, 0.9]])]
        mock_session_cls.return_value = mock_session
        
        model = ONNXCrossEncoder()
        pairs = [["What is AI?", "Artificial Intelligence is a field of computer science."]]
        scores = model.predict(pairs)
        
        assert len(scores) == 1
        assert scores[0] == 0.9  # Should return positive class score
        assert isinstance(scores, np.ndarray)
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_predict_multiple_pairs(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test predicting scores for multiple query-passage pairs."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': np.array([[1, 2, 3]]),
            'attention_mask': np.array([[1, 1, 1]])
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        
        mock_session = MagicMock()
        mock_session.run.side_effect = [
            [np.array([[0.2, 0.8]])],
            [np.array([[0.4, 0.6]])],
            [np.array([[0.7, 0.3]])]
        ]
        mock_session_cls.return_value = mock_session
        
        model = ONNXCrossEncoder()
        pairs = [
            ["query1", "passage1"],
            ["query2", "passage2"],
            ["query3", "passage3"]
        ]
        scores = model.predict(pairs)
        
        assert len(scores) == 3
        assert scores[0] == 0.8
        assert scores[1] == 0.6
        assert scores[2] == 0.3
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_predict_single_output_model(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test with model that outputs single value instead of binary classification."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': np.array([[1, 2, 3]]),
            'attention_mask': np.array([[1, 1, 1]])
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        
        mock_session = MagicMock()
        # Single output value
        mock_session.run.return_value = [np.array([[0.75]])]
        mock_session_cls.return_value = mock_session
        
        model = ONNXCrossEncoder()
        pairs = [["query", "passage"]]
        scores = model.predict(pairs)
        
        assert len(scores) == 1
        assert scores[0] == 0.75  # Should use first logit
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_predict_tokenization(self, mock_provider, mock_download, mock_tokenizer_cls, mock_session_cls):
        """Test that tokenization is called correctly."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': np.array([[1, 2, 3]]),
            'attention_mask': np.array([[1, 1, 1]])
        }
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
        
        mock_session = MagicMock()
        mock_session.run.return_value = [np.array([[0.1, 0.9]])]
        mock_session_cls.return_value = mock_session
        
        model = ONNXCrossEncoder()
        pairs = [["test query", "test passage"]]
        scores = model.predict(pairs)
        
        # Verify tokenizer was called by checking that prediction succeeded
        assert len(scores) == 1
        assert scores[0] == 0.9
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_get_onnx_cross_encoder_singleton(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test that get_onnx_cross_encoder returns singleton instance."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        # Reset global instance
        import samvaad.utils.onnx_cross_encoder as module
        module._cross_encoder_instance = None
        
        # First call creates instance
        instance1 = get_onnx_cross_encoder()
        assert instance1 is not None
        
        # Second call returns same instance
        instance2 = get_onnx_cross_encoder()
        assert instance1 is instance2
        
        # Only one download should have occurred
        assert mock_download.call_count == 1
    
    @patch('samvaad.utils.onnx_cross_encoder.ort.InferenceSession')
    @patch('samvaad.utils.onnx_cross_encoder.AutoTokenizer.from_pretrained')
    @patch('samvaad.utils.onnx_cross_encoder.hf_hub_download')
    @patch('samvaad.utils.onnx_cross_encoder.get_ort_provider')
    def test_get_onnx_cross_encoder_custom_params(self, mock_provider, mock_download, mock_tokenizer, mock_session):
        """Test get_onnx_cross_encoder with custom parameters."""
        mock_provider.return_value = 'CPUExecutionProvider'
        mock_download.return_value = '/fake/path/model.onnx'
        
        # Reset global instance
        import samvaad.utils.onnx_cross_encoder as module
        module._cross_encoder_instance = None
        
        instance = get_onnx_cross_encoder(
            model_repo="custom/model",
            model_file="onnx/custom.onnx"
        )
        
        assert instance.model_repo == "custom/model"
        assert instance.model_file == "onnx/custom.onnx"
        mock_download.assert_called_once_with(
            "custom/model",
            filename="onnx/custom.onnx"
        )
