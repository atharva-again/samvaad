import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { requireAuth } from "../auth.js";
import type { ApiEnv } from "../types.js";
import { generateId, stripMarkdown } from "../utils.js";

const ttsSchema = z.object({
  text: z.string().min(1).max(30_000),
  language: z.string().default("en"),
});
const tokenSchema = z.object({ text: z.string().min(1).max(30_000) });
const ttsTokens = new Map<string, { text: string; createdAt: number }>();
const TOKEN_TTL_MS = 5 * 60_000;

export const ttsRouter = new Hono<ApiEnv>();

async function proxyTts(text: string): Promise<Response> {
  const apiKey = process.env.DEEPGRAM_API_KEY;
  if (!apiKey) return Response.json({ error: "DEEPGRAM_API_KEY not set" }, { status: 500 });
  const response = await fetch(
    "https://api.deepgram.com/v1/speak?model=aura-2-asteria-en&encoding=mp3",
    {
      method: "POST",
      headers: {
        Authorization: `Token ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text: stripMarkdown(text) }),
      signal: AbortSignal.timeout(60_000),
    },
  );
  if (!response.ok) {
    return Response.json({ error: "Text-to-speech provider request failed" }, { status: 502 });
  }
  return new Response(response.body, {
    headers: {
      "Content-Type": "audio/mpeg",
      "Content-Disposition": "inline; filename=speech.mp3",
    },
  });
}

ttsRouter.post("/tts", requireAuth, zValidator("json", ttsSchema), async (c) => {
  try {
    const { text } = c.req.valid("json");
    return await proxyTts(text);
  } catch (error) {
    console.error("[tts] Request failed", error);
    return c.json({ error: "Failed to generate speech" }, 502);
  }
});

ttsRouter.post("/tts/token", requireAuth, zValidator("json", tokenSchema), async (c) => {
  const now = Date.now();
  for (const [token, data] of ttsTokens) {
    if (now - data.createdAt > TOKEN_TTL_MS) ttsTokens.delete(token);
  }
  const { text } = c.req.valid("json");
  const token = generateId();
  ttsTokens.set(token, { text, createdAt: now });
  return c.json({ token });
});

ttsRouter.get("/tts/stream/:token", async (c) => {
  const token = c.req.param("token");
  const entry = ttsTokens.get(token);
  if (!entry || Date.now() - entry.createdAt > TOKEN_TTL_MS) {
    ttsTokens.delete(token);
    return c.json({ detail: "Token not found or expired" }, 404);
  }
  return proxyTts(entry.text);
});
