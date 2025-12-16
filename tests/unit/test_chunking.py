import pytest
from unittest.mock import patch, MagicMock

# Import modules to test
from samvaad.pipeline.ingestion.chunking import (
    parse_file,
    chunk_text,
    find_new_chunks,
    update_chunk_file_db,
    _cleanup_temp_file,
    _recursive_chunk_text,
    get_llama_parser,
)


@pytest.fixture(autouse=True)
def reset_chunking_globals():
    """Reset global variables between tests to ensure clean state."""
    import samvaad.pipeline.ingestion.chunking
    samvaad.pipeline.ingestion.chunking._parser = None


@pytest.fixture
def mock_llama_parser():
    """Mock the LlamaParse API."""
    with patch('samvaad.pipeline.ingestion.chunking.LlamaParse') as mock_cls:
        mock_parser = MagicMock()
        mock_cls.return_value = mock_parser
        yield mock_parser


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
    @patch('samvaad.pipeline.ingestion.chunking.os.unlink')
    def test_parse_file_pdf(self, mock_unlink, mock_temp_file, mock_get_parser):
        """Test parsing a PDF file with LlamaParse."""
        # Mock LlamaParse response
        mock_doc = MagicMock()
        mock_doc.text = "Parsed PDF content"
        mock_parser = MagicMock()
        mock_parser.load_data.return_value = [mock_doc]
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
        mock_parser.load_data.assert_called_once_with("/tmp/test.pdf")

    @patch('samvaad.pipeline.ingestion.chunking.get_llama_parser')
    @patch('samvaad.pipeline.ingestion.chunking.tempfile.NamedTemporaryFile')
    @patch('samvaad.pipeline.ingestion.chunking._cleanup_temp_file')
    def test_parse_file_api_failure_fallback(self, mock_cleanup, mock_temp_file, mock_get_parser):
        """Test fallback to UTF-8 decode when LlamaParse fails."""
        mock_parser = MagicMock()
        mock_parser.load_data.side_effect = Exception("API error")
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
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, chunk_size=10)  # Force splitting
        
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


class TestDeduplication:
    """Test chunk deduplication functions."""

    def test_find_new_chunks(self):
        """Test find_new_chunks deduplication."""
        with patch('samvaad.pipeline.ingestion.chunking.chunk_exists') as mock_exists:
            mock_exists.return_value = False  # No chunks exist

            chunks = ["chunk1", "chunk2", "chunk1"]  # Duplicate in batch
            file_id = "test_file"

            new_chunks = find_new_chunks(chunks, file_id)

            # Should return 2 unique chunks
            assert len(new_chunks) == 2
            assert new_chunks[0][0] == "chunk1"
            assert new_chunks[1][0] == "chunk2"

    def test_find_new_chunks_existing(self):
        """Test find_new_chunks when some chunks exist."""
        with patch('samvaad.pipeline.ingestion.chunking.chunk_exists') as mock_exists, \
             patch('samvaad.pipeline.ingestion.chunking.generate_chunk_id') as mock_hash:
            
            mock_hash.side_effect = lambda chunk: f"{chunk}_hash"
            mock_exists.side_effect = lambda chunk_id, file_id=None: chunk_id == "chunk1_hash"

            chunks = ["chunk1", "chunk2"]
            file_id = "test_file"

            new_chunks = find_new_chunks(chunks, file_id)

            assert len(new_chunks) == 1
            assert new_chunks[0][0] == "chunk2"

    def test_update_chunk_file_db(self):
        """Test update_chunk_file_db adds chunks to database."""
        with patch('samvaad.pipeline.ingestion.chunking.chunk_exists') as mock_exists, \
             patch('samvaad.pipeline.ingestion.chunking.add_chunk') as mock_add:
            
            mock_exists.return_value = False

            chunks = ["chunk1", "chunk2"]
            file_id = "test_file"

            update_chunk_file_db(chunks, file_id)

            assert mock_add.call_count == 2


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

        with pytest.raises(ValueError, match="LLAMA_CLOUD_API_KEY"):
            get_llama_parser()

    @patch('samvaad.pipeline.ingestion.chunking.LlamaParse')
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