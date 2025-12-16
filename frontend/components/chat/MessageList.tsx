import React, { useEffect, useRef } from "react";
import { ChatMessage } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  onEdit?: (index: number, content: string) => void;
}

export function MessageList({ messages, isLoading, onEdit }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto px-4 py-8 overflow-y-auto">
      {messages.map((msg, index) => (
        <MessageBubble
          key={index}
          message={msg}
          index={index}
          onEdit={onEdit}
        />
      ))}

      {isLoading && (
        <div className="flex justify-start mb-6">
          <div className="max-w-[85%] md:max-w-[70%] pl-0">
            <div className="flex items-center gap-2 mb-1 opacity-50">
              <div className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
              <span className="text-xs font-mono uppercase tracking-wider">Samvaad</span>
            </div>
            <div className="flex gap-1 h-4 items-center">
              <div className="w-1.5 h-1.5 bg-white/20 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-1.5 h-1.5 bg-white/20 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-1.5 h-1.5 bg-white/20 rounded-full animate-bounce" />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
