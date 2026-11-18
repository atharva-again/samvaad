import { describe, expect, it } from "vite-plus/test";
import { app } from "./app.js";

describe("Hono API shell", () => {
  it("exposes an unauthenticated health endpoint", async () => {
    const response = await app.request("/health");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
  });

  it("requires a Better Auth session for private routes", async () => {
    const response = await app.request("/conversations/");
    expect(response.status).toBe(401);
  });

  it("mounts Better Auth's session endpoint", async () => {
    const response = await app.request("/api/auth/get-session");
    expect(response.status).toBe(200);
  });

  it("keeps the LiveKit bridge behind its shared secret", async () => {
    const previousSecret = process.env.VOICE_AGENT_SHARED_SECRET;
    delete process.env.VOICE_AGENT_SHARED_SECRET;
    try {
      const response = await app.request("/internal/voice/context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      expect(response.status).toBe(503);
    } finally {
      if (previousSecret) process.env.VOICE_AGENT_SHARED_SECRET = previousSecret;
    }
  });
});
