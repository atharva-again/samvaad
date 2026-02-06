# pyright: ignore-all
"""Conversation Service - CRUD operations for conversations and messages."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update  # noqa: F401
from sqlalchemy.orm import joinedload

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
        conversation_id: UUID | None = None,
        active_strict_mode: bool | None = None,
        active_persona: str | None = None,
    ) -> Conversation:
        """Create a new conversation for a user.

        Args:
            user_id: The ID of the user who owns the conversation.
            title: Title for the conversation.
            conversation_id: Optional UUID to use as the conversation ID.
                           If provided, this ID will be used instead of auto-generating.
            active_strict_mode: Optional strict mode override for this conversation.
            active_persona: Optional persona override for this conversation.
        """
        with get_db_context() as db:
            conversation_data: dict[str, Any] = {"user_id": user_id, "title": title}
            if conversation_id:
                conversation_data["id"] = conversation_id
            if active_strict_mode is not None:
                conversation_data["active_strict_mode"] = active_strict_mode
            if active_persona is not None:
                conversation_data["active_persona"] = active_persona
            conversation = Conversation(**conversation_data)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            return conversation

    def get_conversation(self, conversation_id: UUID, user_id: str) -> Conversation | None:
        """Get a conversation by ID for a specific user."""
        with get_db_context() as db:
            result = db.execute(
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .where(Conversation.user_id == user_id)
                .options(joinedload(Conversation.messages))
            )
            return result.scalars().first()

    def list_conversations(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Conversation]:
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
        title: str | None = None,
        summary: str | None = None,
        facts: str | None = None,
        is_pinned: bool | None = None,
        active_strict_mode: bool | None = None,
        active_persona: str | None = None,
    ) -> Conversation | None:
        """Update a conversation's fields and settings."""
        with get_db_context() as db:
            conversation = (
                db.execute(
                    select(Conversation)
                    .where(Conversation.id == conversation_id)
                    .where(Conversation.user_id == user_id)
                )
                .scalars()
                .first()
            )

            if not conversation:
                return None

            update_data: dict[str, Any] = {}
            if title is not None:
                update_data["title"] = title
            if summary is not None:
                update_data["summary"] = summary
            if facts is not None:
                update_data["facts"] = facts
            if is_pinned is not None:
                update_data["is_pinned"] = is_pinned
            if active_strict_mode is not None:
                update_data["active_strict_mode"] = active_strict_mode
            if active_persona is not None:
                update_data["active_persona"] = active_persona
            for field_name, value in update_data.items():
                setattr(conversation, field_name, value)

            db.commit()
            db.refresh(conversation)
            return conversation

    def delete_conversation(self, conversation_id: UUID, user_id: str) -> bool:
        """Delete a conversation and all its messages (cascade)."""
        with get_db_context() as db:
            result = db.execute(
                delete(Conversation).where(Conversation.id == conversation_id).where(Conversation.user_id == user_id)
            )
            db.commit()
            return getattr(result, "rowcount", 0) > 0

    def delete_conversations(self, conversation_ids: list[UUID], user_id: str) -> int:
        """
        Delete multiple conversations at once (Bulk Delete).
        Returns number of deleted records.
        """
        with get_db_context() as db:
            result = db.execute(
                delete(Conversation).where(Conversation.id.in_(conversation_ids)).where(Conversation.user_id == user_id)
            )
            count = getattr(result, "rowcount", 0)
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
        sources: list[dict] | None = None,
        token_count: int | None = None,
        message_id: UUID | None = None,
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
                token_count=token_count,
            )
            # Use client-provided ID if given
            if message_id:
                setattr(message, "id", message_id)

            db.add(message)

            # Update conversation's updated_at timestamp
            db.execute(
                update(Conversation).where(Conversation.id == conversation_id).values(updated_at=message.created_at)
            )

            db.commit()
            db.refresh(message)
            return message

    def get_messages(self, conversation_id: UUID, limit: int | None = None) -> list[Message]:
        """Get messages for a conversation, ordered by creation time."""
        with get_db_context() as db:
            query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
            if limit:
                query = query.limit(limit)

            result = db.execute(query)
            return list(result.scalars().all())

    def get_message_count(self, conversation_id: UUID) -> int:
        """Get the number of messages in a conversation."""
        with get_db_context() as db:
            from sqlalchemy import func

            result = db.execute(select(func.count(Message.id)).where(Message.conversation_id == conversation_id))
            return result.scalar() or 0

    def get_messages_since(self, conversation_id: UUID, user_id: str, after: Optional[Any] = None) -> list[Message]:
        """Get messages created after a timestamp (for delta sync).

        First verifies the conversation belongs to the user.
        If 'after' is None, returns all messages.
        """

        with get_db_context() as db:
            # Verify ownership
            conv = db.execute(
                select(Conversation.id).where(Conversation.id == conversation_id).where(Conversation.user_id == user_id)
            ).scalar()

            if not conv:
                return []

            # Build query
            query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)

            if after is not None:
                query = query.where(Message.created_at > after)

            result = db.execute(query)
            return list(result.scalars().all())

    def get_or_create_conversation(self, conversation_id: str, user_id: str) -> Conversation:
        from sqlalchemy.exc import IntegrityError

        conversation = self.get_conversation(UUID(conversation_id), user_id)
        if conversation:
            return conversation

        try:
            return self.create_conversation(user_id=user_id, conversation_id=UUID(conversation_id))
        except IntegrityError:
            db_conversation = self.get_conversation(UUID(conversation_id), user_id)
            if not db_conversation:
                raise
            return db_conversation  # type: ignore

    def truncate_messages_from(self, conversation_id: UUID, user_id: str, keep_message_ids: list[str]) -> int:
        """Truncate messages in a conversation, keeping only the specified message IDs.

        Used for edit functionality - deletes messages that are not in keep_message_ids.
        Returns the number of deleted messages.
        """
        with get_db_context() as db:
            conv = db.execute(
                select(Conversation.id).where(Conversation.id == conversation_id).where(Conversation.user_id == user_id)
            ).scalar()

            if not conv:
                return 0

            keep_uuids = [UUID(mid) for mid in keep_message_ids]

            delete_stmt = (
                delete(Message).where(Message.conversation_id == conversation_id).where(Message.id.notin_(keep_uuids))
            )

            result = db.execute(delete_stmt)
            deleted_count = getattr(result, "rowcount", 0)

            if deleted_count > 0:
                db.execute(update(Conversation).where(Conversation.id == conversation_id).values(updated_at=func.now()))

            db.commit()
            return deleted_count

    def toggle_message_pin(self, message_id: UUID, user_id: str) -> Message | None:
        with get_db_context() as db:
            message = (
                db.execute(
                    select(Message)
                    .join(Conversation)
                    .where(Message.id == message_id)
                    .where(Conversation.user_id == user_id)
                )
                .scalars()
                .first()
            )

            if not message:
                return None

            message.is_pinned = not message.is_pinned
            db.commit()
            db.refresh(message)
            return message

    def get_pinned_messages(self, conversation_id: UUID, user_id: str) -> list[Message]:
        with get_db_context() as db:
            conv = db.execute(
                select(Conversation.id).where(Conversation.id == conversation_id).where(Conversation.user_id == user_id)
            ).scalar()

            if not conv:
                return []

            result = db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .where(Message.is_pinned == True)
                .order_by(Message.created_at.desc())
            )
            return list(result.scalars().all())
