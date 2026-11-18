import { query } from "./db.js";
import type { CitationSource, RagChunk } from "./types.js";

const VOYAGE_BASE_URL = "https://api.voyageai.com/v1";
const VOYAGE_EMBEDDING_MODEL = process.env.VOYAGE_EMBEDDING_MODEL ?? "voyage-4-large";
const VOYAGE_RERANK_MODEL = process.env.VOYAGE_RERANK_MODEL ?? "rerank-3";
const VOYAGE_EMBEDDING_DIMENSIONS = 1024;

function getVoyageKey(): string {
  const key = process.env.VOYAGE_API_KEY;
  if (!key) throw new Error("VOYAGE_API_KEY is required");
  return key;
}

export function scrubPii(value: string): string {
  return value
    .replace(/[\w.-]+@[\w.-]+\.\w+/g, "[EMAIL_REDACTED]")
    .replace(/\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g, "[PHONE_REDACTED]")
    .replace(/\b\d{3}-\d{2}-\d{4}\b/g, "[SSN_REDACTED]")
    .replace(/\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g, "[CARD_REDACTED]");
}

async function voyageRequest<T>(path: string, body: unknown): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt < 6; attempt += 1) {
    try {
      const response = await fetch(`${VOYAGE_BASE_URL}${path}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getVoyageKey()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(60_000),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Voyage ${path} failed (${response.status}): ${detail.slice(0, 500)}`);
      }
      return (await response.json()) as T;
    } catch (error) {
      lastError = error;
      if (attempt < 5) {
        const ceiling = Math.min(60_000, 1_000 * 2 ** attempt);
        await new Promise((resolve) => setTimeout(resolve, Math.random() * ceiling));
      }
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Voyage request failed");
}

export async function embedTexts(
  texts: string[],
  inputType: "document" | "query" = "document",
): Promise<number[][]> {
  if (texts.length === 0) return [];
  const response = await voyageRequest<{ data: Array<{ embedding: number[] }> }>("/embeddings", {
    input: inputType === "document" ? texts.map(scrubPii) : texts,
    model: VOYAGE_EMBEDDING_MODEL,
    input_type: inputType,
    output_dimension: VOYAGE_EMBEDDING_DIMENSIONS,
  });
  return response.data.map(({ embedding }) => {
    if (embedding.length !== VOYAGE_EMBEDDING_DIMENSIONS) {
      throw new Error(
        `Voyage returned ${embedding.length} embedding dimensions; expected ${VOYAGE_EMBEDDING_DIMENSIONS}`,
      );
    }
    return embedding;
  });
}

export async function embedQuery(text: string): Promise<number[]> {
  const [embedding] = await embedTexts([text], "query");
  if (!embedding) throw new Error("Voyage returned no query embedding");
  return embedding;
}

export async function rerankDocuments(
  queryText: string,
  documents: string[],
): Promise<Array<{ index: number; relevance_score: number }>> {
  if (documents.length === 0) return [];
  const response = await voyageRequest<{
    data: Array<{ index: number; relevance_score: number }>;
  }>("/rerank", {
    query: queryText,
    documents,
    model: VOYAGE_RERANK_MODEL,
  });
  return response.data;
}

export async function searchSimilarChunks(
  queryEmbedding: number[],
  queryText: string,
  options: { userId: string; fileIds?: string[] | null; topK?: number },
): Promise<RagChunk[]> {
  const vector = `[${queryEmbedding.join(",")}]`;
  const { rows } = await query<{
    hash: string;
    content: string;
    filename: string;
    file_id: string;
    chunk_metadata: Record<string, unknown> | null;
    distance: number;
  }>(
    `SELECT gc.hash,
		        gc.content,
		        f.filename,
		        f.id AS file_id,
		        gfc.chunk_metadata,
		        gc.embedding <=> $1::vector AS distance
		 FROM global_chunks AS gc
		 JOIN global_file_chunks AS gfc ON gc.hash = gfc.chunk_hash
		 JOIN global_files AS gf ON gfc.global_file_hash = gf.hash
		 JOIN files AS f ON f.content_hash = gf.hash
		 WHERE f.user_id = $2
		   AND ($3::text[] IS NULL OR f.id = ANY($3::text[]))
		 ORDER BY gc.embedding <=> $1::vector
		 LIMIT 6`,
    [vector, options.userId, options.fileIds?.length ? options.fileIds : null],
  );

  const chunks: RagChunk[] = rows.map((row) => ({
    content: row.content,
    metadata: {
      filename: row.filename,
      file_id: row.file_id,
      extra: row.chunk_metadata ?? {},
    },
    distance: Number(row.distance),
    filename: row.filename || "unknown",
    chunk_id: row.hash,
  }));
  if (chunks.length === 0) return [];

  const ranked = await rerankDocuments(
    queryText,
    chunks.map((chunk) => chunk.content),
  );
  const reranked: RagChunk[] = [];
  for (const item of ranked) {
    const chunk = chunks[item.index];
    if (chunk) reranked.push({ ...chunk, rerank_score: item.relevance_score });
  }
  return reranked
    .sort((left, right) => (right.rerank_score ?? 0) - (left.rerank_score ?? 0))
    .slice(0, options.topK ?? 3);
}

export async function ragQuery(
  queryText: string,
  options: { userId: string; fileIds?: string[] | null; topK?: number },
): Promise<{ query: string; chunks: RagChunk[]; success: boolean }> {
  try {
    const queryEmbedding = await embedQuery(queryText);
    const chunks = await searchSimilarChunks(queryEmbedding, queryText, options);
    console.info(`[RAG] Query finished; returned ${chunks.length} chunks`);
    return { query: queryText, chunks, success: true };
  } catch (error) {
    console.error("[RAG] Query failed", error);
    return { query: queryText, chunks: [], success: false };
  }
}

export function citationSources(chunks: RagChunk[]): CitationSource[] {
  return chunks.slice(0, 3).map((chunk) => ({
    filename: chunk.filename || "document",
    content_preview: chunk.content.slice(0, 1000),
    rerank_score: chunk.rerank_score,
    chunk_id: chunk.chunk_id,
    metadata: chunk.metadata,
  }));
}
