import pytest
import os
import sys
import builtins
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../backend'))

from backend.pipeline.retrieval.query_voice import clean_transcription, initialize_whisper_model


class TestCleanTranscription:
    """Test cases for the clean_transcription function."""

    def setup_method(self):
        """Reset function cache before each test."""
        # Clear any cached client from previous tests
        if hasattr(clean_transcription, '_client'):
            delattr(clean_transcription, '_client')
        if hasattr(clean_transcription, '_types'):
            delattr(clean_transcription, '_types')

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.genai')
    def test_clean_transcription_success(self, mock_genai):
        """Test successful text cleaning with Gemini API."""
        # Mock the Gemini client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Cleaned text"
        mock_client.models.generate_content.return_value = mock_response

        mock_genai.Client.return_value = mock_client
        mock_genai.types = Mock()

        result = clean_transcription("raw transcription text")

        assert result == "Cleaned text"
        mock_client.models.generate_content.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)  # No GEMINI_API_KEY
    def test_clean_transcription_no_api_key(self):
        """Test behavior when GEMINI_API_KEY is not set."""
        result = clean_transcription("raw text")
        assert result == "raw text"

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.genai')
    def test_clean_transcription_api_error(self, mock_genai):
        """Test error handling when Gemini API fails."""
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = Exception("API Error")

        mock_genai.Client.return_value = mock_client
        mock_genai.types = Mock()

        result = clean_transcription("raw text")
        assert result == "raw text"

    def test_clean_transcription_empty_text(self):
        """Test cleaning empty or whitespace-only text."""
        assert clean_transcription("") == ""
        assert clean_transcription("   ") == "   "
        assert clean_transcription(None) == None

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.genai')
    def test_clean_transcription_response_formatting(self, mock_genai):
        """Test that response formatting removes quotes."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = '"Cleaned text"'
        mock_client.models.generate_content.return_value = mock_response

        mock_genai.Client.return_value = mock_client
        mock_genai.types = Mock()

        result = clean_transcription("raw text")
        assert result == "Cleaned text"


class TestInitializeWhisperModel:
    """Test cases for the initialize_whisper_model function."""

    @patch('backend.pipeline.retrieval.query_voice.torch.cuda.is_available', return_value=True)
    @patch('faster_whisper.WhisperModel')
    def test_initialize_whisper_model_gpu(self, mock_whisper_model, mock_cuda_available):
        """Test Whisper model initialization with GPU available."""
        mock_model_instance = Mock()
        mock_whisper_model.return_value = mock_model_instance

        result = initialize_whisper_model("base", "auto", "default")

        mock_whisper_model.assert_called_once_with("base", device="cuda", compute_type="float16")
        assert result == mock_model_instance

    @patch('backend.pipeline.retrieval.query_voice.torch.cuda.is_available', return_value=False)
    @patch('faster_whisper.WhisperModel')
    def test_initialize_whisper_model_cpu(self, mock_whisper_model, mock_cuda_available):
        """Test Whisper model initialization with CPU only."""
        mock_model_instance = Mock()
        mock_whisper_model.return_value = mock_model_instance

        result = initialize_whisper_model("base", "auto", "default")

        mock_whisper_model.assert_called_once_with("base", device="cpu", compute_type="int8")
        assert result == mock_model_instance

    @patch('faster_whisper.WhisperModel')
    def test_initialize_whisper_model_explicit_device(self, mock_whisper_model):
        """Test Whisper model initialization with explicit device."""
        mock_model_instance = Mock()
        mock_whisper_model.return_value = mock_model_instance

        result = initialize_whisper_model("small", "cpu", "int8")

        mock_whisper_model.assert_called_once_with("small", device="cpu", compute_type="int8")
        assert result == mock_model_instance

    @patch('faster_whisper.WhisperModel', side_effect=Exception("Import error"))
    def test_initialize_whisper_model_import_error(self, mock_whisper_model):
        """Test error handling when Whisper model fails to initialize."""
        result = initialize_whisper_model("base")
        assert result is None


class TestVoiceQueryCLI:
    """Test cases for the voice_query_cli function."""

    @patch('backend.pipeline.retrieval.query_voice.torch.cuda.is_available', return_value=True)
    @patch('backend.pipeline.retrieval.query_voice.clean_transcription')
    @patch('backend.pipeline.retrieval.query_voice.initialize_whisper_model')
    @patch('webrtcvad.Vad')
    @patch('pyaudio.PyAudio')
    @patch('backend.pipeline.retrieval.query_voice.rag_query_pipeline')
    @patch('builtins.print')  # Mock print to avoid cluttering test output
    def test_voice_query_cli_full_flow(self, mock_print, mock_rag_pipeline, mock_pyaudio,
                                      mock_vad, mock_init_whisper, mock_clean_transcription,
                                      mock_cuda_available):
        """Test the complete voice query CLI flow with mocked dependencies."""
        # Setup mocks
        mock_whisper_model = Mock()
        mock_init_whisper.return_value = mock_whisper_model

        mock_vad_instance = Mock()
        mock_vad.return_value = mock_vad_instance

        mock_audio = Mock()
        mock_stream = Mock()
        mock_pyaudio.return_value = mock_audio
        mock_audio.open.return_value = mock_stream

        # Mock audio data - simulate speech then silence
        speech_data = b'\x00\x01' * 160  # 20ms of "speech"
        silence_data = b'\x00\x00' * 160  # 20ms of silence

        # Simulate: speech detected, then 151 frames of silence
        mock_stream.read.side_effect = [speech_data] + [silence_data] * 151

        # Mock VAD - detect speech initially, then silence
        mock_vad_instance.is_speech.side_effect = [True] + [False] * 151

        # Mock transcription
        mock_segment = Mock()
        mock_segment.text = "Hello world"
        mock_whisper_model.transcribe.return_value = ([mock_segment], Mock())

        # Mock cleaning
        mock_clean_transcription.return_value = "Hello world"

        # Mock RAG pipeline
        mock_rag_pipeline.return_value = {
            'answer': 'Test answer',
            'success': True,
            'sources': [{'filename': 'test.pdf', 'content_preview': 'test content'}],
            'retrieval_count': 1
        }

        # Run the function (it will run in a separate thread to avoid blocking)
        from backend.pipeline.retrieval.query_voice import voice_query_cli
        import threading

        # Run in thread to avoid blocking the test
        cli_thread = threading.Thread(target=voice_query_cli, args=("en", "gemini-2.5-flash"))
        cli_thread.daemon = True
        cli_thread.start()

        # Wait a bit for the function to start
        import time
        time.sleep(0.1)

        # The function should complete on its own due to the mocked silence detection
        cli_thread.join(timeout=5)  # Timeout after 5 seconds

        # Verify that RAG pipeline was called
        mock_rag_pipeline.assert_called_once_with("Hello world", model="gemini-2.5-flash", language="en")

    @patch('backend.pipeline.retrieval.query_voice.initialize_whisper_model', return_value=None)
    @patch('builtins.print')
    def test_voice_query_cli_whisper_init_failure(self, mock_print, mock_init_whisper):
        """Test CLI behavior when Whisper model initialization fails."""
        from backend.pipeline.retrieval.query_voice import voice_query_cli

        voice_query_cli("en", "gemini-2.5-flash")

        # Should not crash, should exit gracefully
        mock_print.assert_called()  # Some prints should have been called

    @patch('backend.pipeline.retrieval.query_voice.clean_transcription', return_value='test')
    @patch('backend.pipeline.retrieval.query_voice.torch.cuda.is_available', return_value=False)
    @patch('builtins.print')
    def test_voice_query_cli_missing_dependencies(self, mock_print, mock_cuda_available, mock_clean_transcription):
        """If required packages are missing we should surface a helpful error."""
        from backend.pipeline.retrieval.query_voice import voice_query_cli

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name in {"faster_whisper", "webrtcvad", "pyaudio"}:
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=fake_import):
            voice_query_cli("en", "gemini-2.5-flash")

        mock_print.assert_any_call("❌ Failed to import required packages: not installed")
        mock_print.assert_any_call("Please install: pip install faster-whisper webrtcvad pyaudio")

    @patch('backend.pipeline.retrieval.query_voice.torch.cuda.is_available', return_value=False)
    @patch('backend.pipeline.retrieval.query_voice.clean_transcription', return_value="")
    @patch('backend.pipeline.retrieval.query_voice.initialize_whisper_model')
    @patch('webrtcvad.Vad')
    @patch('pyaudio.PyAudio')
    @patch('backend.pipeline.retrieval.query_voice.rag_query_pipeline')
    @patch('builtins.print')
    def test_voice_query_cli_empty_transcription(self, mock_print, mock_rag_pipeline, mock_pyaudio,
                                                 mock_vad, mock_init_whisper, mock_clean_transcription,
                                                 mock_cuda_available):
        """If transcription yields no text we should not hit the RAG pipeline."""
        from backend.pipeline.retrieval.query_voice import voice_query_cli

        mock_whisper_model = Mock()
        mock_whisper_model.transcribe.return_value = ([], Mock())
        mock_init_whisper.return_value = mock_whisper_model

        mock_vad_instance = Mock()
        mock_vad_instance.is_speech.side_effect = [True] + [False] * 151
        mock_vad.return_value = mock_vad_instance

        mock_audio = Mock()
        mock_stream = Mock()
        mock_stream.read.side_effect = [b'\x00\x01' * 160] + [b'\x00\x00' * 160] * 151
        mock_audio.open.return_value = mock_stream
        mock_pyaudio.return_value = mock_audio

        voice_query_cli("en", "gemini-2.5-flash")

        mock_clean_transcription.assert_called()
        mock_rag_pipeline.assert_not_called()
        mock_stream.stop_stream.assert_called_once()
        mock_print.assert_any_call("❌ No speech detected. Please try again.")


class TestIntegration:
    """Integration tests that test multiple components together."""

    def setup_method(self):
        """Reset function cache before each test."""
        # Clear any cached client from previous tests
        if hasattr(clean_transcription, '_client'):
            delattr(clean_transcription, '_client')
        if hasattr(clean_transcription, '_types'):
            delattr(clean_transcription, '_types')

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.genai')
    def test_clean_transcription_caching(self, mock_genai):
        """Test that the Gemini client is cached between calls."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Cleaned"
        mock_client.models.generate_content.return_value = mock_response

        mock_genai.Client.return_value = mock_client
        mock_genai.types = Mock()

        # First call
        clean_transcription("text 1")
        # Second call
        clean_transcription("text 2")

        # Client should only be created once
        assert mock_genai.Client.call_count == 1
        # But generate_content should be called twice
        assert mock_client.models.generate_content.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__])
