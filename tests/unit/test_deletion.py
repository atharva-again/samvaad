import pytest
from unittest.mock import patch, MagicMock, mock_open

# Import modules to test
from samvaad.pipeline.deletion.deletion import delete_file_and_embeddings


class TestDeletion:
    """Test deletion functions."""

    @patch('samvaad.pipeline.deletion.deletion.open', new_callable=mock_open, read_data=b"test content")
    @patch('samvaad.pipeline.deletion.deletion.generate_file_id')
    @patch('samvaad.pipeline.deletion.deletion.delete_file_and_cleanup')
    @patch('samvaad.pipeline.deletion.deletion.get_collection')
    def test_delete_file_and_embeddings(self, mock_get_collection, mock_cleanup, mock_generate_id, mock_file):
        """Test deleting file and its embeddings."""
        mock_generate_id.return_value = "test_file_id"
        mock_cleanup.return_value = ["chunk1", "chunk2"]
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        file_path = "test.txt"
        result = delete_file_and_embeddings(file_path)

        assert result == ["chunk1", "chunk2"]
        mock_cleanup.assert_called_once_with("test_file_id")
        mock_collection.delete.assert_called_once_with(ids=["chunk1", "chunk2"])

    @patch('samvaad.pipeline.deletion.deletion.open', new_callable=mock_open, read_data=b"test content")
    @patch('samvaad.pipeline.deletion.deletion.generate_file_id')
    @patch('samvaad.pipeline.deletion.deletion.delete_file_and_cleanup')
    @patch('samvaad.pipeline.deletion.deletion.get_collection')
    def test_delete_file_and_embeddings_no_orphaned_chunks(self, mock_get_collection, mock_cleanup, mock_generate_id, mock_file):
        """Test deleting file when no chunks are orphaned (all chunks are shared with other files)."""
        mock_generate_id.return_value = "test_file_id"
        mock_cleanup.return_value = []  # No orphaned chunks
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        file_path = "test.txt"
        result = delete_file_and_embeddings(file_path)

        assert result == []
        mock_cleanup.assert_called_once_with("test_file_id")
        # collection.delete should not be called when no chunks are orphaned
        mock_collection.delete.assert_not_called()


class TestDeletionErrorHandling:
    """Test error handling in deletion functions."""

    @patch('samvaad.pipeline.deletion.deletion.open', new_callable=mock_open, read_data=b"test content")
    @patch('samvaad.pipeline.deletion.deletion.generate_file_id')
    @patch('samvaad.pipeline.deletion.deletion.delete_file_and_cleanup')
    @patch('samvaad.pipeline.deletion.deletion.get_collection')
    def test_delete_file_chromadb_failure(self, mock_get_collection, mock_cleanup, mock_generate_id, mock_file):
        """Test handling of ChromaDB deletion failure."""
        mock_generate_id.return_value = "test_file_id"
        mock_cleanup.return_value = ["chunk1", "chunk2"]
        
        mock_collection = MagicMock()
        mock_collection.delete.side_effect = Exception("ChromaDB deletion failed")
        mock_get_collection.return_value = mock_collection
        
        file_path = "test.txt"
        
        with pytest.raises(Exception, match="ChromaDB deletion failed"):
            delete_file_and_embeddings(file_path)
    
    @patch('samvaad.pipeline.deletion.deletion.open')
    @patch('samvaad.pipeline.deletion.deletion.generate_file_id')
    def test_delete_file_not_found(self, mock_generate_id, mock_file):
        """Test handling of non-existent file."""
        mock_file.side_effect = FileNotFoundError("File not found")
        
        file_path = "nonexistent.txt"
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            delete_file_and_embeddings(file_path)
    
    @patch('samvaad.pipeline.deletion.deletion.open', new_callable=mock_open, read_data=b"test content")
    @patch('samvaad.pipeline.deletion.deletion.generate_file_id')
    @patch('samvaad.pipeline.deletion.deletion.delete_file_and_cleanup')
    @patch('samvaad.pipeline.deletion.deletion.get_collection')
    def test_delete_file_database_error(self, mock_get_collection, mock_cleanup, mock_generate_id, mock_file):
        """Test handling of database errors during cleanup."""
        mock_generate_id.return_value = "test_file_id"
        mock_cleanup.side_effect = Exception("Database transaction failed")
        
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        
        file_path = "test.txt"
        
        with pytest.raises(Exception, match="Database transaction failed"):
            delete_file_and_embeddings(file_path)