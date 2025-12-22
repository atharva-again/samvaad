
import React from 'react';
import { useUIStore, type SourceItem, type DuplicateItem } from '@/lib/stores/useUIStore';
import { listFiles, uploadFile, deleteFile } from '@/lib/api';
import { filesCache } from '@/lib/cache/filesCache';
import { CachedFile } from '@/lib/cache/db';
import { toast } from 'sonner';
import { useConversationStore } from '@/lib/stores/useConversationStore';
import { uuidv7 } from 'uuidv7';

// Helper to convert API response to SourceItem
const apiToSourceItem = (f: any): SourceItem => ({
    id: f.id,
    name: f.filename,
    type: f.filename.split('.').pop()?.toUpperCase() || "FILE",
    size: f.size_bytes ? (f.size_bytes / 1024).toFixed(1) + " KB" : "Unknown",
    uploadedAt: f.created_at,
    status: 'synced' as const,
    contentHash: f.content_hash
});

// Helper to convert CachedFile to SourceItem
const cacheToSourceItem = (f: CachedFile): SourceItem => ({
    id: f.id,
    name: f.filename,
    type: f.fileType,
    size: f.sizeBytes ? (f.sizeBytes / 1024).toFixed(1) + " KB" : "Unknown",
    uploadedAt: f.createdAt,
    status: 'synced' as const,
    contentHash: f.contentHash
});

// Helper to convert API response to CachedFile
const apiToCachedFile = (f: any, userId: string): CachedFile => ({
    id: f.id,
    userId, // [SECURITY-FIX #01]
    filename: f.filename,
    fileType: f.filename.split('.').pop()?.toUpperCase() || "FILE",
    sizeBytes: f.size_bytes || 0,
    contentHash: f.content_hash,
    createdAt: f.created_at,
    cachedAt: new Date().toISOString()
});

export function useFileProcessor() {
    const {
        sources,
        setSources,
        addSource,
        removeSource,
        updateSource,
        updateSourceStatus,
        hasFetchedSources,
        setHasFetchedSources,
        setPendingDuplicates,
        setShowDuplicateModal,
        pendingDuplicates,
        setSourcesPanelOpen
    } = useUIStore();

    const userId = useConversationStore(state => state.userId);

    // Cache-first loading with stale-while-revalidate
    const refreshSources = React.useCallback(async () => {
        try {
            // 0. Safety check
            if (!userId) return [];

            // 1. Check cache first - show instantly
            const cachedFiles = await filesCache.getAll(userId);
            if (cachedFiles.length > 0) {
                console.log('[FileProcessor] Cache HIT - showing', cachedFiles.length, 'files');
                const mapped = cachedFiles.map(cacheToSourceItem);
                setSources(mapped);
                setHasFetchedSources(true);

                // 2. Revalidate in background (stale-while-revalidate)
                listFiles().then(async (files) => {
                    console.log('[FileProcessor] Background sync - got', files.length, 'files from server');
                    const freshMapped = files.map(apiToSourceItem);
                    setSources(freshMapped);

                    // Update cache with fresh data
                    const cachedData = files.map(f => apiToCachedFile(f, userId));
                    await filesCache.saveAll(cachedData, userId);
                }).catch(err => {
                    console.warn('[FileProcessor] Background sync failed:', err);
                });

                return mapped;
            }

            // 3. Cache miss - fetch from server
            console.log('[FileProcessor] Cache MISS - fetching from server');
            setHasFetchedSources(true);
            const files = await listFiles();
            const mapped = files.map(apiToSourceItem);
            setSources(mapped);

            // Save to cache
            const cachedData = files.map(f => apiToCachedFile(f, userId));
            await filesCache.saveAll(cachedData, userId);

            return mapped;
        } catch (e) {
            console.error("Failed to list files:", e);
            toast.error("Failed to load files");
            return [];
        }
    }, [setHasFetchedSources, setSources, userId]);

    const uploadSingleFile = async (file: File): Promise<{ success: boolean, name: string, error?: string }> => {
        console.log("[useFileProcessor] Processing file:", file.name);
        // [SECURITY-FIX #02] Use UUIDv7 for consistent IDs
        const tempId = uuidv7();
        const newSource = {
            id: tempId,
            name: file.name,
            type: file.name.split('.').pop()?.toUpperCase() || "FILE",
            size: (file.size / 1024).toFixed(1) + " KB",
            uploadedAt: new Date().toISOString(),
            status: 'uploading' as const
        };

        addSource(newSource);

        try {
            console.log("[useFileProcessor] Calling uploadFile for:", file.name);
            const result = await uploadFile(file);
            console.log("[useFileProcessor] uploadFile result:", result);

            // Check for backend processing errors (e.g., LlamaParse failures)
            if (result.error) {
                console.error("[useFileProcessor] Backend processing error:", result.error);
                updateSourceStatus(tempId, 'error');
                updateSourceStatus(tempId, 'error');
                // toast.error(`Failed to process ${file.name}: ${result.error}`); // Suppress for batch summary
                return { success: false, name: file.name, error: result.error };
            }

            if (result.file_id) {
                const finalId = result.file_id;
                const sizeBytes = result.size_bytes || file.size;
                const createdAt = result.created_at || new Date().toISOString();

                updateSource(tempId, {
                    id: finalId,
                    status: 'synced',
                    size: (sizeBytes / 1024).toFixed(1) + " KB",
                    uploadedAt: createdAt
                });

                // Write-through to cache
                if (userId) {
                    await filesCache.saveFile({
                        id: finalId,
                        userId, // [SECURITY-FIX #01]
                        filename: file.name,
                        fileType: file.name.split('.').pop()?.toUpperCase() || "FILE",
                        sizeBytes,
                        contentHash: result.content_hash,
                        createdAt,
                        cachedAt: new Date().toISOString()
                    });
                    console.log("[FileProcessor] File saved to cache:", finalId);
                }
            } else {
                updateSourceStatus(tempId, 'synced');
            }
            // toast.success(`${file.name} uploaded successfully`); // Suppress for batch summary
            return { success: true, name: file.name };
        } catch (error) {
            console.error("[useFileProcessor] Upload error:", error);
            removeSource(tempId);
            // toast.error(`Failed to upload ${file.name}`); // Suppress for batch summary
            return { success: false, name: file.name, error: String(error) };
        }
    };

    const calculateSHA256 = async (file: File): Promise<string> => {
        const buffer = await file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        return hashHex;
    };

    const processFiles = async (files: File[]) => {
        console.log("[useFileProcessor] processFiles called with", files.length, "files");
        if (files.length > 0) {
            // [UX-FIX] Client-side file size validation (25MB limit)
            const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB
            const oversizedFiles = files.filter(f => f.size > MAX_FILE_SIZE);
            const validFiles = files.filter(f => f.size <= MAX_FILE_SIZE);

            if (oversizedFiles.length > 0) {
                const names = oversizedFiles.map(f => f.name).join(', ');
                toast.error(`File${oversizedFiles.length > 1 ? 's' : ''} too large (max 25MB): ${names}`);
            }

            if (validFiles.length === 0) {
                return; // No valid files to process
            }

            // Auto-open the knowledge base panel to show upload progress
            setSourcesPanelOpen(true);

            let currentSources = sources;
            if (!hasFetchedSources) {
                currentSources = await refreshSources();
            }

            const duplicates: DuplicateItem[] = [];
            const uniqueFiles: File[] = [];

            // We need to check async hashes
            await Promise.all(validFiles.map(async (file) => {
                let duplicateMatch: SourceItem | null = null; // SourceItem

                // 1. Check Filename Collision
                const nameMatch = currentSources.find((s) => s.name === file.name);
                if (nameMatch) {
                    duplicateMatch = nameMatch;
                } else {
                    // 2. Check Content Collision (Local Scope)
                    try {
                        const fileHash = await calculateSHA256(file);
                        const contentMatch = currentSources.find((s) => s.contentHash === fileHash);
                        if (contentMatch) {
                            console.log(`[useFileProcessor] Content duplicate found: ${file.name} matches ${contentMatch.name}`);
                            duplicateMatch = contentMatch;
                        }
                    } catch (e) {
                        console.error("Error calculating hash:", e);
                    }
                }

                if (duplicateMatch) {
                    duplicates.push({ file, match: { name: duplicateMatch.name, id: duplicateMatch.id } });
                } else {
                    uniqueFiles.push(file);
                }
            }));

            if (uniqueFiles.length > 0) {
                const results = await Promise.all(uniqueFiles.map(uploadSingleFile));

                // [UX-FIX] Batch Toast Summary
                const successCount = results.filter(r => r.success).length;
                const errors = results.filter(r => !r.success);

                if (successCount > 0) {
                    toast.success(`Uploaded ${successCount} file${successCount > 1 ? 's' : ''} successfully`);
                }

                if (errors.length > 0) {
                    toast.error(`Failed to upload ${errors.length} file${errors.length > 1 ? 's' : ''}`);
                    console.error("Upload failures:", errors);
                }
            }

            if (duplicates.length > 0) {
                setPendingDuplicates(duplicates);
                setShowDuplicateModal(true);
            }
        }
    };

    const handleReplaceDuplicates = async () => {
        setShowDuplicateModal(false);
        const itemsToProcess = [...pendingDuplicates];
        setPendingDuplicates([]);

        await Promise.all(itemsToProcess.map(async (item) => {
            // item is now { file, match }
            const { file, match } = item;

            if (match) {
                try {
                    // Upload new version FIRST (Preserves Shared Chunks/Deduplication)
                    await uploadSingleFile(file);

                    // Then Delete old version (Cleans up only truly orphaned chunks)
                    await deleteFile(String(match.id));
                    if (userId) await filesCache.deleteFile(String(match.id), userId);  // Remove from cache too

                    // Update UI
                    removeSource(match.id);
                } catch (err) {
                    console.error("Failed to replace file:", err);
                    toast.error(`Failed to replace ${file.name}`);
                }
            } else {
                // Should not happen if logic is correct
                await uploadSingleFile(file);
            }
        }));
    };

    return {
        processFiles,
        handleReplaceDuplicates,
        refreshSources
    };
}
