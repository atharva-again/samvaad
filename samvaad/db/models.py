import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, BigInteger, Table, func
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
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    
    # Pointer to the global content
    content_hash = Column(String, ForeignKey("global_files.hash"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="files")
    content_ref = relationship("GlobalFile", backref="references")

# Deleted old Chunk class as it is replaced by GlobalChunk + Association
