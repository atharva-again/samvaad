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
        conversation_id: Optional[UUID] = None
    ) -> Conversation:
        """Create a new conversation for a user.
        
        Args:
            user_id: The ID of the user who owns the conversation.
            title: Title for the conversation.
            conversation_id: Optional UUID to use as the conversation ID.
                           If provided, this ID will be used instead of auto-generating.
        """
        with get_db_context() as db:
            conversation = Conversation(
                user_id=user_id,
                title=title
            )
            # Use client-provided ID if given
            if conversation_id:
                conversation.id = conversation_id
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
        facts: Optional[str] = None,
        is_pinned: Optional[bool] = None
    ) -> Optional[Conversation]:
        """Update a conversation's title, summary, facts, or pinned status."""
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
            if facts is not None:
                conversation.facts = facts
            if is_pinned is not None:
                conversation.is_pinned = is_pinned
            
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

    def delete_conversations(self, conversation_ids: List[UUID], user_id: str) -> int:
        """
        Delete multiple conversations at once (Bulk Delete).
        Returns number of deleted records.
        """
        with get_db_context() as db:
            result = db.execute(
                delete(Conversation)
                .where(Conversation.id.in_(conversation_ids))
                .where(Conversation.user_id == user_id)
            )
            # Use result.rowcount to get deleted count
            count = result.rowcount
            db.commit()
            return count
    
    # ─────────────────────────────────────────────────────────────────────
    # Message CRUD
    # ─────────────────────────────────────────────────────────────────────
    
    def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None,
        token_count: Optional[int] = None,
        message_id: Optional[UUID] = None
    ) -> Message:
        """Add a message to a conversation.
        
        If message_id is provided (from client), use it instead of auto-generating.
        This enables cache consistency between frontend and backend.
        """
        with get_db_context() as db:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                sources=sources or [],
                token_count=token_count
            )
            # Use client-provided ID if given
            if message_id:
                message.id = message_id
            
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
    
    def get_messages_since(
        self,
        conversation_id: UUID,
        user_id: str,
        after: Optional['datetime'] = None
    ) -> List[Message]:
        """Get messages created after a timestamp (for delta sync).
        
        First verifies the conversation belongs to the user.
        If 'after' is None, returns all messages.
        """
        from datetime import datetime
        
        with get_db_context() as db:
            # Verify ownership
            conv = db.execute(
                select(Conversation.id)
                .where(Conversation.id == conversation_id)
                .where(Conversation.user_id == user_id)
            ).scalar()
            
            if not conv:
                return []
            
            # Build query
            query = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            
            if after is not None:
                query = query.where(Message.created_at > after)
            
            result = db.execute(query)
            return list(result.scalars().all())
    
    def get_or_create_conversation(
        self,
        conversation_id: Optional[UUID],
        user_id: str
    ) -> Conversation:
        """Get an existing conversation or create a new one.
        
        If conversation_id is provided and exists for this user, returns it.
        If conversation_id is provided but doesn't exist, creates a new conversation WITH that ID.
        If conversation_id is None, creates a new conversation with auto-generated ID.
        """
        if conversation_id:
            conversation = self.get_conversation(conversation_id, user_id)
            if conversation:
                return conversation
            # ID was provided but conversation doesn't exist - create with that ID
            return self.create_conversation(user_id=user_id, conversation_id=conversation_id)
        
        # No ID provided - create with auto-generated ID
        return self.create_conversation(user_id=user_id)

    def truncate_messages_from(
        self,
        conversation_id: UUID,
        user_id: str,
        keep_message_ids: List[str]
    ) -> int:
        """Truncate messages in a conversation, keeping only the specified message IDs.
        
        Used for edit functionality - deletes messages that are not in keep_message_ids.
        Returns the number of deleted messages.
        """
        with get_db_context() as db:
            # Verify ownership
            conv = db.execute(
                select(Conversation.id)
                .where(Conversation.id == conversation_id)
                .where(Conversation.user_id == user_id)
            ).scalar()
            
            if not conv:
                return 0
            
            # Convert string IDs to UUIDs for comparison
            keep_uuids = [UUID(mid) for mid in keep_message_ids]
            
            # Delete messages NOT in the keep list
            delete_stmt = (
                delete(Message)
                .where(Message.conversation_id == conversation_id)
                .where(Message.id.notin_(keep_uuids))
            )
            
            result = db.execute(delete_stmt)
            deleted_count = result.rowcount
            
            # Update conversation's updated_at
            if deleted_count > 0:
                from datetime import datetime, timezone
                db.execute(
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(updated_at=datetime.now(timezone.utc))
                )
            
            db.commit()
            return deleted_count

