import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { requireAuth } from "../auth.js";
import { query, withTransaction } from "../db.js";
import type { ApiEnv, ConversationRow, StoredMessage } from "../types.js";
import { generateId } from "../utils.js";

const conversationIdSchema = z.string().uuid();
const createSchema = z.object({
  id: z.string().uuid().optional(),
  title: z.string().nullable().optional(),
  active_strict_mode: z.boolean().nullable().optional(),
  active_persona: z.string().nullable().optional(),
});
const updateSchema = z.object({
  title: z.string().nullable().optional(),
  is_pinned: z.boolean().nullable().optional(),
  active_strict_mode: z.boolean().nullable().optional(),
  active_persona: z.string().nullable().optional(),
});
const settingsSchema = z.object({
  active_strict_mode: z.boolean().nullable().optional(),
  active_persona: z.string().nullable().optional(),
});
const truncateSchema = z.object({ keep_message_ids: z.array(z.string().uuid()) });
const bulkDeleteSchema = z.object({ conversation_ids: z.array(z.string().uuid()) });

function conversationSummary(row: ConversationRow & { message_count?: number | string }) {
  return {
    id: row.id,
    title: row.title,
    mode: "text",
    created_at: row.created_at,
    updated_at: row.updated_at,
    is_pinned: row.is_pinned ?? false,
    message_count: Number(row.message_count ?? 0),
  };
}

function messagePayload(message: StoredMessage) {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    sources: message.sources ?? [],
    created_at: message.created_at,
  };
}

async function findOwnedConversation(id: string, userId: string) {
  const { rows } = await query<ConversationRow>(
    "SELECT * FROM conversations WHERE id = $1 AND user_id = $2",
    [id, userId],
  );
  return rows[0] ?? null;
}

export const conversationsRouter = new Hono<ApiEnv>({ strict: false });
conversationsRouter.use("*", requireAuth);

conversationsRouter.post("/", zValidator("json", createSchema), async (c) => {
  const user = c.get("user");
  const body = c.req.valid("json");
  if (body.id) {
    const existing = await findOwnedConversation(body.id, user.id);
    if (existing) {
      const { rows: countRows } = await query<{ count: string }>(
        "SELECT count(*)::text AS count FROM messages WHERE conversation_id = $1",
        [body.id],
      );
      return c.json(conversationSummary({ ...existing, message_count: countRows[0]?.count }));
    }
  }
  const id = body.id ?? generateId();
  const { rows } = await query<ConversationRow>(
    `INSERT INTO conversations
		   (id, user_id, title, active_strict_mode, active_persona)
		 VALUES ($1, $2, $3, $4, $5)
		 RETURNING *`,
    [
      id,
      user.id,
      body.title ?? "New Conversation",
      body.active_strict_mode ?? null,
      body.active_persona ?? null,
    ],
  );
  return c.json(conversationSummary(rows[0]!));
});

conversationsRouter.get("/", async (c) => {
  const user = c.get("user");
  const rawLimit = Number(c.req.query("limit") ?? 50);
  const rawOffset = Number(c.req.query("offset") ?? 0);
  if (
    !Number.isInteger(rawLimit) ||
    !Number.isInteger(rawOffset) ||
    rawLimit < 1 ||
    rawOffset < 0
  ) {
    return c.json({ detail: "Invalid pagination values" }, 422);
  }
  const limit = Math.min(rawLimit, 100);
  const offset = rawOffset;
  const { rows } = await query<ConversationRow & { message_count: string }>(
    `SELECT c.*,
		        (SELECT count(*) FROM messages m WHERE m.conversation_id = c.id)::text AS message_count
		 FROM conversations c
		 WHERE c.user_id = $1
		 ORDER BY c.is_pinned DESC, c.updated_at DESC
		 LIMIT $2 OFFSET $3`,
    [user.id, limit, offset],
  );
  return c.json(rows.map(conversationSummary));
});

conversationsRouter.get("/:conversationId/messages", async (c) => {
  const user = c.get("user");
  const id = c.req.param("conversationId");
  if (!conversationIdSchema.safeParse(id).success) {
    return c.json({ detail: "Invalid conversation ID" }, 422);
  }
  const conversation = await findOwnedConversation(id, user.id);
  if (!conversation) return c.json([]);

  const afterValue = c.req.query("after");
  const after = afterValue ? new Date(afterValue) : null;
  if (afterValue && Number.isNaN(after?.getTime())) {
    return c.json({ detail: "Invalid after timestamp" }, 422);
  }
  const { rows } = await query<StoredMessage>(
    `SELECT id, conversation_id, role, content, sources, created_at
		 FROM messages
		 WHERE conversation_id = $1 AND ($2::timestamptz IS NULL OR created_at > $2)
		 ORDER BY created_at`,
    [id, after],
  );
  return c.json(rows.map(messagePayload));
});

conversationsRouter.get("/:conversationId/settings", async (c) => {
  const user = c.get("user");
  const id = c.req.param("conversationId");
  if (!conversationIdSchema.safeParse(id).success) {
    return c.json({ detail: "Invalid conversation ID" }, 422);
  }
  const conversation = await findOwnedConversation(id, user.id);
  if (!conversation) return c.json({ detail: "Conversation not found" }, 404);
  return c.json({
    active_strict_mode: conversation.active_strict_mode,
    active_persona: conversation.active_persona,
  });
});

conversationsRouter.put(
  "/:conversationId/settings",
  zValidator("json", settingsSchema),
  async (c) => {
    const user = c.get("user");
    const id = c.req.param("conversationId");
    if (!conversationIdSchema.safeParse(id).success) {
      return c.json({ detail: "Invalid conversation ID" }, 422);
    }
    const settings = c.req.valid("json");
    const assignments: string[] = [];
    const values: unknown[] = [];
    if (settings.active_strict_mode != null) {
      values.push(settings.active_strict_mode);
      assignments.push(`active_strict_mode = $${values.length}`);
    }
    if (settings.active_persona != null) {
      values.push(settings.active_persona);
      assignments.push(`active_persona = $${values.length}`);
    }
    let conversation: ConversationRow | null;
    if (assignments.length > 0) {
      values.push(id, user.id);
      const { rows } = await query<ConversationRow>(
        `UPDATE conversations
				 SET ${assignments.join(", ")}, updated_at = now()
				 WHERE id = $${values.length - 1} AND user_id = $${values.length}
				 RETURNING *`,
        values,
      );
      conversation = rows[0] ?? null;
    } else {
      conversation = await findOwnedConversation(id, user.id);
    }
    if (!conversation) return c.json({ detail: "Conversation not found" }, 404);
    return c.json({
      active_strict_mode: conversation.active_strict_mode,
      active_persona: conversation.active_persona,
    });
  },
);

conversationsRouter.delete(
  "/:conversationId/messages",
  zValidator("json", truncateSchema),
  async (c) => {
    const user = c.get("user");
    const id = c.req.param("conversationId");
    if (!conversationIdSchema.safeParse(id).success) {
      return c.json({ detail: "Invalid conversation ID" }, 422);
    }
    const { keep_message_ids: keepIds } = c.req.valid("json");
    const deletedCount = await withTransaction(async (client) => {
      const owned = await client.query(
        "SELECT id FROM conversations WHERE id = $1 AND user_id = $2 FOR UPDATE",
        [id, user.id],
      );
      if (owned.rowCount === 0) return 0;
      const result =
        keepIds.length > 0
          ? await client.query(
              "DELETE FROM messages WHERE conversation_id = $1 AND NOT (id = ANY($2::uuid[]))",
              [id, keepIds],
            )
          : await client.query("DELETE FROM messages WHERE conversation_id = $1", [id]);
      if (result.rowCount) {
        await client.query("UPDATE conversations SET updated_at = now() WHERE id = $1", [id]);
      }
      return result.rowCount ?? 0;
    });
    return c.json({ deleted_count: deletedCount });
  },
);

conversationsRouter.patch("/:conversationId", zValidator("json", updateSchema), async (c) => {
  const user = c.get("user");
  const id = c.req.param("conversationId");
  if (!conversationIdSchema.safeParse(id).success) {
    return c.json({ detail: "Invalid conversation ID" }, 422);
  }
  const body = c.req.valid("json");
  const assignments: string[] = [];
  const values: unknown[] = [];
  const allowed: Array<keyof typeof body> = [
    "title",
    "is_pinned",
    "active_strict_mode",
    "active_persona",
  ];
  for (const key of allowed) {
    if (body[key] !== undefined && body[key] !== null) {
      values.push(body[key]);
      assignments.push(`${key} = $${values.length}`);
    }
  }
  if (assignments.length > 0) {
    assignments.push("updated_at = now()");
  }
  values.push(id, user.id);
  const { rows } = await query<ConversationRow>(
    `UPDATE conversations SET ${assignments.length ? assignments.join(", ") : "updated_at = updated_at"}
			 WHERE id = $${values.length - 1} AND user_id = $${values.length}
			 RETURNING *`,
    values,
  );
  const conversation = rows[0];
  if (!conversation) return c.json({ detail: "Conversation not found" }, 404);
  const { rows: countRows } = await query<{ count: string }>(
    "SELECT count(*)::text AS count FROM messages WHERE conversation_id = $1",
    [id],
  );
  return c.json(
    conversationSummary({
      ...conversation,
      message_count: countRows[0]?.count,
    }),
  );
});

conversationsRouter.get("/:conversationId", async (c) => {
  const user = c.get("user");
  const id = c.req.param("conversationId");
  if (!conversationIdSchema.safeParse(id).success) {
    return c.json({ detail: "Invalid conversation ID" }, 422);
  }
  const conversation = await findOwnedConversation(id, user.id);
  if (!conversation) return c.json({ detail: "Conversation not found" }, 404);
  const { rows: messages } = await query<StoredMessage>(
    `SELECT id, conversation_id, role, content, sources, created_at
		 FROM messages WHERE conversation_id = $1 ORDER BY created_at`,
    [id],
  );
  return c.json({
    id: conversation.id,
    title: conversation.title,
    mode: "text",
    summary: conversation.summary,
    created_at: conversation.created_at,
    updated_at: conversation.updated_at,
    messages: messages.map(messagePayload),
    active_strict_mode: conversation.active_strict_mode,
    active_persona: conversation.active_persona,
  });
});

conversationsRouter.delete("/batch", zValidator("json", bulkDeleteSchema), async (c) => {
  const user = c.get("user");
  const { conversation_ids: ids } = c.req.valid("json");
  if (ids.length === 0) return c.json({ deleted_count: 0 });
  const { rowCount } = await query(
    "DELETE FROM conversations WHERE id = ANY($1::uuid[]) AND user_id = $2",
    [ids, user.id],
  );
  return c.json({ deleted_count: rowCount ?? 0, success: true });
});

conversationsRouter.delete("/:conversationId", async (c) => {
  const user = c.get("user");
  const id = c.req.param("conversationId");
  if (!conversationIdSchema.safeParse(id).success) {
    return c.json({ detail: "Invalid conversation ID" }, 422);
  }
  const { rowCount } = await query("DELETE FROM conversations WHERE id = $1 AND user_id = $2", [
    id,
    user.id,
  ]);
  if (!rowCount) return c.json({ detail: "Conversation not found" }, 404);
  return c.json({ success: true, message: "Conversation deleted" });
});
