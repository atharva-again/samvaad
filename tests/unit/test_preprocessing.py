import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
import shutil

# Import modules to test
from backend.pipeline.preprocessing import preprocess_file, update_file_metadata_db


class TestPreprocessing:
    """Test preprocessing functions."""

    def setup_method(self):
        """Set up temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_filehashes.sqlite3')

    def teardown_method(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('backend.utils.filehash_db.DB_PATH')
    def test_preprocess_file_new_file(self, mock_db_path):
        """Test preprocess_file for a new file."""
        # Mock the database path
        mock_db_path.__str__ = lambda: self.db_path
        mock_db_path.__fspath__ = lambda: self.db_path
        
        with patch('backend.pipeline.preprocessing.init_db'):
            with patch('backend.pipeline.preprocessing.file_exists', return_value=False):
                content = b"test content"
                filename = "test.txt"

                # Should return False (not duplicate)
                result = preprocess_file(content, filename)
                assert result == False

    @patch('backend.utils.filehash_db.DB_PATH')
    def test_preprocess_file_duplicate(self, mock_db_path):
        """Test preprocess_file for a duplicate file."""
        mock_db_path.__str__ = lambda: self.db_path
        mock_db_path.__fspath__ = lambda: self.db_path
        
        with patch('backend.pipeline.preprocessing.init_db'):
            with patch('backend.pipeline.preprocessing.file_exists', return_value=True):
                content = b"test content"
                filename = "test.txt"

                # Should return True (duplicate)
                result = preprocess_file(content, filename)
                assert result == True

    @patch('backend.pipeline.preprocessing.add_file')
    @patch('backend.pipeline.preprocessing.generate_file_id')
    def test_update_file_metadata_db(self, mock_generate_id, mock_add_file):
        """Test update_file_metadata_db calls add_file with correct parameters."""
        mock_generate_id.return_value = "test_file_id"
        content = b"test content"
        filename = "test.txt"

        update_file_metadata_db(content, filename)

        mock_generate_id.assert_called_once_with(content)
        mock_add_file.assert_called_once_with("test_file_id", filename)