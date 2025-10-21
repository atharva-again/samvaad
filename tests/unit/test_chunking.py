import pytest
from unittest.mock import patch, MagicMock

# Import modules to test
from samvaad.pipeline.ingestion.chunking import (
    parse_file,
    chunk_text,
    find_new_chunks,
    update_chunk_file_db,
    _cleanup_temp_file,
    _fallback_chunk_text,
    get_docling_converter,
    get_docling_chunker,
)


@pytest.fixture(scope="module", autouse=True)
def mock_tokenizer():
    """Mock the transformers tokenizer to avoid slow model loading."""
    with patch('transformers.AutoTokenizer.from_pretrained') as mock_tokenizer:
        mock_tokenizer.return_value = MagicMock()
        mock_tokenizer.return_value.encode.return_value = [1, 2, 3, 4, 5]  # Mock token IDs
        mock_tokenizer.return_value.decode.return_value = "mock decoded text"
        yield


@pytest.fixture(autouse=True)
def reset_chunking_globals():
    """Reset global variables between tests to ensure clean state."""
    # Reset the global Docling components
    import samvaad.pipeline.ingestion.chunking
    samvaad.pipeline.ingestion.chunking._converter = None
    samvaad.pipeline.ingestion.chunking._chunker = None
    # Reset parse_file state
    samvaad.pipeline.ingestion.chunking.parse_file._last_document = None
    samvaad.pipeline.ingestion.chunking.parse_file._last_was_text = True


class TestIngestion:
    """Test ingestion functions."""

    @patch('samvaad.pipeline.ingestion.chunking.get_docling_converter')
    @patch('samvaad.pipeline.ingestion.chunking.tempfile.NamedTemporaryFile')
    @patch('samvaad.pipeline.ingestion.chunking.os.unlink')
    def test_parse_file_txt(self, mock_unlink, mock_temp_file, mock_converter):
        """Test parsing a text file."""
        filename = "test.txt"
        content = b"Hello, World!"
        content_type = "text/plain"

        # Mock Docling converter for text files
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "Hello, World!"
        mock_converter_instance = MagicMock()
        mock_converter_instance.convert.return_value = mock_result
        mock_converter.return_value = mock_converter_instance

        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.__enter__.return_value = mock_temp
        mock_temp.__exit__.return_value = None
        mock_temp.name = "/tmp/test.txt"
        mock_temp_file.return_value = mock_temp

        # Call parse_file
        text, error = parse_file(filename, content_type, content)

        assert text == "Hello, World!"
        assert error is None
        mock_converter_instance.convert.assert_called_once_with("/tmp/test.txt", format="md")

    @patch('samvaad.pipeline.ingestion.chunking.get_docling_converter')
    @patch('samvaad.pipeline.ingestion.chunking.tempfile.NamedTemporaryFile')
    @patch('samvaad.pipeline.ingestion.chunking.os.unlink')
    def test_parse_file_pdf(self, mock_unlink, mock_temp_file, mock_converter):
        """Test parsing a PDF file."""
        # Mock Docling converter and result
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "Parsed PDF content"
        mock_converter_instance = MagicMock()
        mock_converter_instance.convert.return_value = mock_result
        mock_converter.return_value = mock_converter_instance

        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.__enter__.return_value = mock_temp
        mock_temp.__exit__.return_value = None
        mock_temp.name = "/tmp/test.pdf"
        mock_temp_file.return_value = mock_temp

        filename = "test.pdf"
        content = b"PDF content"
        content_type = "application/pdf"

        # Call parse_file
        text, error = parse_file(filename, content_type, content)

        assert text == "Parsed PDF content"
        assert error is None
        mock_converter_instance.convert.assert_called_once_with("/tmp/test.pdf")

    @patch('samvaad.pipeline.ingestion.chunking.get_docling_chunker')
    def test_chunk_text_with_docling_doc(self, mock_get_chunker):
        """Test chunk_text with a Docling document."""
        # Mock chunker and chunks
        mock_chunker = MagicMock()
        mock_chunk = MagicMock()
        mock_chunker.chunk.return_value = [mock_chunk]
        mock_chunker.contextualize.return_value = "Chunked content"
        mock_get_chunker.return_value = mock_chunker

        # Set up parse_file state as if we just parsed a document
        parse_file._last_document = MagicMock()
        parse_file._last_was_text = False

        text = "Some text"

        chunks = chunk_text(text)

        assert chunks == ["Chunked content"]
        mock_chunker.chunk.assert_called_once()
        mock_chunker.contextualize.assert_called_once_with(chunk=mock_chunk)

    def test_chunk_text_fallback(self):
        """Test chunk_text fallback when Docling fails."""
        # Ensure no Docling document
        parse_file._last_document = None
        parse_file._last_was_text = True

        text = "This is a test text that should be chunked."

        chunks = chunk_text(text)

        # Should return chunks (fallback implementation)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    @patch('samvaad.pipeline.ingestion.chunking._fallback_chunk_text')
    @patch('samvaad.pipeline.ingestion.chunking.get_docling_chunker')
    def test_chunk_text_uses_fallback_on_chunker_error(self, mock_get_chunker, mock_fallback):
        """If the Docling chunker blows up, we should fall back gracefully."""
        parse_file._last_document = MagicMock()
        parse_file._last_was_text = False
        mock_get_chunker.side_effect = RuntimeError("chunker offline")
        mock_fallback.return_value = ["fallback chunk"]

        chunks = chunk_text("irrelevant")

        assert chunks == ["fallback chunk"]
        mock_fallback.assert_called_once()

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

    def test_update_chunk_file_db(self):
        """Test update_chunk_file_db adds chunks to database."""
        with patch('samvaad.pipeline.ingestion.chunking.chunk_exists') as mock_exists, \
            patch('samvaad.pipeline.ingestion.chunking.add_chunk') as mock_add:

            mock_exists.return_value = False  # No chunks exist yet

            chunks = ["chunk1", "chunk2"]
            file_id = "test_file"

            update_chunk_file_db(chunks, file_id)

            # Should call add_chunk for each chunk with real SHA256 hashes
            assert mock_add.call_count == 2
            # SHA256 hash of "chunk1"
            mock_add.assert_any_call("9118bfec488b6ef57e10826a6104b0b9dd8ff7a9b8df6f9028f844f16d432118", file_id)
            # SHA256 hash of "chunk2"
            mock_add.assert_any_call("412cb322137d81a561102174568c4f9c84e5db95f51dcc3e298078e0ece8c774", file_id)

    def test_parse_file_invalid_utf8(self):
        """Test parse_file error handling for invalid UTF-8."""
        filename = "test.txt"
        content = b"\xff\xfe\xfd"  # Invalid UTF-8 bytes
        content_type = "text/plain"

        # Call parse_file
        text, error = parse_file(filename, content_type, content)

        assert text == ""
        assert error is not None
        assert "Docling and UTF-8 decoding both failed" in error

    @patch('samvaad.pipeline.ingestion.chunking.get_docling_converter')
    @patch('samvaad.pipeline.ingestion.chunking.tempfile.NamedTemporaryFile')
    @patch('samvaad.pipeline.ingestion.chunking.os.unlink')
    def test_parse_file_docling_failure(self, mock_unlink, mock_temp_file, mock_converter):
        """Test parse_file error handling when Docling fails."""
        # Mock Docling converter to raise an exception
        mock_converter_instance = MagicMock()
        mock_converter_instance.convert.side_effect = Exception("Docling conversion failed")
        mock_converter.return_value = mock_converter_instance

        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.__enter__.return_value = mock_temp
        mock_temp.__exit__.return_value = None
        mock_temp.name = "/tmp/test.pdf"
        mock_temp_file.return_value = mock_temp

        filename = "test.pdf"
        content = b"PDF content"
        content_type = "application/pdf"

        # Call parse_file
        text, error = parse_file(filename, content_type, content)

        assert text == "PDF content"
        assert error is None

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
    def test_cleanup_temp_file_retry_on_failure(self, mock_sleep, mock_exists, mock_unlink):
        """Test temp file cleanup with retry on failure."""
        mock_exists.return_value = True
        # First 4 calls fail, 5th succeeds
        mock_unlink.side_effect = [OSError("File in use")] * 4 + [None]

        _cleanup_temp_file("/tmp/test.pdf")

        # Should be called 5 times (max retries)
        assert mock_unlink.call_count == 5
        # Should have slept 4 times with increasing delays
        assert mock_sleep.call_count == 4

    @patch('samvaad.pipeline.ingestion.chunking.os.unlink')
    @patch('samvaad.pipeline.ingestion.chunking.os.path.exists')
    def test_cleanup_temp_file_nonexistent(self, mock_exists, mock_unlink):
        """Test temp file cleanup when file doesn't exist."""
        mock_exists.return_value = False

        _cleanup_temp_file("/tmp/nonexistent.pdf")

        # Should not attempt to unlink if file doesn't exist
        mock_unlink.assert_not_called()

    def test_chunk_text_empty(self):
        """Test chunk_text with empty text."""
        # Ensure no Docling document
        parse_file._last_document = None
        parse_file._last_was_text = True

        text = ""

        chunks = chunk_text(text)

        assert chunks == []

    def test_chunk_text_very_large(self):
        """Test chunk_text with large text."""
        # Ensure no Docling document (fallback to simple chunking)
        parse_file._last_document = None
        parse_file._last_was_text = True

        # Create a moderately large text (100 words instead of 10,000)
        large_text = "word " * 100

        chunks = chunk_text(large_text)

        # Should return chunks
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_find_new_chunks_existing_chunks(self):
        """Test find_new_chunks when some chunks already exist."""
        with patch('samvaad.pipeline.ingestion.chunking.chunk_exists') as mock_exists, \
             patch('samvaad.pipeline.ingestion.chunking.generate_chunk_id') as mock_hash:

            # Mock hash function to return predictable values
            mock_hash.side_effect = lambda chunk: f"{chunk}_hash"

            # Mock chunk_exists to return True for chunk1_hash, False for chunk2_hash
            mock_exists.side_effect = lambda chunk_id, file_id=None: chunk_id == "chunk1_hash"

            chunks = ["chunk1", "chunk2"]
            file_id = "test_file"

            new_chunks = find_new_chunks(chunks, file_id)

            # Should return only the new chunk (chunk2)
            assert len(new_chunks) == 1
            assert new_chunks[0][0] == "chunk2"
            assert new_chunks[0][1] == "chunk2_hash"

    def test_update_chunk_file_db_existing_chunks(self):
        """Test update_chunk_file_db when chunks already exist for file."""
        with patch('samvaad.pipeline.ingestion.chunking.chunk_exists') as mock_exists, \
            patch('samvaad.pipeline.ingestion.chunking.add_chunk') as mock_add:

            # All chunks already exist for this file
            mock_exists.return_value = True

            chunks = ["chunk1", "chunk2"]
            file_id = "test_file"

            update_chunk_file_db(chunks, file_id)

            # Should not call add_chunk for any chunk
            mock_add.assert_not_called()

    @patch('samvaad.pipeline.ingestion.chunking.DocumentConverter')
    def test_get_docling_converter_singleton(self, mock_converter_cls):
        """Document converter should be instantiated once and cached."""
        instance = MagicMock()
        mock_converter_cls.return_value = instance

        first = get_docling_converter()
        second = get_docling_converter()

        assert first is instance
        assert second is instance
        mock_converter_cls.assert_called_once()

    @patch('samvaad.pipeline.ingestion.chunking.AutoTokenizer.from_pretrained')
    @patch('samvaad.pipeline.ingestion.chunking.HierarchicalChunker')
    @patch('samvaad.pipeline.ingestion.chunking.HuggingFaceTokenizer')
    def test_get_docling_chunker_singleton(self, mock_hf_tokenizer, mock_chunker_cls, mock_auto_from_pretrained):
        """Docling chunker should be created once with shared tokenizer."""
        tokenizer_instance = MagicMock()
        chunker_instance = MagicMock()
        mock_auto_from_pretrained.return_value = MagicMock()
        mock_hf_tokenizer.return_value = tokenizer_instance
        mock_chunker_cls.return_value = chunker_instance

        first = get_docling_chunker()
        second = get_docling_chunker()

        assert first is chunker_instance
        assert second is chunker_instance
        mock_hf_tokenizer.assert_called_once()
        mock_chunker_cls.assert_called_once()
        _, kwargs = mock_chunker_cls.call_args
        assert kwargs['tokenizer'] is tokenizer_instance
        assert kwargs['merge_list_items'] is False

    @patch('samvaad.pipeline.ingestion.chunking.AutoTokenizer.from_pretrained')
    def test_fallback_chunk_text_caches_tokenizer(self, mock_auto_from_pretrained):
        """The fallback tokenizer should be cached across calls."""
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3, 4]
        mock_tokenizer.decode.side_effect = lambda tokens: " ".join(f"tok{i}" for i in tokens)
        mock_auto_from_pretrained.return_value = mock_tokenizer

        # Reset cached attributes if present
        for attr in ("_tokenizer", "_tokenizer_lock"):
            if hasattr(_fallback_chunk_text, attr):
                delattr(_fallback_chunk_text, attr)

        _fallback_chunk_text("one two three four", chunk_size=2)
        _fallback_chunk_text("five six seven eight", chunk_size=2)

        assert mock_auto_from_pretrained.call_count == 1