CREATE EXTENSION IF NOT EXISTS vector;
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS users (
    id text PRIMARY KEY,
    email text NOT NULL UNIQUE,
    has_seen_walkthrough boolean DEFAULT false,
    created_at timestamptz DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS user_settings (
    user_id text PRIMARY KEY REFERENCES users(id),
    default_strict_mode boolean NOT NULL DEFAULT false,
    default_persona text NOT NULL DEFAULT 'default'
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS global_chunks (
    hash text PRIMARY KEY,
    content text NOT NULL,
    embedding vector(1024),
    created_at timestamptz DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS global_files (
    hash text PRIMARY KEY,
    size bigint,
    created_at timestamptz DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS global_file_chunks (
    global_file_hash text NOT NULL REFERENCES global_files(hash) ON DELETE CASCADE,
    chunk_hash text NOT NULL REFERENCES global_chunks(hash) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    chunk_metadata json,
    PRIMARY KEY (global_file_hash, chunk_hash)
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS files (
    id text PRIMARY KEY,
    user_id text NOT NULL REFERENCES users(id),
    filename text NOT NULL,
    content_hash text NOT NULL REFERENCES global_files(hash),
    created_at timestamptz DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL REFERENCES users(id),
    title text DEFAULT 'New Conversation',
    summary text,
    facts text,
    is_pinned boolean DEFAULT false,
    active_strict_mode boolean,
    active_persona text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role text NOT NULL,
    content text NOT NULL,
    sources json DEFAULT '[]'::json,
    token_count integer,
    created_at timestamptz DEFAULT now()
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_files_user_id ON files(user_id);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages(conversation_id);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_global_chunks_hash ON global_chunks(hash);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_global_files_hash ON global_files(hash);
--> statement-breakpoint
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS name text,
    ADD COLUMN IF NOT EXISTS email_verified boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS image text,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz;
--> statement-breakpoint
UPDATE users
SET name = COALESCE(name, ''),
    has_seen_walkthrough = COALESCE(has_seen_walkthrough, false),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, created_at, now());
--> statement-breakpoint
ALTER TABLE users
    ALTER COLUMN name SET DEFAULT '',
    ALTER COLUMN name SET NOT NULL,
    ALTER COLUMN has_seen_walkthrough SET DEFAULT false,
    ALTER COLUMN has_seen_walkthrough SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL;
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS auth_sessions (
    id text PRIMARY KEY,
    expires_at timestamptz NOT NULL,
    token text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    ip_address text,
    user_agent text,
    user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS auth_accounts (
    id text PRIMARY KEY,
    account_id text NOT NULL,
    provider_id text NOT NULL,
    user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_token text,
    refresh_token text,
    id_token text,
    access_token_expires_at timestamptz,
    refresh_token_expires_at timestamptz,
    scope text,
    password text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS auth_verifications (
    id text PRIMARY KEY,
    identifier text NOT NULL,
    value text NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id ON auth_sessions(user_id);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_auth_accounts_user_id ON auth_accounts(user_id);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS ix_auth_verifications_identifier ON auth_verifications(identifier);
