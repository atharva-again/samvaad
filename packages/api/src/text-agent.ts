import Groq from "groq-sdk";
import { buildSystemPrompt, formatMessagesForPrompt } from "./prompts.js";
import { citationSources, ragQuery } from "./rag.js";
import type { CitationSource, StoredMessage } from "./types.js";
import { formatRagContext } from "./utils.js";

const GROQ_CHAT_MODEL = process.env.GROQ_CHAT_MODEL ?? "openai/gpt-oss-120b";

const FETCH_CONTEXT_TOOL = {
  type: "function" as const,
  function: {
    name: "fetch_context",
    description:
      "Search the knowledge base for information. Use when the user asks about uploaded documents or needs their specific information. Call only once per question.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "The search query - use key terms or topic",
        },
      },
      required: ["query"],
    },
  },
};

let groqClient: Groq | undefined;
function getGroqClient(): Groq {
  if (groqClient) return groqClient;
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) throw new Error("GROQ_API_KEY is required");
  groqClient = new Groq({ apiKey, maxRetries: 2 });
  return groqClient;
}

async function executeRag(
  queryText: string,
  userId: string,
  fileIds?: string[] | null,
): Promise<{ context: string; sources: CitationSource[] }> {
  let timeout: ReturnType<typeof setTimeout> | undefined;
  try {
    const result = await Promise.race([
      ragQuery(queryText, { userId, fileIds, topK: 3 }),
      new Promise<never>(
        (_, reject) =>
          (timeout = setTimeout(() => reject(new Error("RAG search timed out")), 10_000)),
      ),
    ]);
    const chunks = result.chunks;
    return { context: formatRagContext(chunks), sources: citationSources(chunks) };
  } catch (error) {
    console.error("[text-agent] RAG failed", error);
    return {
      context:
        error instanceof Error && error.message.includes("timed out")
          ? "Search timed out. Please try again."
          : "An error occurred while searching.",
      sources: [],
    };
  } finally {
    if (timeout) clearTimeout(timeout);
  }
}

export async function textAgentRespond(options: {
  query: string;
  userId: string;
  messages: StoredMessage[];
  persona?: string;
  strictMode?: boolean;
  summary?: string | null;
  facts?: string | null;
  fileIds?: string[] | null;
}): Promise<{ response: string; sources: CitationSource[]; usedTool: boolean }> {
  const recentMessages = options.messages.slice(-6);
  const systemPrompt = buildSystemPrompt({
    persona: options.persona,
    strictMode: options.strictMode,
    mode: "text",
    history: formatMessagesForPrompt(recentMessages),
    summary: options.summary,
    facts: options.facts,
  });

  const messages: Groq.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: systemPrompt },
    ...recentMessages.map((message) => ({
      role: message.role === "user" ? ("user" as const) : ("assistant" as const),
      content: message.content,
    })),
    { role: "user", content: options.query },
  ];

  const completion = await getGroqClient().chat.completions.create({
    model: GROQ_CHAT_MODEL,
    messages,
    tools: [FETCH_CONTEXT_TOOL],
    tool_choice: "auto",
    temperature: 0.3,
    max_tokens: 1024,
  });

  const assistantMessage = completion.choices[0]?.message;
  const toolCall = assistantMessage?.tool_calls?.[0];
  if (!assistantMessage || !toolCall || toolCall.function.name !== "fetch_context") {
    return {
      response: assistantMessage?.content ?? "",
      sources: [],
      usedTool: false,
    };
  }

  let toolArgs: { query?: string };
  try {
    toolArgs = JSON.parse(toolCall.function.arguments) as { query?: string };
  } catch {
    toolArgs = {};
  }
  const ragResult = await executeRag(
    toolArgs.query?.trim() || options.query,
    options.userId,
    options.fileIds,
  );

  const finalMessages: Groq.Chat.ChatCompletionMessageParam[] = [
    ...messages,
    {
      role: "assistant",
      content: assistantMessage.content,
      tool_calls: [
        {
          id: toolCall.id,
          type: "function",
          function: {
            name: toolCall.function.name,
            arguments: toolCall.function.arguments,
          },
        },
      ],
    },
    {
      role: "tool",
      tool_call_id: toolCall.id,
      content: ragResult.context,
    },
  ];
  const finalCompletion = await getGroqClient().chat.completions.create({
    model: GROQ_CHAT_MODEL,
    messages: finalMessages,
    temperature: 0.3,
    max_tokens: 1024,
  });

  return {
    response: finalCompletion.choices[0]?.message?.content ?? "",
    sources: ragResult.sources,
    usedTool: true,
  };
}
