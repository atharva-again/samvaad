# Samvaad web app

Vite + React single-page app for Samvaad's document chat and LiveKit voice
experience. TanStack Router handles client-side routes and Base UI provides
accessible menu and popover primitives. It is part of the root pnpm workspace.

## Local development

From the repository root:

```bash
vp install
vpr dev:web
```

Configure the browser-visible `VITE_API_URL` in the single repository-root
`.env` (copy [`../../.env.example`](../../.env.example)); Vite loads it from the
workspace root.

Authentication is handled by Better Auth on the Hono API. The browser uses
cookie credentials when calling the API; configure `FRONTEND_URL` and
`BETTER_AUTH_URL` in the API environment. The API, not the browser app, owns the
LiveKit API secret and issues participant tokens.

For Google OAuth callback URLs and full local setup, see the root
[`README.md`](../../README.md).

## Checks

```bash
vp run --filter @samvaad/web build
vp check
```

For self-hosting, build the web container from the repository root and set the
browser-visible API origin at build time:

```bash
podman build --format docker -f packages/web/Containerfile \
  --build-arg VITE_API_URL=https://api.example.com -t samvaad-web .
```

The container serves the static Vite build with a small Node.js SPA fallback
server. The API origin is embedded at build time; rebuild to change it.
