from dotenv import load_dotenv
load_dotenv()

from samvaad.db.session import engine
from samvaad.db.models import Base
from sqlalchemy import text

def reset_schema():
    print("Beginning migration to Global Deduplication Schema...")
    with engine.connect() as conn:
        print("Dropping old tables...")
        # Cascade ensures dependent tables/constraints are removed
        conn.execute(text("DROP TABLE IF EXISTS chunks CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS global_chunks CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS global_file_chunks CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS file_content_chunks CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS files CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS global_files CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS file_contents CASCADE"))
        conn.commit()
        print("Dropped 'chunks', 'files', 'file_contents'.")

    print("Re-creating tables from new models...")
    Base.metadata.create_all(bind=engine)
    print("Schema migration complete.")

if __name__ == "__main__":
    reset_schema()
