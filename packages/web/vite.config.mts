import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, lazyPlugins } from "vite-plus";

const webRoot = fileURLToPath(new URL(".", import.meta.url));
const workspaceRoot = fileURLToPath(new URL("../..", import.meta.url));

export default defineConfig({
  envDir: workspaceRoot,
  plugins: lazyPlugins(() => [
    react({
      compiler: true,
    }),
  ]),
  resolve: {
    alias: {
      "@": resolve(webRoot),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5177,
    strictPort: true,
    allowedHosts: ["fedora.tail1acf57.ts.net"],
    proxy: {
      "/api": "http://127.0.0.1:18765",
      "/text-mode": "http://127.0.0.1:18765",
      "/ingest": "http://127.0.0.1:18765",
      "/tts": "http://127.0.0.1:18765",
      "/livekit": "http://127.0.0.1:18765",
      "/conversations": "http://127.0.0.1:18765",
      "/files": "http://127.0.0.1:18765",
      "/users": "http://127.0.0.1:18765",
      "/health": "http://127.0.0.1:18765",
    },
  },
});
