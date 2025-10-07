import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from io import BytesIO

# Import the FastAPI app
from backend.main import app


class TestAPIEndpoints:
    """Test FastAPI endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @patch('backend.main.ingest_file_pipeline')
    def test_ingest_endpoint_success(self, mock_ingest):
        """Test successful file ingestion."""
        mock_ingest.return_value = {
            "num_chunks": 5,
            "new_chunks_embedded": 3,
            "error": None
        }

        # Create a mock PDF file
        file_content = b"mock pdf content"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}

        response = self.client.post("/ingest", files=files)

        assert response.status_code == 200
        result = response.json()
        assert result["num_chunks"] == 5
        assert result["new_chunks_embedded"] == 3
        mock_ingest.assert_called_once()
        args, kwargs = mock_ingest.call_args
        assert args[0] == "test.pdf"
        assert args[1] == "application/pdf"
        assert args[2] == file_content

    @patch('backend.main.ingest_file_pipeline')
    def test_ingest_endpoint_with_error(self, mock_ingest):
        """Test file ingestion with error."""
        mock_ingest.return_value = {
            "num_chunks": 0,
            "new_chunks_embedded": 0,
            "error": "Failed to process file"
        }

        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}

        response = self.client.post("/ingest", files=files)

        assert response.status_code == 200
        result = response.json()
        assert result["error"] == "Failed to process file"

    @patch('backend.main.rag_query_pipeline')
    def test_query_endpoint_success(self, mock_rag):
        """Test successful text query."""
        mock_rag.return_value = {
            "success": True,
            "answer": "This is a test answer",
            "sources": [{"filename": "test.txt", "content_preview": "test content"}],
            "query": "What is this?",
            "retrieval_count": 1
        }

        request_data = {"query": "What is this?"}
        response = self.client.post("/query", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["answer"] == "This is a test answer"
        assert len(result["sources"]) == 1
        mock_rag.assert_called_once_with("What is this?", model="gemini-2.5-flash")

    @patch('backend.main.rag_query_pipeline')
    def test_query_endpoint_with_error(self, mock_rag):
        """Test query endpoint with processing error."""
        mock_rag.side_effect = Exception("Processing failed")

        request_data = {"query": "What is this?"}
        response = self.client.post("/query", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "Processing failed" in result["error"]

    @patch('backend.main.rag_query_pipeline')
    def test_voice_query_endpoint(self, mock_rag):
        """Test voice query endpoint."""
        mock_rag.return_value = {
            "success": True,
            "answer": "Voice query response",
            "sources": [],
            "query": "Voice input",
            "retrieval_count": 0
        }

        request_data = {"query": "Voice input", "language": "en"}
        response = self.client.post("/voice-query", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["answer"] == "Voice query response"
        mock_rag.assert_called_once_with("Voice input", model="gemini-2.5-flash")

    @patch('backend.main.get_kokoro_tts')
    def test_tts_endpoint_kokoro_success(self, mock_get_kokoro):
        """Test TTS endpoint with Kokoro engine."""
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.return_value = (b"wav_data", 24000)
        mock_get_kokoro.return_value = mock_tts

        request_data = {
            "text": "Hello world",
            "language": "en",
            "engine": "kokoro"
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "audio_base64" in result
        assert result["sample_rate"] == 24000
        assert result["format"] == "wav"

        # Verify the mock was called correctly
        mock_tts.synthesize_wav.assert_called_once_with(
            "Hello world",
            language="en",
            speed=1.0
        )

    @patch('backend.main.get_piper_tts')
    def test_tts_endpoint_piper_success(self, mock_get_piper):
        """Test TTS endpoint with Piper engine (default)."""
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.return_value = (b"wav_data", 22050)
        mock_get_piper.return_value = mock_tts

        request_data = {
            "text": "Hello world",
            "language": "en",
            "engine": "piper"
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "audio_base64" in result
        assert result["sample_rate"] == 22050
        assert result["format"] == "wav"

        # Verify the mock was called correctly
        mock_tts.synthesize_wav.assert_called_once_with(
            "Hello world",
            language="en"
        )

    @patch('backend.main.get_piper_tts')
    def test_tts_endpoint_default_engine(self, mock_get_piper):
        """Test TTS endpoint with default engine (piper)."""
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.return_value = (b"wav_data", 22050)
        mock_get_piper.return_value = mock_tts

        request_data = {
            "text": "Hello world",
            "language": "en"
            # No engine specified, should default to piper
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        mock_get_piper.assert_called_once()
        mock_tts.synthesize_wav.assert_called_once()

    @patch('backend.main.get_kokoro_tts')
    def test_tts_endpoint_kokoro_error(self, mock_get_kokoro):
        """Test TTS endpoint with Kokoro engine error."""
        mock_get_kokoro.side_effect = RuntimeError("TTS initialization failed")

        request_data = {
            "text": "Hello world",
            "language": "en",
            "engine": "kokoro"
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "TTS initialization failed" in result["error"]

    @patch('backend.main.get_piper_tts')
    def test_tts_endpoint_synthesis_error(self, mock_get_piper):
        """Test TTS endpoint with synthesis error."""
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.side_effect = Exception("Synthesis failed")
        mock_get_piper.return_value = mock_tts

        request_data = {
            "text": "Hello world",
            "language": "en",
            "engine": "piper"
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "Synthesis failed" in result["error"]

    @patch('backend.main.get_piper_tts')
    def test_tts_endpoint_invalid_engine(self, mock_get_piper):
        """Test TTS endpoint with invalid engine."""
        mock_get_piper.side_effect = RuntimeError("TTS initialization failed")

        request_data = {
            "text": "Hello world",
            "language": "en",
            "engine": "invalid"
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "TTS initialization failed" in result["error"]

    @patch('backend.main.strip_markdown')
    @patch('backend.main.get_piper_tts')
    def test_tts_endpoint_markdown_stripping(self, mock_get_piper, mock_strip_markdown):
        """Test that TTS endpoint strips markdown from text."""
        mock_strip_markdown.return_value = "Plain text without markdown"
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.return_value = (b"wav_data", 22050)
        mock_get_piper.return_value = mock_tts

        request_data = {
            "text": "# Header\n**Bold text**\nRegular text",
            "language": "en",
            "engine": "piper"
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        # Verify markdown stripping was called
        mock_strip_markdown.assert_called_once_with("# Header\n**Bold text**\nRegular text")
        # Verify TTS was called with stripped text
        mock_tts.synthesize_wav.assert_called_once_with(
            "Plain text without markdown",
            language="en"
        )