import { toast } from "sonner";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";
import { conversationCache } from "@/lib/cache/conversationCache";
import { isValidUUID, sanitizeInput } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────

export interface Message {
	id: string;
	role: "user" | "assistant" | "system";
	content: string;
	sources?: Record<string, unknown>[];
	createdAt: string;
}

export interface Conversation {
	id: string;
	title: string;
	mode: "text" | "voice";
	createdAt: string;
	updatedAt: string | null;
	isPinned: boolean;
	messageCount: number;
}

export interface ConversationDetail extends Conversation {
	summary: string | null;
	messages: Message[];
}

// Backend snake_case response types (used for API responses)
interface BackendConversation {
	id: string;
	title: string;
	mode: string;
	created_at: string;
	updated_at: string | null;
	is_pinned: boolean;
	message_count: number;
}

interface BackendMessage {
	id: string;
	role: string;
	content: string;
	sources: Record<string, unknown>[];
	created_at: string;
}

interface BackendConversationDetail {
	id: string;
	title: string;
	summary: string | null;
	created_at: string;
	updated_at: string | null;
	messages: BackendMessage[];
}

// ─────────────────────────────────────────────────────────────────────
// Transform Helpers (snake_case → camelCase)
// ─────────────────────────────────────────────────────────────────────

const transformConversation = (conv: BackendConversation): Conversation => ({
	id: conv.id,
	title: conv.title,
	mode: conv.mode as "text" | "voice",
	createdAt: conv.created_at,
	updatedAt: conv.updated_at,
	isPinned: conv.is_pinned,
	messageCount: conv.message_count,
});

const transformMessage = (msg: BackendMessage): Message => ({
	id: msg.id,
	role: msg.role as "user" | "assistant" | "system",
	content: msg.content,
	sources: msg.sources || [],
	createdAt: msg.created_at,
});

// ─────────────────────────────────────────────────────────────────────
// Store State
// ─────────────────────────────────────────────────────────────────────

interface ConversationState {
	// Current conversation
	currentConversationId: string | null;
	messages: Message[];
	isLoadingMessages: boolean;
	isStreaming: boolean; // LLM response streaming in progress
	userId: string | null; // [SECURITY-FIX #01] Store current userId for checking isolation

	// Conversation list
	conversations: Conversation[];
	isLoadingConversations: boolean;
	hasFetchedConversations: boolean;

	// Actions - Local State
	setCurrentConversation: (id: string | null) => void;
	setIsStreaming: (isStreaming: boolean) => void; // Set streaming state
	addMessage: (message: Message, conversationId?: string) => void;
	addMessageToUI: (message: Message) => void; // UI-only, no cache (for voice mode)
	updateMessage: (id: string, updates: Partial<Message>) => void;
	clearMessages: () => void;
	truncateMessagesAt: (index: number) => void;

	// Actions - API
	fetchConversations: (forceRefresh?: boolean) => Promise<void>;
	createConversation: (
		title?: string,
		mode?: "text" | "voice",
	) => Promise<string>;
	loadConversation: (id: string) => Promise<void>;
	deleteConversation: (id: string) => Promise<void>;
	updateConversationTitle: (id: string, title: string) => Promise<void>;
	togglePinConversation: (id: string) => Promise<void>;

	// New Chat
	startNewChat: () => void;
	addConversationOptimistic: (
		id: string,
		title: string,
		mode?: "text" | "voice",
	) => void;
	updateConversationId: (tempId: string, realId: string) => void;
	setUserId: (userId: string | null) => void; // Action to set user
	migratingIds: Set<string>; // [SECURITY-FIX #02] Track actively migrating IDs to prevent race
	reloadFromBackend: (id: string) => Promise<void>; // Full reload, no delta sync (for voice mode)

	// Bulk Actions
	isSelectMode: boolean;
	selectedIds: Set<string>;
	toggleSelectMode: () => void;
	toggleSelection: (id: string) => void;
	selectAll: () => void;
	deselectAll: () => void;
	deleteSelectedConversations: () => Promise<void>;
}

// ─────────────────────────────────────────────────────────────────────
// Store Implementation
// ─────────────────────────────────────────────────────────────────────

export const useConversationStore = create<ConversationState>()(
	persist(
		(set, get) => ({
			// Initial State
			currentConversationId: null,
			messages: [],
			isLoadingMessages: false,
			isStreaming: false,
			userId: null,
			migratingIds: new Set(),
			conversations: [],
			isLoadingConversations: false,
			hasFetchedConversations: false,

			isSelectMode: false,
			selectedIds: new Set(),

			// ─────────────────────────────────────────────────────────────
			// Local State Actions
			// ─────────────────────────────────────────────────────────────

			setCurrentConversation: (id) => set({ currentConversationId: id }),
			setIsStreaming: (isStreaming) => set({ isStreaming }),
			setUserId: (userId) => set({ userId }),

			// UI-only message add (no cache write) - for voice mode
			// Backend saves messages with auto IDs, so we skip local cache to avoid ID mismatch
			addMessageToUI: (message) => {
				// Skip empty messages
				if (!message.content || !message.content.trim()) {
					console.debug("[Store] Empty message, skipping");
					return;
				}

				const state = get();

				// Skip if a message with same role and content already exists (prevent duplicates)
				// Check last 5 messages to avoid expensive full scan
				const recentMessages = state.messages.slice(-5);
				const isDuplicate = recentMessages.some(
					(m) =>
						m.role === message.role && m.content.trim() === message.content.trim(),
				);
				if (isDuplicate) {
					console.debug(
						"[Store] Duplicate message detected, skipping:",
						message.content.slice(0, 50),
					);
					return;
				}

				const safeContent = sanitizeInput(message.content);
				const safeMessage = { ...message, content: safeContent };
				set((state) => ({ messages: [...state.messages, safeMessage] }));
			},

			addMessage: async (message, explicitConversationId) => {
				const state = get();
				if (!state.userId) return; // Cannot save without user

				// Update UI state immediately
				// [SECURITY-FIX] Sanitize optimistic updates to prevent XSS
				const safeContent = sanitizeInput(message.content);
				const safeMessage = { ...message, content: safeContent };

				set({ messages: [...state.messages, safeMessage] });

				// Write-through to cache (fire and forget for responsiveness)
				// Use explicit ID if provided, otherwise fall back to state
				const conversationId =
					explicitConversationId || state.currentConversationId;
				if (conversationId) {
					// [SECURITY-FIX #38] Await critical storage operations to prevent data loss
					// Although we return void to UI, we catch errors here.
					try {
						await conversationCache.saveMessage(conversationId, {
							id: message.id,
							userId: state.userId, // [SECURITY-FIX #01]
							conversationId,
							role: message.role,
							content: message.content,
							sources: message.sources,
							createdAt: message.createdAt,
						});
					} catch (err) {
						console.error("[Cache] Failed to save message:", err);
						// Potential rollback or toast here?
					}
				}
			},

			updateMessage: (id, updates) =>
				set((state) => ({
					messages: state.messages.map((msg) =>
						msg.id === id ? { ...msg, ...updates } : msg,
					),
				})),

			clearMessages: () => set({ messages: [], currentConversationId: null }),

			truncateMessagesAt: (index) => {
				const state = get();
				// [RESILIENCE-FIX] Rollback support
				const previousMessages = state.messages;

				const newMessages = state.messages.slice(0, index);
				const keepMessageIds = newMessages.map((m) => m.id);

				// Update UI state immediately
				set({ messages: newMessages });

				// Sync with cache in background
				if (state.currentConversationId) {
					conversationCache
						.truncateMessages(state.currentConversationId, keepMessageIds)
						.catch((err) => console.warn("[Cache] Failed to truncate:", err));

					// Sync with backend (fire and forget for responsiveness)
					api
						.delete(`/conversations/${state.currentConversationId}/messages`, {
							data: { keep_message_ids: keepMessageIds },
						})
						.then(() => {
							console.log("[Store] Backend messages truncated");
						})
						.catch((err) => {
							console.warn("[Store] Failed to truncate backend messages:", err);
							// [RESILIENCE-FIX] Rollback UI on backend failure
							set({ messages: previousMessages });
							toast.error("Failed to delete messages. Restoring state...");
						});
				}
			},

			startNewChat: () => {
				set({
					currentConversationId: null,
					messages: [],
				});
			},

			addConversationOptimistic: (id, title, mode = "text") => {
				// Check if conversation already exists (prevent duplicates)
				const state = get();
				if (state.conversations.some((c) => c.id === id)) {
					console.debug(
						"[Store] Conversation already exists, skipping optimistic add:",
						id,
					);
					return;
				}

				// Instantly add a new conversation to the top of the list (optimistic update)
				const newConversation: Conversation = {
					id,
					title,
					mode,
					createdAt: new Date().toISOString(),
					updatedAt: new Date().toISOString(),
					isPinned: false,
					messageCount: 0,
				};
				set((state) => ({
					conversations: [newConversation, ...state.conversations],
				}));

				// Sync with cache
				// Sync with cache
				const userId = get().userId;
				if (userId) {
					conversationCache
						.upsertConversation({
							id: newConversation.id,
							userId, // [SECURITY-FIX #01]
							title: newConversation.title,
							mode: newConversation.mode,
							isPinned: newConversation.isPinned,
							createdAt: newConversation.createdAt,
							updatedAt: newConversation.updatedAt || newConversation.createdAt,
						})
						.catch((err) =>
							console.warn("[Store] Failed to cache optimistic conv:", err),
						);
				}
			},

			updateConversationId: (tempId: string, realId: string) => {
				// Replace temp ID with real ID from backend
				set((state) => ({
					conversations: state.conversations.map((c) =>
						c.id === tempId ? { ...c, id: realId } : c,
					),
					currentConversationId:
						state.currentConversationId === tempId
							? realId
							: state.currentConversationId,
				}));

				// Sync with cache
				// Sync with cache
				// [SECURITY-FIX #02] Prevent race condition in migrations
				if (get().migratingIds.has(tempId)) return;

				set((s) => ({ migratingIds: new Set(s.migratingIds).add(tempId) }));

				conversationCache
					.migrateId(tempId, realId)
					.then(() => {
						set((s) => {
							const newSet = new Set(s.migratingIds);
							newSet.delete(tempId);
							return { migratingIds: newSet };
						});
					})
					.catch((err) =>
						console.warn("[Store] Failed to migrate cache ID:", err),
					);
			},

			// ─────────────────────────────────────────────────────────────
			// Bulk Actions
			// ─────────────────────────────────────────────────────────────

			toggleSelectMode: () =>
				set((state) => ({
					isSelectMode: !state.isSelectMode,
					selectedIds: new Set(), // Clear selection when toggling
				})),

			toggleSelection: (id) =>
				set((state) => {
					const newSelected = new Set(state.selectedIds);
					if (newSelected.has(id)) {
						newSelected.delete(id);
					} else {
						newSelected.add(id);
					}
					return { selectedIds: newSelected };
				}),

			selectAll: () =>
				set((state) => ({
					selectedIds: new Set(state.conversations.map((c) => c.id)),
				})),

			deselectAll: () => set({ selectedIds: new Set() }),

			deleteSelectedConversations: async () => {
				const { selectedIds, conversations } = get();
				if (selectedIds.size === 0) return;

				const idsToDelete = Array.from(selectedIds);
				const previousConversations = conversations;

				// Optimistic Update
				set((state) => ({
					conversations: state.conversations.filter(
						(c) => !selectedIds.has(c.id),
					),
					selectedIds: new Set(),
					isSelectMode: false, // Exit select mode after delete
					currentConversationId:
						state.currentConversationId &&
						selectedIds.has(state.currentConversationId)
							? null
							: state.currentConversationId,
				}));

				// Cache Update
				conversationCache
					.deleteMultiple(idsToDelete)
					.catch((err) =>
						console.warn("[Store] Failed to bulk delete from cache:", err),
					);

				try {
					await api.delete("/conversations/batch", {
						data: idsToDelete,
					});
					toast.success(`Deleted ${idsToDelete.length} conversations`);
				} catch (error) {
					console.error("Failed to bulk delete:", error);
					toast.error("Failed to delete conversations");
					// Rollback
					set({ conversations: previousConversations });
				}
			},

			// ─────────────────────────────────────────────────────────────
			// API Actions
			// ─────────────────────────────────────────────────────────────

			fetchConversations: async (forceRefresh = false) => {
				// Prevent duplicate fetches unless force refresh
				if (get().isLoadingConversations) return;
				if (!forceRefresh && get().hasFetchedConversations) return;

				set({ isLoadingConversations: true });

				// Helper to save conversations to cache
				// Helper to save conversations to cache and remove orphans
				// Helper to save conversations to cache
				const saveToCache = async (data: BackendConversation[]) => {
					const currentUserId = get().userId;
					if (!currentUserId) return;

					// 1. Save fresh data
					for (const conv of data) {
						await conversationCache
							.upsertConversation({
								id: conv.id,
								userId: currentUserId,
								title: conv.title,
								mode: conv.mode as "text" | "voice",
								isPinned: conv.is_pinned,
								createdAt: conv.created_at,
								updatedAt: conv.updated_at || conv.created_at,
							})
							.catch(() => {
								/* ignore */
							});
					}

					// 2. Identify and remove orphans (cached items not in current server response)
					const serverIds = new Set(data.map((c) => c.id));
					// conversationCache.getAll(userId) fetches only for this user
					const userCached = await conversationCache.getAll(currentUserId);
					const orphans = userCached
						.filter((c) => !serverIds.has(c.id))
						.map((c) => c.id);

					if (orphans.length > 0) {
						console.log("[Cache] Evicting orphans:", orphans.length);
						await conversationCache.deleteMultiple(orphans);
					}
				};

				try {
					// 1. Cache-first: Load from IndexedDB instantly (skip if force refresh)
					const currentUserId = get().userId;
					if (!forceRefresh && currentUserId) {
						const cached = await conversationCache.getAll(currentUserId);
						if (cached.length > 0) {
							console.log(
								"[Cache] HIT - Showing cached conversations:",
								cached.length,
							);
							// Transform cached to Conversation format
							const cachedConversations: Conversation[] = cached.map((c) => ({
								id: c.id,
								title: c.title,
								mode: c.mode || "text",
								createdAt: c.createdAt,
								updatedAt: c.updatedAt,
								isPinned: c.isPinned,
								messageCount: 0, // Not stored in cache
							}));
							set({
								conversations: cachedConversations,
								isLoadingConversations: false,
								hasFetchedConversations: true,
							});

							// 2. Background sync: Fetch fresh data from backend
							api
								.get<BackendConversation[]>("/conversations/")
								.then((response) => {
									const conversations = response.data.map(
										transformConversation,
									);
									console.log(
										"[Cache] Background sync complete:",
										conversations.length,
									);
									set({ conversations });
									saveToCache(response.data);
								})
								.catch((err) =>
									console.warn("[Cache] Background sync failed:", err),
								);

							return;
						}
					}

					// 3. Cache miss or force refresh: Fetch from server
					console.log("[Cache] MISS - Fetching from server...");
					const response =
						await api.get<BackendConversation[]>("/conversations/");
					const conversations = response.data.map(transformConversation);

					set({
						conversations,
						isLoadingConversations: false,
						hasFetchedConversations: true,
					});

					// Save to cache for next time
					saveToCache(response.data);
				} catch (error) {
					console.error("Failed to fetch conversations:", error);
					set({ isLoadingConversations: false, hasFetchedConversations: true });
				}
			},

			createConversation: async (title = "New Conversation", mode = "text") => {
				try {
					const response = await api.post<{
						id: string;
						title: string;
						created_at: string;
						updated_at: string;
					}>("/conversations", {
						title,
						mode,
					});
					const newConversation = {
						id: response.data.id,
						title: response.data.title,
						isPinned: false,
						createdAt: response.data.created_at,
						updatedAt: response.data.updated_at,
						mode: mode || "text",
						messageCount: 0,
					};

					set((state) => ({
						conversations: [newConversation, ...state.conversations],
						currentConversationId: newConversation.id,
						messages: [],
					}));

					return newConversation.id;
				} catch (error) {
					console.error("Failed to create conversation:", error);
					throw error;
				}
			},

			loadConversation: async (id) => {
				// [SECURITY-FIX] Validate ID format
				if (!isValidUUID(id)) {
					console.error("Invalid conversation ID format");
					toast.error("Invalid conversation ID");
					return;
				}

				const state = get();
				if (state.isLoadingMessages) return;

				// If already loaded, we only do a background delta sync
				const isAlreadyLoaded =
					state.currentConversationId === id && state.messages.length > 0;

				if (!isAlreadyLoaded) {
					set({ isLoadingMessages: true });
				}

				try {
					// 1. Check cache first (only if not already loaded in memory)
					let lastSyncedAt = "1970-01-01T00:00:00.000Z";
					if (!isAlreadyLoaded) {
						const currentUserId = get().userId;
						// [SECURITY-FIX #01] Require userId for cache access
						const cached = currentUserId
							? await conversationCache.get(id, currentUserId)
							: null;
						if (cached) {
							console.log("[Cache] HIT - Showing cached data instantly");
							lastSyncedAt = cached.conversation.cachedAt;
							set({
								currentConversationId: id,
								messages: cached.messages.map((m) => ({
									id: m.id,
									role: m.role,
									content: m.content,
									sources: m.sources,
									createdAt: m.createdAt,
								})),
								isLoadingMessages: false,
							});
						}
					} else {
						// Already in memory, find the last sync time from cache meta
						const meta = await conversationCache.getMeta(id);
						if (meta) lastSyncedAt = meta.cachedAt;
					}

					// 2. Sync with backend (always do this to get fresh messages)
					try {
						console.log("[Cache] Syncing delta since:", lastSyncedAt);
						const deltaResponse = await api.get<BackendMessage[]>(
							`/conversations/${id}/messages`,
							{ params: { after: lastSyncedAt } },
						);

						if (deltaResponse.data.length > 0) {
							const newUIMessages = deltaResponse.data.map(transformMessage);
							const currentUserId = get().userId;
							if (currentUserId) {
								const newCacheMessages = deltaResponse.data.map((msg) => ({
									...transformMessage(msg),
									conversationId: id,
									userId: currentUserId,
								}));
								await conversationCache.appendMessages(id, newCacheMessages);
							}

							set((state) => {
								const existingIds = new Set(state.messages.map((m) => m.id));
								const uniqueNewMessages = newUIMessages.filter(
									(m) => !existingIds.has(m.id),
								);
								return {
									messages: [...state.messages, ...uniqueNewMessages],
								};
							});
						}
					} catch (deltaError) {
						console.debug("[Cache] Background sync failed:", deltaError);
					}

					// 3. Fallback for cache miss (+ full load)
					if (!isAlreadyLoaded && !get().messages.length) {
						console.log("[Cache] MISS - Full fetch from server...");
						const response = await api.get<BackendConversationDetail>(
							`/conversations/${id}`,
						);
						const detail = response.data;
						const currentUserId = get().userId;

						if (currentUserId) {
							const cms = detail.messages.map((m) => ({
								...transformMessage(m),
								conversationId: id,
								userId: currentUserId,
							}));
							await conversationCache.save(
								{
									id: detail.id,
									title: detail.title,
									summary: detail.summary || undefined,
									userId: currentUserId,
									isPinned: false,
									createdAt: detail.created_at,
									updatedAt: detail.updated_at || detail.created_at,
								},
								cms,
							);
						}

						set({
							currentConversationId: id,
							messages: detail.messages.map(transformMessage),
							isLoadingMessages: false,
						});
					}
				} catch (error) {
					console.error("Failed to load/sync conversation:", error);
				} finally {
					set({ isLoadingMessages: false });
				}
			},

			reloadFromBackend: async (id) => {
				if (!isValidUUID(id)) {
					console.error("Invalid conversation ID format");
					return;
				}

				set({ messages: [], isLoadingMessages: true });

				try {
					const response = await api.get<BackendConversationDetail>(`/conversations/${id}`);
					const detail = response.data;
					const currentUserId = get().userId;

					if (currentUserId) {
						const cms = detail.messages.map((m) => ({
							...transformMessage(m),
							conversationId: id,
							userId: currentUserId,
						}));
						await conversationCache.save(
							{
								id: detail.id,
								title: detail.title,
								summary: detail.summary || undefined,
								userId: currentUserId,
								isPinned: false,
								createdAt: detail.created_at,
								updatedAt: detail.updated_at || detail.created_at,
							},
							cms,
						);
					}

					set({
						currentConversationId: id,
						messages: detail.messages.map(transformMessage),
						isLoadingMessages: false,
					});
					console.debug("[Store] Full reload from backend completed:", id);
				} catch (error) {
					console.error("Failed to reload conversation:", error);
					set({ isLoadingMessages: false });
				}
			},

			deleteConversation: async (id) => {
				// Optimistic update - remove from UI immediately
				const { currentConversationId, conversations } = get();
				const previousConversations = conversations;

				set((state) => ({
					conversations: state.conversations.filter((c) => c.id !== id),
					currentConversationId:
						currentConversationId === id ? null : currentConversationId,
					messages: currentConversationId === id ? [] : state.messages,
				}));

				// Sync with cache
				conversationCache
					.delete(id)
					.catch((err) =>
						console.warn("[Store] Failed to delete from cache:", err),
					);

				try {
					await api.delete(`/conversations/${id}`);
				} catch (error) {
					// Rollback on error
					console.error("Failed to delete conversation:", error);
					set({ conversations: previousConversations });
					throw error;
				}
			},

			updateConversationTitle: async (id, title) => {
				// Optimistic update - change title immediately
				const previousConversations = get().conversations;

				set((state) => ({
					conversations: state.conversations.map((c) =>
						c.id === id ? { ...c, title } : c,
					),
				}));

				// Sync with cache
				conversationCache
					.updateConversation(id, { title })
					.catch((err) =>
						console.warn("[Store] Failed to update title in cache:", err),
					);

				try {
					await api.patch(`/conversations/${id}`, { title });
				} catch (error) {
					// Rollback on error
					console.error("Failed to update conversation title:", error);
					set({ conversations: previousConversations });
					throw error;
				}
			},

			togglePinConversation: async (id) => {
				const conversation = get().conversations.find((c) => c.id === id);
				if (!conversation) return;

				const newPinnedParam = !conversation.isPinned;
				const previousConversations = get().conversations;

				// Optimistic update - toggle pin and re-sort immediately
				set((state) => {
					const updatedConversations = state.conversations.map((c) =>
						c.id === id ? { ...c, isPinned: newPinnedParam } : c,
					);

					// Sort: Pinned first, then by date
					const sortedConversations = [...updatedConversations].sort((a, b) => {
						if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1;
						return (
							new Date(b.updatedAt || b.createdAt).getTime() -
							new Date(a.updatedAt || a.createdAt).getTime()
						);
					});

					return { conversations: sortedConversations };
				});

				// Sync with cache
				conversationCache
					.updateConversation(id, { isPinned: newPinnedParam })
					.catch((err) =>
						console.warn("[Store] Failed to update cache pin:", err),
					);

				try {
					await api.patch(`/conversations/${id}`, {
						is_pinned: newPinnedParam,
					});
				} catch (error) {
					// Rollback on error
					console.error("Failed to toggle pin:", error);
					set({ conversations: previousConversations });
					throw error;
				}
			},
		}),
		{
			name: "samvaad-conversations",
			// NO persistence of currentConversationId - rely on URL
			partialize: (_state) => ({}),
		},
	),
);
