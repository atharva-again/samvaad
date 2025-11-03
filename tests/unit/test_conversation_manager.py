"""Tests for ConversationManager class."""

import pytest
from datetime import datetime, timedelta
from samvaad.pipeline.retrieval.voice_mode import ConversationManager, ConversationMessage


@pytest.mark.unit
class TestConversationMessage:
    """Test ConversationMessage class."""
    
    def test_initialization_default(self):
        """Test creating a message with default parameters."""
        msg = ConversationMessage(role="user", content="Hello")
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}
    
    def test_initialization_with_metadata(self):
        """Test creating a message with metadata."""
        metadata = {'source': 'test', 'confidence': 0.95}
        msg = ConversationMessage(
            role="assistant",
            content="Response",
            metadata=metadata
        )
        
        assert msg.metadata == metadata
    
    def test_initialization_with_custom_timestamp(self):
        """Test creating a message with custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        msg = ConversationMessage(
            role="system",
            content="System message",
            timestamp=custom_time
        )
        
        assert msg.timestamp == custom_time
    
    def test_to_dict(self):
        """Test serializing message to dictionary."""
        msg = ConversationMessage(
            role="user",
            content="Test message",
            metadata={'key': 'value'}
        )
        
        result = msg.to_dict()
        
        assert result['role'] == "user"
        assert result['content'] == "Test message"
        assert 'timestamp' in result
        assert result['metadata'] == {'key': 'value'}
    
    def test_from_dict(self):
        """Test deserializing message from dictionary."""
        data = {
            'role': 'assistant',
            'content': 'Response text',
            'timestamp': datetime(2024, 1, 1, 12, 0, 0).isoformat(),
            'metadata': {'source': 'test'}
        }
        
        msg = ConversationMessage.from_dict(data)
        
        assert msg.role == 'assistant'
        assert msg.content == 'Response text'
        assert msg.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert msg.metadata == {'source': 'test'}
    
    def test_from_dict_without_metadata(self):
        """Test deserializing message without metadata."""
        data = {
            'role': 'user',
            'content': 'Question',
            'timestamp': datetime.now().isoformat()
        }
        
        msg = ConversationMessage.from_dict(data)
        
        assert msg.metadata == {}


@pytest.mark.unit
class TestConversationManager:
    """Test ConversationManager class."""
    
    def test_initialization(self):
        """Test creating a conversation manager."""
        manager = ConversationManager()
        
        assert manager.messages == []
        assert manager.max_history == 50
        assert manager.context_window == 10
        assert not manager.is_active
        assert 'language' in manager.settings
        assert 'model' in manager.settings
    
    def test_initialization_custom_params(self):
        """Test creating manager with custom parameters."""
        manager = ConversationManager(max_history=100, context_window=20)
        
        assert manager.max_history == 100
        assert manager.context_window == 20
    
    def test_start_conversation(self):
        """Test starting a conversation."""
        manager = ConversationManager()
        manager.start_conversation()
        
        assert manager.is_active
        assert len(manager.messages) == 1
        assert manager.messages[0].role == 'system'
        assert 'started' in manager.messages[0].content.lower()
    
    def test_end_conversation(self):
        """Test ending a conversation."""
        manager = ConversationManager()
        manager.start_conversation()
        manager.end_conversation()
        
        assert not manager.is_active
        assert len(manager.messages) == 2
        assert manager.messages[-1].role == 'system'
        assert 'ended' in manager.messages[-1].content.lower()
    
    def test_add_user_message(self):
        """Test adding a user message."""
        manager = ConversationManager()
        manager.add_user_message("Hello, how are you?")
        
        assert len(manager.messages) == 1
        assert manager.messages[0].role == 'user'
        assert manager.messages[0].content == "Hello, how are you?"
    
    def test_add_user_message_with_metadata(self):
        """Test adding user message with metadata."""
        manager = ConversationManager()
        metadata = {'source': 'voice', 'language': 'en'}
        manager.add_user_message("Test", metadata=metadata)
        
        assert manager.messages[0].metadata == metadata
    
    def test_add_assistant_message(self):
        """Test adding an assistant message."""
        manager = ConversationManager()
        manager.add_assistant_message("I'm doing well, thank you!")
        
        assert len(manager.messages) == 1
        assert manager.messages[0].role == 'assistant'
        assert manager.messages[0].content == "I'm doing well, thank you!"
    
    def test_add_system_message(self):
        """Test adding a system message."""
        manager = ConversationManager()
        manager.add_system_message("System notification")
        
        assert len(manager.messages) == 1
        assert manager.messages[0].role == 'system'
    
    def test_get_context_empty(self):
        """Test getting context from empty conversation."""
        manager = ConversationManager()
        context = manager.get_context()
        
        assert context == ""
    
    def test_get_context_single_message(self):
        """Test getting context with single message."""
        manager = ConversationManager()
        manager.add_user_message("Hello")
        context = manager.get_context()
        
        assert "User: Hello" in context
    
    def test_get_context_multiple_messages(self):
        """Test getting context with multiple messages."""
        manager = ConversationManager()
        manager.add_user_message("Question 1")
        manager.add_assistant_message("Answer 1")
        manager.add_user_message("Question 2")
        
        context = manager.get_context()
        
        assert "User: Question 1" in context
        assert "Assistant: Answer 1" in context
        assert "User: Question 2" in context
    
    def test_get_context_respects_window(self):
        """Test that context window limits returned messages."""
        manager = ConversationManager(context_window=2)
        
        for i in range(5):
            manager.add_user_message(f"Message {i}")
        
        context = manager.get_context()
        
        # Should only contain last 2 messages
        assert "Message 3" in context
        assert "Message 4" in context
        assert "Message 0" not in context
        assert "Message 1" not in context
    
    def test_get_messages_for_prompt(self):
        """Test getting messages formatted for LLM prompt."""
        manager = ConversationManager()
        manager.add_user_message("Hello")
        manager.add_assistant_message("Hi there")
        manager.add_system_message("System note")
        
        messages = manager.get_messages_for_prompt()
        
        assert len(messages) == 3
        assert messages[0] == {'role': 'user', 'content': 'Hello'}
        assert messages[1] == {'role': 'assistant', 'content': 'Hi there'}
        assert messages[2] == {'role': 'system', 'content': 'System note'}
    
    def test_get_messages_for_prompt_respects_window(self):
        """Test that messages for prompt respect context window."""
        manager = ConversationManager(context_window=3)
        
        for i in range(10):
            manager.add_user_message(f"Message {i}")
        
        messages = manager.get_messages_for_prompt()
        
        assert len(messages) == 3
        assert messages[0]['content'] == "Message 7"
        assert messages[2]['content'] == "Message 9"
    
    def test_clear_history(self):
        """Test clearing conversation history."""
        manager = ConversationManager()
        manager.add_user_message("Message 1")
        manager.add_assistant_message("Response 1")
        
        manager.clear_history()
        
        # Should only have the "History cleared" system message
        assert len(manager.messages) == 1
        assert manager.messages[0].role == 'system'
        assert 'cleared' in manager.messages[0].content.lower()
    
    def test_trim_history(self):
        """Test that history is automatically trimmed."""
        manager = ConversationManager(max_history=5)
        
        # Add more messages than max_history
        for i in range(10):
            manager.add_user_message(f"Message {i}")
        
        # Should only keep last 5 messages
        assert len(manager.messages) == 5
        assert manager.messages[0].content == "Message 5"
        assert manager.messages[-1].content == "Message 9"
    
    def test_settings_default_values(self):
        """Test default settings values."""
        manager = ConversationManager()
        
        assert manager.settings['language'] == 'en'
        assert manager.settings['model'] == 'gemini-2.5-flash'
        assert manager.settings['voice_activity_detection'] is True
        assert manager.settings['auto_save'] is True
    
    def test_settings_modification(self):
        """Test modifying settings."""
        manager = ConversationManager()
        
        manager.settings['language'] = 'es'
        manager.settings['model'] = 'gemini-pro'
        
        assert manager.settings['language'] == 'es'
        assert manager.settings['model'] == 'gemini-pro'
    
    def test_conversation_id_format(self):
        """Test conversation ID has correct format."""
        manager = ConversationManager()
        
        assert isinstance(manager.conversation_id, str)
        assert len(manager.conversation_id) == 15  # YYYYmmdd_HHMMSS
        assert '_' in manager.conversation_id
    
    def test_full_conversation_flow(self):
        """Test a complete conversation flow."""
        manager = ConversationManager()
        
        # Start conversation
        manager.start_conversation()
        assert manager.is_active
        
        # Add messages
        manager.add_user_message("What is AI?")
        manager.add_assistant_message("AI stands for Artificial Intelligence.")
        manager.add_user_message("Tell me more")
        manager.add_assistant_message("It's a broad field...")
        
        # Check context
        context = manager.get_context()
        assert "What is AI?" in context
        assert "Artificial Intelligence" in context
        
        # End conversation
        manager.end_conversation()
        assert not manager.is_active
        
        # Should have 6 messages total (start, 4 conversation, end)
        assert len(manager.messages) == 6
