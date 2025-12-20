import React from "react";
import { useUIStore } from "@/lib/stores/useUIStore";
import { useFileProcessor } from "@/hooks/useFileProcessor";
import { motion, AnimatePresence } from "framer-motion";
import { X, FileText, Trash2, ChevronLeft, FileAudio, FileImage, FileVideo, FileCode, FileSpreadsheet, File, Loader2, Search, UploadCloud, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ActionTooltip } from "@/components/ui/action-tooltip";
import { listFiles, uploadFile, deleteFile } from "@/lib/api";
import { filesCache } from "@/lib/cache/filesCache";
import { usePlatform } from "@/hooks/usePlatform";

// Helper function to get icon based on file type
const getFileIcon = (type: string) => {
    const iconMap: Record<string, React.ReactNode> = {
        "PDF": <FileText className="w-5 h-5" />,
        "DOCX": <FileText className="w-5 h-5" />,
        "DOC": <FileText className="w-5 h-5" />,
        "TXT": <FileText className="w-5 h-5" />,
        "AUDIO": <FileAudio className="w-5 h-5" />,
        "MP3": <FileAudio className="w-5 h-5" />,
        "WAV": <FileAudio className="w-5 h-5" />,
        "IMAGE": <FileImage className="w-5 h-5" />,
        "PNG": <FileImage className="w-5 h-5" />,
        "JPG": <FileImage className="w-5 h-5" />,
        "JPEG": <FileImage className="w-5 h-5" />,
        "GIF": <FileImage className="w-5 h-5" />,
        "VIDEO": <FileVideo className="w-5 h-5" />,
        "MP4": <FileVideo className="w-5 h-5" />,
        "MOV": <FileVideo className="w-5 h-5" />,
        "CODE": <FileCode className="w-5 h-5" />,
        "JS": <FileCode className="w-5 h-5" />,
        "TS": <FileCode className="w-5 h-5" />,
        "PY": <FileCode className="w-5 h-5" />,
        "CSV": <FileSpreadsheet className="w-5 h-5" />,
        "XLSX": <FileSpreadsheet className="w-5 h-5" />,
        "XLS": <FileSpreadsheet className="w-5 h-5" />,
    };
    return iconMap[type.toUpperCase()] || <File className="w-5 h-5" />;
};

// Helper for time ago
const getTimeAgo = (dateString: string) => {
    if (!dateString || dateString === "Uploading...") return "Just now";
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes ago";
    return "Just now";
};

export function SourcesPanel() {
    const { isMobile } = usePlatform();
    const {
        isSourcesPanelOpen,
        toggleSourcesPanel,
        sources,
        setSources,
        removeSource,
        hasFetchedSources,
        setHasFetchedSources,
        setSourcesPanelOpen,

        // Duplicates (Global State)
        pendingDuplicates,
        setPendingDuplicates,
        showDuplicateModal,
        setShowDuplicateModal
    } = useUIStore();

    const { processFiles, handleReplaceDuplicates, refreshSources } = useFileProcessor();

    const fileInputRef = React.useRef<HTMLInputElement>(null);
    const searchInputRef = React.useRef<HTMLInputElement>(null);
    const [searchQuery, setSearchQuery] = React.useState("");
    const [deletingIds, setDeletingIds] = React.useState<Set<string>>(new Set());

    const filteredSources = sources.filter((file) =>
        file.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const [isLoading, setIsLoading] = React.useState(false);
    const [isDragging, setIsDragging] = React.useState(false);
    const [isFetchingInfo, setIsFetchingInfo] = React.useState(!hasFetchedSources);

    // Initial fetch
    React.useEffect(() => {
        const init = async () => {
            if (!hasFetchedSources && isSourcesPanelOpen) {
                setIsFetchingInfo(true);
                await refreshSources();
                setIsFetchingInfo(false);
            }
        };
        init();
    }, [isSourcesPanelOpen, hasFetchedSources, refreshSources]);

    // Back button handling for mobile
    React.useEffect(() => {
        if (!isMobile || !isSourcesPanelOpen) return;

        // Push a state so back button doesn't leave the page
        window.history.pushState({ panel: "sources" }, "");

        const handlePopState = () => {
            // If user presses back, close the panel
            setSourcesPanelOpen(false);
        };

        window.addEventListener("popstate", handlePopState);

        return () => {
            window.removeEventListener("popstate", handlePopState);
            // If we're closing manually (not via popstate), we might want to revert the history?
            // Checking this reliably is tricky, so we'll leave the history entry for now safety.
        };
    }, [isSourcesPanelOpen, isMobile, setSourcesPanelOpen]);


    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    // processFiles and handleReplaceDuplicates now come from useFileProcessor


    // --- DRAG & DROP LOGIC ---
    const dragCounter = React.useRef(0);

    const handleDragEnter = (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter.current += 1;
        if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
            setIsDragging(true);
        }
    };

    const handleDragLeave = (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter.current -= 1;
        // Only hide if we have left the window (counter 0)
        if (dragCounter.current <= 0) {
            setIsDragging(false);
            dragCounter.current = 0;
        }
    };

    const handleDragOver = (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = async (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        dragCounter.current = 0;

        if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
            const files = Array.from(e.dataTransfer.files);
            console.log("Files dropped (Global):", files.length);

            await processFiles(files);
        }
    };

    React.useEffect(() => {
        window.addEventListener("dragenter", handleDragEnter as unknown as EventListener);
        window.addEventListener("dragleave", handleDragLeave as unknown as EventListener);
        window.addEventListener("dragover", handleDragOver as unknown as EventListener);
        window.addEventListener("drop", handleDrop as unknown as EventListener);

        return () => {
            window.removeEventListener("dragenter", handleDragEnter as unknown as EventListener);
            window.removeEventListener("dragleave", handleDragLeave as unknown as EventListener);
            window.removeEventListener("dragover", handleDragOver as unknown as EventListener);
            window.removeEventListener("drop", handleDrop as unknown as EventListener);
        };
    }, [isSourcesPanelOpen, toggleSourcesPanel, setSourcesPanelOpen]); // Dependencies for potential closure issues

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(event.target.files || []);
        if (files.length > 0) {
            if (!isSourcesPanelOpen) setSourcesPanelOpen(true);
            await processFiles(files);
        }
    };

    // Keyboard Shortcut (Alt + S)
    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.altKey && e.code === 'KeyS') {
                e.preventDefault();
                toggleSourcesPanel();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [toggleSourcesPanel]);

    // Search Shortcut (Ctrl + K)
    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                if (!isSourcesPanelOpen) {
                    toggleSourcesPanel();
                }
                // Wait for panel to mount/transition
                setTimeout(() => searchInputRef.current?.focus(), 100);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isSourcesPanelOpen, toggleSourcesPanel]);

    return (
        <>
            {/* Only show Overlay if dragging. Renders globally fixed. */}
            <AnimatePresence>
                {isDragging && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex flex-col items-center justify-center pointer-events-none transition-all duration-300 supports-[backdrop-filter]:bg-black/50"
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: 10 }}
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            className="relative bg-[#0A0A0A] border border-white/10 rounded-3xl p-10 max-w-md w-full shadow-2xl flex flex-col items-center gap-6 overflow-hidden"
                        >
                            {/* Decorative Background Gradient */}
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-32 bg-accent/20 blur-[80px] rounded-full pointer-events-none" />

                            {/* Icon Group */}
                            <div className="relative w-24 h-24 mb-2">
                                <div className="absolute inset-0 bg-accent/10 rounded-full blur-xl animate-pulse" />
                                <div className="relative w-full h-full bg-gradient-to-b from-white/10 to-transparent rounded-full flex items-center justify-center border border-white/5 shadow-inner">
                                    <UploadCloud className="w-10 h-10 text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.3)]" />
                                </div>
                            </div>

                            {/* Typography */}
                            <div className="text-center space-y-3 relative z-10">
                                <h3 className="text-3xl font-bold text-white tracking-tight">
                                    Drop files to upload
                                </h3>
                                <p className="text-text-secondary text-base leading-relaxed px-4">
                                    Instantly analyze documents, images, and audio files with your voice agent.
                                </p>
                            </div>

                            {/* Supported formats hint */}
                            <div className="flex gap-3 mt-2">
                                {['PDF', 'DOCX', 'TXT', 'MD', 'JSON', 'CSV'].map((ext) => (
                                    <span key={ext} className="px-3 py-1 bg-white/5 border border-white/5 rounded-full text-xs font-medium text-text-secondary uppercase tracking-wider">
                                        {ext}
                                    </span>
                                ))}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Duplicate Confirmation Modal */}
            <AnimatePresence>
                {showDuplicateModal && (
                    <div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                            onClick={() => setShowDuplicateModal(false)}
                        />
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="relative bg-[#0A0A0A] border border-white/10 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl"
                        >
                            <div className="p-6">
                                <div className="flex flex-col items-center text-center gap-4">
                                    <div className="w-12 h-12 rounded-full bg-yellow-500/10 flex items-center justify-center shrink-0 mb-1">
                                        <AlertTriangle className="w-6 h-6 text-yellow-500" />
                                    </div>
                                    <div className="flex-1 w-full">
                                        <h3 className="text-lg font-medium text-white">
                                            {pendingDuplicates.length > 1 ? 'Duplicate Files Found' : 'Duplicate File Found'}
                                        </h3>
                                        <p className="text-sm text-text-secondary mt-1">
                                            {pendingDuplicates.length > 1
                                                ? "The following files already exist in your sources."
                                                : "The following file already exists in your sources."
                                            }
                                            <br></br>Do you want to replace {pendingDuplicates.length > 1 ? 'them' : 'it'}?
                                        </p>
                                        <div className="mt-6 bg-white/5 rounded-lg border border-white/5 max-h-48 overflow-y-auto custom-scrollbar text-left">
                                            {pendingDuplicates.map((item, i) => (
                                                <div key={i} className="px-3 py-2 text-sm text-white/90 border-b border-white/5 last:border-0 flex items-center gap-2">
                                                    <File className="w-4 h-4 text-text-secondary shrink-0" />
                                                    <div className="flex items-center gap-2 truncate text-xs sm:text-sm">
                                                        <span className="text-red-300 line-through decoration-white/20">{item.match.name}</span>
                                                        <span className="text-text-secondary">→</span>
                                                        <span className="text-green-300">{item.file.name}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-3 mt-6">
                                    <Button
                                        variant="ghost"
                                        onClick={() => {
                                            setShowDuplicateModal(false);
                                            setPendingDuplicates([]);
                                        }}
                                        className="w-full text-text-secondary hover:text-white bg-white/5 hover:bg-white/10"
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        onClick={handleReplaceDuplicates}
                                        className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                                    >
                                        Replace {pendingDuplicates.length > 1 ? 'All' : ''}
                                    </Button>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Persistent Toggle (Visible when closed) - Mobile only */}
            <AnimatePresence>
                {!isSourcesPanelOpen && isMobile && (
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        className="fixed right-0 top-1/2 -translate-y-1/2 z-30"
                    >
                        <div
                            onClick={toggleSourcesPanel}
                            className="h-12 w-1.5 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-l-full cursor-pointer transition-all duration-300 hover:w-6 flex items-center justify-center group overflow-visible relative"
                        >
                            <ChevronLeft className="w-3 h-3 text-white/50 group-hover:text-white opacity-0 group-hover:opacity-100 transition-all duration-300 relative z-10" />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            <AnimatePresence mode="wait">
                {isSourcesPanelOpen && (
                    <motion.div
                        initial={isMobile ? { x: "100%", opacity: 1 } : { width: 0, opacity: 0 }}
                        animate={isMobile ? { x: 0, opacity: 1 } : { width: 420, opacity: 1 }}
                        exit={isMobile ? { x: "100%", opacity: 1 } : { width: 0, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30, mass: 0.8 }}
                        className="fixed top-[60px] left-0 bottom-0 w-full md:static md:h-full border-l border-white/5 bg-[#050505] md:bg-[#050505]/80 backdrop-blur-3xl flex flex-col shrink-0 overflow-hidden z-50 md:z-40 shadow-2xl"
                    >
                        <div
                            className={`w-full md:w-[420px] flex flex-col h-full bg-gradient-to-b from-white/[0.02] to-transparent transition-colors duration-300`}
                        >

                            {/* Hidden Input */}
                            <input
                                type="file"
                                multiple
                                ref={fileInputRef}
                                className="hidden"
                                onChange={handleFileChange}
                            />

                            {/* Header */}
                            <div className="flex items-center justify-between px-6 md:px-8 py-6 md:py-8">
                                <div>
                                    <h2 className="text-xl font-medium text-white tracking-tight flex items-center gap-2">
                                        Knowledge Base
                                    </h2>
                                    <p className="text-sm text-text-secondary mt-1 font-light tracking-wide">
                                        Manage your context sources
                                    </p>
                                </div>
                                <Button
                                    size="icon"
                                    variant="ghost"
                                    onClick={toggleSourcesPanel}
                                    className="text-text-secondary hover:text-white hover:bg-white/5 rounded-full w-10 h-10 transition-all duration-300"
                                >
                                    <X className="w-5 h-5" />
                                </Button>
                            </div>

                            {/* Search */}
                            <div className="px-6 md:px-8 pb-6">
                                <div className="relative group">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50 group-focus-within:text-white transition-colors" />
                                    <input
                                        ref={searchInputRef}
                                        type="text"
                                        placeholder="Search sources... (Ctrl+K)"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full bg-white/5 border border-white/5 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-text-secondary/50 focus:outline-none focus:bg-white/10 focus:border-white/20 transition-all font-light"
                                    />
                                </div>
                            </div>

                            {/* List */}
                            <div className="flex-1 overflow-y-auto px-4 md:px-6 pb-6 space-y-2 custom-scrollbar">
                                <div className="flex items-center justify-between px-2 pb-2">
                                    <span className="text-xs font-medium text-text-secondary/60 uppercase tracking-widest">Active Sources</span>
                                    <span className="text-xs font-mono text-text-secondary/40">{filteredSources.length} items</span>
                                </div>

                                {isFetchingInfo ? (
                                    <div className="space-y-3 pt-2">
                                        {[...Array(3)].map((_, i) => (
                                            <motion.div
                                                key={i}
                                                initial={{ opacity: 0, y: 10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: i * 0.1 }}
                                                className="flex items-center gap-4 p-4 rounded-2xl bg-white/[0.01] border border-white/[0.02]"
                                            >
                                                <div className="w-12 h-12 rounded-xl bg-white/5 animate-pulse" />
                                                <div className="flex-1 space-y-2">
                                                    <div className="h-4 w-24 bg-white/5 rounded-md animate-pulse" />
                                                    <div className="h-3 w-16 bg-white/5 rounded-md animate-pulse" />
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                ) : filteredSources.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
                                        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
                                            <File className="w-5 h-5 text-white/20" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-white/60">No sources yet</p>
                                            <p className="text-xs text-text-secondary/40 mt-1 max-w-[200px]">Upload documents to give your agent more context.</p>
                                        </div>
                                    </div>
                                ) : (
                                    filteredSources.map((file) => (
                                        <div
                                            key={file.id}
                                            className="group relative flex items-center gap-4 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.03] hover:bg-white/[0.04] hover:border-white/10 transition-all duration-300 cursor-pointer"
                                        >
                                            {/* Icon */}
                                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-white/5 to-transparent border border-white/5 flex items-center justify-center text-text-secondary group-hover:text-white group-hover:scale-105 transition-all duration-300 shadow-inner relative">
                                                {file.status === 'uploading' ? (
                                                    <div className="absolute inset-0 bg-black/50 rounded-xl flex items-center justify-center backdrop-blur-sm z-10">
                                                        <Loader2 className="w-5 h-5 animate-spin text-white" />
                                                    </div>
                                                ) : null}
                                                {getFileIcon(file.type)}
                                            </div>

                                            {/* Info */}
                                            <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                                                <h4 className="text-sm font-medium text-white/90 truncate group-hover:text-white transition-colors tracking-tight">{file.name}</h4>
                                                <div className="flex items-center gap-2 text-xs text-text-secondary/70 group-hover:text-text-secondary transition-colors font-mono">
                                                    {file.status === 'uploading' ? (
                                                        <span className="text-blue-400 flex items-center gap-1">
                                                            Uploading...
                                                        </span>
                                                    ) : (
                                                        <>
                                                            <span>{file.type}</span>
                                                            <span className="w-0.5 h-0.5 rounded-full bg-white/20" />
                                                            <span>Uploaded {getTimeAgo(file.uploadedAt)}</span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Actions */}
                                            <Button
                                                size="icon"
                                                variant="ghost"
                                                disabled={deletingIds.has(String(file.id))}
                                                onClick={async (e) => {
                                                    e.stopPropagation();
                                                    try {
                                                        const idStr = String(file.id);
                                                        setDeletingIds(prev => new Set(prev).add(idStr));
                                                        await deleteFile(idStr);
                                                        await filesCache.deleteFile(idStr);  // Remove from cache too
                                                        removeSource(file.id);
                                                        toast.success(`${file.name} removed`);
                                                    } catch (err) {
                                                        console.error(err);
                                                        toast.error("Failed to delete file");
                                                    } finally {
                                                        setDeletingIds(prev => {
                                                            const next = new Set(prev);
                                                            next.delete(String(file.id));
                                                            return next;
                                                        });
                                                    }
                                                }}
                                                className="h-9 w-9 opacity-100 md:opacity-0 group-hover:opacity-100 text-text-secondary hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all duration-300 transform md:translate-x-2 group-hover:translate-x-0"
                                            >
                                                {deletingIds.has(String(file.id)) ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <Trash2 className="w-4 h-4" />
                                                )}
                                            </Button>
                                        </div>
                                    ))
                                )}


                            </div>

                            {/* Footer */}
                            <div className={`px-6 pt-6 relative ${isMobile ? 'pb-[150px] pb-safe' : 'pb-11'}`}>
                                {/* Gradient Fade */}
                                <div className="absolute top-0 left-0 right-0 h-12 -mt-12 bg-gradient-to-t from-[#050505] to-transparent pointer-events-none" />

                                <Button
                                    onClick={handleUploadClick}
                                    className="w-full h-14 bg-white text-black hover:bg-white/90 hover:scale-[1.01] transition-all duration-300 rounded-2xl font-semibold text-base shadow-[0_0_20px_rgba(255,255,255,0.1)] flex items-center justify-center gap-2 group relative"
                                >
                                    <span className="text-xl leading-none font-light">+</span> Add Source
                                    <ActionTooltip label="Add Source" shortcut="Alt+A" side="top" />
                                </Button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
