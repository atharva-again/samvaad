import "dotenv/config";
import { serve } from "@hono/node-server";
import { assertDatabaseUrl } from "./db.js";
import { app } from "./app.js";
import { closePool } from "./db.js";

assertDatabaseUrl();
const port = Number(process.env.PORT ?? process.env.API_PORT ?? 18765);
const server = serve(
  {
    fetch: app.fetch,
    port,
    hostname: process.env.HOST ?? process.env.API_HOST ?? "127.0.0.1",
  },
  (info) => {
    console.info(`[api] Hono listening on http://${info.address}:${info.port}`);
  },
);

async function shutdown() {
  server.close(async () => {
    await closePool();
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
