import { Hono } from "hono";
import { bodyLimit } from "hono/body-limit";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { requireAuth } from "../auth.js";
import { query } from "../db.js";
import { runPostResponseTasks, detectQueryComplexity } from "../memory.js";
import { getOrCreateConversation, saveAssistantMessage, saveUserMessage } from "../persistence.js";
import { buildSlidingWindow } from "../prompts.js";
import { textAgentRespond } from "../text-agent.js";
import type { ApiEnv, StoredMessage } from "../types.js";
import { generateId } from "../utils.js";

const textMessageSchema = z.object({
  message: z.string().min(1).max(30_000),
  conversation_id: z.string().uuid(),
  user_message_id: z.string().uuid().optional().nullable(),
  assistant_message_id: z.string().uuid().optional().nullable(),
  persona: z.string().min(1).max(100).default("default"),
  strict_mode: z.boolean().default(false),
  allowed_file_ids: z.array(z.string().min(1)).max(100).nullable().optional(),
});

export const textRouter = new Hono<ApiEnv>();
textRouter.use("/text-mode", bodyLimit({ maxSize: 1_048_576 }));
textRouter.post("/text-mode", requireAuth, zValidator("json", textMessageSchema), async (c) => {
  const user = c.get("user");
  const body = c.req.valid("json");
  try {
    const conversation = await getOrCreateConversation(body.conversation_id, user.id);
    if (!conversation) {
      return c.json({ error: "Conversation not found", success: false });
    }
    const userMessageId = body.user_message_id ?? generateId();
    const { rows: dbMessages } = await query<StoredMessage>(
      `SELECT id, conversation_id, role, content, sources, created_at
				 FROM messages WHERE conversation_id = $1 AND id <> $2 ORDER BY created_at`,
      [conversation.id, userMessageId],
    );
    const [recentMessages] = buildSlidingWindow(dbMessages, 6);
    const savedUserMessage = await saveUserMessage({
      conversationId: conversation.id,
      userId: user.id,
      userMessageId,
      userMessage: body.message,
    });

    const complexity = detectQueryComplexity(body.message);
    if (complexity.recommendation !== "baseline") {
      console.info("[Memory] Complex query detected", complexity.signals);
    }

    const result = await textAgentRespond({
      query: body.message,
      userId: user.id,
      messages: recentMessages,
      persona: body.persona,
      strictMode: body.strict_mode,
      summary: conversation.summary,
      facts: conversation.facts,
      fileIds: body.allowed_file_ids,
    });
    const savedAssistantMessage = await saveAssistantMessage({
      conversationId: conversation.id,
      userId: user.id,
      userMessageId: savedUserMessage.userMessageId,
      assistantMessageId: body.assistant_message_id,
      assistantMessage: result.response,
      sources: result.sources,
    });
    if (savedAssistantMessage.inserted) {
      void runPostResponseTasks({
        conversationId: conversation.id,
        userId: user.id,
        userMessage: body.message,
        assistantResponse: result.response,
      });
    }
    return c.json({
      conversation_id: conversation.id,
      response: result.response,
      success: true,
      sources: result.sources,
      user_message_id: savedUserMessage.userMessageId,
      assistant_message_id: savedAssistantMessage.assistantMessageId,
      conversation_title: savedAssistantMessage.conversationTitle,
    });
  } catch (error) {
    console.error("[text-mode] Request failed", error);
    return c.json({ error: "An internal server error occurred.", success: false });
  }
});
