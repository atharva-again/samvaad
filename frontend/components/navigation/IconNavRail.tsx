"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
	ChevronsLeft,
	ChevronsRight,
	FolderOpen,
	History,
	MessageSquarePlus,
	Pin,
	Search,
} from "lucide-react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
	DeleteConfirmModal,
	RenameModal,
	SettingsModal,
	UniversalSearchModal,
} from "@/components/modals";
import { ActionTooltip } from "@/components/ui/action-tooltip";
import { useAuth } from "@/contexts/AuthContext";
import { useGroupedConversations } from "@/hooks/useGroupedConversations";
import { usePlatform } from "@/hooks/usePlatform";
import {
	type Conversation,
	useConversationStore,
} from "@/lib/stores/useConversationStore";
import { useInputBarStore } from "@/lib/stores/useInputBarStore";
import { useUIStore } from "@/lib/stores/useUIStore";
import { cn } from "@/lib/utils";
import { createClient } from "@/utils/supabase/client";
import { AccountMenu } from "./sidebar/AccountMenu";
import { ConversationItem } from "./sidebar/ConversationItem";
import { NavItem } from "./sidebar/NavItem";
import { PopoverContent } from "./sidebar/PopoverContent";
import { SectionWithPopover } from "./sidebar/SectionWithPopover";

export function IconNavRail() {
	const router = useRouter();
	const { user, isLoading } = useAuth();
	const {
		isSidebarOpen: isExpanded,
		toggleSidebar: setToggleSidebar,
		isSearchOpen,
	} = useUIStore();
	const [showAccountMenu, setShowAccountMenu] = useState(false);

	// User info from Google auth
	const userAvatar =
		user?.user_metadata?.avatar_url || user?.user_metadata?.picture;
	const userName =
		user?.user_metadata?.full_name || user?.user_metadata?.name || user?.email;
	const userInitial = userName ? userName.charAt(0).toUpperCase() : "U";
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

		// Clear local caches for privacy
		const { conversationCache } = await import("@/lib/cache/conversationCache");
		const { filesCache } = await import("@/lib/cache/filesCache");
		await Promise.all([conversationCache.clear(), filesCache.clear()]);

		// Reset store states
		useConversationStore.setState({
			conversations: [],
			messages: [],
			currentConversationId: null,
			pendingConversationId: null,
			conversationStatus: "idle",
			hasFetchedConversations: false,
		});
		useUIStore.setState({
			sources: [],
			hasFetchedSources: false,
		});
		useInputBarStore.setState({
			hasInteracted: false,
		});

		router.push("/login");
	};

	const {
		conversations,
		currentConversationId,
		isLoadingConversations,
		fetchConversations,
		deleteConversation,
		updateConversationTitle,
		togglePinConversation,
		// Bulk Actions
		isSelectMode,
		selectedIds,
		toggleSelectMode,
		toggleSelection,
		selectAll,
		deselectAll,
		deleteSelectedConversations,
	} = useConversationStore();
	const { toggleSourcesPanel, isSourcesPanelOpen, toggleSearch } = useUIStore();
	const { modifier: altKey, isMac } = usePlatform();
	const metaKey = isMac ? "Cmd" : "Ctrl";

	const [isPinnedMenuOpen, setIsPinnedMenuOpen] = useState(false);
	const [isHistoryMenuOpen, setIsHistoryMenuOpen] = useState(false);

	// Modal states
	const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null);
	const [renameTarget, setRenameTarget] = useState<Conversation | null>(null);
	const [isDeleting, setIsDeleting] = useState(false);
	const [isRenaming, setIsRenaming] = useState(false);
	const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);

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
			document.addEventListener("mousedown", handleClickOutside);
		}
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, [showAccountMenu]);

	// Global Keyboard Shortcuts for Sidebar
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			// New Chat: Alt + N (Option + N)
			if (e.altKey && (e.key === "n" || e.key === "N")) {
				e.preventDefault();
				router.push("/");
			}

			// Toggle Sidebar: Ctrl + / (Cmd + /)
			// Use metaKey for Mac, ctrlKey for Windows/Linux
			const isCmdOrCtrl = isMac ? e.metaKey : e.ctrlKey;
			if (isCmdOrCtrl && e.key === "/") {
				e.preventDefault();
				setToggleSidebar();
			}

			// Universal Search: Cmd/Ctrl + K
			if (isCmdOrCtrl && (e.key === "k" || e.key === "K")) {
				e.preventDefault();
				toggleSearch();
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [isMac, setToggleSidebar, router, toggleSearch]);

	// Fetch conversations on mount (cache-first, then background sync)
	useEffect(() => {
		fetchConversations(); // No forceRefresh = cache-first behavior
	}, [fetchConversations]);

	// ─────────────────────────────────────────────────────────────────────
	// Handlers
	// ─────────────────────────────────────────────────────────────────────
	// Group conversations by date
	const groupedConversations = useGroupedConversations(conversations);

	const pinnedConversations = groupedConversations.pinned;

	const _handleSelectConversation = (id: string) => {
		router.push(`/chat/${id}`);
	};

	const handleRenameConversation = (id: string) => {
		const conv = conversations.find((c) => c.id === id);
		if (conv) setRenameTarget(conv);
	};

	const handlePinConversation = (id: string) => {
		const conv = conversations.find((c) => c.id === id);
		const wasPinned = conv?.isPinned;
		togglePinConversation(id);
		toast.success(wasPinned ? "Unpinned conversation" : "Pinned conversation");
	};

	const handleDeleteConversation = (id: string) => {
		const conv = conversations.find((c) => c.id === id);
		if (conv) setDeleteTarget(conv);
	};

	const confirmDelete = async () => {
		if (!deleteTarget) return;
		const title = deleteTarget.title;
		setIsDeleting(true);
		try {
			await deleteConversation(deleteTarget.id);
			setDeleteTarget(null);
			toast.success(`Deleted "${title}"`);
		} catch {
			toast.error("Failed to delete conversation");
		} finally {
			setIsDeleting(false);
		}
	};

	const confirmRename = async (newName: string) => {
		if (!renameTarget) return;
		setIsRenaming(true);
		try {
			await updateConversationTitle(renameTarget.id, newName);
			setRenameTarget(null);
			toast.success("Conversation renamed");
		} catch {
			toast.error("Failed to rename conversation");
		} finally {
			setIsRenaming(false);
		}
	};

	// Bulk Delete Handlers
	const _handleBulkDelete = async () => {
		if (
			!confirm(
				`Are you sure you want to delete ${selectedIds.size} conversations?`,
			)
		)
			return;
		await deleteSelectedConversations();
	};

	return (
		<div
			className={cn(
				"h-full bg-[#0a0a0a] border-r border-white/5 flex flex-col transition-all duration-300 relative",
				isExpanded ? "w-60" : "w-14",
			)}
		>
			<Link
				href="/"
				className={cn(
					"h-14 border-b border-white/5 shrink-0 flex items-center hover:bg-white/5 transition-colors",
					isExpanded ? "px-5 justify-start" : "justify-center"
				)}
			>
				{isExpanded ? (
					<span className="text-white font-bold text-lg tracking-tight">Samvaad</span>
				) : (
					<span className="text-white font-bold text-xl">S</span>
				)}
			</Link>

			{/* Navigation */}
			<nav
				className={cn(
					"flex-1 py-3 px-2",
					isExpanded ? "overflow-y-auto" : "overflow-visible",
				)}
			>
				{/* Top Navigation Items */}
				<div className="space-y-1">
					<NavItem
						id="walkthrough-search-trigger"
						icon={<Search className="w-5 h-5" />}
						label="Search"
						shortcut="⌘K"
						isExpanded={isExpanded}
						isActive={isSearchOpen}
						onClick={toggleSearch}
						tooltipLabel="Search"
						tooltipShortcut="Mod+K"
					/>
					<NavItem
						id="walkthrough-new-chat"
						icon={<MessageSquarePlus className="w-5 h-5" />}
						label="New Chat"
						isExpanded={isExpanded}
						isActive={
							!currentConversationId && !isSearchOpen && !isSourcesPanelOpen
						}
						onClick={() => {
							router.push("/");
						}}
						tooltipLabel="New Chat"
						tooltipShortcut={`${altKey} + N`}
					/>
					<NavItem
						id="walkthrough-sources-trigger"
						icon={<FolderOpen className="w-5 h-5" />}
						label="Sources"
						isExpanded={isExpanded}
						isActive={isSourcesPanelOpen}
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
							isLoading={isLoadingConversations}
							onRename={handleRenameConversation}
							onPin={handlePinConversation}
							onDelete={handleDeleteConversation}
							onMenuOpenChange={setIsPinnedMenuOpen}
							isSelectMode={isSelectMode}
							selectedIds={selectedIds}
							onToggleSelect={toggleSelection}
						/>
					}
				>
					{isLoadingConversations ? (
						/* Skeleton loaders for expanded sidebar */
						<div className="space-y-1 py-1">
							{[1, 2, 3].map((i) => (
								<div
									key={i}
									className="ml-9 w-[calc(100%-36px)] pl-2 pr-8 py-1.5 rounded-md animate-pulse"
								>
									<div className="h-4 bg-white/10 rounded w-3/4" />
								</div>
							))}
						</div>
					) : (
						pinnedConversations.map((conv) => (
							<ConversationItem
								key={conv.id}
								conversation={conv}
								isActive={currentConversationId === conv.id}
								onRename={() => handleRenameConversation(conv.id)}
								onPin={() => handlePinConversation(conv.id)}
								onDelete={() => handleDeleteConversation(conv.id)}
								isSelectMode={isSelectMode}
								isSelected={selectedIds.has(conv.id)}
								onToggleSelect={() => toggleSelection(conv.id)}
							/>
						))
					)}
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
							isLoading={isLoadingConversations}
							onRename={handleRenameConversation}
							onPin={handlePinConversation}
							onDelete={handleDeleteConversation}
							onMenuOpenChange={setIsHistoryMenuOpen}
							isSelectMode={isSelectMode}
							selectedIds={selectedIds}
							onToggleSelect={toggleSelection}
						/>
					}
				>
					{isLoadingConversations ? (
						/* Skeleton loaders for expanded sidebar */
						<div className="space-y-1 py-1">
							{[1, 2, 3, 4].map((i) => (
								<div
									key={i}
									className="ml-9 w-[calc(100%-36px)] pl-2 pr-8 py-1.5 rounded-md animate-pulse"
								>
									<div className="h-4 bg-white/10 rounded w-3/4" />
								</div>
							))}
						</div>
					) : (
						<>
							{/* Today */}
							{groupedConversations.today.length > 0 && (
								<>
									<div className="pl-11 pr-3 py-1 text-[10px] text-white/30 uppercase">
										Today
									</div>
									{groupedConversations.today.slice(0, 5).map((conv) => (
										<ConversationItem
											key={conv.id}
											conversation={conv}
											isActive={currentConversationId === conv.id}
											onRename={() => handleRenameConversation(conv.id)}
											onPin={() => handlePinConversation(conv.id)}
											onDelete={() => handleDeleteConversation(conv.id)}
											isSelectMode={isSelectMode}
											isSelected={selectedIds.has(conv.id)}
											onToggleSelect={() => toggleSelection(conv.id)}
										/>
									))}
								</>
							)}
							{/* Yesterday */}
							{groupedConversations.yesterday.length > 0 && (
								<>
									<div className="pl-11 pr-3 py-1 text-[10px] text-white/30 uppercase mt-2">
										Yesterday
									</div>
									{groupedConversations.yesterday.slice(0, 5).map((conv) => (
										<ConversationItem
											key={conv.id}
											conversation={conv}
											isActive={currentConversationId === conv.id}
											onRename={() => handleRenameConversation(conv.id)}
											onPin={() => handlePinConversation(conv.id)}
											onDelete={() => handleDeleteConversation(conv.id)}
											isSelectMode={isSelectMode}
											isSelected={selectedIds.has(conv.id)}
											onToggleSelect={() => toggleSelection(conv.id)}
										/>
									))}
								</>
							)}
							{/* Previous 7 Days */}
							{groupedConversations.previous7Days.length > 0 && (
								<>
									<div className="pl-11 pr-3 py-1 text-[10px] text-white/30 uppercase mt-2">
										Previous 7 Days
									</div>
									{groupedConversations.previous7Days
										.slice(0, 5)
										.map((conv) => (
											<ConversationItem
												key={conv.id}
												conversation={conv}
												isActive={currentConversationId === conv.id}
												onRename={() => handleRenameConversation(conv.id)}
												onPin={() => handlePinConversation(conv.id)}
												onDelete={() => handleDeleteConversation(conv.id)}
												isSelectMode={isSelectMode}
												isSelected={selectedIds.has(conv.id)}
												onToggleSelect={() => toggleSelection(conv.id)}
											/>
										))}
								</>
							)}
							{/* Monthly groups (older conversations) */}
							{Object.entries(groupedConversations.months)
								.sort(([a], [b]) => {
									// Sort by date descending (most recent month first)
									const parseMonth = (key: string) => {
										const [month, year] = key.split(" ");
										const monthIndex = [
											"January",
											"February",
											"March",
											"April",
											"May",
											"June",
											"July",
											"August",
											"September",
											"October",
											"November",
											"December",
										].indexOf(month);
										return new Date(parseInt(year, 10), monthIndex).getTime();
									};
									return parseMonth(b) - parseMonth(a);
								})
								.map(
									([monthKey, convs]) =>
										convs.length > 0 && (
											<React.Fragment key={monthKey}>
												<div className="pl-11 pr-3 py-1 text-[10px] text-white/30 uppercase mt-2">
													{monthKey}
												</div>
												{convs.slice(0, 5).map((conv) => (
													<ConversationItem
														key={conv.id}
														conversation={conv}
														isActive={currentConversationId === conv.id}
														onRename={() => handleRenameConversation(conv.id)}
														onPin={() => handlePinConversation(conv.id)}
														onDelete={() => handleDeleteConversation(conv.id)}
														isSelectMode={isSelectMode}
														isSelected={selectedIds.has(conv.id)}
														onToggleSelect={() => toggleSelection(conv.id)}
													/>
												))}
											</React.Fragment>
										),
								)}
							{/* See all link - only show when more than 10 conversations */}
							{isExpanded && conversations.length > 10 && (
								<button className="w-full text-left pl-11 pr-3 py-1.5 text-[12px] text-white/40 hover:text-white/60 transition-colors" type="button">
									See all
								</button>
							)}
						</>
					)}
				</SectionWithPopover>
			</nav>

			{/* Bottom Section */}
			<div className="p-2 border-t border-white/5">
				{/* User Avatar with Account Menu */}
				{/* User Avatar with Account Menu */}
				<div
					className="relative"
				>
					<button
						ref={accountButtonRef}
						onClick={handleAccountMouseEnter}
						onMouseEnter={handleAccountMouseEnter}
						onMouseLeave={handleAccountMouseLeave}
						className={cn(
							"flex items-center transition-colors hover:bg-white/5 cursor-pointer",
							isExpanded
								? "gap-3 px-3 py-2 rounded-lg w-full"
								: "justify-center w-10 h-10 rounded-full mx-auto",
						)}
						type="button"
					>
						{isLoading ? (
							<>
								<div className="w-7 h-7 rounded-full bg-white/10 animate-pulse shrink-0" />
								{isExpanded && (
									<div className="w-20 h-4 bg-white/10 rounded animate-pulse" />
								)}
							</>
						) : (
							<>
								{userAvatar ? (
									<Image
										src={userAvatar}
										alt="Profile"
										width={28}
										height={28}
										className="w-7 h-7 rounded-full object-cover shrink-0"
										referrerPolicy="no-referrer"
									/>
								) : (
									<div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0">
										<span className="text-white text-xs font-medium">
											{userInitial}
										</span>
									</div>
								)}
								{isExpanded && (
									<span className="text-[13px] text-white/70 truncate">
										{userName || "My Account"}
									</span>
								)}
							</>
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
								onMouseEnter={handleAccountMouseEnter}
								onMouseLeave={handleAccountMouseLeave}
								className={cn(
									"absolute bottom-full mb-2 z-[100]",
									isExpanded ? "left-0 right-0" : "left-0",
								)}
							>
								<div className="bg-[#0F0F0F] border border-white/10 rounded-xl shadow-2xl overflow-hidden">
									<AccountMenu
										onClose={() => setShowAccountMenu(false)}
										onLogout={handleLogout}
										onSettingsOpen={() => setIsSettingsModalOpen(true)}
									/>
								</div>
							</motion.div>
						)}
					</AnimatePresence>
				</div>

				{/* Expand/Collapse Toggle */}
				<button
					onClick={() => setToggleSidebar()}
					className={cn(
						"flex items-center justify-center mt-1 text-white/30 hover:text-white/60 transition-colors hover:bg-white/5 relative group cursor-pointer",
						isExpanded
							? "w-full py-2 rounded-lg"
							: "w-10 h-10 rounded-full mx-auto",
					)}
					type="button"
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

			{/* Modals */}
			<DeleteConfirmModal
				isOpen={!!deleteTarget}
				onClose={() => setDeleteTarget(null)}
				onConfirm={confirmDelete}
				isDeleting={isDeleting}
				itemName={deleteTarget?.title}
			/>
			<RenameModal
				isOpen={!!renameTarget}
				onClose={() => setRenameTarget(null)}
				onConfirm={confirmRename}
				isRenaming={isRenaming}
				currentName={renameTarget?.title || ""}
			/>
			<UniversalSearchModal />
			<SettingsModal
				isOpen={isSettingsModalOpen}
				onClose={() => setIsSettingsModalOpen(false)}
			/>
		</div>
	);
}
