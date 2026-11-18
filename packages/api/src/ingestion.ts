import LlamaCloud from "@llamaindex/llama-cloud";
import { query, withTransaction } from "./db.js";
import { embedTexts } from "./rag.js";
import { generateId, sha256 } from "./utils.js";

export interface DocumentChunk {
  content: string;
  metadata: {
    page_number: number;
    heading: string | null;
    breadcrumbs: string[];
    content_type: string;
  };
}

interface ParsedItem {
  type?: string;
  md?: string;
  value?: string | number | null;
  level?: number;
  lvl?: number;
}

interface ParsedPage {
  page?: number;
  page_number?: number;
  items?: ParsedItem[];
}

function metadataFor(
  page: number,
  breadcrumbs: string[],
  contentType: string,
): DocumentChunk["metadata"] {
  return {
    page_number: page,
    heading: breadcrumbs.at(-1) ?? null,
    breadcrumbs: [...breadcrumbs],
    content_type: contentType,
  };
}

function splitContent(
  text: string,
  limit: number,
  overlap: number,
  separators: string[],
): string[] {
  const input = text.trim();
  if (input.length <= limit) return input ? [input] : [];
  const separator = separators.find((candidate) => candidate && input.includes(candidate));
  if (!separator) {
    const chunks: string[] = [];
    const step = Math.max(1, limit - overlap);
    for (let start = 0; start < input.length; start += step) {
      chunks.push(input.slice(start, start + limit).trim());
    }
    return chunks.filter(Boolean);
  }

  const parts = input.split(separator);
  const output: string[] = [];
  let current = "";
  for (const part of parts) {
    const candidate = current ? `${current}${separator}${part}` : part;
    if (candidate.length <= limit || !current) {
      if (candidate.length <= limit) {
        current = candidate;
        continue;
      }
      output.push(
        ...splitContent(part, limit, overlap, separators.slice(separators.indexOf(separator) + 1)),
      );
      current = "";
      continue;
    }
    output.push(current.trim());
    const overlapText = current.slice(-overlap);
    current = overlapText ? `${overlapText}${separator}${part}` : part;
    if (current.length > limit) {
      output.push(
        ...splitContent(
          current,
          limit,
          overlap,
          separators.slice(separators.indexOf(separator) + 1),
        ),
      );
      current = "";
    }
  }
  if (current.trim()) output.push(current.trim());
  return output;
}

export function structuralChunk(
  pages: ParsedPage[],
  options: { limit?: number; overlap?: number } = {},
): DocumentChunk[] {
  const limit = options.limit ?? 1200;
  const overlap = options.overlap ?? 80;
  const chunks: DocumentChunk[] = [];
  const headingStack: Array<{ level: number; text: string }> = [];
  let pending: string[] = [];
  let pendingPage = 1;
  let pendingType = "text";

  const flush = () => {
    const text = pending.join("\n\n").trim();
    if (text) {
      for (const content of splitContent(text, limit, overlap, ["\n\n", "\n", ". ", " ", ""])) {
        chunks.push({
          content,
          metadata: metadataFor(
            pendingPage,
            headingStack.map((heading) => heading.text),
            pendingType,
          ),
        });
      }
    }
    pending = [];
  };

  for (const page of pages) {
    const pageNumber = page.page_number ?? page.page ?? 1;
    for (const item of page.items ?? []) {
      const type = item.type ?? "text";
      const content = String(item.md || item.value || "");
      if (!content.trim()) continue;

      if (pending.length === 0) pendingPage = pageNumber;
      if (type === "heading") {
        flush();
        const level = item.level ?? item.lvl ?? 1;
        while (headingStack.length && headingStack.at(-1)!.level >= level) {
          headingStack.pop();
        }
        const heading = String(item.value ?? content)
          .replace(/^#+\s*/, "")
          .trim();
        headingStack.push({ level, text: heading });
        pending = [`${"#".repeat(Math.min(level, 6))} ${heading}`];
        pendingType = "text";
        pendingPage = pageNumber;
        continue;
      }
      if (type === "table") {
        flush();
        const breadcrumbs = headingStack.map((heading) => heading.text);
        for (const text of splitContent(content, limit, overlap, ["\n\n", "\n", "  ", ""])) {
          chunks.push({
            content: text,
            metadata: metadataFor(pageNumber, breadcrumbs, "table"),
          });
        }
        continue;
      }
      pending.push(content);
      pendingType = "text";
      if (pending.join("\n\n").length > limit) flush();
    }
  }
  flush();
  return chunks;
}

function parseSimpleText(filename: string, contents: Buffer): ParsedPage[] | null {
  const extension = filename.toLowerCase().split(".").at(-1);
  if (!extension || !["csv", "json", "xml", "yaml", "yml"].includes(extension)) {
    return null;
  }
  const text = new TextDecoder("utf-8", { fatal: true }).decode(contents);
  return [{ page: 1, items: [{ type: "text", value: text, md: text }] }];
}

let llamaCloud: LlamaCloud | undefined;
function getLlamaCloud(): LlamaCloud {
  if (llamaCloud) return llamaCloud;
  const apiKey = process.env.LLAMA_CLOUD_API_KEY;
  if (!apiKey) throw new Error("LLAMA_CLOUD_API_KEY is required");
  llamaCloud = new LlamaCloud({ apiKey, timeout: 60_000, maxRetries: 2 });
  return llamaCloud;
}

async function parseDocument(
  filename: string,
  contentType: string | undefined,
  contents: Buffer,
): Promise<ParsedPage[]> {
  const directPages = parseSimpleText(filename, contents);
  if (directPages) return directPages;

  const file = new File([new Uint8Array(contents)], filename, {
    type: contentType || "application/octet-stream",
  });
  const parsed = await getLlamaCloud().parsing.parse(
    {
      tier: "cost_effective",
      version: "latest",
      upload_file: file,
      expand: ["items"],
      processing_options: { ocr_parameters: { languages: ["en"] } },
    },
    { timeout: 15 * 60_000 },
  );
  const pages = parsed.items?.pages ?? [];
  return pages
    .filter((page) => page.success)
    .map((page) => ({
      page: page.page_number,
      items: page.items.map((item) => ({
        type: item.type,
        md: item.md,
        value: "value" in item ? item.value : item.md,
        level: "level" in item ? item.level : undefined,
      })),
    }));
}

export async function ingestDocument(options: {
  filename: string;
  contentType?: string;
  contents: Buffer;
  userId: string;
}): Promise<Record<string, unknown>> {
  const filename = options.filename;
  const { contentType, contents, userId } = options;
  const fileHash = sha256(contents);
  const { rows: existingFiles } = await query<{ hash: string }>(
    "SELECT hash FROM global_files WHERE hash = $1",
    [fileHash],
  );
  if (existingFiles.length > 0) {
    const fileId = generateId();
    await query(
      `INSERT INTO files (id, user_id, filename, content_hash)
			 VALUES ($1, $2, $3, $4)`,
      [fileId, userId, filename, fileHash],
    );
    return {
      file_id: fileId,
      filename,
      content_type: contentType ?? null,
      size_bytes: contents.length,
      num_chunks: 0,
      new_chunks_embedded: 0,
      chunk_preview: [],
      error: null,
      status: "linked",
    };
  }

  let pages: ParsedPage[];
  try {
    pages = await parseDocument(filename, contentType, contents);
  } catch (error) {
    if (
      ["csv", "json", "xml", "yaml", "yml"].includes(filename.toLowerCase().split(".").at(-1) ?? "")
    ) {
      return {
        filename,
        content_type: contentType ?? null,
        size_bytes: contents.length,
        num_chunks: 0,
        new_chunks_embedded: 0,
        chunk_preview: [],
        error: error instanceof Error ? error.message : "Unable to parse file",
      };
    }
    const fallback = contents.toString("utf8").replace(/\uFFFD/g, "");
    pages = [{ page: 1, items: [{ type: "text", md: fallback }] }];
  }

  const chunks = structuralChunk(pages);
  if (chunks.length === 0) {
    return {
      filename,
      content_type: contentType ?? null,
      size_bytes: contents.length,
      num_chunks: 0,
      new_chunks_embedded: 0,
      chunk_preview: [],
      error: "No text extracted",
    };
  }

  const hashes = chunks.map((chunk) => sha256(chunk.content));
  const { rows: existingChunks } = await query<{ hash: string }>(
    "SELECT hash FROM global_chunks WHERE hash = ANY($1::text[])",
    [hashes],
  );
  const existingHashes = new Set(existingChunks.map((row) => row.hash));
  const chunksToEmbed = chunks.filter((_, index) => !existingHashes.has(hashes[index]!));
  const embeddings = await embedTexts(
    chunksToEmbed.map((chunk) => chunk.content),
    "document",
  );
  const embeddingByHash = new Map<string, number[]>();
  let embeddingIndex = 0;
  for (let index = 0; index < chunks.length; index += 1) {
    const hash = hashes[index]!;
    if (!existingHashes.has(hash)) {
      const embedding = embeddings[embeddingIndex++];
      if (embedding) embeddingByHash.set(hash, embedding);
    }
  }

  const fileId = generateId();
  await withTransaction(async (client) => {
    await client.query(
      "INSERT INTO global_files (hash, size) VALUES ($1, $2) ON CONFLICT (hash) DO NOTHING",
      [fileHash, contents.length],
    );
    for (const [hash, embedding] of embeddingByHash) {
      const chunk = chunks[hashes.indexOf(hash)]!;
      await client.query(
        `INSERT INTO global_chunks (hash, content, embedding)
				 VALUES ($1, $2, $3::vector)
				 ON CONFLICT (hash) DO NOTHING`,
        [hash, chunk.content, `[${embedding.join(",")}]`],
      );
    }
    for (let index = 0; index < chunks.length; index += 1) {
      await client.query(
        `INSERT INTO global_file_chunks
				   (global_file_hash, chunk_hash, chunk_index, chunk_metadata)
				 VALUES ($1, $2, $3, $4::json)
				 ON CONFLICT (global_file_hash, chunk_hash) DO NOTHING`,
        [fileHash, hashes[index], index, JSON.stringify(chunks[index]!.metadata)],
      );
    }
    await client.query(
      `INSERT INTO files (id, user_id, filename, content_hash)
			 VALUES ($1, $2, $3, $4)`,
      [fileId, userId, filename.split(/[\\/]/).at(-1) ?? filename, fileHash],
    );
  });

  return {
    file_id: fileId,
    filename,
    content_type: contentType ?? null,
    size_bytes: contents.length,
    num_chunks: chunks.length,
    new_chunks_embedded: embeddingByHash.size,
    chunk_preview: chunks.slice(0, 3).map((chunk) => chunk.content),
    error: null,
  };
}
