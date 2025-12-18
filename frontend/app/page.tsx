"use client";

import React, { useState, useEffect, useRef } from "react";
import { MessageList } from "@/components/chat/MessageList";
import { InputBar } from "@/components/chat/InputBar";
import { SourcesPanel } from "@/components/chat/SourcesPanel";
import { WelcomeScreen } from "@/components/chat/WelcomeScreen";
import { IconNavRail } from "@/components/navigation/IconNavRail";

import { ChatMessage, sendMessage } from "@/lib/api";
import { toast } from "sonner";

import { useUIStore } from "@/lib/stores/useUIStore";
import { useConversationStore } from "@/lib/stores/useConversationStore";

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);

  // Conversation store
  const {
    currentConversationId,
    messages: storeMessages,
    addMessage,
    setCurrentConversation,
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
  const { setSourcesPanelOpen } = useUIStore();

  // Load conversation if ID is persisted
  useEffect(() => {
    if (currentConversationId && storeMessages.length === 0) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId, storeMessages.length, loadConversation]);

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
  };

  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendMessage = async (
    text: string,
    persona: string = "default",
    strictMode: boolean = false
  ) => {
    // Generate temp ID for new conversation if this is the first message
    const isNewConversation = !currentConversationId;
    const tempConversationId = isNewConversation ? `temp-${Date.now()}` : null;

    // If new conversation, immediately add to sidebar (optimistic update)
    if (isNewConversation && tempConversationId) {
      addConversationOptimistic(tempConversationId, text.slice(0, 50) + (text.length > 50 ? '...' : ''));
      setCurrentConversation(tempConversationId);
    }

    // Optimistic update - add user message to store
    const tempId = `temp-msg-${Date.now()}`;
    addMessage({
      id: tempId,
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    });
    setIsLoading(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const data = await sendMessage(
        text,
        currentConversationId,
        abortController.signal,
        persona,
        strictMode
      );

      if (data.success) {
        // Update temp conversation ID with real ID from backend
        if (data.conversation_id && tempConversationId) {
          updateConversationId(tempConversationId, data.conversation_id);
        }

        // Add assistant response
        addMessage({
          id: `resp-${Date.now()}`,
          role: "assistant",
          content: data.response,
          sources: data.sources,
          createdAt: new Date().toISOString(),
        });
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

  const handleVoiceMessage = (message: { role: "user" | "assistant" | "system"; content: string }) => {
    addMessage({
      id: `voice-${Date.now()}`,
      role: message.role,
      content: message.content,
      createdAt: new Date().toISOString(),
    });
  };

  const [editMessageContent, setEditMessageContent] = useState<string | null>(null);

  const handleEditMessage = (index: number, content: string) => {
    setEditMessageContent(content);
  };

  return (
    <main
      className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Grok-style Icon Navigation Rail - Always visible on desktop */}
      <div className="hidden md:flex h-full shrink-0">
        <IconNavRail />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col relative min-w-0 overflow-hidden">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {messages.length === 0 ? (
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
          />
        </div>
      </div>

      {/* Sources Panel - Untouched */}
      <SourcesPanel />
    </main>
  );
}
