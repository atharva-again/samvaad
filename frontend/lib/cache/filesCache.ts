import { type CachedFile, db } from "./db";

export const filesCache = {
	/**
	 * Get all cached files
	 */
	async getAll(userId: string): Promise<CachedFile[]> {
		return await db.files.where("userId").equals(userId).toArray();
	},

	/**
	 * Get a single cached file by ID
	 */
	async get(id: string, userId: string): Promise<CachedFile | null> {
		return (await db.files.get({ userId, id })) ?? null;
	},

	/**
	 * Save multiple files to cache (for full sync)
	 */
	async saveAll(files: CachedFile[], userId: string): Promise<void> {
		const now = new Date().toISOString();

		await db.transaction("rw", [db.files, db.cacheMeta], async () => {
			// Clear existing for THIS user
			await db.files.where("userId").equals(userId).delete();

			// Add cachedAt and userId
			const filesWithCachedAt = files.map((f) => ({
				...f,
				userId,
				cachedAt: now,
			}));

			if (filesWithCachedAt.length > 0) {
				await db.files.bulkPut(filesWithCachedAt);
			}

			// Update last sync timestamp (scoped by user ideally, but key is global string?)
			// We should scope cacheMeta keys too -> 'files_last_sync_USERID'
			await db.cacheMeta.put({
				key: `files_last_sync_${userId}`,
				value: now,
			});
		});
	},

	/**
	 * Save a single file (write-through for uploads)
	 */
	async saveFile(file: CachedFile): Promise<void> {
		if (!file.userId) throw new Error("userId required for saveFile");
		await db.files.put({
			...file,
			cachedAt: new Date().toISOString(),
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
	async deleteFile(id: string, userId: string): Promise<void> {
		// Use userId index + filter to be robust against schema versions (V2 vs V4)
		// This avoids DataError if the PK schema migration hasn't fully propagated
		await db.files
			.where("userId")
			.equals(userId)
			.filter((f) => f.id === id)
			.delete();
	},

	/**
	 * Clear all cached files (for logout)
	 */
	async clear(userId?: string): Promise<void> {
		await db.transaction("rw", [db.files, db.cacheMeta], async () => {
			if (userId) {
				await db.files.where("userId").equals(userId).delete();
				await db.cacheMeta.delete(`files_last_sync_${userId}`);
			} else {
				await db.files.clear();
				// Clear all sync meta keys
				await db.cacheMeta
					.filter((item) => item.key.startsWith("files_last_sync_"))
					.delete();
			}
		});
	},

	/**
	 * Get last sync timestamp
	 */
	async getLastSync(userId: string): Promise<string | null> {
		const meta = await db.cacheMeta.get(`files_last_sync_${userId}`);
		return meta?.value ?? null;
	},

	/**
	 * Check if cache is stale (older than threshold)
	 */
	async isStale(
		userId: string,
		maxAgeMs: number = 5 * 60 * 1000,
	): Promise<boolean> {
		const lastSync = await this.getLastSync(userId);
		if (!lastSync) return true;

		const age = Date.now() - new Date(lastSync).getTime();
		return age > maxAgeMs;
	},

	/**
	 * Find file by content hash (for deduplication)
	 */
	async findByContentHash(hash: string): Promise<CachedFile | null> {
		return (await db.files.where("contentHash").equals(hash).first()) ?? null;
	},

	/**
	 * Find file by filename
	 */
	async findByFilename(
		filename: string,
		userId: string,
	): Promise<CachedFile | null> {
		return (
			(await db.files
				.where("userId")
				.equals(userId)
				.filter((f) => f.filename === filename)
				.first()) ?? null
		);
	},
};
