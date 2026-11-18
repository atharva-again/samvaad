export interface AuthUser {
  id: string;
  email: string;
  name: string;
  image: string | null;
}

export type ApiEnv = {
  Variables: {
    user: AuthUser;
  };
};

export interface StoredMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources: CitationSource[];
  created_at: string;
}

export interface CitationSource {
  filename: string;
  content_preview: string;
  rerank_score?: number;
  chunk_id?: string;
  metadata?: Record<string, unknown>;
}

export interface ConversationRow {
  id: string;
  user_id: string;
  title: string;
  summary: string | null;
  facts: string | null;
  is_pinned: boolean;
  active_strict_mode: boolean | null;
  active_persona: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface RagChunk {
  content: string;
  metadata: Record<string, unknown>;
  distance: number;
  filename: string;
  chunk_id: string;
  rerank_score?: number;
}
