import { createHash } from "node:crypto";
import { uuidv7 } from "uuidv7";

export function sha256(value: string | Uint8Array): string {
  return createHash("sha256").update(value).digest("hex");
}

export function generateId(): string {
  return uuidv7();
}

export function conversationTitleFromMessage(message: string): string | null {
  const normalized = message.trim().replace(/\s+/gu, " ");
  if (!normalized) return null;

  const characters = Array.from(normalized);
  return characters.length > 50 ? `${characters.slice(0, 50).join("")}...` : normalized;
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

export function formatRagContext(
  chunks: Array<{ content: string }>,
  maxContentLength = 500,
): string {
  if (chunks.length === 0) {
    return "No relevant information found in the knowledge base.";
  }
  return chunks
    .slice(0, 3)
    .map(
      (chunk, index) =>
        `<document id="${index + 1}">\n${escapeXml(chunk.content.slice(0, maxContentLength))}\n</document>`,
    )
    .join("\n\n");
}

export function stripMarkdown(input: string): string {
  if (!input) return input;
  return input
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/^#+\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/_([^_]+)_/g, "$1")
    .replace(/~~([^~]+)~~/g, "$1")
    .replace(/!\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^>\s+/gm, "")
    .replace(/^[-*+]\s+/gm, "")
    .replace(/^[-*_]{3,}$/gm, "")
    .replace(/[ \t]+/g, " ")
    .replace(/\n\s*\n/g, "\n\n")
    .trim();
}
