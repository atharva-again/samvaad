"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { uuidv7 } from "uuidv7";
import { MessageList } from "@/components/chat/MessageList";
import { InputBar } from "@/components/chat/InputBar";
import { WelcomeScreen } from "@/components/chat/WelcomeScreen";

import { ChatMessage, sendMessage } from "@/lib/api";
import { toast } from "sonner";

import { useUIStore } from "@/lib/stores/useUIStore";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { cn } from "@/lib/utils";

interface ChatViewProps {
    conversationId?: string;
}

export function ChatView({ conversationId }: ChatViewProps) {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    // Conversation store
    const {
        currentConversationId,
        messages: storeMessages,
        isLoadingMessages,
        addMessage,
        setCurrentConversation,
        clearMessages,
        truncateMessagesAt,
        addConversationOptimistic,
        updateConversationId,
        loadConversation,
    } = useConversationStore();

    // Convert store messages to ChatMessage format
    const messages: ChatMessage[] = storeMessages.map((m) => ({
        role: m.role,
        content: m.content,
    }));

    // Swipe Detection for Sources Panel
    const touchStart = useRef<number | null>(null);
    const touchEnd = useRef<number | null>(null);
    const { setSourcesPanelOpen, isSidebarOpen, isSourcesPanelOpen, hasInteracted, setHasInteracted } = useUIStore();

    // Auto-set interaction state if messages exist (fixes refresh desync)
    useEffect(() => {
        if (messages.length > 0 && !hasInteracted) {
            setHasInteracted(true);
        }
    }, [messages.length, hasInteracted, setHasInteracted]);

    // Load conversation from URL param if provided
    useEffect(() => {
        if (conversationId) {
            console.debug("[ChatView] loading/syncing conversationId:", conversationId);
            loadConversation(conversationId);
        }
    }, [conversationId, loadConversation]);

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
    }, [conversationId]); // Only depend on conversationId, not storeMessages.length

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
        strictMode: boolean = false
    ) => {
        // Generate UUIDv7 for new conversation if this is the first message
        const isNewConversation = !conversationId && !currentConversationId;
        const newConversationId = isNewConversation ? uuidv7() : null;

        // If new conversation, immediately navigate to the new URL and update state
        if (isNewConversation && newConversationId) {
            addConversationOptimistic(newConversationId, text.slice(0, 50) + (text.length > 50 ? '...' : ''));
            setCurrentConversation(newConversationId);
            // Update URL without triggering Next.js navigation (no page reload)
            window.history.replaceState(
                { ...window.history.state, as: `/chat/${newConversationId}`, url: `/chat/${newConversationId}` },
                '',
                `/chat/${newConversationId}`
            );
        }

        // Use the conversation ID from URL, current state, or newly generated
        const activeConversationId = conversationId || currentConversationId || newConversationId;

        // Optimistic update - add user message to store + cache (write-through)
        const userMessageId = uuidv7();
        const assistantMessageId = uuidv7();  // Generate assistant ID upfront (#4, #5)

        addMessage({
            id: userMessageId,
            role: "user",
            content: text,
            createdAt: new Date().toISOString(),
        }, activeConversationId ?? undefined);
        setIsLoading(true);

        const abortController = new AbortController();
        abortControllerRef.current = abortController;

        try {
            const data = await sendMessage(
                text,
                activeConversationId,
                abortController.signal,
                persona,
                strictMode,
                userMessageId,       // Client-generated user message ID
                assistantMessageId   // Client-generated assistant message ID
            );

            if (data.success) {
                // For new conversations, update temp ID with real ID from backend if different
                if (newConversationId && data.conversation_id && data.conversation_id !== newConversationId) {
                    // Backend returned a different ID (shouldn't happen with our new logic, but handle gracefully)
                    updateConversationId(newConversationId, data.conversation_id);
                    router.replace(`/chat/${data.conversation_id}`);
                }

                // Add assistant response with client-generated ID (matches backend)
                addMessage({
                    id: assistantMessageId,  // Use same ID we sent to backend
                    role: "assistant",
                    content: data.response,
                    sources: data.sources,
                    createdAt: new Date().toISOString(),
                }, activeConversationId ?? undefined);

            } else {
                toast.error(data.error || "Failed to get response");
            }
        } catch (error: any) {
            if (error.name === "CanceledError" || error.code === "ERR_CANCELED") {
                console.debug("Request canceled via stop button");
            } else {
                console.error("Error calling text-mode:", error);
                toast.error("Something went wrong. Please try again.");
            }
        } finally {
            setIsLoading(false);
            abortControllerRef.current = null;
        }
    };

    const handleStop = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            setIsLoading(false);
        }
    };

    // Track voice conversation ID to avoid creating multiple conversations per session
    const voiceConversationIdRef = useRef<string | null>(null);

    const handleVoiceMessage = (message: { role: "user" | "assistant" | "system"; content: string }) => {
        // For new conversations (no URL param, no current ID), create one on first message
        const isNewConversation = !conversationId && !currentConversationId && !voiceConversationIdRef.current;

        let activeConversationId = conversationId || currentConversationId || voiceConversationIdRef.current;

        if (isNewConversation && message.role === "user") {
            // Create new conversation for voice mode
            const newId = uuidv7();
            voiceConversationIdRef.current = newId;
            activeConversationId = newId;

            // Update state and URL like text mode does
            addConversationOptimistic(newId, message.content.slice(0, 50) + (message.content.length > 50 ? '...' : ''));
            setCurrentConversation(newId);
            window.history.replaceState(
                { ...window.history.state, as: `/chat/${newId}`, url: `/chat/${newId}` },
                '',
                `/chat/${newId}`
            );
            console.debug("[ChatView] Created new voice conversation:", newId);
        }

        addMessage({
            id: uuidv7(),
            role: message.role,
            content: message.content,
            createdAt: new Date().toISOString(),
        }, activeConversationId ?? undefined);
    };

    const [editMessageContent, setEditMessageContent] = useState<string | null>(null);

    const handleEditMessage = (index: number, content: string) => {
        // 1. Truncate messages: remove this message and everything after it
        truncateMessagesAt(index);
        // 2. Set the content in input bar for editing
        setEditMessageContent(content);
    };

    // Calculate the right padding to offset the sidebar and center content in viewport
    // only when the sources panel is closed. If sources panel is open, we just center in remaining space.
    const viewportOffsetClass = !isSourcesPanelOpen ? (isSidebarOpen ? "md:pr-[240px]" : "md:pr-[56px]") : "";

    return (
        <div
            className={cn(
                "flex-1 flex flex-col relative min-w-0 overflow-hidden transition-all duration-300",
                viewportOffsetClass
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
                        <p className="text-white/30 text-sm mt-8 animate-pulse">Loading conversation...</p>
                    </div>
                ) : messages.length === 0 ? (
                    <WelcomeScreen />
                ) : (
                    <MessageList
                        messages={messages}
                        isLoading={isLoading}
                        onEdit={handleEditMessage}
                    />
                )}
                <InputBar
                    onSendMessage={handleSendMessage}
                    isLoading={isLoading}
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
