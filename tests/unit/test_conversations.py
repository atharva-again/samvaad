"""Tests for ConversationService operations."""

from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestConversationBulkDelete:
    """Test bulk delete conversation operations."""

    @patch("samvaad.db.conversation_service.get_db_context")
    def test_delete_conversations_success(self, mock_db_context):
        """Test successful bulk deletion of conversations."""
        from samvaad.db.conversation_service import ConversationService

        # Mock DB setup
        mock_db = MagicMock()
        mock_db_context.return_value.__enter__.return_value = mock_db

        # Mock successful execute result
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute.return_value = mock_result

        service = ConversationService()
        user_id = "user_123"
        conv_ids = [uuid4() for _ in range(3)]

        result = service.delete_conversations(conv_ids, user_id)

        assert result == 3

        # Verify call args
        mock_db.execute.assert_called_once()
        # Should call commit
        mock_db.commit.assert_called_once()

    @patch("samvaad.db.conversation_service.get_db_context")
    def test_delete_conversations_empty_list(self, mock_db_context):
        """Test bulk delete with empty list."""
        from samvaad.db.conversation_service import ConversationService

        mock_db = MagicMock()
        mock_db_context.return_value.__enter__.return_value = mock_db

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        service = ConversationService()
        result = service.delete_conversations([], "user_123")

        assert result == 0
