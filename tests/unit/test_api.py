import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from io import BytesIO

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

    @patch('samvaad.interfaces.api.ingest_file_pipeline')
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

    @patch('samvaad.interfaces.api.ingest_file_pipeline')
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

    @patch('samvaad.interfaces.api.rag_query_pipeline')
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

    @patch('samvaad.interfaces.api.rag_query_pipeline')
    def test_query_endpoint_with_error(self, mock_rag):
        """Test query endpoint with processing error."""
        mock_rag.side_effect = Exception("Processing failed")

        request_data = {"query": "What is this?"}
        response = self.client.post("/query", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "Processing failed" in result["error"]

    @patch('samvaad.interfaces.api.rag_query_pipeline')
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

    @patch('samvaad.interfaces.api.get_tts')
    def test_tts_endpoint_success(self, mock_get_tts):
        """Test TTS endpoint with Kokoro engine."""
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.return_value = (b"wav_data", 22050)
        mock_get_tts.return_value = mock_tts

        request_data = {
            "text": "Hello world",
            "language": "en"
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
            language="en",
            speed=1.0
        )

    @patch('samvaad.interfaces.api.get_tts')
    def test_tts_endpoint_error(self, mock_get_tts):
        """Test TTS endpoint with TTS initialization error."""
        mock_get_tts.side_effect = RuntimeError("TTS initialization failed")

        request_data = {
            "text": "Hello world",
            "language": "en"
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "TTS initialization failed" in result["error"]

    @patch('samvaad.interfaces.api.strip_markdown')
    @patch('samvaad.interfaces.api.get_tts')
    def test_tts_endpoint_markdown_stripping(self, mock_get_tts, mock_strip_markdown):
        """Test that TTS endpoint strips markdown from text."""
        mock_strip_markdown.return_value = "Plain text without markdown"
        mock_tts = MagicMock()
        mock_tts.synthesize_wav.return_value = (b"wav_data", 22050)
        mock_get_tts.return_value = mock_tts

        request_data = {
            "text": "# Header\n**Bold text**\nRegular text",
            "language": "en"
        }
        response = self.client.post("/tts", json=request_data)

        assert response.status_code == 200
        # Verify markdown stripping was called
        mock_strip_markdown.assert_called_once_with("# Header\n**Bold text**\nRegular text")
        # Verify TTS was called with stripped text
        mock_tts.synthesize_wav.assert_called_once_with(
            "Plain text without markdown",
            language="en",
            speed=1.0
        )

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_start_conversation_success(self, mock_get_manager):
        """Test starting a conversation successfully."""
        mock_manager = MagicMock()
        mock_manager.is_active = False
        mock_get_manager.return_value = mock_manager

        response = self.client.post("/conversation/start?session_id=test_session")

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "started"
        assert result["session_id"] == "test_session"
        assert "started successfully" in result["message"]
        mock_manager.start_conversation.assert_called_once()

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_start_conversation_already_active(self, mock_get_manager):
        """Test starting a conversation that is already active."""
        mock_manager = MagicMock()
        mock_manager.is_active = True
        mock_get_manager.return_value = mock_manager

        response = self.client.post("/conversation/start?session_id=test_session")

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "started"
        mock_manager.start_conversation.assert_not_called()

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_start_conversation_error(self, mock_get_manager):
        """Test starting a conversation with error."""
        mock_get_manager.side_effect = Exception("Test error")

        response = self.client.post("/conversation/start?session_id=test_session")

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert result["session_id"] == "test_session"

    @patch('samvaad.interfaces.api.rag_query_pipeline')
    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_send_conversation_message_success(self, mock_get_manager, mock_rag):
        """Test sending a message to conversation successfully."""
        mock_manager = MagicMock()
        mock_manager.settings = {'model': 'test-model'}
        mock_manager.get_context.return_value = {"messages": []}
        mock_get_manager.return_value = mock_manager

        mock_rag.return_value = {
            'answer': 'Test response',
            'success': True,
            'sources': [{'title': 'Test source'}]
        }

        request_data = {
            "message": "Hello",
            "session_id": "test_session"
        }
        response = self.client.post("/conversation/message", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert result["session_id"] == "test_session"
        assert result["response"] == "Test response"
        assert result["success"] is True
        assert len(result["sources"]) == 1
        mock_manager.add_user_message.assert_called_once_with("Hello")
        mock_manager.add_assistant_message.assert_called_once_with("Test response")

    @patch('samvaad.interfaces.api.rag_query_pipeline')
    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_send_conversation_message_error(self, mock_get_manager, mock_rag):
        """Test sending a message to conversation with error."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        mock_rag.side_effect = Exception("RAG error")

        request_data = {
            "message": "Hello",
            "session_id": "test_session"
        }
        response = self.client.post("/conversation/message", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert result["session_id"] == "test_session"
        assert "RAG error" in result["response"]

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_update_conversation_settings_success(self, mock_get_manager):
        """Test updating conversation settings successfully."""
        mock_manager = MagicMock()
        mock_manager.settings = {'language': 'en', 'model': 'gpt-4'}
        mock_get_manager.return_value = mock_manager

        request_data = {
            "session_id": "test_session",
            "language": "es",
            "model": "gpt-3.5"
        }
        response = self.client.post("/conversation/settings", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "updated"
        assert result["session_id"] == "test_session"
        mock_manager.update_settings.assert_called_once_with(language="es", model="gpt-3.5")

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_update_conversation_settings_partial(self, mock_get_manager):
        """Test updating conversation settings with partial updates."""
        mock_manager = MagicMock()
        mock_manager.settings = {'language': 'en', 'model': 'gpt-4'}
        mock_get_manager.return_value = mock_manager

        request_data = {
            "session_id": "test_session",
            "language": "es"
        }
        response = self.client.post("/conversation/settings", json=request_data)

        assert response.status_code == 200
        mock_manager.update_settings.assert_called_once_with(language="es")

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_update_conversation_settings_error(self, mock_get_manager):
        """Test updating conversation settings with error."""
        mock_get_manager.side_effect = Exception("Settings error")

        request_data = {
            "session_id": "test_session",
            "language": "es"
        }
        response = self.client.post("/conversation/settings", json=request_data)

        assert response.status_code == 200
        result = response.json()
        assert "error" in result

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_get_conversation_status_success(self, mock_get_manager):
        """Test getting conversation status successfully."""
        mock_manager = MagicMock()
        mock_manager.get_conversation_summary.return_value = {"active": True, "messages": 5}
        mock_get_manager.return_value = mock_manager

        response = self.client.get("/conversation/status/test_session")

        assert response.status_code == 200
        result = response.json()
        assert result["session_id"] == "test_session"
        assert result["status"] == {"active": True, "messages": 5}

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_get_conversation_status_error(self, mock_get_manager):
        """Test getting conversation status with error."""
        mock_get_manager.side_effect = Exception("Status error")

        response = self.client.get("/conversation/status/test_session")

        assert response.status_code == 200
        result = response.json()
        assert "error" in result

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_clear_conversation_success(self, mock_get_manager):
        """Test clearing conversation successfully."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        response = self.client.post("/conversation/clear/test_session")

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "cleared"
        assert result["session_id"] == "test_session"
        mock_manager.clear_history.assert_called_once()

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_clear_conversation_error(self, mock_get_manager):
        """Test clearing conversation with error."""
        mock_get_manager.side_effect = Exception("Clear error")

        response = self.client.post("/conversation/clear/test_session")

        assert response.status_code == 200
        result = response.json()
        assert "error" in result

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_end_conversation_success(self, mock_get_manager):
        """Test ending conversation successfully."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        response = self.client.post("/conversation/end/test_session")

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "ended"
        assert result["session_id"] == "test_session"
        mock_manager.end_conversation.assert_called_once()

    @patch('samvaad.interfaces.api.get_conversation_manager')
    def test_end_conversation_error(self, mock_get_manager):
        """Test ending conversation with error."""
        mock_get_manager.side_effect = Exception("End error")

        response = self.client.post("/conversation/end/test_session")

        assert response.status_code == 200
        result = response.json()
        assert "error" in result