import pytest
from unittest.mock import patch, MagicMock

# Import modules to test
from samvaad.pipeline.generation.generation import generate_answer_with_gemini


class TestGeneration:
    """Test generation functions."""

    @patch('samvaad.pipeline.generation.generation.genai')
    @patch('os.getenv')
    def test_generate_answer_with_gemini(self, mock_getenv, mock_genai):
        """Test generating answer with Gemini."""
        mock_getenv.return_value = "fake_key"

        # Mock Gemini client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated answer"
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        chunks = [{"content": "test content", "filename": "test.txt"}]
        answer = generate_answer_with_gemini("test query", chunks)

        assert answer == "Generated answer"

    @patch('samvaad.pipeline.generation.generation.genai')
    @patch('os.getenv', return_value=None)
    def test_generate_answer_missing_api_key(self, mock_getenv, mock_genai):
        """Expect a ValueError when GEMINI_API_KEY is absent."""
        chunks = [{"content": "test content", "filename": "test.txt"}]

        with pytest.raises(ValueError):
            generate_answer_with_gemini("test query", chunks)