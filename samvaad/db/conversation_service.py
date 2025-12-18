"""
Conversation Service - CRUD operations for conversations and messages.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session, joinedload

from samvaad.db.models import Conversation, Message
from samvaad.db.session import get_db_context


class ConversationService:
    """Service for managing conversations and messages."""
    
    # ─────────────────────────────────────────────────────────────────────
    # Conversation CRUD
    # ─────────────────────────────────────────────────────────────────────
    
    def create_conversation(
        self,
        user_id: str,
        title: str = "New Conversation",
        mode: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Create a new conversation for a user."""
        with get_db_context() as db:
            conversation = Conversation(
                user_id=user_id,
                title=title,
                mode=mode,
                metadata_=metadata or {}
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            return conversation
    
    def get_conversation(
        self,
        conversation_id: UUID,
        user_id: str
    ) -> Optional[Conversation]:
        """Get a conversation by ID for a specific user."""
        with get_db_context() as db:
            result = db.execute(
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .where(Conversation.user_id == user_id)
                .options(joinedload(Conversation.messages))
            )
            return result.scalars().first()
    
    def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """List conversations for a user, ordered by most recent."""
        with get_db_context() as db:
            result = db.execute(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return list(result.scalars().all())
    
    def update_conversation(
        self,
        conversation_id: UUID,
        user_id: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        is_pinned: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Conversation]:
        """Update a conversation's title, summary, pinned status, or metadata."""
        with get_db_context() as db:
            conversation = db.execute(
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .where(Conversation.user_id == user_id)
            ).scalars().first()
            
            if not conversation:
                return None
            
            if title is not None:
                conversation.title = title
            if summary is not None:
                conversation.summary = summary
            if is_pinned is not None:
                conversation.is_pinned = is_pinned
            if metadata is not None:
                conversation.metadata_ = metadata
            
            db.commit()
            db.refresh(conversation)
            return conversation
    
    def delete_conversation(
        self,
        conversation_id: UUID,
        user_id: str
    ) -> bool:
        """Delete a conversation and all its messages (cascade)."""
        with get_db_context() as db:
            result = db.execute(
                delete(Conversation)
                .where(Conversation.id == conversation_id)
                .where(Conversation.user_id == user_id)
            )
            db.commit()
            return result.rowcount > 0
    
    # ─────────────────────────────────────────────────────────────────────
    # Message CRUD
    # ─────────────────────────────────────────────────────────────────────
    
    def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None,
        token_count: Optional[int] = None
    ) -> Message:
        """Add a message to a conversation."""
        with get_db_context() as db:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                sources=sources or [],
                token_count=token_count
            )
            db.add(message)
            
            # Update conversation's updated_at timestamp
            db.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(updated_at=message.created_at)
            )
            
            db.commit()
            db.refresh(message)
            return message
    
    def get_messages(
        self,
        conversation_id: UUID,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get messages for a conversation, ordered by creation time."""
        with get_db_context() as db:
            query = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            if limit:
                query = query.limit(limit)
            
            result = db.execute(query)
            return list(result.scalars().all())
    
    def get_message_count(self, conversation_id: UUID) -> int:
        """Get the number of messages in a conversation."""
        with get_db_context() as db:
            from sqlalchemy import func
            result = db.execute(
                select(func.count(Message.id))
                .where(Message.conversation_id == conversation_id)
            )
            return result.scalar() or 0
    
    def get_or_create_conversation(
        self,
        conversation_id: Optional[UUID],
        user_id: str,
        mode: str = "text"
    ) -> Conversation:
        """Get an existing conversation or create a new one."""
        if conversation_id:
            conversation = self.get_conversation(conversation_id, user_id)
            if conversation:
                return conversation
        
        # Create new conversation
        return self.create_conversation(user_id=user_id, mode=mode)
