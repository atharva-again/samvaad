"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, MessageSquare, FileText, X, FolderOpen, Pencil, Pin, Trash2, ChevronRight, Loader2, Eye, EyeOff } from "lucide-react";
import { useConversationStore, Conversation } from "@/lib/stores/useConversationStore";
import { useUIStore, SourceItem } from "@/lib/stores/useUIStore";
import { usePlatform } from "@/hooks/usePlatform";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { deleteFile, renameFile } from "@/lib/api";
import { filesCache } from "@/lib/cache/filesCache";

type SearchCategory = "conversations" | "sources";

interface SearchResult {
    id: string;
    title: string;
    subtitle?: string;
    category: SearchCategory;
    icon: React.ReactNode;
    score: number; // For fuzzy ranking
    originalData?: Conversation | SourceItem;
}

interface ConversationAction {
    id: "open" | "rename" | "pin" | "delete";
    label: string;
    icon: React.ReactNode;
    shortcut?: string;
}

const CONVERSATION_ACTIONS: ConversationAction[] = [
    { id: "open", label: "Open", icon: <FolderOpen className="w-4 h-4" />, shortcut: "↵" },
    { id: "rename", label: "Rename", icon: <Pencil className="w-4 h-4" />, shortcut: "R" },
    { id: "pin", label: "Pin/Unpin", icon: <Pin className="w-4 h-4" />, shortcut: "P" },
    { id: "delete", label: "Delete", icon: <Trash2 className="w-4 h-4 text-red-400" />, shortcut: "D" },
];

interface SourceAction {
    id: "open" | "rename" | "toggle-rag" | "delete";
    label: string;
    icon: React.ReactNode;
    shortcut?: string;
}

const SOURCE_ACTIONS: SourceAction[] = [
    { id: "open", label: "View in Panel", icon: <FolderOpen className="w-4 h-4" />, shortcut: "↵" },
    { id: "rename", label: "Rename", icon: <Pencil className="w-4 h-4" />, shortcut: "R" },
    { id: "delete", label: "Delete", icon: <Trash2 className="w-4 h-4 text-red-400" />, shortcut: "D" },
];

// ─────────────────────────────────────────────────────────────────────
// Fuzzy Search Implementation
// ─────────────────────────────────────────────────────────────────────

/**
 * Simple fuzzy search with scoring.
 * Returns a score (higher is better match), or 0 if no match.
 */
function fuzzyMatch(text: string, query: string): number {
    if (!query) return 1; // No query = show all

    const textLower = text.toLowerCase();
    const queryLower = query.toLowerCase();

    // Exact match gets highest score
    if (textLower === queryLower) return 100;

    // Starts with query gets high score
    if (textLower.startsWith(queryLower)) return 90;

    // Contains exact substring gets good score
    if (textLower.includes(queryLower)) return 80;

    // Fuzzy match: check if all query chars appear in order
    let queryIdx = 0;
    let score = 0;
    let consecutiveBonus = 0;
    let lastMatchIdx = -2;

    for (let i = 0; i < textLower.length && queryIdx < queryLower.length; i++) {
        if (textLower[i] === queryLower[queryIdx]) {
            score += 10;
            // Bonus for consecutive matches
            if (i === lastMatchIdx + 1) {
                consecutiveBonus += 5;
            }
            // Bonus for matching at word boundaries
            if (i === 0 || textLower[i - 1] === ' ' || textLower[i - 1] === '-' || textLower[i - 1] === '_') {
                score += 5;
            }
            lastMatchIdx = i;
            queryIdx++;
        }
    }

    // All query chars must be found
    if (queryIdx < queryLower.length) return 0;

    return score + consecutiveBonus;
}

export function UniversalSearchModal() {
    const router = useRouter();
    const { isMac } = usePlatform();
    const inputRef = useRef<HTMLInputElement>(null);

    // Store state
    const { isSearchOpen, setSearchOpen, setSourcesPanelOpen, removeSource, updateSource, toggleAllowedSource, allowedSourceIds } = useUIStore();
    const { conversations, deleteConversation, updateConversationTitle, togglePinConversation } = useConversationStore();
    const { sources } = useUIStore();

    // Local state
    const [query, setQuery] = useState("");
    const [activeCategory, setActiveCategory] = useState<SearchCategory>("conversations");
    const [selectedIndex, setSelectedIndex] = useState(0);

    // Submenu state for conversations
    const [showSubmenu, setShowSubmenu] = useState(false);
    const [submenuIndex, setSubmenuIndex] = useState(0);
    const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);

    // Rename modal state (inline)
    const [showRenameInput, setShowRenameInput] = useState(false);
    const [renameValue, setRenameValue] = useState("");
    const renameInputRef = useRef<HTMLInputElement>(null);

    // Delete confirmation state
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    // Async operation states
    const [isDeleting, setIsDeleting] = useState(false);
    const [isRenaming, setIsRenaming] = useState(false);
    const [isPinning, setIsPinning] = useState(false);

    // Refs to access latest state in keyboard handler (avoids stale closure)
    const stateRef = useRef({
        showDeleteConfirm: false,
        isDeleting: false,
        isRenaming: false,
        isPinning: false,
        showRenameInput: false,
        showSubmenu: false,
        submenuIndex: 0,
        selectedIndex: 0,
        selectedResult: null as SearchResult | null,
        renameValue: "",
    });

    // Keep refs in sync with state
    useEffect(() => {
        stateRef.current = {
            showDeleteConfirm,
            isDeleting,
            isRenaming,
            isPinning,
            showRenameInput,
            showSubmenu,
            submenuIndex,
            selectedIndex,
            selectedResult,
            renameValue,
        };
    });

    // Compute filtered results with fuzzy search for BOTH categories
    const allFilteredResults = useMemo(() => {
        const getConversationResults = (): SearchResult[] => {
            if (!query.trim()) {
                return conversations.slice(0, 8).map((conv) => ({
                    id: conv.id,
                    title: conv.title,
                    subtitle: new Date(conv.createdAt).toLocaleDateString(),
                    category: "conversations" as SearchCategory,
                    icon: <MessageSquare className="w-4 h-4 text-blue-400" />,
                    score: 1,
                    originalData: conv,
                }));
            }

            return conversations
                .map((conv) => ({
                    id: conv.id,
                    title: conv.title,
                    subtitle: new Date(conv.createdAt).toLocaleDateString(),
                    category: "conversations" as SearchCategory,
                    icon: <MessageSquare className="w-4 h-4 text-blue-400" />,
                    score: fuzzyMatch(conv.title, query),
                    originalData: conv,
                }))
                .filter((r) => r.score > 0)
                .sort((a, b) => b.score - a.score)
                .slice(0, 10);
        };

        const getSourceResults = (): SearchResult[] => {
            if (!query.trim()) {
                return sources.slice(0, 8).map((source) => ({
                    id: String(source.id),
                    title: source.name,
                    subtitle: source.type,
                    category: "sources" as SearchCategory,
                    icon: <FileText className="w-4 h-4 text-emerald-400" />,
                    score: 1,
                    originalData: source,
                }));
            }

            return sources
                .map((source) => ({
                    id: String(source.id),
                    title: source.name,
                    subtitle: source.type,
                    category: "sources" as SearchCategory,
                    icon: <FileText className="w-4 h-4 text-emerald-400" />,
                    score: fuzzyMatch(source.name, query),
                    originalData: source,
                }))
                .filter((r) => r.score > 0)
                .sort((a, b) => b.score - a.score)
                .slice(0, 10);
        };

        return {
            conversations: getConversationResults(),
            sources: getSourceResults(),
        };
    }, [query, conversations, sources]);

    // Get current category results
    const filteredResults = activeCategory === "conversations"
        ? allFilteredResults.conversations
        : allFilteredResults.sources;

    // Count for tabs
    const conversationCount = query.trim() ? allFilteredResults.conversations.length : conversations.length;
    const sourceCount = query.trim() ? allFilteredResults.sources.length : sources.length;

    // Reset selection when results change
    useEffect(() => {
        setSelectedIndex(0);
        setShowSubmenu(false);
        setSubmenuIndex(0);
    }, [filteredResults.length, activeCategory]);

    // Focus input when modal opens
    useEffect(() => {
        if (isSearchOpen) {
            setQuery("");
            setSelectedIndex(0);
            setShowSubmenu(false);
            setShowRenameInput(false);
            setTimeout(() => inputRef.current?.focus(), 50);
        }
    }, [isSearchOpen]);

    // Focus rename input
    useEffect(() => {
        if (showRenameInput) {
            setTimeout(() => renameInputRef.current?.focus(), 50);
        }
    }, [showRenameInput]);

    // Handle conversation actions
    const handleConversationAction = useCallback(async (action: ConversationAction["id"], result: SearchResult) => {
        const conv = result.originalData as Conversation;

        switch (action) {
            case "open":
                router.push(`/chat/${result.id}`);
                setSearchOpen(false);
                break;
            case "rename":
                setRenameValue(conv.title);
                setShowRenameInput(true);
                break;
            case "pin":
                if (isPinning) return;
                setIsPinning(true);
                try {
                    await togglePinConversation(result.id);
                    toast.success(conv.isPinned ? "Unpinned conversation" : "Pinned conversation");
                    setShowSubmenu(false);
                } catch (error) {
                    toast.error("Failed to update pin status");
                } finally {
                    setIsPinning(false);
                }
                break;
            case "delete":
                setShowDeleteConfirm(true);
                break;
        }
    }, [router, setSearchOpen, togglePinConversation, deleteConversation, isPinning]);

    // Handle source actions
    const handleSourceAction = useCallback(async (action: SourceAction["id"], result: SearchResult) => {
        const source = result.originalData as SourceItem;

        switch (action) {
            case "open":
                // Set the source name in the sources panel search via store
                useUIStore.getState().setSourcesSearchQuery(result.title);
                useUIStore.getState().setSourcesPanelTab("knowledge-base");
                setSourcesPanelOpen(true);
                setSearchOpen(false);
                break;
            case "rename":
                const lastDot = source.name.lastIndexOf('.');
                const baseName = lastDot !== -1 ? source.name.slice(0, lastDot) : source.name;
                setRenameValue(baseName);
                setShowRenameInput(true);
                break;
            case "toggle-rag":
                toggleAllowedSource(String(source.id));
                const isNowAllowed = allowedSourceIds === null || !allowedSourceIds.has(String(source.id));
                toast.success(isNowAllowed ? "Source enabled for RAG" : "Source disabled for RAG");
                setShowSubmenu(false);
                break;
            case "delete":
                setShowDeleteConfirm(true);
                break;
        }
    }, [setSourcesPanelOpen, setSearchOpen, toggleAllowedSource, allowedSourceIds]);

    // Handle source selection - show submenu (same as conversations)
    const handleSourceSelect = useCallback((result: SearchResult) => {
        // Show submenu for sources too
        setSelectedResult(result);
        setShowSubmenu(true);
        setSubmenuIndex(0);
    }, []);

    // Handle result selection (Enter key)
    const handleSelect = useCallback((result: SearchResult) => {
        if (result.category === "conversations") {
            // Show submenu for conversations
            setSelectedResult(result);
            setShowSubmenu(true);
            setSubmenuIndex(0);
        } else {
            // Show submenu for sources too
            handleSourceSelect(result);
        }
    }, [handleSourceSelect]);

    // Handle rename submit (for both conversations and sources)
    const handleRenameSubmit = useCallback(async () => {
        if (!selectedResult || !renameValue.trim() || isRenaming) return;
        setIsRenaming(true);
        try {
            if (selectedResult.category === "conversations") {
                await updateConversationTitle(selectedResult.id, renameValue.trim());
                toast.success("Conversation renamed");
            } else {
                // Source rename
                let finalName = renameValue.trim();
                // Append original extension if it logic calls for it
                if (selectedResult.title.includes('.')) {
                    const ext = selectedResult.title.slice(selectedResult.title.lastIndexOf('.'));
                    // Only append if simpler logic: always re-append extension if we stripped it
                    finalName += ext;
                }

                await renameFile(selectedResult.id, finalName);
                updateSource(selectedResult.id, { name: finalName });
                toast.success("Source renamed");
            }
            setShowRenameInput(false);
            setShowSubmenu(false);
        } catch (error) {
            toast.error(selectedResult.category === "conversations" ? "Failed to rename conversation" : "Failed to rename source");
        } finally {
            setIsRenaming(false);
        }
    }, [selectedResult, renameValue, updateConversationTitle, updateSource, isRenaming]);

    // Keyboard navigation
    useEffect(() => {
        if (!isSearchOpen) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            const state = stateRef.current;

            // Handle delete confirmation mode FIRST (highest priority)
            if (state.showDeleteConfirm && state.selectedResult) {
                e.preventDefault();
                e.stopPropagation();

                if (e.key === "Escape" || e.key === "c" || e.key === "C") {
                    setShowDeleteConfirm(false);
                    // Go back to submenu, not close everything
                } else if (e.key === "Enter" && !state.isDeleting) {
                    const conv = state.selectedResult.originalData as Conversation;
                    setIsDeleting(true);

                    // Add minimum delay to ensure spinner is visible (UX)
                    Promise.all([
                        deleteConversation(state.selectedResult.id),
                        new Promise(resolve => setTimeout(resolve, 800))
                    ]).then(() => {
                        toast.success(`Deleted "${conv.title}"`);
                        setIsDeleting(false);
                        setShowDeleteConfirm(false);
                        setShowSubmenu(false);
                        setSelectedResult(null);
                        // Stay in modal, back to search screen
                    }).catch(() => {
                        toast.error("Failed to delete conversation");
                        setIsDeleting(false);
                    });
                }
                return;
            }

            // Handle rename input mode - only intercept specific keys
            if (state.showRenameInput) {
                if (e.key === "Escape") {
                    e.preventDefault();
                    e.stopPropagation();
                    setShowRenameInput(false);
                } else if (e.key === "Enter") {
                    e.preventDefault();
                    e.stopPropagation();
                    // Inline rename submit using ref values
                    if (state.selectedResult && state.renameValue.trim() && !state.isRenaming) {
                        const isConversation = state.selectedResult.category === "conversations";
                        setIsRenaming(true);

                        if (isConversation) {
                            updateConversationTitle(state.selectedResult.id, state.renameValue.trim())
                                .then(() => {
                                    toast.success("Conversation renamed");
                                    setIsRenaming(false);
                                    setShowRenameInput(false);
                                    setShowSubmenu(false);
                                })
                                .catch(() => {
                                    toast.error("Failed to rename conversation");
                                    setIsRenaming(false);
                                });
                        } else {
                            // Source rename
                            renameFile(state.selectedResult.id, state.renameValue.trim())
                                .then(() => {
                                    updateSource(state.selectedResult!.id, { name: state.renameValue.trim() });
                                    toast.success("Source renamed");
                                    setIsRenaming(false);
                                    setShowRenameInput(false);
                                    setShowSubmenu(false);
                                })
                                .catch(() => {
                                    toast.error("Failed to rename source");
                                    setIsRenaming(false);
                                });
                        }
                    }
                }
                // Don't intercept other keys - let user type!
                return;
            }

            // Handle submenu mode
            if (state.showSubmenu && state.selectedResult) {
                const isConversation = state.selectedResult.category === "conversations";
                const actionsList = isConversation ? CONVERSATION_ACTIONS : SOURCE_ACTIONS;

                switch (e.key) {
                    case "ArrowDown":
                        e.preventDefault();
                        setSubmenuIndex((prev) => (prev < actionsList.length - 1 ? prev + 1 : 0));
                        break;
                    case "ArrowUp":
                        e.preventDefault();
                        setSubmenuIndex((prev) => (prev > 0 ? prev - 1 : actionsList.length - 1));
                        break;
                    case "Enter":
                        e.preventDefault();
                        if (isConversation) {
                            handleConversationAction(CONVERSATION_ACTIONS[state.submenuIndex].id, state.selectedResult);
                        } else {
                            handleSourceAction(SOURCE_ACTIONS[state.submenuIndex].id, state.selectedResult);
                        }
                        break;
                    case "Escape":
                        e.preventDefault();
                        setShowSubmenu(false);
                        break;
                    case "r":
                    case "R":
                        e.preventDefault();
                        if (isConversation) {
                            handleConversationAction("rename", state.selectedResult);
                        } else {
                            handleSourceAction("rename", state.selectedResult);
                        }
                        break;
                    case "p":
                    case "P":
                        // Pin/Unpin only for conversations
                        if (isConversation) {
                            e.preventDefault();
                            if (!state.isPinning) {
                                handleConversationAction("pin", state.selectedResult);
                            }
                        }
                        break;
                    case "t":
                    case "T":
                        // Toggle RAG only for sources
                        if (!isConversation) {
                            e.preventDefault();
                            handleSourceAction("toggle-rag", state.selectedResult);
                        }
                        break;
                    case "d":
                    case "D":
                        e.preventDefault();
                        if (isConversation) {
                            handleConversationAction("delete", state.selectedResult);
                        } else {
                            handleSourceAction("delete", state.selectedResult);
                        }
                        break;
                }
                return;
            }

            // Normal mode
            switch (e.key) {
                case "ArrowDown":
                    e.preventDefault();
                    setSelectedIndex((prev) =>
                        prev < filteredResults.length - 1 ? prev + 1 : 0
                    );
                    break;
                case "ArrowUp":
                    e.preventDefault();
                    setSelectedIndex((prev) =>
                        prev > 0 ? prev - 1 : filteredResults.length - 1
                    );
                    break;
                case "Enter":
                    e.preventDefault();
                    if (filteredResults[state.selectedIndex]) {
                        handleSelect(filteredResults[state.selectedIndex]);
                    }
                    break;
                case "Escape":
                    e.preventDefault();
                    setSearchOpen(false);
                    break;
                case "Tab":
                    e.preventDefault();
                    setActiveCategory((prev) =>
                        prev === "conversations" ? "sources" : "conversations"
                    );
                    break;
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [isSearchOpen, filteredResults, handleSelect, setSearchOpen, handleConversationAction, deleteConversation, updateConversationTitle]);

    // Highlight matching text with fuzzy support
    const highlightMatch = (text: string, query: string) => {
        if (!query.trim()) return text;

        // For simple contains match, highlight the substring
        const lowerText = text.toLowerCase();
        const lowerQuery = query.toLowerCase();
        const idx = lowerText.indexOf(lowerQuery);

        if (idx >= 0) {
            return (
                <>
                    {text.slice(0, idx)}
                    <span className="text-white bg-white/20 rounded px-0.5">
                        {text.slice(idx, idx + query.length)}
                    </span>
                    {text.slice(idx + query.length)}
                </>
            );
        }

        // For fuzzy match, highlight individual matching chars
        const result: React.ReactNode[] = [];
        let queryIdx = 0;

        for (let i = 0; i < text.length; i++) {
            if (queryIdx < lowerQuery.length && text[i].toLowerCase() === lowerQuery[queryIdx]) {
                result.push(
                    <span key={i} className="text-white bg-white/20 rounded px-0.5">
                        {text[i]}
                    </span>
                );
                queryIdx++;
            } else {
                result.push(text[i]);
            }
        }

        return <>{result}</>;
    };

    return (
        <AnimatePresence>
            {isSearchOpen && (
                <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] p-4">
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={() => setSearchOpen(false)}
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0, y: -20 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.95, opacity: 0, y: -20 }}
                        transition={{ type: "spring", stiffness: 400, damping: 30 }}
                        className="relative bg-[#0A0A0A] border border-white/10 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl"
                    >
                        {/* Search Input */}
                        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
                            <Search className="w-5 h-5 text-white/40 shrink-0" />
                            <input
                                ref={inputRef}
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search conversations and sources..."
                                className="flex-1 bg-transparent text-white text-sm placeholder:text-white/30 outline-none"
                            />
                            <button
                                onClick={() => setSearchOpen(false)}
                                className="p-1 hover:bg-white/10 rounded-md transition-colors"
                            >
                                <X className="w-4 h-4 text-white/40" />
                            </button>
                        </div>

                        {/* Category Tabs with counts */}
                        <div className="flex items-center gap-1 px-4 py-2 border-b border-white/5">
                            <button
                                onClick={() => setActiveCategory("conversations")}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-medium rounded-lg transition-all",
                                    activeCategory === "conversations"
                                        ? "bg-white/10 text-white"
                                        : "text-white/50 hover:text-white/70 hover:bg-white/5"
                                )}
                            >
                                <span className="flex items-center gap-1.5">
                                    <MessageSquare className="w-3.5 h-3.5" />
                                    Conversations
                                    {query.trim() && (
                                        <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-white/10 rounded-full">
                                            {allFilteredResults.conversations.length}
                                        </span>
                                    )}
                                </span>
                            </button>
                            <button
                                onClick={() => setActiveCategory("sources")}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-medium rounded-lg transition-all",
                                    activeCategory === "sources"
                                        ? "bg-white/10 text-white"
                                        : "text-white/50 hover:text-white/70 hover:bg-white/5"
                                )}
                            >
                                <span className="flex items-center gap-1.5">
                                    <FileText className="w-3.5 h-3.5" />
                                    Sources
                                    {query.trim() && (
                                        <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-white/10 rounded-full">
                                            {allFilteredResults.sources.length}
                                        </span>
                                    )}
                                </span>
                            </button>
                            <span className="ml-auto text-[10px] text-white/30 font-mono">
                                Tab to switch
                            </span>
                        </div>

                        {/* Results */}
                        <div className="max-h-[50vh] overflow-y-auto">
                            {filteredResults.length === 0 ? (
                                <div className="py-12 text-center">
                                    <p className="text-sm text-white/40">
                                        {query ? "No results found" : "No items yet"}
                                    </p>
                                </div>
                            ) : showSubmenu && selectedResult ? (
                                /* Submenu for conversation actions */
                                <div className="py-2">
                                    <div className="px-4 py-2 border-b border-white/5">
                                        <p className="text-xs text-white/40">Actions for:</p>
                                        <p className="text-sm text-white truncate">{selectedResult.title}</p>
                                    </div>

                                    {showRenameInput ? (
                                        <div className="px-4 py-4">
                                            <div className="flex items-center bg-white/5 border border-white/10 rounded-lg px-3 focus-within:border-white/20">
                                                <input
                                                    ref={renameInputRef}
                                                    type="text"
                                                    value={renameValue}
                                                    onChange={(e) => setRenameValue(e.target.value)}
                                                    placeholder="New name..."
                                                    className="w-full bg-transparent py-2.5 text-sm text-white placeholder:text-white/30 outline-none flex-1 min-w-0"
                                                />
                                                {selectedResult.category === 'sources' && selectedResult.title.includes('.') && (
                                                    <span className="text-sm text-white/40 select-none ml-1">
                                                        {selectedResult.title.slice(selectedResult.title.lastIndexOf('.'))}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex gap-2 mt-3">
                                                <button
                                                    onClick={() => setShowRenameInput(false)}
                                                    disabled={isRenaming}
                                                    className="flex-1 py-2.5 text-xs text-white/50 hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                                                >
                                                    Cancel
                                                    <kbd className="px-1.5 py-0.5 text-[10px] bg-white/10 text-white/40 rounded font-mono">C</kbd>
                                                </button>
                                                <button
                                                    onClick={handleRenameSubmit}
                                                    disabled={isRenaming}
                                                    className="flex-1 py-2.5 text-xs bg-white/10 text-white hover:bg-white/20 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-70"
                                                >
                                                    {isRenaming ? (
                                                        <>
                                                            <Loader2 className="w-3 h-3 animate-spin" />
                                                            Saving...
                                                        </>
                                                    ) : (
                                                        <>
                                                            Save
                                                            <kbd className="px-1.5 py-0.5 text-[10px] bg-white/10 text-white/40 rounded font-mono">↵</kbd>
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    ) : showDeleteConfirm ? (
                                        <div className="px-4 py-4">
                                            <div className="text-center mb-4">
                                                <p className="text-sm text-white">
                                                    Delete this {selectedResult.category === "conversations" ? "conversation" : "source"}?
                                                </p>
                                                <p className="text-xs text-white/40 mt-1">This action cannot be undone.</p>
                                            </div>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => setShowDeleteConfirm(false)}
                                                    disabled={isDeleting}
                                                    className="flex-1 py-2.5 text-xs text-white/50 hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                                                >
                                                    Cancel
                                                    <kbd className="px-1.5 py-0.5 text-[10px] bg-white/10 text-white/40 rounded font-mono">C</kbd>
                                                </button>
                                                <button
                                                    onClick={async () => {
                                                        if (selectedResult && !isDeleting) {
                                                            setIsDeleting(true);

                                                            try {
                                                                if (selectedResult.category === "conversations") {
                                                                    const conv = selectedResult.originalData as Conversation;
                                                                    await Promise.all([
                                                                        deleteConversation(selectedResult.id),
                                                                        new Promise(resolve => setTimeout(resolve, 800))
                                                                    ]);
                                                                    toast.success(`Deleted "${conv.title}"`);
                                                                } else {
                                                                    const source = selectedResult.originalData as SourceItem;
                                                                    await deleteFile(selectedResult.id);
                                                                    const userId = useConversationStore.getState().userId;
                                                                    if (userId) {
                                                                        await filesCache.deleteFile(selectedResult.id, userId);
                                                                    }
                                                                    removeSource(source.id);
                                                                    toast.success(`Deleted "${source.name}"`);
                                                                }
                                                                setIsDeleting(false);
                                                                setShowDeleteConfirm(false);
                                                                setShowSubmenu(false);
                                                                setSelectedResult(null);
                                                            } catch {
                                                                toast.error(`Failed to delete ${selectedResult.category === "conversations" ? "conversation" : "source"}`);
                                                                setIsDeleting(false);
                                                            }
                                                        }
                                                    }}
                                                    disabled={isDeleting}
                                                    className="flex-1 py-2.5 text-xs bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-70"
                                                >
                                                    {isDeleting ? (
                                                        <>
                                                            <Loader2 className="w-3 h-3 animate-spin" />
                                                            Deleting...
                                                        </>
                                                    ) : (
                                                        <>
                                                            Delete
                                                            <kbd className="px-1.5 py-0.5 text-[10px] bg-red-500/20 text-red-300/60 rounded font-mono">↵</kbd>
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    ) : selectedResult.category === "conversations" ? (
                                        CONVERSATION_ACTIONS.map((action, index) => {
                                            // Dynamic overrides for Pin action
                                            let label = action.label;
                                            let icon = action.icon;
                                            let isLoading = false;

                                            if (action.id === "pin" && selectedResult) {
                                                const conv = selectedResult.originalData as Conversation;
                                                label = conv.isPinned ? "Unpin" : "Pin";
                                                icon = <Pin className={cn("w-4 h-4", conv.isPinned && "fill-current")} />;
                                                isLoading = isPinning;
                                            }

                                            return (
                                                <button
                                                    key={action.id}
                                                    onClick={() => handleConversationAction(action.id, selectedResult)}
                                                    onMouseEnter={() => setSubmenuIndex(index)}
                                                    disabled={isLoading}
                                                    className={cn(
                                                        "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors disabled:opacity-70",
                                                        submenuIndex === index
                                                            ? "bg-white/10"
                                                            : "hover:bg-white/5"
                                                    )}
                                                >
                                                    <div className="shrink-0 text-white/60">
                                                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
                                                    </div>
                                                    <span className="flex-1 text-sm text-white">{label}</span>
                                                    {action.shortcut && (
                                                        <kbd className="px-1.5 py-0.5 text-[10px] bg-white/10 text-white/40 rounded font-mono">
                                                            {action.shortcut}
                                                        </kbd>
                                                    )}
                                                </button>
                                            );
                                        })
                                    ) : (
                                        /* Source Actions */
                                        SOURCE_ACTIONS.map((action, index) => {
                                            // Dynamic overrides for Toggle RAG action
                                            let label = action.label;
                                            let icon = action.icon;

                                            if (action.id === "toggle-rag" && selectedResult) {
                                                const source = selectedResult.originalData as SourceItem;
                                                const isAllowed = allowedSourceIds === null || allowedSourceIds.has(String(source.id));
                                                label = isAllowed ? "Disable for RAG" : "Enable for RAG";
                                                icon = isAllowed ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />;
                                            }

                                            return (
                                                <button
                                                    key={action.id}
                                                    onClick={() => handleSourceAction(action.id, selectedResult)}
                                                    onMouseEnter={() => setSubmenuIndex(index)}
                                                    className={cn(
                                                        "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
                                                        submenuIndex === index
                                                            ? "bg-white/10"
                                                            : "hover:bg-white/5"
                                                    )}
                                                >
                                                    <div className="shrink-0 text-white/60">
                                                        {icon}
                                                    </div>
                                                    <span className="flex-1 text-sm text-white">{label}</span>
                                                    {action.shortcut && (
                                                        <kbd className="px-1.5 py-0.5 text-[10px] bg-white/10 text-white/40 rounded font-mono">
                                                            {action.shortcut}
                                                        </kbd>
                                                    )}
                                                </button>
                                            );
                                        })
                                    )}
                                </div>
                            ) : (
                                <div className="py-2">
                                    {filteredResults.map((result, index) => (
                                        <button
                                            key={result.id}
                                            onClick={() => handleSelect(result)}
                                            onMouseEnter={() => setSelectedIndex(index)}
                                            className={cn(
                                                "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
                                                selectedIndex === index
                                                    ? "bg-white/10"
                                                    : "hover:bg-white/5"
                                            )}
                                        >
                                            <div className="shrink-0">{result.icon}</div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm text-white truncate">
                                                    {highlightMatch(result.title, query)}
                                                </p>
                                                {result.subtitle && (
                                                    <p className="text-xs text-white/40 truncate">
                                                        {result.subtitle}
                                                    </p>
                                                )}
                                            </div>
                                            {selectedIndex === index && (
                                                <ChevronRight className="w-4 h-4 text-white/30 shrink-0" />
                                            )}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Footer with keyboard hints */}
                        <div className="flex items-center justify-between px-4 py-2.5 border-t border-white/5 bg-white/[0.02]">
                            <div className="flex items-center gap-4 text-[10px] text-white/30">
                                <span className="flex items-center gap-1">
                                    <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono">↑</kbd>
                                    <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono">↓</kbd>
                                    <span className="ml-1">navigate</span>
                                </span>
                                <span className="flex items-center gap-1">
                                    <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono">↵</kbd>
                                    <span className="ml-1">{showSubmenu ? "confirm" : "actions"}</span>
                                </span>
                                <span className="flex items-center gap-1">
                                    <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono">esc</kbd>
                                    <span className="ml-1">{showSubmenu ? "back" : "close"}</span>
                                </span>
                            </div>
                            <div className="flex items-center gap-1 text-[10px] text-white/30">
                                <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono">
                                    {isMac ? "⌘" : "Ctrl"}
                                </kbd>
                                <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono">K</kbd>
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
