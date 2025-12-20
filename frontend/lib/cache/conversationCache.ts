import { db, CachedConversation, CachedMessage } from './db';

const MAX_CACHED_CONVERSATIONS = 50;

export interface CachedConversationWithMessages {
    conversation: CachedConversation;
    messages: CachedMessage[];
}

export const conversationCache = {
    /**
     * Get cached conversation with all its messages
     */
    async get(id: string): Promise<CachedConversationWithMessages | null> {
        const conversation = await db.conversations.get(id);
        if (!conversation) return null;

        const messages = await db.messages
            .where('conversationId')
            .equals(id)
            .sortBy('createdAt');

        return { conversation, messages };
    },

    /**
     * Get just the conversation metadata (for checking if cache exists)
     */
    async getMeta(id: string): Promise<CachedConversation | null> {
        return await db.conversations.get(id) ?? null;
    },

    /**
     * Get all cached conversations (for sidebar list)
     * Returns sorted by updatedAt descending
     * Filters out placeholder entries (created by saveMessage before backend sync)
     */
    async getAll(): Promise<CachedConversation[]> {
        const conversations = await db.conversations.toArray();
        // Filter out placeholder conversations that haven't been synced yet
        const validConversations = conversations.filter(c => c.title !== 'New conversation');
        // Sort: Pinned first, then by updatedAt descending
        return validConversations.sort((a, b) => {
            if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1;
            return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
        });
    },

    /**
     * Get all conversations regardless of status
     */
    async getAllRaw(): Promise<CachedConversation[]> {
        return await db.conversations.toArray();
    },

    /**
     * Save a full conversation with all messages to cache
     */
    async save(
        conversation: Omit<CachedConversation, 'cachedAt'>,
        messages: CachedMessage[]
    ): Promise<void> {
        const now = new Date().toISOString();

        await db.transaction('rw', [db.conversations, db.messages], async () => {
            // Save conversation with cache timestamp
            await db.conversations.put({
                ...conversation,
                cachedAt: now
            });

            // Bulk insert messages for efficiency
            if (messages.length > 0) {
                await db.messages.bulkPut(messages);
            }
        });

        // Evict old conversations if over limit
        await this.evictOld();
    },

    /**
     * Append new messages to an existing cached conversation (delta sync)
     */
    async appendMessages(conversationId: string, newMessages: CachedMessage[]): Promise<void> {
        if (newMessages.length === 0) return;

        const now = new Date().toISOString();

        await db.transaction('rw', [db.conversations, db.messages], async () => {
            // Bulk insert new messages
            await db.messages.bulkPut(newMessages);

            // Update the cachedAt timestamp
            await db.conversations.update(conversationId, {
                cachedAt: now
            });
        });
    },

    /**
     * Save a single message (write-through cache for real-time updates)
     * Creates conversation cache entry if it doesn't exist
     */
    async saveMessage(conversationId: string, message: CachedMessage): Promise<void> {
        const now = new Date().toISOString();

        await db.transaction('rw', [db.conversations, db.messages], async () => {
            // Ensure conversation exists in cache
            const existing = await db.conversations.get(conversationId);
            if (!existing) {
                // Create minimal conversation entry - will be enriched on next full load
                await db.conversations.put({
                    id: conversationId,
                    title: 'New conversation',
                    isPinned: false,
                    createdAt: now,
                    updatedAt: now,
                    cachedAt: '1970-01-01T00:00:00.000Z' // Never synced from server
                });
            } else {
                // Update updatedAt but NOT cachedAt. 
                // cachedAt should only be bumped by server-sync to avoid skipping messages from other devices.
                await db.conversations.update(conversationId, {
                    updatedAt: now
                });
            }

            // Save the message
            await db.messages.put(message);
        });
    },

    /**
     * Update a message in cache (e.g., replace temp ID with real ID)
     */
    async updateMessage(messageId: string, updates: Partial<CachedMessage>): Promise<void> {
        await db.messages.update(messageId, updates);
    },

    /**
     * Delete a message from cache (for replacing temp messages)
     */
    async deleteMessage(messageId: string): Promise<void> {
        await db.messages.delete(messageId);
    },

    /**
     * Update or create conversation metadata (upsert)
     * Used to sync sidebar list with cache
     */
    async upsertConversation(conversation: Omit<CachedConversation, 'cachedAt'>): Promise<void> {
        const now = new Date().toISOString();
        await db.conversations.put({
            ...conversation,
            cachedAt: now
        });
    },

    /**
     * Update conversation metadata (e.g., after rename)
     * Only updates if exists
     */
    async updateConversation(id: string, updates: Partial<CachedConversation>): Promise<void> {
        await db.conversations.update(id, updates);
    },

    /**
     * Remove multiple conversations from cache
     */
    async deleteMultiple(ids: string[]): Promise<void> {
        if (ids.length === 0) return;
        await db.transaction('rw', [db.conversations, db.messages], async () => {
            await db.conversations.bulkDelete(ids);
            await db.messages.where('conversationId').anyOf(ids).delete();
        });
    },

    /**
     * Rename a conversation ID in the cache (for replacing temp UUIDs with real IDs)
     */
    async migrateId(tempId: string, realId: string): Promise<void> {
        await db.transaction('rw', [db.conversations, db.messages], async () => {
            const conversation = await db.conversations.get(tempId);
            if (conversation) {
                // 1. Create new entry with real ID
                await db.conversations.put({
                    ...conversation,
                    id: realId
                });
                // 2. Delete old entry
                await db.conversations.delete(tempId);
            }

            // 3. Update all messages
            const messages = await db.messages.where('conversationId').equals(tempId).toArray();
            if (messages.length > 0) {
                const updatedMessages = messages.map(m => ({ ...m, conversationId: realId }));
                await db.messages.bulkPut(updatedMessages);
                await db.messages.where('conversationId').equals(tempId).delete();
            }
        });
    },

    /**
     * Truncate messages in a conversation from a given index (for edit functionality)
     * Removes all messages at and after the specified index
     */
    async truncateMessages(conversationId: string, keepMessageIds: string[]): Promise<void> {
        await db.transaction('rw', [db.conversations, db.messages], async () => {
            // Get all messages for this conversation
            const allMessages = await db.messages
                .where('conversationId')
                .equals(conversationId)
                .toArray();

            // Find messages to delete (those NOT in keepMessageIds)
            const idsToDelete = allMessages
                .filter(m => !keepMessageIds.includes(m.id))
                .map(m => m.id);

            if (idsToDelete.length > 0) {
                await db.messages.bulkDelete(idsToDelete);

                // Update cachedAt so delta sync pulls fresh data
                await db.conversations.update(conversationId, {
                    cachedAt: new Date().toISOString()
                });
            }
        });
    },

    /**
     * Delete a specific conversation from cache
     */
    async delete(id: string): Promise<void> {
        await db.transaction('rw', [db.conversations, db.messages], async () => {
            await db.conversations.delete(id);
            await db.messages.where('conversationId').equals(id).delete();
        });
    },

    /**
     * Clear all cached data (for logout)
     */
    async clear(): Promise<void> {
        await db.transaction('rw', [db.conversations, db.messages], async () => {
            await db.conversations.clear();
            await db.messages.clear();
        });
    },

    /**
     * LRU eviction - remove oldest cached conversations when over limit
     */
    async evictOld(): Promise<void> {
        const count = await db.conversations.count();

        if (count > MAX_CACHED_CONVERSATIONS) {
            const toEvict = count - MAX_CACHED_CONVERSATIONS;

            // Get oldest by cachedAt
            const oldest = await db.conversations
                .orderBy('cachedAt')
                .limit(toEvict)
                .toArray();

            const idsToDelete = oldest.map(c => c.id);

            await db.transaction('rw', [db.conversations, db.messages], async () => {
                await db.conversations.bulkDelete(idsToDelete);
                // Delete all messages for evicted conversations
                await db.messages
                    .where('conversationId')
                    .anyOf(idsToDelete)
                    .delete();
            });
        }
    },

    /**
     * Get cache stats (for debugging)
     */
    async getStats(): Promise<{ conversations: number; messages: number }> {
        return {
            conversations: await db.conversations.count(),
            messages: await db.messages.count()
        };
    }
};
