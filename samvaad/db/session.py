import os
from collections.abc import Generator
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# Load environment variables from .env
load_dotenv()

# Fetch variables with defaults to prevent URL construction errors if env is missing
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    USER = os.getenv("user", "postgres")
    PASSWORD = os.getenv("password", "")
    HOST = os.getenv("host", "localhost")
    PORT = os.getenv("port", "5432")
    DBNAME = os.getenv("dbname", "postgres")
    # Construct the SQLAlchemy connection string
    DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
else:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://") and "psycopg2" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Configure connection args based on deployment
connect_args = {"connect_timeout": 30}

# If using Supabase Transaction Pooler (port 6543), we must disable prepared statements
if "6543" in DATABASE_URL:
    connect_args["prepare_threshold"] = 0

engine = create_engine(
    DATABASE_URL,
    # Use NullPool for serverless environments (Vercel) to effectively close connections
    # after each request, preventing exhaustion (since we can't pool across lambdas).
    poolclass=NullPool,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for DB session (for scripts/CLI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
