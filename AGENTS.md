# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-12T17:12:56Z
**Commit:** 5b9b2c1
**Branch:** docs/update

## OVERVIEW
Samvaad is a full-stack RAG (Retrieval-Augmented Generation) application with voice and text modes. 
The backend is built with FastAPI and Python, while the frontend is a Next.js application.

## STRUCTURE
```
.
├── samvaad/           # Core backend logic (FastAPI, Pipeline, DB)
│   ├── api/           # API routes and entry points
│   ├── core/          # Authentication, memory, and shared logic
│   ├── db/            # Database models and services (Supabase/PostgreSQL)
│   ├── pipeline/      # RAG pipeline (Ingestion, Retrieval, Deletion)
│   ├── prompts/       # AI persona and mode definitions
│   └── utils/         # Citations, text processing, and hashing utilities
├── frontend/          # Next.js/React frontend application
├── tests/             # Unit and integration test suites
├── data/              # Document storage and local data
└── PLANS/             # Project roadmap and technical designs
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| API Endpoints | `samvaad/api/main.py` | FastAPI app definition |
| Database Ops | `samvaad/db/service.py` | Core DB service logic |
| AI Prompting | `samvaad/prompts/` | Persona and style definitions |
| RAG Pipeline | `samvaad/pipeline/` | Document ingestion and retrieval |
| UI Components | `frontend/components/` | React components |
| Auth Logic | `samvaad/core/auth.py` | Backend authentication |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `app` | Variable | `samvaad/api/main.py` | FastAPI application |
| `DBService` | Class | `samvaad/db/service.py` | Primary database interface |
| `TextMessageRequest` | Class | `samvaad/api/main.py` | Schema for text chat requests |
| `VoiceModeRequest` | Class | `samvaad/api/main.py` | Schema for voice session setup |

## CONVENTIONS
- **Python**: Uses `uv` for dependency management. Strict typing with `mypy`.
- **Formatting**: `Black` (88 char) for Python, `Biome` for Frontend.
- **Linting**: `Ruff` for Python, `ESLint` and `Biome` for Frontend.
- **Testing**: `pytest` for backend unit and integration tests.

## ANTI-PATTERNS (THIS PROJECT)
- **Database**: Avoid simple check-then-insert. Use `ON CONFLICT DO NOTHING` for concurrency.
- **Frontend**: Do not depend on hover state in markdown memoization to prevent DOM recreation.
- **AI Responses**: NEVER use filenames in citations (e.g., `[file.pdf]`). Use numeric IDs like `[1]`.

## COMMANDS
```bash
# Backend Dev
uvicorn samvaad.api.main:app --reload

# Frontend Dev
cd frontend && pnpm dev

# Tests
pytest
```

## NOTES
- References to `requirements.txt` in README are deprecated; use `pyproject.toml`.
- `PLANS/` directory contains living architecture documents.
