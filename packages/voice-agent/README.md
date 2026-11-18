# Samvaad LiveKit voice worker

The Hono API authenticates the user, checks conversation ownership, and issues
the short-lived LiveKit participant token. LiveKit dispatches this TypeScript
worker into the room. The worker and API preserve the existing providers
(Groq, Deepgram, Voyage, and LlamaCloud) and the existing RAG, prompt/history,
and citation persistence behavior.

The application runtime is TypeScript/Node.js. The API's private
`/internal/voice/*` routes are protected by `VOICE_AGENT_SHARED_SECRET`.

## Local setup

Run a self-hosted LiveKit server and configure the same LiveKit API key/secret
for the server, API, and worker. LiveKit Cloud is optional.

From the repository root:

```bash
vp install
vpr dev:voice
```

Set the worker and API variables in the single repository-root `.env` copied
from [`../../.env.example`](../../.env.example).

Set the exact same `VOICE_AGENT_SHARED_SECRET` in the worker and API
environments. The LiveKit API secret and API shared secret must never use a
browser-exposed prefix such as `VITE_`.

`DEEPGRAM_STT_MODEL` defaults to the prior Pipecat Deepgram default,
`nova-3-general`, and is configurable. TTS retains the existing
`aura-2-asteria-en` voice. Silero keeps the prior 0.8 activation confidence,
0.5s minimum speech, and 1.0s silence endpoint. Pipecat's separate `min_volume`
gate has no direct LiveKit Silero option and remains a small voice-input parity
gap. `enable_tts=false` keeps the existing voice-to-text / push-to-talk mode.

## Checks and container

```bash
vp run --filter @samvaad/voice-agent build
vp test
```

Build the OCI container from the repository root:

```bash
podman build --format docker -f packages/voice-agent/Containerfile -t samvaad-voice-agent .
podman run --env-file .env samvaad-voice-agent
```
