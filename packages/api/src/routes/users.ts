import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { requireAuth } from "../auth.js";
import { query } from "../db.js";
import type { ApiEnv } from "../types.js";

const walkthroughSchema = z.object({ has_seen: z.boolean() });
const userSettingsSchema = z.object({
  default_strict_mode: z.boolean(),
  default_persona: z.string().min(1).max(100),
});

export const usersRouter = new Hono<ApiEnv>({ strict: false });
usersRouter.use("*", requireAuth);

usersRouter.get("/me", async (c) => {
  const user = c.get("user");
  const { rows } = await query<{
    id: string;
    email: string;
    has_seen_walkthrough: boolean;
  }>("SELECT id, email, has_seen_walkthrough FROM users WHERE id = $1", [user.id]);
  const profile = rows[0];
  return c.json({
    id: user.id,
    email: profile?.email ?? user.email,
    has_seen_walkthrough: profile?.has_seen_walkthrough ?? false,
  });
});

usersRouter.post("/walkthrough", zValidator("json", walkthroughSchema), async (c) => {
  const { has_seen } = c.req.valid("json");
  const { rows } = await query<{ has_seen_walkthrough: boolean }>(
    `UPDATE users SET has_seen_walkthrough = $1
			 WHERE id = $2 RETURNING has_seen_walkthrough`,
    [has_seen, c.get("user").id],
  );
  if (!rows[0]) return c.json({ detail: "User not found" }, 404);
  return c.json({
    success: true,
    has_seen_walkthrough: rows[0].has_seen_walkthrough,
  });
});

usersRouter.get("/settings", async (c) => {
  const userId = c.get("user").id;
  const { rows } = await query<{
    default_strict_mode: boolean;
    default_persona: string;
  }>(
    `INSERT INTO user_settings (user_id)
		 VALUES ($1)
		 ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
		 RETURNING default_strict_mode, default_persona`,
    [userId],
  );
  return c.json(rows[0]);
});

usersRouter.put("/settings", zValidator("json", userSettingsSchema), async (c) => {
  const settings = c.req.valid("json");
  const { rows } = await query(
    `INSERT INTO user_settings (user_id, default_strict_mode, default_persona)
			 VALUES ($1, $2, $3)
			 ON CONFLICT (user_id) DO UPDATE
			   SET default_strict_mode = EXCLUDED.default_strict_mode,
			       default_persona = EXCLUDED.default_persona
			 RETURNING default_strict_mode, default_persona`,
    [c.get("user").id, settings.default_strict_mode, settings.default_persona],
  );
  return c.json(rows[0]);
});
