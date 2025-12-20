import { db, CachedFile } from './db';

export const filesCache = {
    /**
     * Get all cached files
     */
    async getAll(): Promise<CachedFile[]> {
        return await db.files.toArray();
    },

    /**
     * Get a single cached file by ID
     */
    async get(id: string): Promise<CachedFile | null> {
        return await db.files.get(id) ?? null;
    },

    /**
     * Save multiple files to cache (for full sync)
     */
    async saveAll(files: CachedFile[]): Promise<void> {
        const now = new Date().toISOString();

        await db.transaction('rw', [db.files, db.cacheMeta], async () => {
            // Clear existing and replace with fresh data
            await db.files.clear();

            // Add cachedAt to all files
            const filesWithCachedAt = files.map(f => ({
                ...f,
                cachedAt: now
            }));

            if (filesWithCachedAt.length > 0) {
                await db.files.bulkPut(filesWithCachedAt);
            }

            // Update last sync timestamp
            await db.cacheMeta.put({
                key: 'files_last_sync',
                value: now
            });
        });
    },

    /**
     * Save a single file (write-through for uploads)
     */
    async saveFile(file: CachedFile): Promise<void> {
        await db.files.put({
            ...file,
            cachedAt: new Date().toISOString()
        });
    },

    /**
     * Update a file in cache
     */
    async updateFile(id: string, updates: Partial<CachedFile>): Promise<void> {
        await db.files.update(id, updates);
    },

    /**
     * Delete a file from cache
     */
    async deleteFile(id: string): Promise<void> {
        await db.files.delete(id);
    },

    /**
     * Clear all cached files (for logout)
     */
    async clear(): Promise<void> {
        await db.transaction('rw', [db.files, db.cacheMeta], async () => {
            await db.files.clear();
            await db.cacheMeta.delete('files_last_sync');
        });
    },

    /**
     * Get last sync timestamp
     */
    async getLastSync(): Promise<string | null> {
        const meta = await db.cacheMeta.get('files_last_sync');
        return meta?.value ?? null;
    },

    /**
     * Check if cache is stale (older than threshold)
     */
    async isStale(maxAgeMs: number = 5 * 60 * 1000): Promise<boolean> {
        const lastSync = await this.getLastSync();
        if (!lastSync) return true;

        const age = Date.now() - new Date(lastSync).getTime();
        return age > maxAgeMs;
    },

    /**
     * Find file by content hash (for deduplication)
     */
    async findByContentHash(hash: string): Promise<CachedFile | null> {
        return await db.files.where('contentHash').equals(hash).first() ?? null;
    },

    /**
     * Find file by filename
     */
    async findByFilename(filename: string): Promise<CachedFile | null> {
        return await db.files.where('filename').equals(filename).first() ?? null;
    }
};
