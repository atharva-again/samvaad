import pytest
import os
import tempfile
import sqlite3
import warnings
from unittest.mock import patch, MagicMock

# Import modules to test
from backend.utils.hashing import generate_file_id, generate_chunk_id
from backend.utils.filehash_db import init_db, file_exists, add_file, chunk_exists, add_chunk, delete_file_and_cleanup
from backend.utils.gpu_utils import get_device


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
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
            init_db()

    def teardown_method(self):
        """Clean up temporary database."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_init_db_creates_tables(self):
        """Test that init_db creates the required tables."""
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
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
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
            assert not file_exists("nonexistent")

    def test_add_and_check_file_exists(self):
        """Test adding a file and checking if it exists."""
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
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
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
            file_id = "test_file_id"
            filename = "test.txt"

            # Add file twice
            add_file(file_id, filename)
            add_file(file_id, filename)  # Should not raise error

            assert file_exists(file_id)

    def test_chunk_exists_false_for_new_chunk(self):
        """Test chunk_exists returns False for non-existent chunk."""
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
            assert not chunk_exists("nonexistent_chunk")

    def test_add_and_check_chunk_exists(self):
        """Test adding a chunk and checking if it exists."""
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
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
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
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
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
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
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
            chunk_id = "test_chunk_id"
            file_id = "test_file_id"

            # Add chunk twice for the same file
            add_chunk(chunk_id, file_id)
            add_chunk(chunk_id, file_id)  # Should not raise error

            # Should still exist
            assert chunk_exists(chunk_id, file_id)

    def test_delete_file_with_shared_chunk(self):
        """Test deleting a file with a chunk that is shared with another file."""
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
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
        with patch('backend.utils.filehash_db.DB_PATH', self.db_path):
            # Ensure DB is empty
            assert not file_exists("ghost")

            orphaned = delete_file_and_cleanup("ghost")

            assert orphaned == []
            # DB should remain empty
            assert not file_exists("ghost")


class TestGPUUtils:
    """Test GPU utility functions."""

    @patch('backend.utils.gpu_utils.torch.cuda.is_available')
    def test_get_device_cuda_available(self, mock_cuda_available):
        """Test get_device returns 'cuda' when CUDA is available."""
        mock_cuda_available.return_value = True
        assert get_device() == 'cuda'

    @patch('backend.utils.gpu_utils.torch.cuda.is_available')
    def test_get_device_cpu_fallback(self, mock_cuda_available):
        """Test get_device returns 'cpu' when CUDA is not available."""
        mock_cuda_available.return_value = False
        assert get_device() == 'cpu'

    @patch('backend.utils.gpu_utils.torch.cuda.is_available')
    def test_get_device_handles_runtime_error(self, mock_cuda_available):
        """Even if torch raises, we should conservatively fall back to CPU."""
        mock_cuda_available.side_effect = RuntimeError("driver issue")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            assert get_device() == 'cpu'


class TestCLIImports:
    """Test CLI import dependencies can be loaded without errors."""

    def test_load_ingestion_dependencies(self):
        """Test that ingestion dependencies can be imported."""
        # Import the load function
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Mock the imports to avoid actual loading
        with patch('backend.pipeline.ingestion.parse_file'), \
             patch('backend.pipeline.ingestion.chunk_text'), \
             patch('backend.pipeline.ingestion.find_new_chunks'), \
             patch('backend.pipeline.ingestion.update_chunk_file_db'), \
             patch('backend.pipeline.embedding.embed_chunks_with_dedup'), \
             patch('backend.pipeline.vectorstore.add_embeddings'), \
             patch('backend.pipeline.preprocessing.preprocess_file'), \
             patch('backend.utils.hashing.generate_file_id'), \
             patch('backend.utils.hashing.generate_chunk_id'), \
             patch('backend.utils.filehash_db.add_file'):
            
            # Import and call the load function
            from backend.test import load_ingestion_dependencies
            # This should not raise an ImportError
            load_ingestion_dependencies()

    def test_load_query_dependencies(self):
        """Test that query dependencies can be imported."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        with patch('backend.pipeline.query.rag_query_pipeline'):
            from backend.test import load_query_dependencies
            load_query_dependencies()

    def test_load_deletion_dependencies(self):
        """Test that deletion dependencies can be imported."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        with patch('backend.pipeline.deletion.delete_file_and_embeddings'):
            from backend.test import load_deletion_dependencies
            load_deletion_dependencies()