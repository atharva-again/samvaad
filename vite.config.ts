import { defineConfig } from "vite-plus";

export default defineConfig({
  defaultPackage: "./packages/web",
  staged: {
    "*": "vp check --fix",
  },
  fmt: {},
  test: {
    include: ["packages/api/src/**/*.test.ts", "packages/voice-agent/src/**/*.test.ts"],
    environment: "node",
  },
  lint: {
    plugins: ["react"],
    jsPlugins: [{ name: "vite-plus", specifier: "vite-plus/oxlint-plugin" }],
    rules: {
      "vite-plus/prefer-vite-plus-imports": "error",
      "react/rules-of-hooks": "error",
      "react/exhaustive-deps": "warn",
    },
    options: { typeAware: true, typeCheck: true },
  },
});
