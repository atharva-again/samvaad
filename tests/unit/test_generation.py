import pytest
from unittest.mock import patch, MagicMock

# Import modules to test
from samvaad.pipeline.generation.generation import generate_answer_with_groq


class TestGeneration:
    """Test generation functions."""

    @patch('samvaad.pipeline.generation.generation.Groq')
    @patch('os.getenv')
    def test_generate_answer_with_groq(self, mock_getenv, mock_groq_class):
        """Test generating answer with Groq."""
        mock_getenv.return_value = "fake_key"

        # Mock Groq client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Generated answer"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        chunks = [{"content": "test content", "filename": "test.txt"}]
        answer = generate_answer_with_groq("test query", chunks)

        assert answer == "Generated answer"

    @patch('samvaad.pipeline.generation.generation.Groq')
    @patch('os.getenv', return_value=None)
    def test_generate_answer_missing_api_key(self, mock_getenv, mock_groq_class):
        """Expect a ValueError when GROQ_API_KEY is absent."""
        chunks = [{"content": "test content", "filename": "test.txt"}]

        with pytest.raises(ValueError):
            generate_answer_with_groq("test query", chunks)