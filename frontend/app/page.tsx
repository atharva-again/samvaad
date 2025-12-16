"use client";

import React, { useState } from "react";
import { Header } from "@/components/shared/Header";
import { MessageList } from "@/components/chat/MessageList";
import { InputBar } from "@/components/chat/InputBar";
import { SourcesPanel } from "@/components/chat/SourcesPanel";

import { ChatMessage, sendMessage } from "@/lib/api";
import { toast } from "sonner";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Systems online. I am Samvaad. How can I assist you today?",
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const abortControllerRef = React.useRef<AbortController | null>(null);

  const handleSendMessage = async (text: string, persona: string = "default", strictMode: boolean = false) => {
    // Optimistic update
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    // Create new abort controller
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const data = await sendMessage(text, "default", abortController.signal, persona, strictMode);
      if (data.success) {
        const botMsg: ChatMessage = {
          role: "assistant",
          content: data.response,
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        toast.error("Failed to get response");
      }
    } catch (error: any) {
      if (error.name === "CanceledError" || error.code === "ERR_CANCELED") {
        console.debug("Request canceled via stop button");
        // Optional: Add a "Stopped" message or just leave as is
      } else {
        console.error(error);
        toast.error("Connection error");
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
      toast.info("Generation stopped");
    }
  };

  // Handle voice transcripts from voice mode
  const handleVoiceMessage = (message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  };

  /* State for editing a previous message */
  const [editMessageContent, setEditMessageContent] = useState<string | null>(null);

  const handleEditMessage = (index: number, content: string) => {
    // 1. Remove all messages from this index onwards (including the one being edited)
    //    so the user can "rewrite" history from that point.
    setMessages((prev) => prev.slice(0, index));

    // 2. Populate the input bar with the content so they can edit it
    setEditMessageContent(content);
  };

  return (
    <main className="flex flex-col h-screen bg-void text-text-primary overflow-hidden relative">
      <Header />

      {/* Content Container (Below Header) */}
      <div className="flex-1 flex overflow-hidden pt-16">

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col relative min-w-0 transition-all duration-300">
          <MessageList
            messages={messages}
            isLoading={isLoading}
            onEdit={handleEditMessage}
          />
          <InputBar
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            onStop={handleStop}
            defaultMessage={editMessageContent}
            onMessageConsumed={() => setEditMessageContent(null)}
            onVoiceMessage={handleVoiceMessage}
          />
        </div>

        {/* Sources Panel (Side Column) */}
        <SourcesPanel />
      </div>
    </main>
  );
}
