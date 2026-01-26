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
import { useInputBarStore } from "@/lib/stores/useInputBarStore";
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
		truncateMessagesAt,
		loadConversation,
		activateConversation,
		updateConversationTitle,
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
	const {
		setSourcesPanelOpen,
		isSidebarOpen,
		isSourcesPanelOpen,
		allowedSourceIds,
		isVoiceSessionActive,
	} = useUIStore();
	const { setHasInteracted } = useInputBarStore();

	const prevConversationIdRef = useRef<string | undefined>(undefined);
	useEffect(() => {
		const previousId = prevConversationIdRef.current;
		if (conversationId && previousId && conversationId !== previousId && !isVoiceSessionActive) {
			setHasInteracted(false);
		}
		prevConversationIdRef.current = conversationId;
	}, [conversationId, setHasInteracted, isVoiceSessionActive]);

	// Load conversation from URL param if provided
	// Skip during active voice sessions to prevent duplicate messages
	useEffect(() => {
		if (conversationId && !isVoiceSessionActive) {
			const isInitialLoad = !storeMessages.length || currentConversationId !== conversationId;
			if (isInitialLoad) {
				console.debug(
					"[ChatView] loading/syncing conversationId:",
					conversationId,
				);
				loadConversation(conversationId);
			}
		}
	}, [conversationId, loadConversation, isVoiceSessionActive, currentConversationId, storeMessages.length]);

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
		let activeConversationId = conversationId || currentConversationId;
		if (!activeConversationId) {
			try {
				const title = text.slice(0, 50) + (text.length > 50 ? "..." : "");
				activeConversationId = await activateConversation({
					mode: "text",
					title,
				});
				router.replace(`/chat/${activeConversationId}`, { scroll: false });
			} catch (err) {
				console.error("[ChatView] Failed to activate conversation:", err);
				toast.error("Failed to start a new conversation");
				return;
			}
		}

		if (currentConversationId !== activeConversationId) {
			setCurrentConversation(activeConversationId);
		}

		const controller = new AbortController();
		abortControllerRef.current = controller;

		const userMessageId = uuidv7();
		const assistantMessageId = uuidv7();

		addMessage(
			{
				id: userMessageId,
				role: "user",
				content: text,
				createdAt: new Date().toISOString(),
			},
			activeConversationId,
		);

		setIsStreaming(true);

		try {
			const data = await sendMessage(
				text,
				activeConversationId,
				controller.signal,
				persona,
				strictMode,
				userMessageId, // Client-generated user message ID
				assistantMessageId, // Client-generated assistant message ID
				allowedSourceIds ? Array.from(allowedSourceIds) : null, // Pass allowed file IDs for RAG filtering
			);

			if (data.success) {
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
		let activeConversationId = conversationId || currentConversationId;
		if (!activeConversationId && message.role === "user") {
			const title =
				message.content.slice(0, 50) +
				(message.content.length > 50 ? "..." : "");
			try {
				activeConversationId = await activateConversation({
					mode: "voice",
					title,
				});
				await updateConversationTitle(activeConversationId, title);
				router.replace(`/chat/${activeConversationId}`, { scroll: false });
			} catch (error) {
				console.error("[ChatView] Failed to activate voice conversation:", error);
				toast.error("Failed to start voice conversation");
			}
		}

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
				conversationId={conversationId || currentConversationId}
			/>
			</div>
		</div>
	);
}
