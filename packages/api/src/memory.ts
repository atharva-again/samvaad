import Groq from "groq-sdk";
import { query } from "./db.js";
import type { StoredMessage } from "./types.js";
import { buildSlidingWindow, formatMessagesForPrompt } from "./prompts.js";

const WINDOW_SIZE = Number(process.env.HISTORY_WINDOW_SIZE ?? 6);
const SUMMARIZATION_BATCH_SIZE = 4;
const GROQ_MEMORY_MODEL = process.env.GROQ_MEMORY_MODEL ?? "openai/gpt-oss-20b";
let groqClient: Groq | undefined;

function getGroqClient(): Groq | null {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) return null;
  groqClient ??= new Groq({ apiKey, maxRetries: 2 });
  return groqClient;
}

export const HISTORY_REFERENCE_PATTERNS = [
  /\b(earlier|before|previously|last time|remember when)\b/i,
  /\b(we discussed|we talked about|you (said|mentioned|told me))\b/i,
  /\b(as you (said|mentioned)|like you (said|mentioned))\b/i,
  /\b(go back to|back to the|referring to)\b/i,
];

export const SYNTHESIS_PATTERNS = [
  /\b(compare|contrast|difference between|similarities)\b/i,
  /\b(summarize|summary|recap|overview)\b/i,
  /\b(all the|everything we|list all)\b/i,
  /\b(how does .+ relate to)\b/i,
];

export const AMBIGUOUS_REFERENCE_PATTERNS = [
  /\btell me more about (it|that|this|him|her|them)\b/i,
  /\bwhat about (it|that|this)\b/i,
  /\bexplain (it|that|this) further\b/i,
];

export function detectQueryComplexity(queryText: string) {
  const patterns = [
    ["history_ref", HISTORY_REFERENCE_PATTERNS],
    ["synthesis", SYNTHESIS_PATTERNS],
    ["ambiguous_ref", AMBIGUOUS_REFERENCE_PATTERNS],
  ] as const;
  const signals: string[] = [];
  const matches = patterns.map(([name, regexes]) => {
    const matched = regexes.find((regex) => regex.test(queryText));
    if (matched) signals.push(`${name}: ${matched.source}`);
    return Boolean(matched);
  });
  const score = matches.filter(Boolean).length;
  return {
    needs_history: matches[0],
    needs_synthesis: matches[1],
    has_ambiguous_refs: matches[2],
    signals,
    recommendation:
      score === 0 ? "baseline" : score === 1 ? "may_need_tools" : "likely_needs_tools",
  };
}

const SUMMARIZATION_PROMPT = `Summarize this conversation by grouping turns into topic ranges.

Previous summary:
{existing_summary}

New messages (turns {start_turn}-{end_turn}):
{new_messages}

Format your summary as:
- Start with: "Started with: [first topic]"
- Group turns: "Turns X-Y: [topic summary]"
- End with: "Currently: [what user is working on]"

Example:
"Started with: VPC networking basics.
Turns 1-4: Explained CIDR blocks and subnet design.
Turns 5-8: Deep dive into NAT Gateway vs NAT Instance.
Currently: User implementing private subnet routing."

Keep under 150 words. Preserve any user preferences mentioned.

Updated summary:`;

const FACT_EXTRACTION_PROMPT = `You manage a list of facts about the user and conversation.

Current facts:
{existing_facts}

New exchange:
User: {user_message}
Assistant: {assistant_message}

Instructions:
1. Extract ALL new facts from this exchange (preferences, progress, decisions, entities).
2. Merge with existing facts to create a COMPREHENSIVE list. Do not drop valid facts.
3. Resolve conflicts with recency bias: when a new fact conflicts with an old one, use the new fact.
4. Keep the list concise (max 20 facts, about 300 words total). Discard least important facts if needed.
5. Strictly deduplicate.

Output the COMPLETE updated facts list as a JSON array of strings. If no changes are needed,
return existing facts as-is.`;

async function summarize(
  existingSummary: string,
  messages: StoredMessage[],
  startTurn: number,
  endTurn: number,
): Promise<string> {
  const client = getGroqClient();
  if (!client) {
    return `${existingSummary}\n${formatMessagesForPrompt(messages)}`.trim().slice(0, 500);
  }
  try {
    const result = await client.chat.completions.create({
      model: GROQ_MEMORY_MODEL,
      messages: [
        {
          role: "user",
          content: SUMMARIZATION_PROMPT.replace(
            "{existing_summary}",
            existingSummary || "No previous summary.",
          )
            .replace("{start_turn}", String(startTurn))
            .replace("{end_turn}", String(endTurn))
            .replace("{new_messages}", formatMessagesForPrompt(messages)),
        },
      ],
      temperature: 0.3,
      max_tokens: 150,
    });
    return result.choices[0]?.message?.content?.trim() || existingSummary;
  } catch (error) {
    console.error("[memory] Summarization failed", error);
    return existingSummary;
  }
}

function parseFacts(content: string): string[] {
  const fenced = content.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const source = fenced?.[1] ?? content;
  const start = source.indexOf("[");
  const end = source.lastIndexOf("]");
  if (start < 0 || end <= start) return [];
  try {
    const value: unknown = JSON.parse(source.slice(start, end + 1));
    return Array.isArray(value)
      ? value
          .map((fact) =>
            typeof fact === "string"
              ? fact.trim()
              : typeof fact === "object" &&
                  fact !== null &&
                  "fact" in fact &&
                  typeof fact.fact === "string"
                ? fact.fact.trim()
                : "",
          )
          .filter(Boolean)
          .slice(0, 20)
      : [];
  } catch {
    return [];
  }
}

async function extractFacts(
  userMessage: string,
  assistantMessage: string,
  existingFacts: string,
): Promise<string | null> {
  const client = getGroqClient();
  if (!client) return null;
  try {
    const result = await client.chat.completions.create({
      model: GROQ_MEMORY_MODEL,
      messages: [
        {
          role: "user",
          content: FACT_EXTRACTION_PROMPT.replace("{existing_facts}", existingFacts || "None yet.")
            .replace("{user_message}", userMessage)
            .replace("{assistant_message}", assistantMessage),
        },
      ],
      temperature: 0.2,
      max_tokens: 200,
    });
    const content = result.choices[0]?.message?.content;
    if (!content) return null;
    return parseFacts(content).join(". ") || null;
  } catch (error) {
    console.error("[memory] Fact extraction failed", error);
    return null;
  }
}

export async function runPostResponseTasks(options: {
  conversationId: string;
  userId: string;
  userMessage: string;
  assistantResponse: string;
}): Promise<void> {
  const { conversationId, userId, userMessage, assistantResponse } = options;
  try {
    const { rows: conversationRows } = await query<{
      summary: string | null;
      facts: string | null;
    }>("SELECT summary, facts FROM conversations WHERE id = $1 AND user_id = $2", [
      conversationId,
      userId,
    ]);
    const conversation = conversationRows[0];
    if (!conversation) return;

    const factPromise = extractFacts(userMessage, assistantResponse, conversation.facts ?? "").then(
      async (facts) => {
        if (facts) {
          await query("UPDATE conversations SET facts = $1 WHERE id = $2 AND user_id = $3", [
            facts,
            conversationId,
            userId,
          ]);
        }
      },
    );

    const { rows: messages } = await query<StoredMessage>(
      `SELECT id, conversation_id, role, content, sources, created_at
			 FROM messages WHERE conversation_id = $1 ORDER BY created_at`,
      [conversationId],
    );
    const [recentMessages] = buildSlidingWindow(messages, WINDOW_SIZE);
    const exitedCount = messages.length - recentMessages.length;
    let summaryPromise: Promise<void> = Promise.resolve();
    if (exitedCount >= SUMMARIZATION_BATCH_SIZE && exitedCount % SUMMARIZATION_BATCH_SIZE < 2) {
      const batchStart = Math.max(0, exitedCount - SUMMARIZATION_BATCH_SIZE);
      const exitingBatch = messages.slice(batchStart, exitedCount);
      if (exitingBatch.length > 0) {
        summaryPromise = summarize(
          conversation.summary ?? "",
          exitingBatch,
          batchStart + 1,
          exitedCount,
        ).then(async (summary) => {
          if (summary) {
            await query("UPDATE conversations SET summary = $1 WHERE id = $2 AND user_id = $3", [
              summary,
              conversationId,
              userId,
            ]);
          }
        });
      }
    }
    await Promise.allSettled([factPromise, summaryPromise]);
  } catch (error) {
    console.error("[memory] Post-response tasks failed", error);
  }
}
