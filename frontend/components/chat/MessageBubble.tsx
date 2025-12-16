import React from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/lib/api";

interface MessageBubbleProps {
  message: ChatMessage;
  index: number;
  onEdit?: (index: number, content: string) => void;
}

const markdownComponents = {
  code({ node, inline, className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || "");
    return match ? (
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={match[1]}
        PreTag="div"
        {...props}
      >
        {String(children).replace(/\n$/, "")}
      </SyntaxHighlighter>
    ) : (
      <code
        className={cn(
          "bg-white/10 rounded px-1.5 py-0.5 font-mono text-sm",
          className,
        )}
        {...props}
      >
        {children}
      </code>
    );
  },
  h1: ({ node, ...props }: any) => (
    <h1 className="text-2xl font-bold mb-4 mt-6 text-white" {...props} />
  ),
  h2: ({ node, ...props }: any) => (
    <h2 className="text-xl font-bold mb-3 mt-5 text-white" {...props} />
  ),
  h3: ({ node, ...props }: any) => (
    <h3 className="text-lg font-semibold mb-2 mt-4 text-white" {...props} />
  ),
  ul: ({ node, ...props }: any) => (
    <ul className="list-disc pl-6 mb-4 space-y-1" {...props} />
  ),
  ol: ({ node, ...props }: any) => (
    <ol className="list-decimal pl-6 mb-4 space-y-1" {...props} />
  ),
  li: ({ node, ...props }: any) => <li className="pl-1" {...props} />,
  p: ({ node, ...props }: any) => (
    <p className="mb-4 last:mb-0 leading-relaxed" {...props} />
  ),
  strong: ({ node, ...props }: any) => (
    <strong className="font-bold text-white" {...props} />
  ),
  blockquote: ({ node, ...props }: any) => (
    <blockquote
      className="border-l-4 border-signal/50 pl-4 italic my-4 text-white/80"
      {...props}
    />
  ),
};

import { Copy, Pencil, Volume2, Loader2, StopCircle } from "lucide-react";
import { toast } from "sonner";
import { useState, useRef } from "react";
import { API_BASE_URL } from "@/lib/api";

export function MessageBubble({ message, index, onEdit }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    toast.success("Copied to clipboard");
  };

  const handleReadAloud = async () => {
    // If playing, stop playback
    if (isPlaying) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setIsPlaying(false);
      return;
    }

    if (isGenerating) return;

    setIsGenerating(true);

    try {
      // 1. Get a temporary token for the text
      const tokenResponse = await fetch(`${API_BASE_URL}/tts/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: message.content }),
      });

      if (!tokenResponse.ok) throw new Error("Failed to get TTS token");
      const { token } = await tokenResponse.json();

      // 2. Clear old audio if playing
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }

      // 3. Create Audio with stream URL - Browser handles streaming natively
      const streamUrl = `${API_BASE_URL}/tts/stream/${token}`;
      const audio = new Audio(streamUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setIsPlaying(false);
      };

      audio.onerror = () => {
        setIsPlaying(false);
        toast.error("Failed to play audio");
      };

      // 4. Start playing immediately - browser will buffer small amount and start
      setIsGenerating(false);
      setIsPlaying(true);
      await audio.play();

    } catch (error) {
      console.error(error);
      toast.error("Failed to generate speech");
      setIsGenerating(false);
      setIsPlaying(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn(
        "flex w-full mb-6 group relative",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[85%] md:max-w-[70%] rounded-2xl px-5 py-3 text-base leading-relaxed relative",
          isUser
            ? "bg-surface border border-white/10 text-text-primary rounded-br-sm shadow-sm"
            : "bg-transparent text-text-primary rounded-bl-sm pl-0",
        )}
      >
        {!isUser && (
          <div className="flex items-center gap-2 mb-1 opacity-50">
            <div className="w-1.5 h-1.5 rounded-full bg-signal" />
            <span className="text-xs font-mono uppercase tracking-wider">
              Samvaad
            </span>
          </div>
        )}

        <div
          className={cn(
            "prose prose-invert max-w-none break-words",
            isUser ? "" : "text-text-secondary",
          )}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={markdownComponents}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Action Buttons */}
        {isUser ? (
          <div className="absolute -bottom-8 right-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1 bg-surface/50 backdrop-blur-sm border border-white/5 rounded-lg p-1">
            <button
              onClick={handleCopy}
              className="p-1.5 hover:bg-white/10 rounded-md text-text-secondary hover:text-white transition-colors cursor-pointer"
              title="Copy"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
            {onEdit && (
              <button
                onClick={() => onEdit(index, message.content)}
                className="p-1.5 hover:bg-white/10 rounded-md text-text-secondary hover:text-white transition-colors cursor-pointer"
                title="Edit"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ) : (
          /* Bot Actions */
          <div className="absolute -bottom-8 left-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1 bg-surface/50 backdrop-blur-sm border border-white/5 rounded-lg p-1">
            <button
              onClick={handleCopy}
              className="p-1.5 hover:bg-white/10 rounded-md text-text-secondary hover:text-white transition-colors cursor-pointer"
              title="Copy"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleReadAloud}
              disabled={isGenerating}
              className={cn(
                "p-1.5 hover:bg-white/10 rounded-md text-text-secondary hover:text-white transition-colors cursor-pointer",
                (isGenerating || isPlaying) && "text-accent"
              )}
              title={isPlaying ? "Stop Reading" : "Read Aloud"}
            >
              {isGenerating ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : isPlaying ? (
                <StopCircle className="w-3.5 h-3.5 animate-pulse" />
              ) : (
                <Volume2 className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
