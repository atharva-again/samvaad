import Dexie, { Table } from 'dexie';

// Cached message structure - mirrors server's Message model
export interface CachedMessage {
    id: string;
    userId: string; // [SECURITY-FIX #01] Added for isolation
    conversationId: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    sources?: Record<string, unknown>[];
    createdAt: string;
}

// Cached conversation metadata
export interface CachedConversation {
    id: string;
    userId: string; // [SECURITY-FIX #01] Added for isolation
    title: string;
    summary?: string;
    mode?: 'text' | 'voice';  // Chat mode
    isPinned: boolean;
    createdAt: string;
    updatedAt: string;
    cachedAt: string;  // When we last synced with server
}

// Cached file/source metadata
export interface CachedFile {
    id: string;
    userId: string; // [SECURITY-FIX #01] Added for isolation
    filename: string;
    fileType: string;
    sizeBytes: number;
    contentHash?: string;  // For deduplication
    createdAt: string;
    cachedAt: string;  // When we last synced with server
}

// Cache metadata for tracking last sync
export interface CacheMeta {
    key: string;  // e.g., 'files_last_sync', 'conversations_last_sync'
    value: string;
}

class SamvaadDB extends Dexie {
    conversations!: Table<CachedConversation>;
    messages!: Table<CachedMessage>;
    files!: Table<CachedFile>;
    cacheMeta!: Table<CacheMeta>;

    constructor() {
        super('samvaad-cache');

        // Version 1: conversations + messages
        this.version(1).stores({
            conversations: 'id, updatedAt, cachedAt',
            messages: 'id, conversationId, createdAt'
        });

        // Version 2: Add files table for sources caching
        this.version(2).stores({
            conversations: 'id, updatedAt, cachedAt',
            messages: 'id, conversationId, createdAt',
            files: 'id, filename, contentHash, cachedAt',
            cacheMeta: 'key'
        });

        // [SECURITY-FIX #01] Version 3: Drop old tables to allow PK change
        // Dexie doesn't support changing PKs in-place, so we must drop and recreate.
        this.version(3).stores({
            conversations: null,
            messages: null,
            files: null
        });

        // Version 4: Recreate with User Isolation (Compound Keys)
        this.version(4).stores({
            conversations: '[userId+id], userId, updatedAt, cachedAt',
            messages: '[userId+id], userId, conversationId, createdAt',
            files: '[userId+id], userId, filename, contentHash, cachedAt',
            cacheMeta: 'key'
        });
    }
}

export const db = new SamvaadDB();
