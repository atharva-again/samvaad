import pytest
import os
import tempfile
import sqlite3
import warnings
from unittest.mock import patch, MagicMock

# Import modules to test
from samvaad.utils.hashing import generate_file_id, generate_chunk_id
from samvaad.utils.filehash_db import init_db, file_exists, add_file, chunk_exists, add_chunk, delete_file_and_cleanup
from samvaad.utils.gpu_utils import get_device


class TestHashing:
    """Test hashing functions."""

    def test_generate_file_id_consistent(self):
        """Test that generate_file_id produces consistent hashes for same content."""
        content = b"Hello, World!"
        id1 = generate_file_id(content)
        id2 = generate_file_id(content)
        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) == 64  # SHA256 hex length

    def test_generate_file_id_different_content(self):
        """Test that generate_file_id produces different hashes for different content."""
        content1 = b"Hello, World!"
        content2 = b"Hello, Universe!"
        id1 = generate_file_id(content1)
        id2 = generate_file_id(content2)
        assert id1 != id2

    def test_generate_chunk_id_consistent(self):
        """Test that generate_chunk_id produces consistent hashes for same content."""
        content = "This is a test chunk."
        id1 = generate_chunk_id(content)
        id2 = generate_chunk_id(content)
        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) == 64  # SHA256 hex length

    def test_generate_chunk_id_different_content(self):
        """Test that generate_chunk_id produces different hashes for different content."""
        content1 = "This is a test chunk."
        content2 = "This is another test chunk."
        id1 = generate_chunk_id(content1)
        id2 = generate_chunk_id(content2)
        assert id1 != id2


class TestFileHashDB:
    """Test file hash database functions."""

    def setup_method(self):
        """Set up a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_filehashes.sqlite3')

        # Patch the DB_PATH to use our temporary database
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            init_db()

    def teardown_method(self):
        """Clean up temporary database."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_init_db_creates_tables(self):
        """Test that init_db creates the required tables."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            # Check if tables exist
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in c.fetchall()]
            conn.close()

            assert 'file_metadata' in tables
            assert 'chunk_file_map' in tables

    def test_file_exists_false_for_new_file(self):
        """Test file_exists returns False for non-existent file."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            assert not file_exists("nonexistent")

    def test_add_and_check_file_exists(self):
        """Test adding a file and checking if it exists."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            file_id = "test_file_id"
            filename = "test.txt"

            # Initially should not exist
            assert not file_exists(file_id)

            # Add file
            add_file(file_id, filename)

            # Now should exist
            assert file_exists(file_id)

    def test_add_file_duplicate_no_error(self):
        """Test adding the same file twice doesn't cause error."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            file_id = "test_file_id"
            filename = "test.txt"

            # Add file twice
            add_file(file_id, filename)
            add_file(file_id, filename)  # Should not raise error

            assert file_exists(file_id)

    def test_chunk_exists_false_for_new_chunk(self):
        """Test chunk_exists returns False for non-existent chunk."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            assert not chunk_exists("nonexistent_chunk")

    def test_add_and_check_chunk_exists(self):
        """Test adding a chunk and checking if it exists."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            chunk_id = "test_chunk_id"
            file_id = "test_file_id"

            # Initially should not exist
            assert not chunk_exists(chunk_id)

            # Add chunk
            add_chunk(chunk_id, file_id)

            # Now should exist globally
            assert chunk_exists(chunk_id)

            # And should exist for this file
            assert chunk_exists(chunk_id, file_id)

    def test_chunk_exists_per_file(self):
        """Test chunk_exists with file_id parameter."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            chunk_id = "test_chunk_id"
            file_id1 = "file1"
            file_id2 = "file2"

            # Add chunk for file1
            add_chunk(chunk_id, file_id1)

            # Should exist for file1
            assert chunk_exists(chunk_id, file_id1)

            # Should not exist for file2
            assert not chunk_exists(chunk_id, file_id2)

    def test_delete_file_and_cleanup(self):
        """Test deleting a file and cleaning up orphaned chunks."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            file_id = "test_file_id"
            chunk_id1 = "chunk1"
            chunk_id2 = "chunk2"

            # Add file and chunks
            add_file(file_id, "test.txt")
            add_chunk(chunk_id1, file_id)
            add_chunk(chunk_id2, file_id)

            # Verify they exist
            assert file_exists(file_id)
            assert chunk_exists(chunk_id1, file_id)
            assert chunk_exists(chunk_id2, file_id)

            # Delete file
            orphaned = delete_file_and_cleanup(file_id)

            # File should be gone
            assert not file_exists(file_id)

            # Chunks should be orphaned since no other files reference them
            assert orphaned == [chunk_id1, chunk_id2]

            # Orphaned chunks should also disappear from the global index
            assert not chunk_exists(chunk_id1)
            assert not chunk_exists(chunk_id2)

    def test_add_chunk_duplicate_no_error(self):
        """Test adding the same chunk-file mapping twice doesn't cause error."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            chunk_id = "test_chunk_id"
            file_id = "test_file_id"

            # Add chunk twice for the same file
            add_chunk(chunk_id, file_id)
            add_chunk(chunk_id, file_id)  # Should not raise error

            # Should still exist
            assert chunk_exists(chunk_id, file_id)

    def test_delete_file_with_shared_chunk(self):
        """Test deleting a file with a chunk that is shared with another file."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            file_id1 = "file1"
            file_id2 = "file2"
            shared_chunk = "shared_chunk"
            unique_chunk = "unique_chunk"

            # Add two files
            add_file(file_id1, "file1.txt")
            add_file(file_id2, "file2.txt")

            # Add shared chunk to both files
            add_chunk(shared_chunk, file_id1)
            add_chunk(shared_chunk, file_id2)

            # Add unique chunk only to file1
            add_chunk(unique_chunk, file_id1)

            # Verify setup
            assert chunk_exists(shared_chunk, file_id1)
            assert chunk_exists(shared_chunk, file_id2)
            assert chunk_exists(unique_chunk, file_id1)
            assert not chunk_exists(unique_chunk, file_id2)

            # Delete file1
            orphaned = delete_file_and_cleanup(file_id1)

            # File1 should be gone
            assert not file_exists(file_id1)
            # File2 should still exist
            assert file_exists(file_id2)

            # Only the unique chunk should be orphaned (shared chunk still exists in file2)
            assert orphaned == [unique_chunk]

            # Shared chunk should still exist for file2
            assert chunk_exists(shared_chunk, file_id2)

    def test_delete_missing_file_is_noop(self):
        """Deleting a non-existent file should be safe and return no orphans."""
        with patch('samvaad.utils.filehash_db.DB_PATH', self.db_path):
            # Ensure DB is empty
            assert not file_exists("ghost")

            orphaned = delete_file_and_cleanup("ghost")

            assert orphaned == []
            # DB should remain empty
            assert not file_exists("ghost")


class TestGPUUtils:
    """Test GPU utility functions."""

    @patch('samvaad.utils.gpu_utils.ort.get_available_providers')
    def test_get_device_cuda_available(self, mock_get_providers):
        """Test get_device returns 'cuda' when CUDA is available."""
        mock_get_providers.return_value = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        assert get_device() == 'cuda'

    @patch('samvaad.utils.gpu_utils.ort.get_available_providers')
    def test_get_device_cpu_fallback(self, mock_get_providers):
        """Test get_device returns 'cpu' when CUDA is not available."""
        mock_get_providers.return_value = ['CPUExecutionProvider']
        assert get_device() == 'cpu'

    @patch('samvaad.utils.gpu_utils.ort.get_available_providers')
    def test_get_device_handles_runtime_error(self, mock_get_providers):
        """Even if onnxruntime raises, we should conservatively fall back to CPU."""
        mock_get_providers.side_effect = RuntimeError("driver issue")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            assert get_device() == 'cpu'


class TestCleanMarkdown:
    """Test clean markdown utility functions."""

    def test_strip_markdown_empty_string(self):
        """Test strip_markdown with empty string."""
        from samvaad.utils.clean_markdown import strip_markdown
        assert strip_markdown("") == ""

    def test_strip_markdown_no_markdown(self):
        """Test strip_markdown with plain text."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "This is plain text."
        assert strip_markdown(text) == text

    def test_strip_markdown_headers(self):
        """Test strip_markdown removes headers."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "# Header 1\n## Header 2\n### Header 3\nNormal text"
        expected = "Header 1\nHeader 2\nHeader 3\nNormal text"
        assert strip_markdown(text) == expected

    def test_strip_markdown_bold(self):
        """Test strip_markdown removes bold formatting."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "This is **bold** and __also bold__ text."
        expected = "This is bold and also bold text."
        assert strip_markdown(text) == expected

    def test_strip_markdown_italic(self):
        """Test strip_markdown removes italic formatting."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "This is *italic* and _also italic_ text."
        expected = "This is italic and also italic text."
        assert strip_markdown(text) == expected

    def test_strip_markdown_code(self):
        """Test strip_markdown removes code formatting."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "This is `inline code` and ```block code```."
        expected = "This is inline code and ."
        assert strip_markdown(text) == expected

    def test_strip_markdown_links(self):
        """Test strip_markdown removes links."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "Check out [this link](https://example.com) for more info."
        expected = "Check out this link for more info."
        assert strip_markdown(text) == expected

    def test_strip_markdown_images(self):
        """Test strip_markdown removes images."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "Here's an image: ![alt text](image.jpg)"
        expected = "Here's an image: !alt text"
        assert strip_markdown(text) == expected

    def test_strip_markdown_lists(self):
        """Test strip_markdown removes list markers."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "- Item 1\n* Item 2\n+ Item 3\nNormal text"
        expected = "Item 1\nItem 2\nItem 3\nNormal text"
        assert strip_markdown(text) == expected

    def test_strip_markdown_blockquotes(self):
        """Test strip_markdown removes blockquotes."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "> This is a blockquote\n> Another line\nNormal text"
        expected = "This is a blockquote\nAnother line\nNormal text"
        assert strip_markdown(text) == expected

    def test_strip_markdown_horizontal_rules(self):
        """Test strip_markdown removes horizontal rules."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "Before\n---\nAfter\n***\nEnd"
        expected = "Before\n\nAfter\n\nEnd"
        assert strip_markdown(text) == expected

    def test_strip_markdown_strikethrough(self):
        """Test strip_markdown removes strikethrough."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "This is ~~strikethrough~~ text."
        expected = "This is strikethrough text."
        assert strip_markdown(text) == expected

    def test_strip_markdown_complex(self):
        """Test strip_markdown with complex markdown."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = """# Header

This is **bold** and *italic* text.

- List item 1
- List item 2

> Blockquote

[Link](url) and ![Image](img.jpg)

```code block```

Normal text."""
        expected = """Header

This is bold and italic text.

List item 1
List item 2

Blockquote

Link and !Image

Normal text."""
        assert strip_markdown(text) == expected

    def test_strip_markdown_whitespace_normalization(self):
        """Test strip_markdown normalizes whitespace."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "Text with   multiple   spaces    and\ttabs"
        expected = "Text with multiple spaces and tabs"
        assert strip_markdown(text) == expected

    def test_strip_markdown_newlines_preserved(self):
        """Test strip_markdown preserves newlines."""
        from samvaad.utils.clean_markdown import strip_markdown
        text = "Line 1\n\nLine 2\nLine 3"
        expected = "Line 1\n\nLine 2\nLine 3"
        assert strip_markdown(text) == expected


class TestCLIImports:
    """Test CLI import dependencies can be loaded without errors."""

    def test_load_ingestion_dependencies(self):
        """Test that ingestion dependencies can be imported."""
        # Import the load function
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Mock the imports to avoid actual loading
        with patch('samvaad.pipeline.ingestion.chunking.parse_file'), \
             patch('samvaad.pipeline.ingestion.chunking.chunk_text'), \
             patch('samvaad.pipeline.ingestion.chunking.find_new_chunks'), \
             patch('samvaad.pipeline.ingestion.chunking.update_chunk_file_db'), \
             patch('samvaad.pipeline.ingestion.embedding.embed_chunks_with_dedup'), \
             patch('samvaad.pipeline.vectorstore.vectorstore.add_embeddings'), \
             patch('samvaad.pipeline.ingestion.preprocessing.preprocess_file'), \
             patch('samvaad.utils.hashing.generate_file_id'), \
             patch('samvaad.utils.hashing.generate_chunk_id'), \
             patch('samvaad.utils.filehash_db.add_file'):
            
            # Import and call the load function
            from samvaad.pipeline.ingestion.ingestion import ingest_file_pipeline


    def test_load_query_dependencies(self):
        """Test that query dependencies can be imported."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        with patch('samvaad.pipeline.retrieval.query.rag_query_pipeline'):
            from samvaad.pipeline.retrieval.query import rag_query_pipeline

    def test_load_deletion_dependencies(self):
        """Test that deletion dependencies can be imported."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        with patch('samvaad.pipeline.deletion.deletion.delete_file_and_embeddings'):
            from samvaad.pipeline.deletion.deletion import delete_file_and_embeddings
