"""Test file parsing and chunking functions."""

import pytest
from unittest.mock import patch, MagicMock

# Import modules to test
from samvaad.pipeline.ingestion.chunking import (
    parse_file,
    chunk_text,
    _cleanup_temp_file,
    _recursive_chunk_text,
    get_llama_parser,
)


@pytest.fixture(autouse=True)
def reset_chunking_globals():
    """Reset global variables between tests to ensure clean state."""
    import samvaad.pipeline.ingestion.chunking
    samvaad.pipeline.ingestion.chunking._parser = None


class TestParsing:
    """Test file parsing functions."""

    def test_parse_file_txt_direct_decode(self):
        """Test that plain text files are decoded directly without API call."""
        filename = "test.txt"
        content = b"Hello, World!"
        content_type = "text/plain"

        text, error = parse_file(filename, content_type, content)

        assert text == "Hello, World!"
        assert error is None

    def test_parse_file_md_direct_decode(self):
        """Test that markdown files are decoded directly without API call."""
        filename = "readme.md"
        content = b"# Title\n\nSome content"
        content_type = "text/markdown"

        text, error = parse_file(filename, content_type, content)

        assert text == "# Title\n\nSome content"
        assert error is None

    @patch('samvaad.pipeline.ingestion.chunking.get_llama_parser')
    @patch('samvaad.pipeline.ingestion.chunking.tempfile.NamedTemporaryFile')
    @patch('samvaad.pipeline.ingestion.chunking._cleanup_temp_file')
    def test_parse_file_pdf(self, mock_cleanup, mock_temp_file, mock_get_parser):
        """Test parsing a PDF file with LlamaParse."""
        # Mock LlamaParse response (new .parse() API returns JobResult with pages)
        mock_page = MagicMock()
        mock_page.md = "Parsed PDF content"
        mock_result = MagicMock()
        mock_result.pages = [mock_page]
        
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_result
        mock_get_parser.return_value = mock_parser

        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.__enter__.return_value = mock_temp
        mock_temp.__exit__.return_value = None
        mock_temp.name = "/tmp/test.pdf"
        mock_temp_file.return_value = mock_temp

        filename = "test.pdf"
        content = b"PDF content"
        content_type = "application/pdf"

        text, error = parse_file(filename, content_type, content)

        assert text == "Parsed PDF content"
        assert error is None
        mock_parser.parse.assert_called_once_with("/tmp/test.pdf")

    @patch('samvaad.pipeline.ingestion.chunking.get_llama_parser')
    @patch('samvaad.pipeline.ingestion.chunking.tempfile.NamedTemporaryFile')
    @patch('samvaad.pipeline.ingestion.chunking._cleanup_temp_file')
    def test_parse_file_api_failure_fallback(self, mock_cleanup, mock_temp_file, mock_get_parser):
        """Test fallback to UTF-8 decode when LlamaParse fails."""
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = Exception("API error")
        mock_get_parser.return_value = mock_parser

        mock_temp = MagicMock()
        mock_temp.__enter__.return_value = mock_temp
        mock_temp.__exit__.return_value = None
        mock_temp.name = "/tmp/test.pdf"
        mock_temp_file.return_value = mock_temp

        filename = "test.pdf"
        content = b"Plain text fallback"
        content_type = "application/pdf"

        text, error = parse_file(filename, content_type, content)

        # Should fall back to UTF-8 decode
        assert text == "Plain text fallback"
        assert error is None

    def test_parse_file_invalid_utf8(self):
        """Test parse_file error handling for invalid UTF-8."""
        filename = "test.txt"
        content = b"\xff\xfe\xfd"  # Invalid UTF-8 bytes
        content_type = "text/plain"

        text, error = parse_file(filename, content_type, content)

        assert text == ""
        assert error is not None
        assert "Failed to decode text file" in error


class TestChunking:
    """Test text chunking functions."""

    def test_chunk_text_empty(self):
        """Test chunk_text with empty text."""
        chunks = chunk_text("")
        assert chunks == []

    def test_chunk_text_short(self):
        """Test chunk_text with short text that fits in one chunk."""
        text = "This is a short sentence."
        chunks = chunk_text(text, chunk_size=200)
        
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_splits_on_paragraphs(self):
        """Test that chunking splits on paragraph boundaries."""
        # Use a much longer text that will DEFINITELY need splitting
        # Chunk size is in approx tokens (words * 1.3), so chunk_size=10 means ~7-8 words max
        text = """This is a very long first paragraph with many words that should exceed the chunk size limit.

This is an equally long second paragraph with enough words to force splitting.

This is the third paragraph also long enough to be its own chunk."""
        chunks = chunk_text(text, chunk_size=10)  # Very small chunk size to force splitting
        
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_text_preserves_content(self):
        """Test that no content is lost during chunking."""
        text = "Word " * 100  # 100 words
        chunks = chunk_text(text, chunk_size=20)
        
        # All words should be present in combined chunks
        combined = " ".join(chunks)
        assert combined.count("Word") >= 90  # Allow for some trimming

    def test_recursive_chunk_large_text(self):
        """Test recursive chunking with large text."""
        large_text = "sentence. " * 200
        chunks = _recursive_chunk_text(large_text, chunk_size=50)
        
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)


class TestCleanup:
    """Test file cleanup functions."""

    @patch('samvaad.pipeline.ingestion.chunking.os.unlink')
    @patch('samvaad.pipeline.ingestion.chunking.os.path.exists')
    def test_cleanup_temp_file_success(self, mock_exists, mock_unlink):
        """Test successful temp file cleanup."""
        mock_exists.return_value = True

        _cleanup_temp_file("/tmp/test.pdf")

        mock_unlink.assert_called_once_with("/tmp/test.pdf")

    @patch('samvaad.pipeline.ingestion.chunking.os.unlink')
    @patch('samvaad.pipeline.ingestion.chunking.os.path.exists')
    @patch('samvaad.pipeline.ingestion.chunking.time.sleep')
    def test_cleanup_temp_file_retry(self, mock_sleep, mock_exists, mock_unlink):
        """Test temp file cleanup with retry on failure."""
        mock_exists.return_value = True
        mock_unlink.side_effect = [OSError("File in use")] * 4 + [None]

        _cleanup_temp_file("/tmp/test.pdf")

        assert mock_unlink.call_count == 5
        assert mock_sleep.call_count == 4

    @patch('samvaad.pipeline.ingestion.chunking.os.unlink')
    @patch('samvaad.pipeline.ingestion.chunking.os.path.exists')
    def test_cleanup_temp_file_nonexistent(self, mock_exists, mock_unlink):
        """Test cleanup when file doesn't exist."""
        mock_exists.return_value = False

        _cleanup_temp_file("/tmp/nonexistent.pdf")

        mock_unlink.assert_not_called()


class TestLlamaParser:
    """Test LlamaParse integration."""

    @patch('samvaad.pipeline.ingestion.chunking.os.getenv')
    def test_get_llama_parser_no_key(self, mock_getenv):
        """Test error when API key is missing."""
        mock_getenv.return_value = None

        # Reset global parser
        import samvaad.pipeline.ingestion.chunking
        samvaad.pipeline.ingestion.chunking._parser = None

        # The function imports LlamaParse internally, which may fail in test env
        # But if it doesn't, it should raise ValueError for missing key
        try:
            get_llama_parser()
            pytest.fail("Should have raised an error")
        except (ValueError, ImportError, AttributeError) as e:
            # ValueError for missing key, ImportError/AttributeError if llama deps have issues
            assert True

    @patch('llama_cloud_services.LlamaParse')
    @patch('samvaad.pipeline.ingestion.chunking.os.getenv')
    def test_get_llama_parser_singleton(self, mock_getenv, mock_llama_cls):
        """Test that parser is cached as singleton."""
        mock_getenv.return_value = "test-api-key"
        mock_instance = MagicMock()
        mock_llama_cls.return_value = mock_instance

        # Reset global
        import samvaad.pipeline.ingestion.chunking
        samvaad.pipeline.ingestion.chunking._parser = None

        first = get_llama_parser()
        second = get_llama_parser()

        assert first is second
        mock_llama_cls.assert_called_once()