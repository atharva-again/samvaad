import { drizzleAdapter } from "@better-auth/drizzle-adapter";
import { betterAuth } from "better-auth";
import { authAccounts, authSessions, authVerifications, db, users } from "@samvaad/db";
import { createMiddleware } from "hono/factory";
import type { ApiEnv, AuthUser } from "./types.js";

const authSecret =
  process.env.BETTER_AUTH_SECRET ??
  (process.env.NODE_ENV === "production"
    ? undefined
    : "local-development-only-secret-replace-before-deploy-32-characters");

if (!authSecret) {
  throw new Error("BETTER_AUTH_SECRET is required in production");
}

const authBaseUrl =
  process.env.BETTER_AUTH_URL ??
  (process.env.NODE_ENV === "production" ? undefined : "http://localhost:5177");
if (!authBaseUrl) {
  throw new Error("BETTER_AUTH_URL is required in production");
}

const googleClientId = process.env.GOOGLE_CLIENT_ID;
const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET;
const frontendUrl =
  process.env.FRONTEND_URL ??
  (process.env.NODE_ENV === "production" ? undefined : "http://localhost:5177");
if (!frontendUrl) {
  throw new Error("FRONTEND_URL is required in production");
}
if (process.env.NODE_ENV === "production" && (!googleClientId || !googleClientSecret)) {
  throw new Error("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required in production");
}

const frontendOrigin = frontendUrl.replace(/\/+$/, "");
const trustedOrigins = ["http://localhost:5177", "http://127.0.0.1:5177", frontendOrigin];

export const auth = betterAuth({
  appName: "Samvaad",
  baseURL: authBaseUrl,
  basePath: "/api/auth",
  secret: authSecret,
  trustedOrigins: [...new Set(trustedOrigins)],
  database: drizzleAdapter(db, {
    provider: "pg",
    schema: {
      user: users,
      session: authSessions,
      account: authAccounts,
      verification: authVerifications,
    },
  }),
  user: {
    additionalFields: {
      hasSeenWalkthrough: {
        type: "boolean",
        required: false,
        input: false,
        defaultValue: false,
      },
    },
  },
  socialProviders:
    googleClientId && googleClientSecret
      ? {
          google: {
            clientId: googleClientId,
            clientSecret: googleClientSecret,
          },
        }
      : {},
  ...(process.env.AUTH_COOKIE_DOMAIN
    ? {
        advanced: {
          crossSubDomainCookies: {
            enabled: true,
            domain: process.env.AUTH_COOKIE_DOMAIN,
          },
        },
      }
    : {}),
});

export const requireAuth = createMiddleware<ApiEnv>(async (c, next) => {
  let session: Awaited<ReturnType<typeof auth.api.getSession>>;
  try {
    session = await auth.api.getSession({ headers: c.req.raw.headers });
  } catch (error) {
    console.error("[auth] Better Auth session lookup failed", error);
    return c.json({ detail: "Authentication service unavailable" }, 503);
  }

  if (!session) {
    return c.json({ detail: "Not authenticated" }, 401);
  }

  const user: AuthUser = {
    id: session.user.id,
    email: session.user.email,
    name: session.user.name,
    image: session.user.image ?? null,
  };
  c.set("user", user);
  await next();
});
