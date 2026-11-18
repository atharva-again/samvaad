import { withTransaction } from "./db.js";
import type { CitationSource, ConversationRow, StoredMessage } from "./types.js";
import { conversationTitleFromMessage, generateId } from "./utils.js";

export async function getOrCreateConversation(
  conversationId: string,
  userId: string,
): Promise<ConversationRow | null> {
  return withTransaction(async (client) => {
    await client.query(
      `INSERT INTO conversations (id, user_id)
			 VALUES ($1, $2)
			 ON CONFLICT (id) DO NOTHING`,
      [conversationId, userId],
    );
    const { rows } = await client.query<ConversationRow>(
      "SELECT * FROM conversations WHERE id = $1 AND user_id = $2",
      [conversationId, userId],
    );
    return rows[0] ?? null;
  });
}

export async function saveUserMessage(options: {
  conversationId: string;
  userId: string;
  userMessageId?: string | null;
  userMessage: string;
}): Promise<{ userMessageId: string; conversationTitle: string }> {
  const userMessageId = options.userMessageId ?? generateId();
  return withTransaction(async (client) => {
    const { rows: conversationRows } = await client.query<{ title: string | null }>(
      "SELECT title FROM conversations WHERE id = $1 AND user_id = $2 FOR UPDATE",
      [options.conversationId, options.userId],
    );
    if (!conversationRows[0]) {
      throw new Error("Conversation not found");
    }

    await client.query(
      `INSERT INTO messages (id, conversation_id, role, content, sources)
       VALUES ($1, $2, 'user', $3, '[]'::json)
       ON CONFLICT (id) DO NOTHING`,
      [userMessageId, options.conversationId, options.userMessage],
    );
    const { rows } = await client.query<StoredMessage>(
      "SELECT id, conversation_id, role, content, sources FROM messages WHERE id = $1",
      [userMessageId],
    );
    const persisted = rows[0];
    if (
      !persisted ||
      persisted.conversation_id !== options.conversationId ||
      persisted.role !== "user" ||
      persisted.content !== options.userMessage
    ) {
      throw new Error("User message ID conflicts with existing data");
    }

    const { rows: firstUserMessages } = await client.query<{ content: string }>(
      `SELECT content FROM messages
       WHERE conversation_id = $1
         AND role = 'user'
         AND btrim(regexp_replace(content, '[[:space:]]+', '', 'g')) <> ''
       ORDER BY created_at, id
       LIMIT 1`,
      [options.conversationId],
    );
    const titleCandidate = conversationTitleFromMessage(
      firstUserMessages[0]?.content ?? options.userMessage,
    );
    const { rows: updatedConversations } = await client.query<{ title: string | null }>(
      `UPDATE conversations
       SET title = CASE
         WHEN title IS NULL OR btrim(title) = '' OR title = 'New Conversation'
         THEN COALESCE($3, 'New Conversation')
         ELSE title
       END,
       updated_at = now()
       WHERE id = $1 AND user_id = $2
       RETURNING title`,
      [options.conversationId, options.userId, titleCandidate],
    );
    return {
      userMessageId,
      conversationTitle: updatedConversations[0]?.title ?? "New Conversation",
    };
  });
}

export async function saveAssistantMessage(options: {
  conversationId: string;
  userId: string;
  userMessageId: string;
  assistantMessageId?: string | null;
  assistantMessage: string;
  sources: CitationSource[];
}): Promise<{
  assistantMessageId: string;
  conversationTitle: string;
  userMessage: string;
  inserted: boolean;
}> {
  const assistantMessageId = options.assistantMessageId ?? generateId();
  return withTransaction(async (client) => {
    const { rows: conversationRows } = await client.query<{ title: string | null }>(
      "SELECT title FROM conversations WHERE id = $1 AND user_id = $2 FOR UPDATE",
      [options.conversationId, options.userId],
    );
    if (!conversationRows[0]) {
      throw new Error("Conversation not found");
    }

    const { rows: userRows } = await client.query<StoredMessage>(
      `SELECT id, conversation_id, role, content, sources
       FROM messages
       WHERE id = $1 AND conversation_id = $2 AND role = 'user'`,
      [options.userMessageId, options.conversationId],
    );
    const userMessage = userRows[0];
    if (!userMessage) {
      throw new Error("User message must be saved before its assistant response");
    }

    const insertResult = await client.query(
      `INSERT INTO messages (id, conversation_id, role, content, sources)
       VALUES ($1, $2, 'assistant', $3, $4::json)
       ON CONFLICT (id) DO NOTHING`,
      [
        assistantMessageId,
        options.conversationId,
        options.assistantMessage,
        JSON.stringify(options.sources),
      ],
    );
    const { rows } = await client.query<StoredMessage>(
      "SELECT id, conversation_id, role, content, sources FROM messages WHERE id = $1",
      [assistantMessageId],
    );
    const assistantRow = rows[0];
    if (
      !assistantRow ||
      assistantRow.conversation_id !== options.conversationId ||
      assistantRow.role !== "assistant" ||
      assistantRow.content !== options.assistantMessage ||
      JSON.stringify(assistantRow.sources ?? []) !== JSON.stringify(options.sources)
    ) {
      throw new Error("Assistant message ID conflicts with existing data");
    }

    const { rows: updatedConversations } = await client.query<{ title: string | null }>(
      `UPDATE conversations SET updated_at = now()
       WHERE id = $1 AND user_id = $2
       RETURNING title`,
      [options.conversationId, options.userId],
    );
    return {
      assistantMessageId,
      conversationTitle: updatedConversations[0]?.title ?? "New Conversation",
      userMessage: userMessage.content,
      inserted: (insertResult.rowCount ?? 0) > 0,
    };
  });
}
