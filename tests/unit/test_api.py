from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
from samvaad.interfaces.api import app


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

    @patch("samvaad.interfaces.api.ingest_file_pipeline")
    def test_ingest_endpoint_success(self, mock_ingest):
        """Test successful file ingestion."""
        mock_ingest.return_value = {
            "num_chunks": 5,
            "new_chunks_embedded": 3,
            "error": None,
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

    @patch("samvaad.interfaces.api.ingest_file_pipeline")
    def test_ingest_endpoint_with_error(self, mock_ingest):
        """Test file ingestion with error."""
        mock_ingest.return_value = {
            "num_chunks": 0,
            "new_chunks_embedded": 0,
            "error": "Failed to process file",
        }

        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}

        response = self.client.post("/ingest", files=files)

        assert response.status_code == 200
        result = response.json()
        assert result["error"] == "Failed to process file"

    @patch("samvaad.interfaces.api.rag_query_pipeline")
    def test_query_endpoint_success(self, mock_rag):
        """Test successful text query."""
        mock_rag.return_value = {
            "success": True,
            "answer": "This is a test answer",
            "sources": [{"filename": "test.txt", "content_preview": "test content"}],
            "query": "What is this?",
            "retrieval_count": 1,
        }

        request_data = {"query": "What is this?"}
        response = self.client.post("/query", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["answer"] == "This is a test answer"
        assert len(result["sources"]) == 1
        mock_rag.assert_called_once_with("What is this?", model="llama-3.3-70b-versatile")

    @patch("samvaad.interfaces.api.rag_query_pipeline")
    def test_query_endpoint_with_error(self, mock_rag):
        """Test query endpoint with processing error."""
        mock_rag.side_effect = Exception("Processing failed")

        request_data = {"query": "What is this?"}
        response = self.client.post("/query", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "Processing failed" in result["error"]

    @patch("samvaad.interfaces.api.rag_query_pipeline")
    def test_voice_query_endpoint(self, mock_rag):
        """Test voice query endpoint."""
        mock_rag.return_value = {
            "success": True,
            "answer": "Voice query response",
            "sources": [],
            "query": "Voice input",
            "retrieval_count": 0,
        }

        request_data = {"query": "Voice input", "language": "en"}
        response = self.client.post("/voice-query", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["answer"] == "Voice query response"
        mock_rag.assert_called_once_with("Voice input", model="llama-3.3-70b-versatile")

    @patch("samvaad.interfaces.api.get_tts")
    def test_tts_endpoint_success(self, mock_get_tts):
        """Test TTS endpoint with Kokoro engine."""
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.return_value = (b"wav_data", 22050)
        mock_get_tts.return_value = mock_tts

        request_data = {"text": "Hello world", "language": "en"}
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "audio_base64" in result
        assert result["sample_rate"] == 22050
        assert result["format"] == "wav"

        # Verify the mock was called correctly
        mock_tts.synthesize_wav.assert_called_once_with(
            "Hello world", language="en", speed=1.0
        )

    @patch("samvaad.interfaces.api.get_tts")
    def test_tts_endpoint_error(self, mock_get_tts):
        """Test TTS endpoint with TTS initialization error."""
        mock_get_tts.side_effect = RuntimeError("TTS initialization failed")

        request_data = {"text": "Hello world", "language": "en"}
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "TTS initialization failed" in result["error"]

    @patch("samvaad.interfaces.api.strip_markdown")
    @patch("samvaad.interfaces.api.get_tts")
    def test_tts_endpoint_markdown_stripping(self, mock_get_tts, mock_strip_markdown):
        """Test that TTS endpoint strips markdown from text."""
        mock_strip_markdown.return_value = "Plain text without markdown"
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.return_value = (b"wav_data", 22050)
        mock_get_tts.return_value = mock_tts

        request_data = {
            "text": "# Header\n**Bold text**\nRegular text",
            "language": "en",
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        # Verify markdown stripping was called
        mock_strip_markdown.assert_called_once_with(
            "# Header\n**Bold text**\nRegular text"
        )
        # Verify TTS was called with stripped text
        mock_tts.synthesize_wav.assert_called_once_with(
            "Plain text without markdown", language="en", speed=1.0
        )

    @patch("samvaad.interfaces.api.rag_query_pipeline")
    def test_text_mode_success(self, mock_rag):
        """Test text mode endpoint successfully."""
        mock_rag.return_value = {
            "answer": "Test response",
            "sources": [{"filename": "test.txt"}],
        }

        request_data = {"message": "Hello", "session_id": "test_session"}
        response = self.client.post("/text-mode", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert result["session_id"] == "test_session"
        assert result["response"] == "Test response"
        assert result["success"] is True
        assert len(result["sources"]) == 1
        mock_rag.assert_called_once_with("Hello", model="llama-3.3-70b-versatile")

    @patch("samvaad.interfaces.api.rag_query_pipeline")
    def test_text_mode_error(self, mock_rag):
        """Test text mode endpoint with error."""
        mock_rag.side_effect = Exception("RAG error")

        request_data = {"message": "Hello", "session_id": "test_session"}
        response = self.client.post("/text-mode", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert result["success"] is False

    @patch("samvaad.interfaces.api.create_daily_room")
    @patch("samvaad.interfaces.api.start_voice_agent")
    def test_voice_mode_success(self, mock_start_agent, mock_create_room):
        """Test voice mode endpoint successfully."""
        mock_create_room.return_value = ("https://daily.co/room123", "token123")

        request_data = {"session_id": "test_session"}
        response = self.client.post("/voice-mode", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert result["room_url"] == "https://daily.co/room123"
        assert result["token"] == "token123"
        assert result["session_id"] == "test_session"
        assert result["success"] is True
        mock_create_room.assert_called_once()
        mock_start_agent.assert_called_once_with("https://daily.co/room123", "token123")

    @patch("samvaad.interfaces.api.create_daily_room")
    def test_voice_mode_error(self, mock_create_room):
        """Test voice mode endpoint with error."""
        mock_create_room.side_effect = Exception("Room creation failed")

        request_data = {"session_id": "test_session"}
        response = self.client.post("/voice-mode", json=request_data)

        assert response.status_code == 500
        result = response.json()
        assert "detail" in result
        assert "Room creation failed" in result["detail"]


class TestAPIErrorHandling:
    """Test error handling in API endpoints."""

    def test_query_empty_string(self):
        """Test query with empty string."""
        from fastapi.testclient import TestClient

        from samvaad.interfaces.api import app

        client = TestClient(app)

        response = client.post("/query", json={"query": ""})

        # Should handle empty query gracefully
        assert response.status_code in [200, 400, 422]

    def test_text_mode_empty_message(self):
        """Test text mode with empty message."""
        from fastapi.testclient import TestClient

        from samvaad.interfaces.api import app

        client = TestClient(app)

        response = client.post("/text-mode", json={"message": "", "session_id": "test"})

        # Should handle empty message gracefully
        assert response.status_code in [200, 400, 422]
