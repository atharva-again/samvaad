import { timingSafeEqual } from "node:crypto";
import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { query } from "../db.js";
import { runPostResponseTasks } from "../memory.js";
import { saveAssistantMessage, saveUserMessage } from "../persistence.js";
import { buildSystemPrompt } from "../prompts.js";
import { citationSources, ragQuery } from "../rag.js";
import type { CitationSource, StoredMessage } from "../types.js";
import { formatRagContext } from "../utils.js";

const contextSchema = z.object({
  user_id: z.string().min(1),
  conversation_id: z.string().uuid(),
  persona: z.string().min(1).max(100).default("default"),
  strict_mode: z.boolean().default(false),
});
const ragSchema = z.object({
  user_id: z.string().min(1),
  query: z.string().min(1).max(500),
});
const sourceSchema = z.object({
  filename: z.string(),
  content_preview: z.string(),
  rerank_score: z.number().optional(),
  chunk_id: z.string().optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
});
const userMessageSchema = z.object({
  user_id: z.string().min(1),
  conversation_id: z.string().uuid(),
  user_message_id: z.string().uuid(),
  user_message: z.string().min(1).max(12_000),
});
const assistantMessageSchema = z.object({
  user_id: z.string().min(1),
  conversation_id: z.string().uuid(),
  user_message_id: z.string().uuid(),
  assistant_message_id: z.string().uuid(),
  assistant_message: z.string().min(1).max(30_000),
  sources: z.array(sourceSchema).default([]),
});

export const voiceInternalRouter = new Hono();

voiceInternalRouter.use("*", async (c, next) => {
  const expected = process.env.VOICE_AGENT_SHARED_SECRET;
  if (!expected) {
    return c.json({ detail: "Voice-agent bridge is not configured" }, 503);
  }
  const supplied =
    c.req
      .header("Authorization")
      ?.replace(/^Bearer\s+/i, "")
      .trim() ?? "";
  const expectedBytes = Buffer.from(expected);
  const suppliedBytes = Buffer.from(supplied);
  if (
    !supplied ||
    expectedBytes.length !== suppliedBytes.length ||
    !timingSafeEqual(expectedBytes, suppliedBytes)
  ) {
    return c.json({ detail: "Invalid voice-agent credentials" }, 401);
  }
  await next();
});

voiceInternalRouter.post("/context", zValidator("json", contextSchema), async (c) => {
  const body = c.req.valid("json");
  const { rows: conversations } = await query<{
    id: string;
    summary: string | null;
    facts: string | null;
  }>("SELECT id, summary, facts FROM conversations WHERE id = $1 AND user_id = $2", [
    body.conversation_id,
    body.user_id,
  ]);
  const conversation = conversations[0];
  if (!conversation) return c.json({ detail: "Conversation not found" }, 404);
  const { rows: messages } = await query<StoredMessage>(
    `SELECT id, conversation_id, role, content, sources, created_at
			 FROM messages WHERE conversation_id = $1
			 ORDER BY created_at DESC LIMIT 6`,
    [body.conversation_id],
  );
  return c.json({
    system_instruction: buildSystemPrompt({
      persona: body.persona,
      strictMode: body.strict_mode,
      mode: "voice",
      summary: conversation.summary,
      facts: conversation.facts,
    }),
    messages: messages.reverse().map(({ role, content }) => ({ role, content })),
  });
});

voiceInternalRouter.post("/rag", zValidator("json", ragSchema), async (c) => {
  const body = c.req.valid("json");
  const result = await ragQuery(body.query.trim(), {
    userId: body.user_id,
    topK: 3,
  });
  const sources: CitationSource[] = citationSources(result.chunks);
  return c.json({
    context: formatRagContext(result.chunks),
    sources,
  });
});

voiceInternalRouter.post("/user-message", zValidator("json", userMessageSchema), async (c) => {
  const body = c.req.valid("json");
  try {
    const saved = await saveUserMessage({
      conversationId: body.conversation_id,
      userId: body.user_id,
      userMessageId: body.user_message_id,
      userMessage: body.user_message,
    });
    return c.json(
      {
        accepted: true,
        user_message_id: saved.userMessageId,
        conversation_title: saved.conversationTitle,
      },
      202,
    );
  } catch (error) {
    if (error instanceof Error && error.message === "Conversation not found") {
      return c.json({ detail: "Conversation not found" }, 404);
    }
    throw error;
  }
});

voiceInternalRouter.post(
  "/assistant-message",
  zValidator("json", assistantMessageSchema),
  async (c) => {
    const body = c.req.valid("json");
    try {
      const saved = await saveAssistantMessage({
        conversationId: body.conversation_id,
        userId: body.user_id,
        userMessageId: body.user_message_id,
        assistantMessageId: body.assistant_message_id,
        assistantMessage: body.assistant_message,
        sources: body.sources as CitationSource[],
      });
      if (saved.inserted) {
        void runPostResponseTasks({
          conversationId: body.conversation_id,
          userId: body.user_id,
          userMessage: saved.userMessage,
          assistantResponse: body.assistant_message,
        });
      }
      return c.json(
        {
          accepted: true,
          user_message_id: body.user_message_id,
          assistant_message_id: saved.assistantMessageId,
          conversation_title: saved.conversationTitle,
        },
        202,
      );
    } catch (error) {
      if (error instanceof Error && error.message === "Conversation not found") {
        return c.json({ detail: "Conversation not found" }, 404);
      }
      if (
        error instanceof Error &&
        error.message === "User message must be saved before its assistant response"
      ) {
        return c.json({ detail: error.message }, 409);
      }
      throw error;
    }
  },
);
