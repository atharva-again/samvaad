"""Test generation functions using Groq."""

from unittest.mock import MagicMock, patch

import pytest


class TestGeneration:
    """Test generation functions."""

    @patch("samvaad.pipeline.generation.generation.Groq")
    @patch("os.getenv")
    def test_generate_answer_with_groq(self, mock_getenv, mock_groq_class):
        """Test generating answer with Groq."""
        from samvaad.pipeline.generation.generation import generate_answer_with_groq

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

    @patch("samvaad.pipeline.generation.generation.Groq")
    @patch("os.getenv", return_value=None)
    def test_generate_answer_missing_api_key(self, mock_getenv, mock_groq_class):
        """Expect a ValueError when GROQ_API_KEY is absent."""
        from samvaad.pipeline.generation.generation import generate_answer_with_groq

        chunks = [{"content": "test content", "filename": "test.txt"}]

        with pytest.raises(ValueError):
            generate_answer_with_groq("test query", chunks)

    @patch("samvaad.pipeline.generation.generation.Groq")
    @patch("os.getenv")
    def test_generate_answer_with_persona(self, mock_getenv, mock_groq_class):
        """Test generating answer with persona parameter."""
        from samvaad.pipeline.generation.generation import generate_answer_with_groq

        mock_getenv.return_value = "fake_key"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Friendly response"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        chunks = [{"content": "test content", "filename": "test.txt"}]
        answer = generate_answer_with_groq("test query", chunks, persona="friend")

        assert answer == "Friendly response"
        mock_client.chat.completions.create.assert_called_once()

    @patch("samvaad.pipeline.generation.generation.Groq")
    @patch("os.getenv")
    def test_generate_answer_with_strict_mode(self, mock_getenv, mock_groq_class):
        """Test generating answer with strict mode enabled."""
        from samvaad.pipeline.generation.generation import generate_answer_with_groq

        mock_getenv.return_value = "fake_key"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Strict response based only on context"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        chunks = [{"content": "test content", "filename": "test.txt"}]
        answer = generate_answer_with_groq("test query", chunks, strict_mode=True)

        assert answer is not None
        mock_client.chat.completions.create.assert_called_once()

    @patch("samvaad.pipeline.generation.generation.Groq")
    @patch("os.getenv")
    def test_generate_answer_with_conversation_context(self, mock_getenv, mock_groq_class):
        """Test generating answer with conversation history."""
        from samvaad.pipeline.generation.generation import generate_answer_with_groq

        mock_getenv.return_value = "fake_key"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Contextual response"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        chunks = [{"content": "test content", "filename": "test.txt"}]
        history = "User: Hi\nAssistant: Hello!"
        answer = generate_answer_with_groq(
            "test query", chunks, conversation_context=history
        )

        assert answer == "Contextual response"

    @patch("samvaad.pipeline.generation.generation.Groq")
    @patch("os.getenv")
    def test_generate_answer_empty_chunks(self, mock_getenv, mock_groq_class):
        """Test generating answer with empty chunks list."""
        from samvaad.pipeline.generation.generation import generate_answer_with_groq

        mock_getenv.return_value = "fake_key"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "No context available"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        answer = generate_answer_with_groq("test query", [])

        assert answer is not None


class TestGenerationErrorHandling:
    """Test error handling in generation functions."""

    @patch("samvaad.pipeline.generation.generation.Groq")
    @patch("os.getenv")
    def test_generate_answer_api_error(self, mock_getenv, mock_groq_class):
        """Test handling of Groq API errors."""
        from samvaad.pipeline.generation.generation import generate_answer_with_groq

        mock_getenv.return_value = "fake_key"

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API rate limit")
        mock_groq_class.return_value = mock_client

        chunks = [{"content": "test content", "filename": "test.txt"}]

        with pytest.raises(Exception, match="API rate limit"):
            generate_answer_with_groq("test query", chunks)
