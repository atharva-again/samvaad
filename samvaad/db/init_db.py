from dotenv import load_dotenv

load_dotenv()

from samvaad.db.models import (
    Base,
)
from samvaad.db.session import engine


def init_db():
    """
    Create all database tables defined in models.py.
    
    Tables:
    - users (id, email, name, created_at)
    - global_chunks (id, file_id, content, chunk_index, embedding)
    - global_files (id, filename, content_hash, metadata, created_at)
    - files (id, user_id, filename, content_hash, created_at)
    - conversations (id, user_id, title, summary, facts, is_pinned, created_at, updated_at)
    - messages (id, conversation_id, role, content, sources, token_count, created_at)
    """
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    init_db()
