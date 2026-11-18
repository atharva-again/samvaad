import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  onEdit?: (index: number, content: string) => void;
}

export function MessageList({ messages, isLoading, onEdit }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom only when new messages are added, not on hover/re-renders
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  return (
    <div className="chat-scrollbar min-h-0 w-full flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-6 py-8 md:px-4">
        {messages.map((msg, index) => (
          <MessageBubble
            key={msg.id || `message-${index}`}
            message={msg}
            index={index}
            onEdit={onEdit}
          />
        ))}

        {isLoading && (
          <div className="mb-6 flex justify-start">
            <div className="max-w-[85%] pl-0 md:max-w-[70%]">
              <div className="mb-1 flex items-center gap-2 opacity-50">
                <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal" />
                <span className="font-mono text-xs uppercase tracking-wider">Samvaad</span>
              </div>
              <div className="flex h-4 items-center gap-1">
                <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/20 [animation-delay:-0.3s]" />
                <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/20 [animation-delay:-0.15s]" />
                <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/20" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
