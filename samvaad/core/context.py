"""
Unified context manager for Samvaad.
Extends Pipecat's OpenAILLMContext with database persistence.
Works seamlessly for both voice and text mode.
"""
from typing import Optional, List
from uuid import UUID
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

from samvaad.db.conversation_service import ConversationService


class SamvaadLLMContext(OpenAILLMContext):
    """
    Database-backed LLM context manager.
    
    Extends OpenAILLMContext to automatically:
    - Load existing conversation history from DB on init
    - Persist new messages to DB when added
    
    This enables seamless switching between voice and text modes
    within the same conversation.
    """
    
    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        conversation_service: Optional[ConversationService] = None,
        **kwargs
    ):
        """
        Initialize context with database backing.
        
        Args:
            conversation_id: UUID of the conversation
            user_id: UUID of the user
            conversation_service: Optional injected service (for testing)
            **kwargs: Passed to OpenAILLMContext (tools, tool_choice, etc.)
        """
        super().__init__(**kwargs)
        self.conversation_id = conversation_id
        self.user_id = user_id
        self._db = conversation_service or ConversationService()
        self._initialized = False
        
    def load_history(self):
        """
        Load existing messages from database into context.
        Call this after initialization to populate history.
        """
        if self._initialized:
            return
            
        messages = self._db.get_messages(UUID(self.conversation_id))
        for msg in messages:
            # Use parent's add_message to avoid re-persisting
            super().add_message({
                "role": msg.role,
                "content": msg.content
            })
        self._initialized = True
    
    def add_message(self, message):
        """
        Override: Add message to context AND persist to database.
        
        Args:
            message: Dict with 'role' and 'content' keys
        """
        # Add to in-memory context
        super().add_message(message)
        
        # Skip system messages from persistence (already in prompts)
        if message.get("role") == "system":
            return
            
        # Skip if not initialized (loading history)
        if not self._initialized:
            return
        
        # Persist to database
        try:
            self._db.add_message(
                conversation_id=UUID(self.conversation_id),
                role=message.get("role", "user"),
                content=message.get("content", "")
            )
        except Exception as e:
            # Log but don't crash the voice pipeline
            print(f"[SamvaadLLMContext] Failed to persist message: {e}")
