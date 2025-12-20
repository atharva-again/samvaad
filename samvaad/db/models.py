import datetime
import uuid_utils  # RFC 9562 compliant, 10x faster (Rust-backed)
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, BigInteger, Table, func, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship, declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    # Supabase uses UUID strings for user IDs
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="owner", cascade="all, delete-orphan")


# Association Table for Many-to-Many between GlobalFile and GlobalChunk
# Stores the order of chunks in a file
global_file_chunks = Table(
    "global_file_chunks",
    Base.metadata,
    Column("global_file_hash", String, ForeignKey("global_files.hash", ondelete="CASCADE"), primary_key=True),
    Column("chunk_hash", String, ForeignKey("global_chunks.hash", ondelete="CASCADE"), primary_key=True),
    Column("chunk_index", Integer, nullable=False)
)


class GlobalChunk(Base):
    """
    Global deduplicated chunks.
    Unique by SHA-256 hash of the text content.
    """
    __tablename__ = "global_chunks"

    hash = Column(String, primary_key=True, index=True) # SHA-256 of text
    content = Column(Text, nullable=False)
    
    # 1024 dimensions to match Voyage AI / standard embedding models
    embedding = Column(Vector(1024))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GlobalFile(Base):
    """
    Global deduplicated content (The Blob).
    Unique by SHA-256 hash of the entire file.
    """
    __tablename__ = "global_files"

    hash = Column(String, primary_key=True, index=True) # SHA-256
    size = Column(BigInteger, nullable=True) # Size in bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Chunks are now many-to-many
    chunks = relationship("GlobalChunk", secondary=global_file_chunks, backref="global_files")


class File(Base):
    """
    User-specific file pointer.
    """
    __tablename__ = "files"

    id = Column(String, primary_key=True)  # UUID for this specific upload
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    
    # Pointer to the global content
    content_hash = Column(String, ForeignKey("global_files.hash"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="files")
    content_ref = relationship("GlobalFile", backref="references")


class Conversation(Base):
    """
    Persistent conversation storage.
    Uses UUID v7 for time-ordered, efficient B-tree indexing.
    """
    __tablename__ = "conversations"
    
    # UUID v7: time-sortable, efficient indexing (converted to str for psycopg2 compatibility)
    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid_utils.uuid7()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="New Conversation")
    summary = Column(Text, nullable=True)  # Compressed context for long conversations
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    owner = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", 
        back_populates="conversation", 
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )


class Message(Base):
    """
    Individual message within a conversation.
    Uses UUID v7 for time-ordered, efficient B-tree indexing.
    """
    __tablename__ = "messages"
    
    # UUID v7: time-sortable, efficient indexing (converted to str for psycopg2 compatibility)
    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid_utils.uuid7()))
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=[])  # RAG sources for assistant messages
    token_count = Column(Integer, nullable=True)  # For context window management
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="messages")
    embedding = relationship("MessageEmbedding", back_populates="message", uselist=False, cascade="all, delete-orphan")


class MessageEmbedding(Base):
    """
    Stores vector embedding for a message.
    Used for semantic search over conversation history.
    """
    __tablename__ = "message_embeddings"
    
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    embedding = Column(Vector(1024), nullable=False)  # Voyage AI dimensions
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    message = relationship("Message", back_populates="embedding")


class ConversationFact(Base):
    """
    Stores extracted facts from conversation.
    Facts are atomic pieces of information linked to entities.
    Used by get_entity_facts() tool for context retrieval.
    """
    __tablename__ = "conversation_facts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid_utils.uuid7()))
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    fact = Column(Text, nullable=False)  # e.g., "User is studying for AWS exam"
    entity_name = Column(String, nullable=True, index=True)  # Primary entity: "AWS"
    related_entity = Column(String, nullable=True)  # Related entity: "VPC"
    relationship_type = Column(String, nullable=True)  # "related_to", "alternative_to"
    source_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation")
    source_message = relationship("Message")

