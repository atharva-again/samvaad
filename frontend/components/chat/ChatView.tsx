"use client";

import { useRouter } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { uuidv7 } from "uuidv7";
import { InputBar } from "@/components/chat/InputBar";
import { MessageList } from "@/components/chat/MessageList";
import { WelcomeScreen } from "@/components/chat/WelcomeScreen";
import { type ChatMessage, sendMessage } from "@/lib/api";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { useUIStore } from "@/lib/stores/useUIStore";
import { cn } from "@/lib/utils";

interface ChatViewProps {
	conversationId?: string;
}

export function ChatView({ conversationId }: ChatViewProps) {
	const router = useRouter();

	// Conversation store
	const {
		currentConversationId,
		messages: storeMessages,
		isLoadingMessages,
		isStreaming,
		setIsStreaming,
		addMessage,
		addMessageToUI,
		setCurrentConversation,
		clearMessages,
		truncateMessagesAt,
		addConversationOptimistic,
		updateConversationId,
		loadConversation,
	} = useConversationStore();

	// Convert store messages to ChatMessage format - MEMOIZED to prevent scroll triggers
	const messages: ChatMessage[] = React.useMemo(
		() =>
			storeMessages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				timestamp: m.createdAt,
				sources: m.sources,
			})),
		[storeMessages],
	);

	// Swipe Detection for Sources Panel
	const touchStart = useRef<number | null>(null);
	const touchEnd = useRef<number | null>(null);
	// Track voice conversation ID for creating new conversations during voice sessions
	const voiceConversationIdRef = useRef<string | null>(null);
	const {
		setSourcesPanelOpen,
		isSidebarOpen,
		isSourcesPanelOpen,
		setHasInteracted,
		allowedSourceIds,
		mode,
		isVoiceSessionActive,
		activeVoiceConversationId,
	} = useUIStore();

	// Reset to mode switcher ONLY when clicking on a DIFFERENT conversation in sidebar
	// Do NOT reset when:
	// - Current conversation updates its own URL (new conversation created)
	// - Voice session is active
	// - Navigating from home (/) to a new conversation created in this session
	const prevConversationIdRef = useRef<string | undefined>(undefined);
	useEffect(() => {
		const isNavigating = conversationId !== prevConversationIdRef.current;
		const wasOnHomePage = prevConversationIdRef.current === undefined;

		if (isNavigating && conversationId) {
			// Check if this is the current conversation updating its URL (not a sidebar click)
			const storeCurrentId =
				useConversationStore.getState().currentConversationId;
			const isCurrentConversationUrlUpdate = storeCurrentId === conversationId;

			// Skip reset if:
			// 1. This is the current conversation updating its URL after creation
			// 2. Voice session is active
			// 3. Voice conversation matches (voice session created this conversation)
			// 4. Navigating from home page to a new conversation (first message sent)
			const shouldSkipReset =
				isCurrentConversationUrlUpdate ||
				isVoiceSessionActive ||
				activeVoiceConversationId === conversationId ||
				(wasOnHomePage && isCurrentConversationUrlUpdate);

			if (!shouldSkipReset) {
				console.debug(
					"[ChatView] Navigated to different chat, resetting to mode switcher",
				);
				setHasInteracted(false);
				voiceConversationIdRef.current = null;
			}
		}
		prevConversationIdRef.current = conversationId;
	}, [conversationId, setHasInteracted, isVoiceSessionActive, activeVoiceConversationId]);

	// Load conversation from URL param if provided
	// Skip during active voice sessions to prevent duplicate messages
	useEffect(() => {
		if (conversationId && !isVoiceSessionActive) {
			console.debug(
				"[ChatView] loading/syncing conversationId:",
				conversationId,
			);
			loadConversation(conversationId);
		}
	}, [conversationId, loadConversation, isVoiceSessionActive]);

	// When on root page (/), ensure we have a clean slate for new chat
	// IMPORTANT: Only run this cleanup on initial mount, not on every message change
	// Otherwise it creates a race condition that clears voice messages immediately
	const didInitialCleanup = useRef(false);
	useEffect(() => {
		if (!conversationId && !didInitialCleanup.current) {
			// On root page - clear any leftover state for fresh start (only once)
			if (currentConversationId || storeMessages.length > 0) {
				clearMessages();
			}
			didInitialCleanup.current = true;
		}
	}, [
		conversationId,
		clearMessages,
		currentConversationId,
		storeMessages.length,
	]); // Only depend on conversationId, not storeMessages.length

	const handleTouchStart = (e: React.TouchEvent) => {
		touchEnd.current = null;
		touchStart.current = e.targetTouches[0].clientX;
	};

	const handleTouchMove = (e: React.TouchEvent) => {
		touchEnd.current = e.targetTouches[0].clientX;
	};

	const handleTouchEnd = () => {
		if (!touchStart.current || !touchEnd.current) return;
		const distance = touchStart.current - touchEnd.current;
		const isLeftSwipe = distance > 50;

		if (isLeftSwipe) {
			setSourcesPanelOpen(true);
		}

		touchStart.current = null;
		touchEnd.current = null;
	};

	const abortControllerRef = useRef<AbortController | null>(null);

	const handleSendMessage = async (
		text: string,
		persona: string = "default",
		strictMode: boolean = false,
	) => {
		// Generate UUIDv7 for new conversation if this is the first message
		const isNewConversation = !conversationId && !currentConversationId;
		const newConversationId = isNewConversation ? uuidv7() : null;

		// If new conversation, immediately navigate to the new URL and update state
		if (isNewConversation && newConversationId) {
			addConversationOptimistic(
				newConversationId,
				text.slice(0, 50) + (text.length > 50 ? "..." : ""),
			);
			setCurrentConversation(newConversationId);
			// [UX-FIX #41] Use Router for safe navigation
			router.replace(`/chat/${newConversationId}`, { scroll: false });
		}

		// Use the conversation ID from URL, current state, or newly generated
		const activeConversationId =
			conversationId || currentConversationId || newConversationId;

		// Optimistic update - add user message to store + cache (write-through)
		const userMessageId = uuidv7();
		const assistantMessageId = uuidv7(); // Generate assistant ID upfront (#4, #5)

		addMessage(
			{
				id: userMessageId,
				role: "user",
				content: text,
				createdAt: new Date().toISOString(),
			},
			activeConversationId ?? undefined,
		);
		setIsStreaming(true);

		const abortController = new AbortController();
		abortControllerRef.current = abortController;

		try {
			const data = await sendMessage(
				text,
				activeConversationId,
				abortController.signal,
				persona,
				strictMode,
				userMessageId, // Client-generated user message ID
				assistantMessageId, // Client-generated assistant message ID
				allowedSourceIds ? Array.from(allowedSourceIds) : null, // Pass allowed file IDs for RAG filtering
			);

			if (data.success) {
				// For new conversations, update temp ID with real ID from backend if different
				if (
					newConversationId &&
					data.conversation_id &&
					data.conversation_id !== newConversationId
				) {
					// Backend returned a different ID (shouldn't happen with our new logic, but handle gracefully)
					updateConversationId(newConversationId, data.conversation_id);
					router.replace(`/chat/${data.conversation_id}`);
				}

				// Add assistant response with client-generated ID (matches backend)
				addMessage(
					{
						id: assistantMessageId, // Use same ID we sent to backend
						role: "assistant",
						content: data.response,
						sources: data.sources,
						createdAt: new Date().toISOString(),
					},
					activeConversationId ?? undefined,
				);
			} else {
				toast.error(data.error || "Failed to get response");
			}
		} catch (error: unknown) {
			const err = error as { name?: string; code?: string };
			if (err.name === "CanceledError" || err.code === "ERR_CANCELED") {
				console.debug("Request canceled via stop button");
			} else {
				console.error("Error calling text-mode:", error);
				toast.error("Something went wrong. Please try again.");
			}
		} finally {
			setIsStreaming(false);
			abortControllerRef.current = null;
		}
	};

	const handleStop = () => {
		if (abortControllerRef.current) {
			abortControllerRef.current.abort();
			setIsStreaming(false);
		}
	};

	const handleVoiceMessage = async (message: {
		role: "user" | "assistant" | "system";
		content: string;
		sources?: unknown[];
	}) => {
		// Guard: Skip empty messages (prevents blank bubbles from partial TTS events)
		if (!message.content || !message.content.trim()) {
			console.debug("[ChatView] Empty voice message, skipping");
			return;
		}

		const storeState = useConversationStore.getState();
		const activeConversationId =
			conversationId || storeState.currentConversationId;

		const isFirstUserMessage =
			!voiceConversationIdRef.current &&
			message.role === "user" &&
			!activeConversationId;

		let targetConversationId = activeConversationId;
		if (isFirstUserMessage) {
			const title =
				message.content.slice(0, 50) +
				(message.content.length > 50 ? "..." : "");

			const newId = await useConversationStore
				.getState()
				.createConversation(title, "voice");
			targetConversationId = newId;
			voiceConversationIdRef.current = newId;

			if (!conversationId) {
				router.replace(`/chat/${newId}`, { scroll: false });
			}
		} else if (
			!voiceConversationIdRef.current &&
			message.role === "user" &&
			activeConversationId
		) {
			voiceConversationIdRef.current = activeConversationId;

			if (!conversationId) {
				const title =
					message.content.slice(0, 50) +
					(message.content.length > 50 ? "..." : "");
				useConversationStore
					.getState()
					.addConversationOptimistic(activeConversationId, title, "voice");
				router.replace(`/chat/${activeConversationId}`, { scroll: false });
			}
		}

		// Use addMessageToUI (UI-only, no cache) for voice mode
		// Backend saves messages via SamvaadLLMContext, we sync via delta fetch after session ends
		addMessageToUI({
			id: uuidv7(),
			role: message.role,
			content: message.content,
			createdAt: new Date().toISOString(),
			sources: message.sources as Record<string, unknown>[] | undefined,
		});
	};

	const [editMessageContent, setEditMessageContent] = useState<string | null>(
		null,
	);

	const handleEditMessage = (index: number, content: string) => {
		// 1. Truncate messages: remove this message and everything after it
		truncateMessagesAt(index);
		// 2. Set the content in input bar for editing
		setEditMessageContent(content);
	};

	// Calculate the right padding to offset the sidebar and center content in viewport
	// only when the sources panel is closed. If sources panel is open, we just center in remaining space.
	const viewportOffsetClass = !isSourcesPanelOpen
		? isSidebarOpen
			? "md:pr-[240px]"
			: "md:pr-[56px]"
		: "";

	return (
		<div
			className={cn(
				"flex-1 flex flex-col relative min-w-0 overflow-hidden transition-all duration-300",
				viewportOffsetClass,
			)}
			onTouchStart={handleTouchStart}
			onTouchMove={handleTouchMove}
			onTouchEnd={handleTouchEnd}
		>
			{/* Chat Area */}
			<div className="flex-1 flex flex-col overflow-hidden">
				{isLoadingMessages ? (
					/* Skeleton Loader - Pulsating animation */
					<div className="flex-1 flex flex-col items-center justify-center px-4">
						<div className="w-full max-w-2xl space-y-6">
							{/* User message skeleton */}
							<div className="flex justify-end">
								<div className="w-3/4 space-y-2">
									<div className="h-4 bg-white/5 rounded-lg animate-pulse ml-auto w-1/2" />
									<div className="h-16 bg-white/5 rounded-2xl animate-pulse" />
								</div>
							</div>
							{/* Assistant message skeleton */}
							<div className="flex justify-start">
								<div className="w-3/4 space-y-2">
									<div className="h-4 bg-white/5 rounded-lg animate-pulse w-1/3" />
									<div className="h-24 bg-white/5 rounded-2xl animate-pulse" />
									<div className="h-16 bg-white/5 rounded-2xl animate-pulse w-2/3" />
								</div>
							</div>
							{/* User message skeleton */}
							<div className="flex justify-end">
								<div className="w-2/3 space-y-2">
									<div className="h-12 bg-white/5 rounded-2xl animate-pulse" />
								</div>
							</div>
							{/* Assistant message skeleton */}
							<div className="flex justify-start">
								<div className="w-3/4 space-y-2">
									<div className="h-20 bg-white/5 rounded-2xl animate-pulse" />
								</div>
							</div>
						</div>
						<p className="text-white/30 text-sm mt-8 animate-pulse">
							Loading conversation...
						</p>
					</div>
				) : messages.length === 0 ? (
					<WelcomeScreen />
				) : (
					<MessageList
						messages={messages}
						isLoading={isStreaming}
						onEdit={handleEditMessage}
					/>
				)}
				<InputBar
					onSendMessage={handleSendMessage}
					isLoading={isStreaming}
					onStop={handleStop}
					defaultMessage={editMessageContent}
					onMessageConsumed={() => setEditMessageContent(null)}
					onVoiceMessage={handleVoiceMessage}
					conversationId={currentConversationId}
				/>
			</div>
		</div>
	);
}
