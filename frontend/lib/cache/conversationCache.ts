import { db, CachedConversation, CachedMessage } from './db';
import Dexie from 'dexie';

const MAX_CACHED_CONVERSATIONS = 50;

export interface CachedConversationWithMessages {
    conversation: CachedConversation;
    messages: CachedMessage[];
}

export const conversationCache = {
    /**
     * Get cached conversation with all its messages [SECURITY-FIX #01]
     */
    async get(id: string, userId: string): Promise<CachedConversationWithMessages | null> {
        // [SECURITY-FIX #01] Use composite key query or filter
        const conversation = await db.conversations.get({ userId, id });
        if (!conversation) return null;

        const messages = await db.messages
            .where('[userId+id]') // Leveraging new index if possible, or just filter
            .between([userId, Dexie.minKey], [userId, Dexie.maxKey])
            .and(m => m.conversationId === id) // Dexie compound index limitations might require manual filter or simpler query
            // Simpler approach with compound index '[userId+conversationId+...]' would be better but requires schema change
            // For now, let's filter by userId AND conversationId
            // Actually, best query for messages: index conversationId? No, that leaks.
            // We need an index on [userId+conversationId].
            // Current index is [userId+id], userId, conversationId.
            // We can query by userId then filter conversationId
            .sortBy('createdAt');

        // Correct query using userId index:
        const userMessages = messages.filter(m => m.conversationId === id && m.userId === userId);

        return { conversation, messages: userMessages };
    },

    /**
     * Get just the conversation metadata (for checking if cache exists)
     */
    async getMeta(id: string): Promise<CachedConversation | null> {
        return await db.conversations.get(id) ?? null;
    },

    /**
     * Get all cached conversations (for sidebar list) [SECURITY-FIX #01]
     */
    async getAll(userId: string): Promise<CachedConversation[]> {
        // [SECURITY-FIX #01] Only get conversations for this user
        const conversations = await db.conversations
            .where('userId')
            .equals(userId)
            .toArray();

        const validConversations = conversations.filter(c => c.title !== 'New conversation');
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
        if (!conversation.userId) {
            console.error('Cannot save conversation without userId');
            return;
        }

        await db.transaction('rw', [db.conversations, db.messages], async () => {
            await db.conversations.put({
                ...conversation,
                cachedAt: now
            });

            if (messages.length > 0) {
                // Ensure messages have userId
                const cleanMessages = messages.map(m => ({
                    ...m,
                    userId: conversation.userId
                }));
                await db.messages.bulkPut(cleanMessages);
            }
        });

        await this.evictOld(conversation.userId);
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
        if (!message.userId) {
            console.error('Cannot save message without userId');
            return;
        }

        await db.transaction('rw', [db.conversations, db.messages], async () => {
            // [SECURITY-FIX #01] Use composite key
            const existing = await db.conversations.get({ userId: message.userId, id: conversationId });

            if (!existing) {
                await db.conversations.put({
                    id: conversationId,
                    userId: message.userId, // Explicit set
                    title: 'New conversation',
                    isPinned: false,
                    createdAt: now,
                    updatedAt: now,
                    cachedAt: '1970-01-01T00:00:00.000Z'
                });
            } else {
                // Compound ID update needs full object put or careful key usage
                // db.update with composite key is tricky, easier to use known key tuple or just put
                await db.conversations.put({
                    ...existing,
                    updatedAt: now
                });
            }

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
     * [RESILIENCE-FIX] Trim conversation to a max number of messages
     * Prevents single conversations from growing infinitely in IndexedDB
     */
    async trimMessages(conversationId: string, maxMessages: number = 1000): Promise<void> {
        const count = await db.messages.where('conversationId').equals(conversationId).count();
        if (count <= maxMessages) return;

        const toDelete = count - maxMessages;
        // Delete oldest messages first
        const oldestKey = await db.messages
            .where('conversationId')
            .equals(conversationId)
            .limit(toDelete)
            .primaryKeys();

        if (oldestKey.length > 0) {
            console.log(`[Cache] Trimming ${oldestKey.length} old messages from ${conversationId}`);
            await db.messages.bulkDelete(oldestKey);
        }
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
    async evictOld(userId: string): Promise<void> {
        // [SECURITY-FIX #01] Evict only for this user
        const count = await db.conversations.where('userId').equals(userId).count();

        if (count > MAX_CACHED_CONVERSATIONS) {
            const toEvict = count - MAX_CACHED_CONVERSATIONS;

            const oldest = await db.conversations
                .where('userId')
                .equals(userId)
                .sortBy('cachedAt'); // sortBy returns array already

            // oldest is array of conversations
            const limited = oldest.slice(0, toEvict);

            const idsToDelete = limited.map(c => c.id);

            await db.transaction('rw', [db.conversations, db.messages], async () => {
                // Cannot bulkDelete with just ID if composite key used? 
                // Actually with [userId+id], we need to delete by key tuple or bulkDelete keys
                const keysToDelete = idsToDelete.map(id => [userId, id]); // Valid for composite keys
                await db.conversations.bulkDelete(keysToDelete);

                // For messages, same issue. Need to find them first.
                // We'll trust the userId filter on messages
                const msgsToDelete = await db.messages.where('conversationId').anyOf(idsToDelete).filter(m => m.userId === userId).toArray();
                const msgKeys = msgsToDelete.map(m => [m.userId, m.id]);
                await db.messages.bulkDelete(msgKeys);
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
