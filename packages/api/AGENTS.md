# API KNOWLEDGE BASE

## OVERVIEW

Self-hostable Hono API running on Node.js. It owns Better Auth session checks,
PostgreSQL persistence, Groq text responses, Voyage retrieval, LlamaCloud
ingestion, user settings, and the private LiveKit worker endpoints.

## STRUCTURE

| Path                 | Role                                                     |
| -------------------- | -------------------------------------------------------- |
| `src/app.ts`         | Hono middleware, Better Auth handler, route mounting     |
| `src/routes/`        | User-facing and private API routes                       |
| `src/auth.ts`        | Better Auth setup and session middleware                 |
| `src/db.ts`          | Re-exports the shared Drizzle/PostgreSQL package         |
| `src/persistence.ts` | Atomic, idempotent conversation-turn persistence         |
| `src/rag.ts`         | Voyage embeddings/rerank and pgvector search             |
| `src/ingestion.ts`   | LlamaCloud parsing, chunking, embeddings, content dedupe |
| `src/text-agent.ts`  | Groq tool-calling chat flow                              |
| `src/memory.ts`      | Summaries, extracted facts, and history heuristics       |

## CONVENTIONS

- Validate untrusted payloads with Zod before service calls.
- Use parameterized SQL only; keep ownership conditions in read, update, and
  delete queries.
- Keep the LiveKit internal routes behind `VOICE_AGENT_SHARED_SECRET`; the
  browser must not be able to publish trusted assistant/citation events.
- Preserve API route paths and response shapes used by the frontend.
- Keep provider keys server-side. Groq, Deepgram, Voyage, and LlamaCloud are
  external providers; don't replace them as part of framework work.
