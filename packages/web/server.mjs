import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("./dist", import.meta.url)));
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

const server = createServer(async (request, response) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { Allow: "GET, HEAD" }).end();
    return;
  }

  let pathname;
  try {
    pathname = decodeURIComponent(new URL(request.url ?? "/", "http://localhost").pathname);
  } catch {
    response.writeHead(400).end("Bad Request");
    return;
  }

  const requestedFile = resolve(join(root, `.${pathname}`));
  if (requestedFile !== root && !requestedFile.startsWith(`${root}${sep}`)) {
    response.writeHead(403).end("Forbidden");
    return;
  }

  try {
    const filePath = await resolveFile(requestedFile, request.headers.accept);
    const body = await readFile(filePath);
    response.writeHead(200, {
      "Content-Type": contentTypes[extname(filePath)] ?? "application/octet-stream",
      "Cache-Control": filePath.endsWith("index.html")
        ? "no-cache"
        : "public, max-age=31536000, immutable",
      "X-Content-Type-Options": "nosniff",
    });
    response.end(request.method === "HEAD" ? undefined : body);
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Not Found");
  }
});

async function resolveFile(requestedFile, accept = "") {
  try {
    const info = await stat(requestedFile);
    if (info.isFile()) return requestedFile;
    if (info.isDirectory()) return join(requestedFile, "index.html");
  } catch {
    // Client-side routes are served by the app shell below.
  }

  if (!extname(requestedFile) || accept.includes("text/html")) {
    return join(root, "index.html");
  }
  throw new Error("Not found");
}

const port = Number(process.env.PORT ?? 15177);
server.listen(port, "0.0.0.0", () => {
  console.log(`Samvaad web listening on http://0.0.0.0:${port}`);
});

function shutdown() {
  server.close((error) => process.exit(error ? 1 : 0));
  setTimeout(() => process.exit(1), 5000).unref();
}

process.once("SIGTERM", shutdown);
process.once("SIGINT", shutdown);
