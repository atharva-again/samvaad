"""Test deletion functions using DBService."""

import pytest
from unittest.mock import patch, MagicMock


class TestDeletion:
    """Test deletion functions."""

    @patch("samvaad.pipeline.deletion.deletion.DBService")
    def test_delete_file_by_id_success(self, mock_db_service):
        """Test successful file deletion."""
        from samvaad.pipeline.deletion.deletion import delete_file_by_id

        mock_db_service.delete_file.return_value = True

        result = delete_file_by_id("test_file_id", "test_user_id")

        assert result is True
        mock_db_service.delete_file.assert_called_once_with("test_file_id", "test_user_id")

    @patch("samvaad.pipeline.deletion.deletion.DBService")
    def test_delete_file_by_id_failure(self, mock_db_service):
        """Test file deletion when file not found."""
        from samvaad.pipeline.deletion.deletion import delete_file_by_id

        mock_db_service.delete_file.return_value = False

        result = delete_file_by_id("nonexistent_file", "test_user_id")

        assert result is False
        mock_db_service.delete_file.assert_called_once()


class TestDeletionErrorHandling:
    """Test error handling in deletion functions."""

    @patch("samvaad.pipeline.deletion.deletion.DBService")
    def test_delete_file_db_error(self, mock_db_service):
        """Test handling of database errors during deletion."""
        from samvaad.pipeline.deletion.deletion import delete_file_by_id

        mock_db_service.delete_file.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            delete_file_by_id("test_file_id", "test_user_id")

    @patch("samvaad.pipeline.deletion.deletion.DBService")
    def test_delete_file_with_empty_id(self, mock_db_service):
        """Test deletion with empty file ID."""
        from samvaad.pipeline.deletion.deletion import delete_file_by_id

        mock_db_service.delete_file.return_value = False

        result = delete_file_by_id("", "test_user_id")

        # Should return False for empty ID
        assert result is False

    @patch("samvaad.pipeline.deletion.deletion.DBService")
    def test_delete_file_with_empty_user_id(self, mock_db_service):
        """Test deletion with empty user ID."""
        from samvaad.pipeline.deletion.deletion import delete_file_by_id

        mock_db_service.delete_file.return_value = False

        result = delete_file_by_id("test_file_id", "")

        # Should return False for empty user ID
        assert result is False