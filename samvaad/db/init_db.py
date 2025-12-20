from dotenv import load_dotenv
load_dotenv()

from samvaad.db.session import engine
from samvaad.db.models import (
    Base,
    # Core tables
    User,
    GlobalChunk,
    GlobalFile,
    File,
    # Conversation tables
    Conversation,
    Message,
    # Memory tables (in-chat memory system)
    MessageEmbedding,
    ConversationFact,
)

def init_db():
    """
    Create all database tables defined in models.py.
    
    Tables created:
    - users
    - global_chunks, global_files, global_file_chunks
    - files
    - conversations, messages
    - message_embeddings, conversation_facts (memory system)
    """
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()

