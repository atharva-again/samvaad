
import React from 'react';
import { useUIStore, type SourceItem, type DuplicateItem } from '@/lib/stores/useUIStore';
import { listFiles, uploadFile, deleteFile } from '@/lib/api';
import { toast } from 'sonner';

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

    // Reusing the fetch logic
    const refreshSources = React.useCallback(async () => {
        try {
            setHasFetchedSources(true);
            const files = await listFiles();
            const mapped = files.map((f: any) => ({
                id: f.id,
                name: f.filename,
                type: f.filename.split('.').pop()?.toUpperCase() || "FILE",
                size: f.size_bytes ? (f.size_bytes / 1024).toFixed(1) + " KB" : "Unknown",
                uploadedAt: f.created_at,
                status: 'synced' as const,
                contentHash: f.content_hash
            }));
            setSources(mapped);
            return mapped;
        } catch (e) {
            console.error("Failed to list files:", e);
            toast.error("Failed to load files");
            return [];
        }
    }, [setHasFetchedSources, setSources]);

    const uploadSingleFile = async (file: File) => {
        console.log("[useFileProcessor] Processing file:", file.name);
        const tempId = Date.now().toString() + Math.random().toString().slice(2, 5); // Unique ID
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
                toast.error(`Failed to process ${file.name}: ${result.error}`);
                return;
            }

            if (result.file_id) {
                updateSource(tempId, {
                    id: result.file_id,
                    status: 'synced',
                    size: result.size_bytes ? (result.size_bytes / 1024).toFixed(1) + " KB" : newSource.size,
                    uploadedAt: result.created_at || new Date().toISOString()
                });
            } else {
                updateSourceStatus(tempId, 'synced');
            }
            toast.success(`${file.name} uploaded successfully`);
        } catch (error) {
            console.error("[useFileProcessor] Upload error:", error);
            removeSource(tempId);
            toast.error(`Failed to upload ${file.name}`);
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
            // Auto-open the knowledge base panel to show upload progress
            setSourcesPanelOpen(true);

            let currentSources = sources;
            if (!hasFetchedSources) {
                currentSources = await refreshSources();
            }

            const duplicates: DuplicateItem[] = [];
            const uniqueFiles: File[] = [];

            // We need to check async hashes
            await Promise.all(files.map(async (file) => {
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
                await Promise.all(uniqueFiles.map(uploadSingleFile));
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
