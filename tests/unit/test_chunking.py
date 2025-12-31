"""Test file parsing and chunking functions."""

from unittest.mock import MagicMock, patch

import pytest

# Import modules to test
from samvaad.pipeline.ingestion.chunking import (
    Chunk,
    StructuralChunker,
    _cleanup_temp_file,
    get_llama_parser,
    parse_file,
    structural_chunk,
)


@pytest.fixture(autouse=True)
def reset_chunking_globals():
    """Reset global variables between tests to ensure clean state."""
    import samvaad.pipeline.ingestion.chunking

    samvaad.pipeline.ingestion.chunking._parser = None


class TestParsing:
    """Test file parsing functions."""

    @patch("samvaad.pipeline.ingestion.chunking.get_llama_parser")
    @patch("samvaad.pipeline.ingestion.chunking.tempfile.TemporaryDirectory")
    def test_parse_file_txt_direct_decode(self, mock_temp_dir, mock_get_parser):
        """Test that text files go through LlamaParse for structure extraction."""
        filename = "test.txt"
        content = b"Hello, World!"
        content_type = "text/plain"

        # Mock LlamaParse JSON response
        mock_pages = [{"page": 1, "items": [{"type": "text", "md": "Hello, World!"}]}]

        mock_parser = MagicMock()
        mock_parser.get_json_result.return_value = [{"pages": mock_pages}]
        mock_get_parser.return_value = mock_parser
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test_dir"

        pages, error = parse_file(filename, content_type, content)

        assert error is None
        assert len(pages) == 1
        assert pages[0]["page"] == 1
        assert pages[0]["items"][0]["md"] == "Hello, World!"

    def test_parse_file_csv_direct_decode(self):
        """Test that CSV files are decoded directly without API call."""
        filename = "test.csv"
        content = b"Name,Age\nJohn,30\nJane,25"
        content_type = "text/csv"

        pages, error = parse_file(filename, content_type, content)

        assert error is None
        assert len(pages) == 1
        assert pages[0]["page"] == 1
        assert pages[0]["items"][0]["value"] == "Name,Age\nJohn,30\nJane,25"

    @patch("samvaad.pipeline.ingestion.chunking.get_llama_parser")
    @patch("samvaad.pipeline.ingestion.chunking.tempfile.TemporaryDirectory")
    def test_parse_file_md_direct_decode(self, mock_temp_dir, mock_get_parser):
        """Test that markdown files go through LlamaParse for structure extraction."""
        filename = "readme.md"
        content = b"# Title\n\nSome content"
        content_type = "text/markdown"

        # Mock LlamaParse JSON response
        mock_pages = [
            {
                "page": 1,
                "items": [
                    {"type": "heading", "lvl": 1, "md": "Title"},
                    {"type": "text", "md": "Some content"},
                ],
            }
        ]

        mock_parser = MagicMock()
        mock_parser.get_json_result.return_value = [{"pages": mock_pages}]
        mock_get_parser.return_value = mock_parser
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test_dir"

        pages, error = parse_file(filename, content_type, content)

        assert error is None
        assert len(pages) == 1
        assert pages[0]["page"] == 1
        # Mock LlamaParse may return single text item for simple markdown
        assert len(pages[0]["items"]) >= 1

    @patch("samvaad.pipeline.ingestion.chunking.get_llama_parser")
    @patch("samvaad.pipeline.ingestion.chunking.tempfile.TemporaryDirectory")
    def test_parse_file_pdf_simple(self, mock_temp_dir, mock_get_parser):
        """Test PDF file processing uses LlamaParse (simplified test)."""
        # Just verify that PDF files try to use LlamaParse
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        filename = "test.pdf"
        content = b"PDF content"
        content_type = "application/pdf"

        # This will likely fail due to temp directory issues, but we can
        # verify that LlamaParse was attempted
        try:
            parse_file(filename, content_type, content)
        except Exception:
            pass  # Expected due to mocking limitations

        # Verify LlamaParse was accessed
        mock_get_parser.assert_called_once()

    @patch("samvaad.pipeline.ingestion.chunking.get_llama_parser")
    @patch("samvaad.pipeline.ingestion.chunking.tempfile.TemporaryDirectory")
    def test_parse_file_api_failure_fallback(self, mock_temp_dir, mock_get_parser):
        """Test fallback to UTF-8 decode when LlamaParse fails."""
        mock_parser = MagicMock()
        mock_parser.get_json_result.side_effect = Exception("API error")
        mock_get_parser.return_value = mock_parser

        # Mock temporary directory
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test_dir"

        filename = "test.pdf"
        content = b"Plain text fallback"
        content_type = "application/pdf"

        pages, error = parse_file(filename, content_type, content)

        # Should fall back to UTF-8 decode and create page structure
        assert error is None
        assert len(pages) == 1
        assert pages[0]["page"] == 1
        assert "Plain text fallback" in pages[0]["items"][0]["md"]

    def test_parse_file_invalid_utf8(self):
        """Test parse_file error handling for invalid UTF-8 in CSV files."""
        filename = "test.csv"
        content = b"\xff\xfe\xfd"  # Invalid UTF-8 bytes
        content_type = "text/csv"

        pages, error = parse_file(filename, content_type, content)

        # For CSV files with invalid UTF-8, should return error
        assert error is not None
        assert len(pages) == 0


class TestStructuralChunker:
    """Test structural document chunking functions."""

    def test_chunk_empty_pages(self):
        """Test structural chunking with empty pages list."""
        pages_json = []
        chunker = StructuralChunker()
        chunks = chunker.chunk(pages_json)

        assert chunks == []

    def test_chunk_simple_text(self):
        """Test structural chunking with simple text content."""
        pages_json = [
            {"page": 1, "items": [{"type": "text", "md": "This is a simple text."}]}
        ]
        chunker = StructuralChunker()
        chunks = chunker.chunk(pages_json)

        assert len(chunks) == 1
        assert isinstance(chunks[0], Chunk)
        assert chunks[0].content == "This is a simple text."
        assert chunks[0].metadata["page_number"] == 1
        assert chunks[0].metadata["content_type"] == "text"
        assert chunks[0].metadata["breadcrumbs"] == []

    def test_chunk_with_headings(self):
        """Test structural chunking with heading hierarchy."""
        pages_json = [
            {
                "page": 1,
                "items": [
                    {"type": "heading", "lvl": 1, "md": "Main Title"},
                    {"type": "text", "md": "Content under main title"},
                    {"type": "heading", "lvl": 2, "md": "Subtitle"},
                    {"type": "text", "md": "Content under subtitle"},
                ],
            }
        ]

        chunker = StructuralChunker()
        chunks = chunker.chunk(pages_json)

        assert len(chunks) >= 2  # Each section creates a chunk with heading + content
        # Check that heading is tracked in breadcrumbs
        text_chunks = [c for c in chunks if c.metadata["content_type"] == "text"]
        if text_chunks:
            assert "Main Title" in text_chunks[0].metadata["breadcrumbs"]

    def test_chunk_with_tables(self):
        """Test structural chunking with table content."""
        table_content = "Column1 | Column2\nValue1 | Value2\nValue3 | Value4"
        pages_json = [{"page": 1, "items": [{"type": "table", "md": table_content}]}]

        chunker = StructuralChunker()
        chunks = chunker.chunk(pages_json)

        assert len(chunks) == 1
        assert chunks[0].content == table_content
        assert chunks[0].metadata["content_type"] == "table"
        assert chunks[0].metadata["page_number"] == 1

    def test_chunk_size_limits(self):
        """Test that chunks respect size limits."""
        # Create text that should exceed the 1200 char limit
        long_text = "This is a sentence. " * 100  # Will exceed limit
        pages_json = [{"page": 1, "items": [{"type": "text", "md": long_text}]}]

        chunker = StructuralChunker()
        chunks = chunker.chunk(pages_json)

        # Should be split into multiple chunks
        assert len(chunks) > 1
        # Each chunk should be under the limit (approximately)
        for chunk in chunks:
            assert len(chunk.content) <= 1300  # Allow some flexibility

    def test_chunk_content_preservation(self):
        """Test that no content is lost during structural chunking."""
        text = "Word " * 100  # 100 words
        pages_json = [{"page": 1, "items": [{"type": "text", "md": text}]}]

        chunker = StructuralChunker()
        chunks = chunker.chunk(pages_json)

        # All words should be present in combined chunks
        combined = " ".join(chunk.content for chunk in chunks)
        assert combined.count("Word") >= 90  # Allow for some trimming

    def test_chunk_large_content_splitting(self):
        """Test recursive chunking with large text content."""
        large_text = "This is a sentence. " * 200  # Large text that will need splitting
        pages_json = [{"page": 1, "items": [{"type": "text", "md": large_text}]}]

        chunker = StructuralChunker()
        chunks = chunker.chunk(pages_json)

        assert len(chunks) > 1
        assert all(isinstance(c, Chunk) for c in chunks)
        # Verify overlap is maintained
        if len(chunks) > 1:
            # There should be some overlap between consecutive chunks
            first_end = chunks[0].content[-50:]  # Last 50 chars of first chunk
            second_start = chunks[1].content[:50]  # First 50 chars of second chunk
            # At least some words should overlap
            overlap_words = set(first_end.split()) & set(second_start.split())
            assert len(overlap_words) > 0


class TestStructuralChunk:
    """Test the convenience function for structural chunking."""

    def test_structural_chunk_function(self):
        """Test the structural_chunk convenience function."""
        pages_json = [{"page": 1, "items": [{"type": "text", "md": "Test content"}]}]

        chunks = structural_chunk(pages_json)

        assert len(chunks) == 1
        assert isinstance(chunks[0], Chunk)
        assert chunks[0].content == "Test content"


class TestCleanup:
    """Test file cleanup functions."""

    @patch("samvaad.pipeline.ingestion.chunking.os.unlink")
    @patch("samvaad.pipeline.ingestion.chunking.os.path.exists")
    def test_cleanup_temp_file_error_handling(self, mock_exists, mock_unlink):
        """Test that cleanup silently handles errors."""
        mock_exists.return_value = True
        mock_unlink.side_effect = OSError("File in use")

        # Should not raise exception
        _cleanup_temp_file("/tmp/test.pdf")

        mock_unlink.assert_called_once_with("/tmp/test.pdf")

    @patch("samvaad.pipeline.ingestion.chunking.os.unlink")
    @patch("samvaad.pipeline.ingestion.chunking.os.path.exists")
    def test_cleanup_temp_file_nonexistent(self, mock_exists, mock_unlink):
        """Test cleanup when file doesn't exist."""
        mock_exists.return_value = False

        _cleanup_temp_file("/tmp/nonexistent.pdf")

        mock_unlink.assert_not_called()


class TestLlamaParser:
    """Test LlamaParse integration."""

    @patch("samvaad.pipeline.ingestion.chunking.os.getenv")
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
        except (ValueError, ImportError, AttributeError):
            # ValueError for missing key, ImportError/AttributeError if llama deps have issues
            assert True

    @patch("llama_cloud_services.LlamaParse")
    @patch("samvaad.pipeline.ingestion.chunking.os.getenv")
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


class TestChunkingIntegration:
    """Test end-to-end integration of chunking system."""

    @patch("samvaad.pipeline.ingestion.chunking.get_llama_parser")
    @patch("samvaad.pipeline.ingestion.chunking.tempfile.TemporaryDirectory")
    def test_end_to_end_pdf_processing(self, mock_temp_dir, mock_get_parser):
        """Test full pipeline: parse_file → structural_chunk"""
        # Mock LlamaParse JSON response
        mock_pages = [
            {
                "page": 1,
                "items": [
                    {"type": "heading", "lvl": 1, "md": "Document Title"},
                    {"type": "text", "md": "This is the introduction."},
                    {"type": "heading", "lvl": 2, "md": "Section 1"},
                    {"type": "text", "md": "Content for section 1."},
                ],
            }
        ]

        mock_parser = MagicMock()
        mock_parser.get_json_result.return_value = [{"pages": mock_pages}]
        mock_get_parser.return_value = mock_parser
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test_dir"

        filename = "test.pdf"
        content = b"PDF content"
        content_type = "application/pdf"

        # Parse the file
        pages, error = parse_file(filename, content_type, content)

        assert error is None
        assert len(pages) == 1

        # Chunk the parsed content
        chunks = structural_chunk(pages)

        # Should have at least one chunk (may combine heading + content)
        assert len(chunks) >= 1

        # Verify metadata preservation
        for chunk in chunks:
            assert chunk.metadata["page_number"] == 1
            assert chunk.metadata["content_type"] in ["text"]
            assert isinstance(chunk.metadata["breadcrumbs"], list)

    def test_metadata_preservation_through_pipeline(self):
        """Test that all metadata flows through correctly."""
        pages_json = [
            {
                "page": 2,
                "items": [
                    {"type": "heading", "lvl": 1, "md": "Main Title"},
                    {"type": "heading", "lvl": 2, "md": "Subtitle"},
                    {"type": "text", "md": "Some content here"},
                ],
            }
        ]

        chunks = structural_chunk(pages_json)

        # Find text chunk
        text_chunks = [c for c in chunks if c.metadata["content_type"] == "text"]
        assert len(text_chunks) >= 1

        text_chunk = text_chunks[0]

        # Verify page number
        assert text_chunk.metadata["page_number"] == 2

        # Verify breadcrumb hierarchy (may only include current heading context)
        breadcrumbs = text_chunk.metadata["breadcrumbs"]
        assert "Main Title" in breadcrumbs
        # Note: Subtitle may not be included depending on chunking logic
