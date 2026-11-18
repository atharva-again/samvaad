# PROJECT KNOWLEDGE BASE

## OVERVIEW

Samvaad is a TypeScript full-stack RAG application with text and LiveKit voice
modes. The pnpm workspace contains a Vite/React web app, a self-hostable Hono
API, a LiveKit TypeScript worker, and shared PostgreSQL/Drizzle and protocol
packages.
Better Auth handles Google OAuth and cookie-based sessions.

## STRUCTURE

```text
.
├── packages/
│   ├── api/             # Hono API, Better Auth, RAG, ingestion, persistence
│   ├── web/             # Vite, React, TanStack Router, Base UI
│   ├── voice-agent/     # LiveKit Agents TypeScript worker
│   ├── db/              # Drizzle schema and migrations
│   └── voice-protocol/  # Shared LiveKit data-channel protocol
```

## WHERE TO LOOK

| Task                  | Location                                                       | Notes                                                |
| --------------------- | -------------------------------------------------------------- | ---------------------------------------------------- |
| API routes/middleware | `packages/api/src/app.ts`, `packages/api/src/routes/`          | Hono API                                             |
| Auth                  | `packages/api/src/auth.ts`, `packages/web/lib/auth-client.ts`  | Better Auth, Google OAuth, cookie sessions           |
| Database              | `packages/db/src/`, `packages/db/drizzle/`                     | PostgreSQL, pgvector, Drizzle                        |
| RAG                   | `packages/api/src/rag.ts`                                      | Voyage embeddings/rerank and user-scoped search      |
| Ingestion             | `packages/api/src/ingestion.ts`                                | LlamaCloud parse, structural chunking, deduplication |
| Text agent/memory     | `packages/api/src/text-agent.ts`, `packages/api/src/memory.ts` | Groq and conversation context                        |
| Voice worker          | `packages/voice-agent/src/index.ts`                            | LiveKit, citations, Deepgram, Groq                   |
| UI                    | `packages/web/components/`                                     | React chat and voice controls                        |

## CONVENTIONS

- **TypeScript**: strict mode; keep API payloads validated at the boundary.
- **Database**: PostgreSQL is self-hosted; Drizzle owns schema and migrations.
  Preserve existing user data and use parameterized SQL for specialized RAG
  queries.
- **RAG**: keep user/file ownership filters in database queries; never expose
  another user's chunks.
- **Auth**: use Better Auth sessions, not bearer tokens. Browser API requests
  must include credentials; API routes must verify the session.
- **Citations**: never cite filenames in model text; use numeric IDs. Preserve
  raw response/citations for UI and persistence; strip markers only from TTS.
- **Self-hosting**: don't add cloud-only dependencies. Keep LiveKit Cloud
  optional and the Node services containerizable with `Containerfile`s.
- **Product parity**: preserve API contracts and UX while porting behavior;
  test uploads, history, citations, auth boundaries, and voice persistence.

## COMMANDS

```bash
vp install
vpr db:migrate
vpr dev
vpr dev:all
vpr dev:api
vpr dev:web
vpr dev:voice
vp check
vp test
vpr build
```
