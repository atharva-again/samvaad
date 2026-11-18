import {
  bigint,
  boolean,
  customType,
  index,
  integer,
  json,
  pgTable,
  primaryKey,
  text,
  timestamp,
  uuid,
} from "drizzle-orm/pg-core";

const vector1024 = customType<{ data: number[]; driverData: string }>({
  dataType: () => "vector(1024)",
  toDriver: (value) => `[${value.join(",")}]`,
  fromDriver: (value) =>
    value
      .slice(1, -1)
      .split(",")
      .map((part) => Number(part)),
});

export const users = pgTable("users", {
  id: text("id").primaryKey(),
  name: text("name").notNull().default(""),
  email: text("email").notNull().unique(),
  emailVerified: boolean("email_verified").notNull().default(false),
  image: text("image"),
  hasSeenWalkthrough: boolean("has_seen_walkthrough").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const authSessions = pgTable(
  "auth_sessions",
  {
    id: text("id").primaryKey(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    token: text("token").notNull().unique(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
    ipAddress: text("ip_address"),
    userAgent: text("user_agent"),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
  },
  (table) => [index("ix_auth_sessions_user_id").on(table.userId)],
);

export const authAccounts = pgTable(
  "auth_accounts",
  {
    id: text("id").primaryKey(),
    accountId: text("account_id").notNull(),
    providerId: text("provider_id").notNull(),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    accessToken: text("access_token"),
    refreshToken: text("refresh_token"),
    idToken: text("id_token"),
    accessTokenExpiresAt: timestamp("access_token_expires_at", {
      withTimezone: true,
    }),
    refreshTokenExpiresAt: timestamp("refresh_token_expires_at", {
      withTimezone: true,
    }),
    scope: text("scope"),
    password: text("password"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index("ix_auth_accounts_user_id").on(table.userId)],
);

export const authVerifications = pgTable(
  "auth_verifications",
  {
    id: text("id").primaryKey(),
    identifier: text("identifier").notNull(),
    value: text("value").notNull(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index("ix_auth_verifications_identifier").on(table.identifier)],
);

export const userSettings = pgTable("user_settings", {
  userId: text("user_id")
    .primaryKey()
    .references(() => users.id, { onDelete: "cascade" }),
  defaultStrictMode: boolean("default_strict_mode").notNull().default(false),
  defaultPersona: text("default_persona").notNull().default("default"),
});

export const globalChunks = pgTable(
  "global_chunks",
  {
    hash: text("hash").primaryKey(),
    content: text("content").notNull(),
    embedding: vector1024("embedding"),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (table) => [index("ix_global_chunks_hash").on(table.hash)],
);

export const globalFiles = pgTable(
  "global_files",
  {
    hash: text("hash").primaryKey(),
    size: bigint("size", { mode: "number" }),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (table) => [index("ix_global_files_hash").on(table.hash)],
);

export const globalFileChunks = pgTable(
  "global_file_chunks",
  {
    globalFileHash: text("global_file_hash")
      .notNull()
      .references(() => globalFiles.hash, { onDelete: "cascade" }),
    chunkHash: text("chunk_hash")
      .notNull()
      .references(() => globalChunks.hash, { onDelete: "cascade" }),
    chunkIndex: integer("chunk_index").notNull(),
    chunkMetadata: json("chunk_metadata"),
  },
  (table) => [
    primaryKey({
      name: "global_file_chunks_pkey",
      columns: [table.globalFileHash, table.chunkHash],
    }),
  ],
);

export const files = pgTable(
  "files",
  {
    id: text("id").primaryKey(),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    filename: text("filename").notNull(),
    contentHash: text("content_hash")
      .notNull()
      .references(() => globalFiles.hash),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (table) => [index("ix_files_user_id").on(table.userId)],
);

export const conversations = pgTable(
  "conversations",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    title: text("title").default("New Conversation"),
    summary: text("summary"),
    facts: text("facts"),
    isPinned: boolean("is_pinned").default(false),
    activeStrictMode: boolean("active_strict_mode"),
    activePersona: text("active_persona"),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  },
  (table) => [index("ix_conversations_user_id").on(table.userId)],
);

export const messages = pgTable(
  "messages",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    conversationId: uuid("conversation_id")
      .notNull()
      .references(() => conversations.id, { onDelete: "cascade" }),
    role: text("role").notNull(),
    content: text("content").notNull(),
    sources: json("sources").default([]),
    tokenCount: integer("token_count"),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (table) => [index("ix_messages_conversation_id").on(table.conversationId)],
);
