import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { requireAuth } from "../auth.js";
import { query, withTransaction } from "../db.js";
import type { ApiEnv } from "../types.js";

const batchSchema = z.object({ file_ids: z.array(z.string().min(1)) });
const renameSchema = z.object({ filename: z.string().min(1).max(255) });

export const filesRouter = new Hono<ApiEnv>({ strict: false });
filesRouter.use("*", requireAuth);

filesRouter.get("/", async (c) => {
  const user = c.get("user");
  const { rows } = await query(
    `SELECT f.id, f.filename, f.created_at, gf.size AS size_bytes,
		        gf.hash AS content_hash
		 FROM files f
		 JOIN global_files gf ON f.content_hash = gf.hash
		 WHERE f.user_id = $1
		 ORDER BY f.created_at DESC`,
    [user.id],
  );
  return c.json(rows);
});

async function removeFile(fileId: string, userId: string): Promise<boolean> {
  return withTransaction(async (client) => {
    const { rows } = await client.query<{ content_hash: string }>(
      "SELECT content_hash FROM files WHERE id = $1 AND user_id = $2 FOR UPDATE",
      [fileId, userId],
    );
    const file = rows[0];
    if (!file) return false;
    await client.query("DELETE FROM files WHERE id = $1 AND user_id = $2", [fileId, userId]);
    const { rows: refs } = await client.query<{ count: string }>(
      "SELECT count(*)::text AS count FROM files WHERE content_hash = $1",
      [file.content_hash],
    );
    if (Number(refs[0]?.count ?? 0) === 0) {
      const { rows: chunks } = await client.query<{ chunk_hash: string }>(
        "SELECT chunk_hash FROM global_file_chunks WHERE global_file_hash = $1",
        [file.content_hash],
      );
      await client.query("DELETE FROM global_files WHERE hash = $1", [file.content_hash]);
      if (chunks.length > 0) {
        await client.query(
          `DELETE FROM global_chunks gc
					 WHERE gc.hash = ANY($1::text[])
					   AND NOT EXISTS (
					     SELECT 1 FROM global_file_chunks gfc
					     WHERE gfc.chunk_hash = gc.hash
					   )`,
          [chunks.map((row) => row.chunk_hash)],
        );
      }
    }
    return true;
  });
}

filesRouter.delete("/batch", zValidator("json", batchSchema), async (c) => {
  const user = c.get("user");
  const { file_ids: ids } = c.req.valid("json");
  const deleted: string[] = [];
  const failed: string[] = [];
  for (const id of ids) {
    try {
      if (await removeFile(id, user.id)) deleted.push(id);
      else failed.push(id);
    } catch (error) {
      console.error(`[files] Failed to delete ${id}`, error);
      failed.push(id);
    }
  }
  return c.json({
    success: true,
    deleted_count: deleted.length,
    deleted,
    failed,
  });
});

filesRouter.delete("/:fileId", async (c) => {
  const deleted = await removeFile(c.req.param("fileId"), c.get("user").id);
  return c.json({
    success: true,
    message: deleted ? "File deleted" : "File already deleted or not found",
  });
});

filesRouter.patch("/:fileId", zValidator("json", renameSchema), async (c) => {
  const { filename } = c.req.valid("json");
  const { rows } = await query(
    `UPDATE files SET filename = $1
			 WHERE id = $2 AND user_id = $3
			 RETURNING id, filename, created_at, content_hash`,
    [filename, c.req.param("fileId"), c.get("user").id],
  );
  if (!rows[0]) return c.json({ detail: "File not found" }, 404);
  return c.json({ success: true, file: rows[0] });
});
