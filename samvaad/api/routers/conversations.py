"""
Conversations Router - API endpoints for conversation management.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import cast

from samvaad.api.deps import get_current_user
from samvaad.db.conversation_service import ConversationService
from samvaad.db.models import User

router = APIRouter(prefix="/conversations", tags=["conversations"])
conversation_service = ConversationService()


# ─────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────


class ConversationCreate(BaseModel):
    id: str | None = None
    title: str | None = "New Conversation"
    active_strict_mode: bool | None = None
    active_persona: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    is_pinned: bool | None = None
    active_strict_mode: bool | None = None
    active_persona: str | None = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: list[dict] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    title: str
    mode: str = "text"
    created_at: datetime
    updated_at: datetime | None
    is_pinned: bool = False
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    mode: str = "text"
    summary: str | None
    created_at: datetime
    updated_at: datetime | None
    messages: list[MessageResponse] = []
    active_strict_mode: bool | None = None
    active_persona: str | None = None

    class Config:
        from_attributes = True


@router.post("/", response_model=ConversationResponse)
def create_conversation(data: ConversationCreate, current_user: User = Depends(get_current_user)):
    """Create a new conversation."""
    from uuid import UUID

    user_id = cast(str, current_user.id)
    conv_id = UUID(data.id) if data.id else None

    if conv_id:
        existing = conversation_service.get_conversation(conv_id, user_id)
        if existing:
            return ConversationResponse(
                id=str(existing.id),
                title=cast(str, existing.title),
                created_at=cast(datetime, existing.created_at),
                updated_at=cast(datetime | None, existing.updated_at),
                message_count=conversation_service.get_message_count(cast(UUID, existing.id)),
            )

    conversation = conversation_service.create_conversation(
        user_id=user_id,
        title=data.title or "New Conversation",
        conversation_id=conv_id,
        active_strict_mode=data.active_strict_mode,
        active_persona=data.active_persona,
    )

    return ConversationResponse(
        id=str(conversation.id),
        title=cast(str, conversation.title),
        created_at=cast(datetime, conversation.created_at),
        updated_at=cast(datetime | None, conversation.updated_at),
        message_count=0,
    )


@router.get("/", response_model=list[ConversationResponse])
def list_conversations(limit: int = 50, offset: int = 0, current_user: User = Depends(get_current_user)):
    """List user's conversations, ordered by most recent."""
    user_id = cast(str, current_user.id)
    conversations = conversation_service.list_conversations(user_id=user_id, limit=limit, offset=offset)

    result = []
    for conv in conversations:
        message_count = conversation_service.get_message_count(cast(UUID, conv.id))
        result.append(
            ConversationResponse(
                id=str(conv.id),
                title=cast(str, conv.title),
                created_at=cast(datetime, conv.created_at),
                updated_at=cast(datetime | None, conv.updated_at),
                is_pinned=cast(bool, conv.is_pinned),
                message_count=message_count,
            )
        )

    return result


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: UUID, current_user: User = Depends(get_current_user)):
    """Get a conversation with all its messages."""
    conversation = conversation_service.get_conversation(
        conversation_id=conversation_id, user_id=cast(str, current_user.id)
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetailResponse(
        id=str(conversation.id),
        title=cast(str, conversation.title),
        summary=cast(str | None, conversation.summary),
        created_at=cast(datetime, conversation.created_at),
        updated_at=cast(datetime | None, conversation.updated_at),
        messages=[
            MessageResponse(
                id=str(msg.id),
                role=cast(str, msg.role),
                content=cast(str, msg.content),
                sources=cast(list[dict], msg.sources) if cast(list[dict] | None, msg.sources) else [],
                created_at=cast(datetime, msg.created_at),
            )
            for msg in conversation.messages
        ],
        active_strict_mode=cast(bool | None, conversation.active_strict_mode),
        active_persona=cast(str | None, conversation.active_persona),
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages_since(
    conversation_id: UUID, after: datetime | None = None, current_user: User = Depends(get_current_user)
):
    """Get messages created after a timestamp (for delta sync).

    If 'after' is not provided, returns all messages.
    """
    messages = conversation_service.get_messages_since(
        conversation_id=conversation_id, user_id=cast(str, current_user.id), after=after
    )

    return [
        MessageResponse(
            id=str(msg.id),
            role=cast(str, msg.role),
            content=cast(str, msg.content),
            sources=cast(list[dict], msg.sources) if cast(list[dict] | None, msg.sources) else [],
            created_at=cast(datetime, msg.created_at),
        )
        for msg in messages
    ]


class ConversationSettingsResponse(BaseModel):
    active_strict_mode: bool | None = None
    active_persona: str | None = None


@router.get("/{conversation_id}/settings", response_model=ConversationSettingsResponse)
def get_conversation_settings(conversation_id: UUID, current_user: User = Depends(get_current_user)):
    conversation = conversation_service.get_conversation(
        conversation_id=conversation_id, user_id=cast(str, current_user.id)
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationSettingsResponse(
        active_strict_mode=cast(bool | None, conversation.active_strict_mode),
        active_persona=cast(str | None, conversation.active_persona),
    )


@router.put("/{conversation_id}/settings", response_model=ConversationSettingsResponse)
def update_conversation_settings_endpoint(
    conversation_id: UUID,
    data: ConversationSettingsResponse,
    current_user: User = Depends(get_current_user),
):
    conversation = conversation_service.update_conversation(
        conversation_id=conversation_id,
        user_id=cast(str, current_user.id),
        active_strict_mode=data.active_strict_mode,
        active_persona=data.active_persona,
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationSettingsResponse(
        active_strict_mode=cast(bool | None, conversation.active_strict_mode),
        active_persona=cast(str | None, conversation.active_persona),
    )


class TruncateMessagesRequest(BaseModel):
    """Request body for truncating messages."""

    keep_message_ids: list[str]


class TruncateMessagesResponse(BaseModel):
    """Response for truncate messages endpoint."""

    deleted_count: int


@router.delete("/{conversation_id}/messages", response_model=TruncateMessagesResponse)
def truncate_messages(
    conversation_id: UUID, request: TruncateMessagesRequest, current_user: User = Depends(get_current_user)
):
    """Truncate messages in a conversation, keeping only the specified message IDs.

    Used for edit functionality - removes messages not in keep_message_ids.
    """
    deleted_count = conversation_service.truncate_messages_from(
        conversation_id=conversation_id,
        user_id=cast(str, current_user.id),
        keep_message_ids=request.keep_message_ids,
    )

    return TruncateMessagesResponse(deleted_count=deleted_count)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: UUID, data: ConversationUpdate, current_user: User = Depends(get_current_user)
):
    """Update a conversation's title."""
    conversation = conversation_service.update_conversation(
        conversation_id=conversation_id,
        user_id=cast(str, current_user.id),
        title=data.title,
        is_pinned=data.is_pinned,
        active_strict_mode=data.active_strict_mode,
        active_persona=data.active_persona,
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message_count = conversation_service.get_message_count(cast(UUID, conversation.id))

    return ConversationResponse(
        id=str(conversation.id),
        title=cast(str, conversation.title),
        is_pinned=cast(bool, conversation.is_pinned),
        created_at=cast(datetime, conversation.created_at),
        updated_at=cast(datetime | None, conversation.updated_at),
        message_count=message_count,
    )


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: UUID, current_user: User = Depends(get_current_user)):
    """Delete a conversation and all its messages."""
    success = conversation_service.delete_conversation(
        conversation_id=conversation_id, user_id=cast(str, current_user.id)
    )

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"success": True, "message": "Conversation deleted"}


# [PHASE-3 #27] Bulk Delete Endpoint
class BulkDeleteRequest(BaseModel):
    conversation_ids: list[UUID]


@router.delete("/batch", response_model=dict)
def bulk_delete_conversations(data: BulkDeleteRequest, current_user: User = Depends(get_current_user)):
    """
    Delete multiple conversations at once.
    Returns the count of deleted conversations.
    """
    if not data.conversation_ids:
        return {"deleted_count": 0}

    count = conversation_service.delete_conversations(
        conversation_ids=data.conversation_ids, user_id=cast(str, current_user.id)
    )
    return {"deleted_count": count, "success": True}
