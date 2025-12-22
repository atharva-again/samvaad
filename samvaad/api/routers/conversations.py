"""
Conversations Router - API endpoints for conversation management.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from samvaad.api.deps import get_current_user
from samvaad.db.models import User
from samvaad.db.conversation_service import ConversationService


router = APIRouter(prefix="/conversations", tags=["conversations"])
conversation_service = ConversationService()


# ─────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: List[dict] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    title: str
    mode: str = "text"  # Hardcoded - mode column removed from DB
    created_at: datetime
    updated_at: Optional[datetime]
    is_pinned: bool = False
    message_count: int = 0
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    mode: str = "text"  # Hardcoded - mode column removed from DB
    summary: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ConversationResponse)
def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation."""
    conversation = conversation_service.create_conversation(
        user_id=current_user.id,
        title=data.title or "New Conversation"
    )
    
    return ConversationResponse(
        id=str(conversation.id),
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0
    )


@router.get("/", response_model=List[ConversationResponse])
def list_conversations(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """List user's conversations, ordered by most recent."""
    conversations = conversation_service.list_conversations(
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    result = []
    for conv in conversations:
        message_count = conversation_service.get_message_count(conv.id)
        result.append(ConversationResponse(
            id=str(conv.id),
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            is_pinned=conv.is_pinned,
            message_count=message_count
        ))
    
    return result


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get a conversation with all its messages."""
    conversation = conversation_service.get_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationDetailResponse(
        id=str(conversation.id),
        title=conversation.title,
        summary=conversation.summary,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                id=str(msg.id),
                role=msg.role,
                content=msg.content,
                sources=msg.sources or [],
                created_at=msg.created_at
            )
            for msg in conversation.messages
        ]
    )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def get_messages_since(
    conversation_id: UUID,
    after: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
):
    """Get messages created after a timestamp (for delta sync).
    
    If 'after' is not provided, returns all messages.
    """
    messages = conversation_service.get_messages_since(
        conversation_id=conversation_id,
        user_id=current_user.id,
        after=after
    )
    
    return [
        MessageResponse(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            sources=msg.sources or [],
            created_at=msg.created_at
        )
        for msg in messages
    ]


class TruncateMessagesRequest(BaseModel):
    """Request body for truncating messages."""
    keep_message_ids: List[str]


class TruncateMessagesResponse(BaseModel):
    """Response for truncate messages endpoint."""
    deleted_count: int


@router.delete("/{conversation_id}/messages", response_model=TruncateMessagesResponse)
def truncate_messages(
    conversation_id: UUID,
    request: TruncateMessagesRequest,
    current_user: User = Depends(get_current_user)
):
    """Truncate messages in a conversation, keeping only the specified message IDs.
    
    Used for edit functionality - removes messages not in keep_message_ids.
    """
    deleted_count = conversation_service.truncate_messages_from(
        conversation_id=conversation_id,
        user_id=current_user.id,
        keep_message_ids=request.keep_message_ids
    )
    
    return TruncateMessagesResponse(deleted_count=deleted_count)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a conversation's title."""
    conversation = conversation_service.update_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
        title=data.title,
        is_pinned=data.is_pinned
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    message_count = conversation_service.get_message_count(conversation.id)
    
    return ConversationResponse(
        id=str(conversation.id),
        title=conversation.title,
        is_pinned=conversation.is_pinned,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count
    )


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Delete a conversation and all its messages."""
    success = conversation_service.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    
    
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"success": True, "message": "Conversation deleted"}


# [PHASE-3 #27] Bulk Delete Endpoint
class BulkDeleteRequest(BaseModel):
    conversation_ids: List[UUID]

@router.delete("/batch", response_model=dict)
def bulk_delete_conversations(
    data: BulkDeleteRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Delete multiple conversations at once.
    Returns the count of deleted conversations.
    """
    if not data.conversation_ids:
        return {"deleted_count": 0}
        
    count = conversation_service.delete_conversations(
        conversation_ids=data.conversation_ids,
        user_id=current_user.id
    )
    return {"deleted_count": count, "success": True}
