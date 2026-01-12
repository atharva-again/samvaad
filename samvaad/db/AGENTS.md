# DB KNOWLEDGE BASE

**Generated:** 2026-01-12T17:15:20Z
**Commit:** 5b9b2c1
**Branch:** docs/update

## OVERVIEW
Core data persistence and service layer handling PostgreSQL/Supabase interactions with vector search support.

## STRUCTURE
```
samvaad/db/
├── session.py          # Database engine configuration and session management
├── models.py           # SQLAlchemy ORM definitions (Users, Files, Chunks, Conversations)
├── service.py          # Primary DBService for RAG operations and deduplication
└── conversation_service.py # Logic for chat history, summaries, and persistent memory
```

## WHERE TO LOOK
| Task | Location | Logic |
|------|----------|-------|
| Smart Ingestion | `service.py` | `add_smart_dedup_content` handles deduplication |
| Vector Search | `service.py` | `search_similar_chunks` uses pgvector cosine distance |
| Orphan Cleanup | `service.py` | `delete_file` ensures zero-leak deletion of shared blobs |
| Ordered Chats | `models.py` | `Conversation` and `Message` use UUID v7 for sorting |
| Global Dedupe | `models.py` | `GlobalFile` and `GlobalChunk` store content by SHA-256 |

## CONVENTIONS
- **Deduplication**: Content-addressable storage using SHA-256 hashes for both files and chunks.
- **Vector Search**: Leverages `pgvector` with 1024-dimension embeddings (Voyage AI).
- **Time Sorting**: Uses `uuid_utils.uuid7()` for conversations and messages to ensure efficient B-tree indexing.
- **Sessions**: Uses `NullPool` to prevent connection exhaustion in serverless/FastAPI environments.

## ANTI-PATTERNS
- **Leaks**: Never delete `GlobalFile` directly. Use `DBService.delete_file` to handle orphan logic.
- **Concurrency**: Avoid check-then-insert. Use `ON CONFLICT DO NOTHING` or `db.merge()` as seen in `service.py`.
- **Sessions**: Do not instantiate `SessionLocal()` directly; use `get_db_context()` or `get_db()`.
- **Joins**: Avoid manual 4-table joins for RAG retrieval; use the optimized `search_similar_chunks`.
