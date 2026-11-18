FROM node:22-bookworm-slim AS build

WORKDIR /workspace
RUN corepack enable && corepack prepare pnpm@12.21.0 --activate

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/api/package.json packages/api/package.json
COPY packages/web/package.json packages/web/package.json
COPY packages/voice-agent/package.json packages/voice-agent/package.json
COPY packages/db/package.json packages/db/package.json
COPY packages/voice-protocol/package.json packages/voice-protocol/package.json
RUN pnpm install --filter @samvaad/api... --frozen-lockfile

COPY packages/api ./packages/api
COPY packages/db ./packages/db
RUN pnpm --filter @samvaad/db build \
	&& pnpm --filter @samvaad/api build \
	&& pnpm --filter @samvaad/api deploy --prod /prod/api

FROM node:22-bookworm-slim AS runtime

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=18765
ENV HOST=0.0.0.0

COPY --from=build /prod/api ./

EXPOSE 18765

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
	CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||18765)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "dist/src/index.js"]
