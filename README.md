# Samvaad (संवाद)

> Dialogue-based learning through text and real-time voice.

Samvaad turns uploaded documents into a conversational learning experience.
Users can chat with their documents, inspect numeric citations, and talk to a
LiveKit voice agent.

## Stack

- **Web:** React, Vite, TanStack Router, Base UI, TypeScript, Tailwind CSS
- **API:** Hono on Node.js and TypeScript
- **Auth:** Better Auth with Google OAuth and cookie sessions
- **Database:** self-hosted PostgreSQL + pgvector, Drizzle ORM/schema/migrations
- **Voice:** LiveKit Agents for TypeScript, Deepgram STT/TTS, Groq, and Silero VAD
- **Document parsing:** LlamaCloud / LlamaParse
- **Embeddings and reranking:** Voyage AI
- **Workspace:** pnpm monorepo

Groq, Deepgram, Voyage AI, and LlamaCloud remain the product providers. The app,
PostgreSQL, and LiveKit server/agent can all be self-hosted; LiveKit Cloud is
optional.

## Repository layout

```text
packages/
  api/             Hono API and Better Auth server
  web/             Vite + React SPA
  voice-agent/     LiveKit Agents TypeScript worker
  db/              Drizzle schema and PostgreSQL migrations
  voice-protocol/  Shared LiveKit data-channel protocol
```

## Local development

Requirements: Node.js 22.18+ (or 24.11+ / 26+), pnpm 12.21+, the Vite+ `vp`
CLI, PostgreSQL with the `vector` extension, and provider credentials.

```bash
vp install
```

Vite+ is pinned in the workspace. `vp dev` starts the web app on port 5177;
`vp check` handles formatting, lint, and type checks; `vp test` runs the
workspace tests. Normal development uses the web and API only. The LiveKit
worker is opt-in.

Create one repository-root `.env` from [`.env.example`](.env.example). The API,
web app, voice worker, and database tooling all read that file; do not create
package-specific env files.

In the Google OAuth client, add
`http://localhost:5177/api/auth/callback/google` as an authorized redirect URI.
For production, use the corresponding `BETTER_AUTH_URL`.

Apply database migrations once:

```bash
vpr db:migrate
```

In separate terminals, run:

```bash
vpr dev:web
vpr dev:api
```

The web dev server runs on port 5177 and proxies API requests to the API on
port 18765, so only the web port needs an SSH tunnel. `vp dev` is Vite+'s
built-in command for the default web package; use `vpr dev:web` to run its
workspace script. The LiveKit worker is not started by `vpr dev`; start it
separately with `vpr dev:voice` only when testing voice.

Samvaad expects its own PostgreSQL instance on port 55432, separate from
services using the conventional 5432 port. The API binds to loopback on port
18765; the web proxy reaches it there.

For production deployments on sibling subdomains (for example,
`app.example.com` and `api.example.com`), set `AUTH_COOKIE_DOMAIN=.example.com`.
Prefer serving the web app and API on the same site; unrelated domains can be
blocked from sharing cookies by browser third-party-cookie policies.
Also set `ALLOWED_HOSTS` to the API host names that should be accepted.
If reusing the existing Vercel project, set its Root Directory to
`packages/web` and set `VITE_API_URL` to the public API origin.

## Checks and containers

```bash
vp check
vp test
vpr build
```

Build with Podman from the repository root:

```bash
podman build --format docker -f Containerfile -t samvaad-api .
podman build --format docker -f packages/web/Containerfile \
  --build-arg VITE_API_URL=https://api.example.com -t samvaad-web .
podman build --format docker -f packages/voice-agent/Containerfile \
  -t samvaad-voice-agent .
```

These `Containerfile`s are intended for Podman builds. PostgreSQL and LiveKit
remain separately self-hostable services. Pass the same root `.env` to runtime
containers with `podman run --env-file .env`; do not copy it into an image.

## Data and migration notes

The Better Auth migration adds auth fields and session/account tables to the
existing `users` table without replacing conversation, file, message, or
pgvector data. New Google sign-ins use Better Auth user IDs. If an existing
database contains users from the previous auth provider, those identities need
an explicit account/data-linking migration before those users can sign in; do
not blindly delete the old user rows.

Voice citations remain in stored/displayed answers; only the speech stream strips
numeric citation markers.
