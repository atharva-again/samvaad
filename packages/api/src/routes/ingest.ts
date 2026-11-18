import { Hono } from "hono";
import { bodyLimit } from "hono/body-limit";
import { requireAuth } from "../auth.js";
import { ingestDocument } from "../ingestion.js";
import { createFixedWindowRateLimiter } from "../rate-limit.js";
import type { ApiEnv } from "../types.js";

const MAX_FILE_SIZE = 25 * 1024 * 1024;
const MAX_MULTIPART_SIZE = MAX_FILE_SIZE + 1024 * 1024;
const ingestRateLimit = createFixedWindowRateLimiter({
  limit: 20,
  windowMs: 60_000,
  maxBuckets: 10_000,
});

export const ingestRouter = new Hono<ApiEnv>();
ingestRouter.post(
  "/ingest",
  bodyLimit({ maxSize: MAX_MULTIPART_SIZE }),
  requireAuth,
  async (c, next) => {
    if (!ingestRateLimit(c.get("user").id)) {
      return c.json({ detail: "Rate limit exceeded" }, 429);
    }
    await next();
  },
  async (c) => {
    const declaredLength = Number(c.req.header("content-length") ?? 0);
    if (declaredLength > MAX_MULTIPART_SIZE) {
      return c.json({ detail: "File too large. Maximum size is 25MB." }, 413);
    }
    let body: Record<string, unknown>;
    try {
      body = await c.req.parseBody();
    } catch {
      return c.json({ detail: "Invalid multipart upload" }, 400);
    }
    const file = body.file;
    if (!(file instanceof File)) {
      return c.json({ detail: "A file field is required" }, 422);
    }
    if (file.size > MAX_FILE_SIZE) {
      return c.json({ detail: "File too large. Maximum size is 25MB." }, 413);
    }
    const contents = Buffer.from(await file.arrayBuffer());
    const result = await ingestDocument({
      filename: file.name || "upload",
      contentType: file.type || undefined,
      contents,
      userId: c.get("user").id,
    });
    return c.json(result);
  },
);
