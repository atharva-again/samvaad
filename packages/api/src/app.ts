import { cors } from "hono/cors";
import { compress } from "hono/compress";
import { Hono } from "hono";
import { auth } from "./auth.js";
import { conversationsRouter } from "./routes/conversations.js";
import { filesRouter } from "./routes/files.js";
import { ingestRouter } from "./routes/ingest.js";
import { textRouter } from "./routes/text.js";
import { ttsRouter } from "./routes/tts.js";
import { usersRouter } from "./routes/users.js";
import { voiceInternalRouter } from "./routes/voice-internal.js";
import { voiceTokenRouter } from "./routes/voice-token.js";
import type { ApiEnv } from "./types.js";

const DEFAULT_HOSTS = ["localhost", "127.0.0.1", "samvaad.live", "www.samvaad.live"];
const allowedHosts = new Set([
  ...DEFAULT_HOSTS,
  ...(process.env.ALLOWED_HOSTS ?? "")
    .split(",")
    .map((host) =>
      host
        .trim()
        .replace(/^["']|["']$/g, "")
        .toLowerCase(),
    )
    .filter(Boolean),
]);

const corsOrigins = new Set(["http://localhost:5177", "http://127.0.0.1:5177"]);
const frontendUrl = (process.env.FRONTEND_URL ?? "").trim().replace(/\/+$/, "");
if (frontendUrl) {
  corsOrigins.add(frontendUrl);
  if (frontendUrl.includes("www.samvaad.live")) {
    corsOrigins.add(frontendUrl.replace("www.", ""));
  } else if (frontendUrl.includes("samvaad.live") && !frontendUrl.includes("www.")) {
    corsOrigins.add(frontendUrl.replace("://", "://www."));
  }
}

export const app = new Hono<ApiEnv>();

// CORS is registered first so it can answer preflight requests before host checks.
app.use(
  "*",
  cors({
    origin: (origin) => (corsOrigins.has(origin) ? origin : ""),
    allowMethods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization"],
    credentials: true,
    maxAge: 600,
  }),
);

app.use("*", async (c, next) => {
  await next();
  c.header("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  c.header("X-Content-Type-Options", "nosniff");
  c.header("X-Frame-Options", "DENY");
  c.header("Referrer-Policy", "strict-origin-when-cross-origin");
});

app.use("*", async (c, next) => {
  if (c.req.path === "/health" || c.req.method === "OPTIONS") {
    await next();
    return;
  }
  const host = (c.req.header("host") ?? "").split(":")[0]?.toLowerCase();
  if (host && !allowedHosts.has("*") && !allowedHosts.has(host)) {
    console.warn(`[security] Rejected untrusted host: ${host}`);
    return c.json({ detail: "Invalid host header" }, 400);
  }
  await next();
});

app.use("*", compress());

app.get("/health", (c) => c.json({ status: "ok" }));

app.all("/api/auth/*", (c) => auth.handler(c.req.raw));
app.route("/internal/voice", voiceInternalRouter);
app.route("/", textRouter);
app.route("/", ingestRouter);
app.route("/", ttsRouter);
app.route("/", voiceTokenRouter);
app.route("/conversations", conversationsRouter);
app.route("/files", filesRouter);
app.route("/users", usersRouter);

app.notFound((c) => c.json({ detail: "Not found" }, 404));
app.onError((error, c) => {
  console.error("[api] Unhandled request error", error);
  return c.json({ detail: "An internal server error occurred." }, 500);
});
