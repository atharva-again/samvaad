"use client";

import React, { useState, useRef, useEffect } from "react";
import {
    Search,
    MessageSquarePlus,
    FolderOpen,
    Pin,
    History,
    ChevronsLeft,
    ChevronsRight,
} from "lucide-react";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { useUIStore } from "@/lib/stores/useUIStore";
import { cn } from "@/lib/utils";
import { ActionTooltip } from "@/components/ui/action-tooltip";
import { motion, AnimatePresence } from "framer-motion";
import { usePlatform } from "@/hooks/usePlatform";
import { createClient } from "@/utils/supabase/client";
import { useRouter } from "next/navigation";

import { useGroupedConversations } from "@/hooks/useGroupedConversations";
import { NavItem } from "./sidebar/NavItem";
import { SectionWithPopover } from "./sidebar/SectionWithPopover";
import { PopoverContent } from "./sidebar/PopoverContent";
import { AccountMenu } from "./sidebar/AccountMenu";
import { ConversationItem } from "./sidebar/ConversationItem";

export function IconNavRail() {
    const router = useRouter();
    const [isExpanded, setIsExpanded] = useState(false);
    const [showAccountMenu, setShowAccountMenu] = useState(false);

    // Account Menu Hover Logic
    const accountTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const handleAccountMouseEnter = () => {
        if (accountTimeoutRef.current) {
            clearTimeout(accountTimeoutRef.current);
            accountTimeoutRef.current = null;
        }
        setShowAccountMenu(true);
    };

    const handleAccountMouseLeave = () => {
        accountTimeoutRef.current = setTimeout(() => {
            setShowAccountMenu(false);
        }, 100);
    };

    const handleLogout = async () => {
        const supabase = createClient();
        await supabase.auth.signOut();
        router.push("/login");
    };

    const {
        conversations,
        currentConversationId,
        loadConversation,
        startNewChat,
        refetchConversations,
        deleteConversation,
        updateConversationTitle,
        togglePinConversation
    } = useConversationStore();
    const { toggleSourcesPanel } = useUIStore();
    const { modifier: altKey, isMac } = usePlatform();
    const metaKey = isMac ? "Cmd" : "Ctrl";

    const [isPinnedMenuOpen, setIsPinnedMenuOpen] = useState(false);
    const [isHistoryMenuOpen, setIsHistoryMenuOpen] = useState(false);

    const accountMenuRef = useRef<HTMLDivElement>(null);
    const accountButtonRef = useRef<HTMLButtonElement>(null);

    // Close account menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (
                accountMenuRef.current &&
                !accountMenuRef.current.contains(e.target as Node) &&
                accountButtonRef.current &&
                !accountButtonRef.current.contains(e.target as Node)
            ) {
                setShowAccountMenu(false);
            }
        };
        if (showAccountMenu) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [showAccountMenu]);

    // Global Keyboard Shortcuts for Sidebar
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // New Chat: Alt + N (Option + N)
            if (e.altKey && (e.key === 'n' || e.key === 'N')) {
                e.preventDefault();
                startNewChat();
            }

            // Toggle Sidebar: Ctrl + / (Cmd + /)
            // Use metaKey for Mac, ctrlKey for Windows/Linux
            const isCmdOrCtrl = isMac ? e.metaKey : e.ctrlKey;
            if (isCmdOrCtrl && e.key === '/') {
                e.preventDefault();
                setIsExpanded(prev => !prev);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [startNewChat, isMac]);

    // Force fetch conversations on mount
    useEffect(() => {
        refetchConversations();
    }, []);

    // ─────────────────────────────────────────────────────────────────────
    // Handlers
    // ─────────────────────────────────────────────────────────────────────
    // Group conversations by date
    const groupedConversations = useGroupedConversations(conversations);

    const pinnedConversations = groupedConversations.pinned;

    const handleSelectConversation = (id: string) => {
        loadConversation(id);
    };

    const handleRenameConversation = (id: string) => {
        const newTitle = prompt('Enter new title:');
        if (newTitle && newTitle.trim()) {
            updateConversationTitle(id, newTitle.trim());
        }
    };

    const handlePinConversation = (id: string) => {
        togglePinConversation(id);
    };

    const handleDeleteConversation = (id: string) => {
        if (confirm('Delete this conversation?')) {
            deleteConversation(id);
        }
    };

    return (
        <div
            className={cn(
                "h-full bg-[#0a0a0a] border-r border-white/5 flex flex-col transition-all duration-300",
                isExpanded ? "w-60" : "w-14"
            )}
        >
            {/* Logo */}
            <div className="h-14 flex items-center justify-center border-b border-white/5 shrink-0">
                <div className={cn(
                    "font-bold text-white tracking-tight transition-all",
                    isExpanded ? "text-lg" : "text-xl"
                )}>
                    {isExpanded ? "Samvaad" : "S"}
                </div>
            </div>

            {/* Navigation */}
            <nav className={cn("flex-1 py-3 px-2", isExpanded ? "overflow-y-auto" : "overflow-visible")}>
                {/* Top Navigation Items */}
                <div className="space-y-1">
                    <NavItem
                        icon={<Search className="w-5 h-5" />}
                        label="Search"
                        shortcut="⌘K"
                        isExpanded={isExpanded}
                        tooltipLabel="Search"
                        tooltipShortcut={`${metaKey} + K`}
                    />
                    <NavItem
                        icon={<MessageSquarePlus className="w-5 h-5" />}
                        label="New Chat"
                        isExpanded={isExpanded}
                        isActive={!currentConversationId}
                        onClick={startNewChat}
                        tooltipLabel="New Chat"
                        tooltipShortcut={`${altKey} + N`}
                    />
                    <NavItem
                        icon={<FolderOpen className="w-5 h-5" />}
                        label="Sources"
                        isExpanded={isExpanded}
                        onClick={toggleSourcesPanel}
                        tooltipLabel="Open Sources"
                        tooltipShortcut={`${altKey} + S`}
                    />
                </div>

                <div className="h-px bg-white/5 my-3" />

                {/* Pinned Section */}
                <SectionWithPopover
                    icon={<Pin className="w-5 h-5" />}
                    label="Pinned"
                    isExpanded={isExpanded}
                    forceOpen={isPinnedMenuOpen}
                    popoverContent={
                        <PopoverContent
                            title="Pinned"
                            conversations={pinnedConversations}
                            onSelect={handleSelectConversation}
                            onRename={handleRenameConversation}
                            onPin={handlePinConversation}
                            onDelete={handleDeleteConversation}
                            onMenuOpenChange={setIsPinnedMenuOpen}
                        />
                    }
                >
                    {pinnedConversations.map(conv => (
                        <ConversationItem
                            key={conv.id}
                            conversation={conv}
                            isActive={currentConversationId === conv.id}
                            onSelect={() => handleSelectConversation(conv.id)}
                            onRename={() => handleRenameConversation(conv.id)}
                            onPin={() => handlePinConversation(conv.id)}
                            onDelete={() => handleDeleteConversation(conv.id)}
                        />
                    ))}
                </SectionWithPopover>

                {/* History Section */}
                <SectionWithPopover
                    icon={<History className="w-5 h-5" />}
                    label="History"
                    isExpanded={isExpanded}
                    forceOpen={isHistoryMenuOpen}
                    popoverContent={
                        <PopoverContent
                            title="History"
                            conversations={groupedConversations}
                            grouped
                            onSelect={handleSelectConversation}
                            onRename={handleRenameConversation}
                            onPin={handlePinConversation}
                            onDelete={handleDeleteConversation}
                            onMenuOpenChange={setIsHistoryMenuOpen}
                        />
                    }
                >
                    {/* Today */}
                    {groupedConversations.today.length > 0 && (
                        <>
                            <div className="pl-11 pr-3 py-1 text-[10px] text-white/30 uppercase">Today</div>
                            {groupedConversations.today.slice(0, 5).map(conv => (
                                <ConversationItem
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={currentConversationId === conv.id}
                                    onSelect={() => handleSelectConversation(conv.id)}
                                    onRename={() => handleRenameConversation(conv.id)}
                                    onPin={() => handlePinConversation(conv.id)}
                                    onDelete={() => handleDeleteConversation(conv.id)}
                                />
                            ))}
                        </>
                    )}
                    {/* Yesterday */}
                    {groupedConversations.yesterday.length > 0 && (
                        <>
                            <div className="pl-11 pr-3 py-1 text-[10px] text-white/30 uppercase mt-2">Yesterday</div>
                            {groupedConversations.yesterday.slice(0, 5).map(conv => (
                                <ConversationItem
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={currentConversationId === conv.id}
                                    onSelect={() => handleSelectConversation(conv.id)}
                                    onRename={() => handleRenameConversation(conv.id)}
                                    onPin={() => handlePinConversation(conv.id)}
                                    onDelete={() => handleDeleteConversation(conv.id)}
                                />
                            ))}
                        </>
                    )}
                    {/* Previous 7 Days */}
                    {groupedConversations.previous7Days.length > 0 && (
                        <>
                            <div className="pl-11 pr-3 py-1 text-[10px] text-white/30 uppercase mt-2">Previous 7 Days</div>
                            {groupedConversations.previous7Days.slice(0, 5).map(conv => (
                                <ConversationItem
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={currentConversationId === conv.id}
                                    onSelect={() => handleSelectConversation(conv.id)}
                                    onRename={() => handleRenameConversation(conv.id)}
                                    onPin={() => handlePinConversation(conv.id)}
                                    onDelete={() => handleDeleteConversation(conv.id)}
                                />
                            ))}
                        </>
                    )}
                    {/* Older */}
                    {groupedConversations.older.length > 0 && (
                        <>
                            <div className="pl-11 pr-3 py-1 text-[10px] text-white/30 uppercase mt-2">Older</div>
                            {groupedConversations.older.slice(0, 5).map(conv => (
                                <ConversationItem
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={currentConversationId === conv.id}
                                    onSelect={() => handleSelectConversation(conv.id)}
                                    onRename={() => handleRenameConversation(conv.id)}
                                    onPin={() => handlePinConversation(conv.id)}
                                    onDelete={() => handleDeleteConversation(conv.id)}
                                />
                            ))}
                        </>
                    )}
                    {/* See all link - only show when more than 10 conversations */}
                    {/* See all link - only show when more than 10 conversations */}
                    {isExpanded && conversations.length > 10 && (
                        <button className="w-full text-left pl-11 pr-3 py-1.5 text-[12px] text-white/40 hover:text-white/60 transition-colors">
                            See all
                        </button>
                    )}
                </SectionWithPopover>
            </nav>

            {/* Bottom Section */}
            <div className="p-2 border-t border-white/5">
                {/* User Avatar with Account Menu */}
                {/* User Avatar with Account Menu */}
                <div
                    className="relative"
                    onMouseEnter={handleAccountMouseEnter}
                    onMouseLeave={handleAccountMouseLeave}
                >
                    <button
                        ref={accountButtonRef}
                        onClick={handleAccountMouseEnter}
                        className={cn(
                            "flex items-center transition-colors hover:bg-white/5 cursor-pointer",
                            isExpanded
                                ? "gap-3 px-3 py-2 rounded-lg w-full"
                                : "justify-center w-10 h-10 rounded-full mx-auto"
                        )}
                    >
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0">
                            <span className="text-white text-xs font-medium">U</span>
                        </div>
                        {isExpanded && (
                            <span className="text-[13px] text-white/70 truncate">My Account</span>
                        )}
                    </button>

                    {/* Account Menu Popover */}
                    <AnimatePresence>
                        {showAccountMenu && (
                            <motion.div
                                ref={accountMenuRef}
                                initial={{ opacity: 0, y: 8, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                                transition={{ duration: 0.12, ease: "easeOut" }}
                                className={cn(
                                    "absolute bottom-full mb-2 z-[100]",
                                    isExpanded ? "left-0 right-0" : "left-0"
                                )}
                            >
                                <div className="bg-[#0F0F0F] border border-white/10 rounded-xl shadow-2xl overflow-hidden">
                                    <AccountMenu
                                        onClose={() => setShowAccountMenu(false)}
                                        onLogout={handleLogout}
                                    />
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Expand/Collapse Toggle */}
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className={cn(
                        "flex items-center justify-center mt-1 text-white/30 hover:text-white/60 transition-colors hover:bg-white/5 relative group cursor-pointer",
                        isExpanded
                            ? "w-full py-2 rounded-lg"
                            : "w-10 h-10 rounded-full mx-auto"
                    )}
                >
                    {isExpanded ? (
                        <ChevronsLeft className="w-4 h-4" />
                    ) : (
                        <ChevronsRight className="w-4 h-4" />
                    )}
                    <ActionTooltip
                        label={isExpanded ? "Collapse Sidebar" : "Open Sidebar"}
                        shortcut={`${metaKey} + /`}
                        side="right"
                    />
                </button>
            </div>
        </div>
    );
}
