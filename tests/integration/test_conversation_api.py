"""Integration tests for conversation API."""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


@pytest.mark.integration
class TestConversationAPIIntegration:
    """Test end-to-end conversation API workflows."""

    def setup_method(self):
        """Set up test client."""
        from samvaad.interfaces.api import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)
        self.session_id = "integration_test_session"
    
    @patch('samvaad.interfaces.api.rag_query_pipeline')
    def test_full_conversation_workflow(self, mock_rag):
        """Test complete conversation workflow from start to end."""
        mock_rag.return_value = {"success": True, "answer": "Test response", "sources": []}
        
        # Start conversation
        response = self.client.post(
            f'/conversation/start?session_id={self.session_id}'
        )
        assert response.status_code == 200
        result = response.json()
        assert result['status'] == 'started'
        assert result['session_id'] == self.session_id
        
        # Send first message
        response = self.client.post(
            '/conversation/message',
            json={'session_id': self.session_id, 'message': 'What is AI?'}
        )
        assert response.status_code == 200
        result = response.json()
        assert 'response' in result
        assert result['response'] == "Test response"
        
        # Send second message
        mock_rag.return_value = {"success": True, "answer": "AI is artificial intelligence", "sources": []}
        response = self.client.post(
            '/conversation/message',
            json={'session_id': self.session_id, 'message': 'Tell me more'}
        )
        assert response.status_code == 200
        result = response.json()
        assert result['response'] == "AI is artificial intelligence"
        
        # Check status
        response = self.client.get(f'/conversation/status/{self.session_id}')
        assert response.status_code == 200
        result = response.json()
        assert result['status']['is_active'] is True
        assert result['status']['message_count'] >= 4  # 2 user + 2 assistant messages + system messages
        
        # Clear history
        response = self.client.post(
            f'/conversation/clear/{self.session_id}'
        )
        assert response.status_code == 200
        
        # Check status after clear
        response = self.client.get(f'/conversation/status/{self.session_id}')
        result = response.json()
        # Should have fewer messages after clear
        assert result['status']['message_count'] < 4
        
        # End conversation
        response = self.client.post(f'/conversation/end/{self.session_id}')
        assert response.status_code == 200
        result = response.json()
        assert result['status'] == 'ended'
        
        # Verify session is inactive
        response = self.client.get(f'/conversation/status/{self.session_id}')
        result = response.json()
        assert result['status']['is_active'] is False
    
    @patch('samvaad.interfaces.api.rag_query_pipeline')
    def test_conversation_settings_update(self, mock_rag):
        """Test updating conversation settings during session."""
        mock_rag.return_value = {"success": True, "answer": "Response", "sources": []}
        
        # Start conversation
        self.client.post(
            f'/conversation/start?session_id={self.session_id}'
        )
        
        # Update settings
        response = self.client.post(
            '/conversation/settings',
            json={
                'session_id': self.session_id,
                'language': 'es',
                'model': 'gemini-pro'
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result['settings']['language'] == 'es'
        assert result['settings']['model'] == 'gemini-pro'
        
        # Send message with new settings
        response = self.client.post(
            '/conversation/message',
            json={'session_id': self.session_id, 'message': '¿Qué es IA?'}
        )
        assert response.status_code == 200
        
        # Clean up
        self.client.post(f'/conversation/end/{self.session_id}')
    
    @patch('samvaad.interfaces.api.rag_query_pipeline')
    def test_multiple_concurrent_sessions(self, mock_rag):
        """Test handling multiple conversation sessions concurrently."""
        mock_rag.return_value = {"success": True, "answer": "Response", "sources": []}
        
        session_ids = ['session_1', 'session_2', 'session_3']
        
        # Start multiple sessions
        for sid in session_ids:
            response = self.client.post(
                f'/conversation/start?session_id={sid}'
            )
            assert response.status_code == 200
        
        # Send messages to different sessions
        for sid in session_ids:
            response = self.client.post(
                '/conversation/message',
                json={'session_id': sid, 'message': f'Message for {sid}'}
            )
            assert response.status_code == 200
        
        # Verify each session is independent
        for sid in session_ids:
            response = self.client.get(f'/conversation/status/{sid}')
            assert response.status_code == 200
            result = response.json()
            assert result['status']['is_active'] is True
        
        # Clean up all sessions
        for sid in session_ids:
            self.client.post(f'/conversation/end/{sid}')
    
    @patch('samvaad.interfaces.api.rag_query_pipeline')
    def test_conversation_with_long_history(self, mock_rag):
        """Test conversation with long message history."""
        mock_rag.return_value = {"success": True, "answer": "Response", "sources": []}
        
        # Start conversation
        self.client.post(
            f'/conversation/start?session_id={self.session_id}'
        )
        
        # Send many messages
        num_messages = 30
        for i in range(num_messages):
            response = self.client.post(
                '/conversation/message',
                json={'session_id': self.session_id, 'message': f'Message {i}'}
            )
            assert response.status_code == 200
        
        # Check status
        response = self.client.get(f'/conversation/status/{self.session_id}')
        result = response.json()
        
        # Should have messages (may be trimmed based on max_history)
        assert result['status']['message_count'] > 0
        
        # Clean up
        self.client.post(f'/conversation/end/{self.session_id}')
    
    @patch('samvaad.interfaces.api.rag_query_pipeline')
    def test_conversation_restart_after_end(self, mock_rag):
        """Test restarting a conversation after ending it."""
        mock_rag.return_value = {"answer": "Response"}
        
        # Start, message, and end
        self.client.post('/conversation/start', json={'session_id': self.session_id})
        self.client.post(
            '/conversation/message',
            json={'session_id': self.session_id, 'message': 'First session'}
        )
        self.client.post(f'/conversation/end/{self.session_id}')
        
        # Start again with same session ID
        response = self.client.post(
            '/conversation/start',
            json={'session_id': self.session_id}
        )
        assert response.status_code == 200
        
        # Send message in new session
        response = self.client.post(
            '/conversation/message',
            json={'session_id': self.session_id, 'message': 'Second session'}
        )
        assert response.status_code == 200
        
        # Clean up
        self.client.post(f'/conversation/end/{self.session_id}')
    
    def teardown_method(self):
        """Clean up after each test."""
        # Ensure test session is ended
        try:
            self.client.post(f'/conversation/end/{self.session_id}')
        except:
            pass
