import { RoomAgentDispatch, RoomConfiguration } from "@livekit/protocol";
import { AccessToken } from "livekit-server-sdk";
import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { requireAuth } from "../auth.js";
import { query } from "../db.js";
import type { ApiEnv } from "../types.js";

const requestSchema = z.object({
  conversationId: z.string().uuid(),
  enableTts: z.boolean(),
  persona: z.string().min(1).max(100),
  strictMode: z.boolean(),
});

export const voiceTokenRouter = new Hono<ApiEnv>();
voiceTokenRouter.post(
  "/livekit/token",
  requireAuth,
  zValidator("json", requestSchema),
  async (c) => {
    const user = c.get("user");
    const { conversationId, enableTts, persona, strictMode } = c.req.valid("json");
    const livekitUrl = process.env.LIVEKIT_URL;
    const livekitApiKey = process.env.LIVEKIT_API_KEY;
    const livekitApiSecret = process.env.LIVEKIT_API_SECRET;
    const agentName = process.env.LIVEKIT_AGENT_NAME ?? "samvaad-voice";

    if (!livekitUrl || !livekitApiKey || !livekitApiSecret) {
      return c.json({ error: "LiveKit is not configured on the server" }, 503);
    }

    const { rows } = await query<{ id: string }>(
      "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
      [conversationId, user.id],
    );
    if (!rows[0]) {
      return c.json({ error: "Conversation not found" }, 404);
    }

    const roomName = `samvaad-${crypto.randomUUID()}`;
    const dispatchMetadata = JSON.stringify({
      user_id: user.id,
      conversation_id: conversationId,
      persona,
      strict_mode: strictMode,
      enable_tts: enableTts,
    });
    const token = new AccessToken(livekitApiKey, livekitApiSecret, {
      identity: `samvaad-${user.id}`,
      name: user.name || "Samvaad learner",
      ttl: "1h",
    });
    token.addGrant({
      roomJoin: true,
      room: roomName,
      canPublish: true,
      canSubscribe: true,
      canPublishData: false,
    });
    token.roomConfig = new RoomConfiguration({
      agents: [
        new RoomAgentDispatch({
          agentName,
          metadata: dispatchMetadata,
        }),
      ],
    });

    return c.json({
      serverUrl: livekitUrl,
      participantToken: await token.toJwt(),
      roomName,
    });
  },
);
