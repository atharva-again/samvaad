# AGENTS: API Layer

## OVERVIEW
Entry point and API routing layer for the Samvaad FastAPI backend, handling authentication, document ingestion, and dialogue management.

## WHERE TO LOOK
| Component | File/Path | Role |
|-----------|-----------|------|
| **Entry Point** | `main.py` | FastAPI app init, middleware config, and core endpoints (`/text-mode`, `/voice-mode`). |
| **Auth Dependency** | `deps.py` | Supabase token verification and automatic user synchronization with local DB. |
| **Conversations** | `routers/conversations.py` | History management, delta sync (messages since), and bulk deletion. |
| **File Management** | `routers/files.py` | User-specific document listing, renaming, and batch deletion. |
| **User Profile** | `routers/users.py` | Profile retrieval and onboarding walkthrough state management. |

## CONVENTIONS
- **Middleware Execution**: Added in REVERSE order of execution. `CORSMiddleware` must be added last to ensure it runs first for preflight requests.
- **Background Operations**: Use FastAPI `BackgroundTasks` for post-response logic (e.g., summary/fact extraction) to minimize latency.
- **I/O Safety**: Use `asyncio.to_thread` for blocking CPU-bound tasks like `ingest_file_pipeline` (LlamaParse) within async endpoints.
- **Idempotency**: Delete endpoints (especially `files.py`) should return success even if the resource is already gone.

## ANTI-PATTERNS
- **Auth in Beacon**: `/voice-mode/disconnect-beacon` bypasses standard auth due to browser `sendBeacon` limitations; use room URLs as capability tokens.
- **Direct DB Access**: Avoid raw SQLAlchemy queries in routers; prefer `ConversationService` or `DBService` abstractions.
- **Error Exposure**: Catch internal exceptions in high-level endpoints to return sanitized error responses to the client.
