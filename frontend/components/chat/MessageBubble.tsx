import React from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/lib/api";
import { useUIStore, CitationItem } from "@/lib/stores/useUIStore";

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

// Separate component with local hover state for instant feedback
interface CitationBadgeProps {
  index: number;
  citationNum: string;
  messageId: string;
  hasSources: boolean;
  sources: any;
  citedIndices: number[] | undefined;
  openCitations: (messageId: string, citations: any[], citedIndices?: number[]) => void;
  setHoveredCitationIndex: (index: number | null, messageId: string | null, source?: 'bubble' | 'panel' | null) => void;
}

function CitationBadge({ index, citationNum, messageId, hasSources, sources, citedIndices, openCitations, setHoveredCitationIndex }: CitationBadgeProps) {
  const [isLocalHovered, setIsLocalHovered] = React.useState(false);
  // Also check global store to support reverse highlighting (SourcesPanel -> MessageBubble)
  const { hoveredCitationIndex, hoveredCitationMessageId } = useUIStore();
  const isGlobalHovered = hoveredCitationIndex === index && hoveredCitationMessageId === messageId;
  const isHovered = isLocalHovered || isGlobalHovered;

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center min-w-[1.2rem] h-[1.2rem] text-[0.65rem] font-bold rounded-full align-text-top ml-0.5 cursor-pointer transition-all duration-150 select-none",
        isHovered
          ? "bg-text-primary text-surface scale-110 shadow-[0_0_10px_rgba(255,255,255,0.3)]"
          : "bg-surface-light border border-white/10 text-text-secondary hover:bg-white/20 hover:text-white"
      )}
      onMouseEnter={() => {
        setIsLocalHovered(true);
        setHoveredCitationIndex(index, messageId, 'bubble');
      }}
      onMouseLeave={() => {
        setIsLocalHovered(false);
        setHoveredCitationIndex(null, null);
      }}
      onClick={(e) => {
        e.stopPropagation();
        if (hasSources && messageId && sources) {
          openCitations(messageId, sources as unknown as CitationItem[], citedIndices);
        }
      }}
    >
      {citationNum}
    </span>
  );
}

// Text that precedes a citation - highlights when the citation is hovered
interface CitationTextProps {
  text: string;
  precedesCitationIndex: number;
  messageId: string;
}

function CitationText({ text, precedesCitationIndex, messageId }: CitationTextProps) {
  const { hoveredCitationIndex, hoveredCitationMessageId } = useUIStore();
  const isHighlighted = hoveredCitationIndex === precedesCitationIndex && hoveredCitationMessageId === messageId;

  return (
    <span
      className={cn(
        "transition-all duration-150",
        isHighlighted && "bg-amber-400/30 text-white rounded-sm px-0.5 py-0.5 -mx-0.5"
      )}
    >
      {text}
    </span>
  );
}

import { Copy, Pencil, Volume2, Loader2, StopCircle, BookMarked } from "lucide-react";
import { toast } from "sonner";
import { useState, useRef } from "react";
import { API_BASE_URL } from "@/lib/api";

export function MessageBubble({ message, index, onEdit }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const messageRef = useRef<HTMLDivElement>(null);

  const { openCitations, hoveredCitationIndex, hoveredCitationMessageId, setHoveredCitationIndex, sourcesPanelTab, setCitations, isSourcesPanelOpen } = useUIStore();

  // Check if message has sources for citations button
  const hasSources = !isUser && message.sources && Array.isArray(message.sources) && message.sources.length > 0;

  // Extract cited indices from content (e.g. [1], [3]) to filter the sources panel
  const citedIndices = React.useMemo(() => {
    if (!hasSources) return undefined;
    const matches = message.content.match(/\[(\d+)\]/g);
    if (!matches) return undefined;

    // Extract numbers, subtract 1 (0-indexed), and get unique values
    const indices = new Set<number>();
    matches.forEach(m => {
      const match = m.match(/\[(\d+)\]/);
      if (match && match[1]) {
        indices.add(parseInt(match[1], 10) - 1);
      }
    });

    return Array.from(indices).sort((a, b) => a - b);
  }, [message.content, hasSources]);

  // Memoize markdown components - DO NOT depend on hover state to prevent DOM recreation on hover
  // Hover highlighting is handled via data-attributes and CSS
  const components = React.useMemo(() => {
    // Helper to process text and inject citation badges
    const renderWithCitations = (text: string) => {
      // Regex to find [N] patterns
      const parts = text.split(/(\[\d+\])/g);

      // If no citations, return text
      if (parts.length === 1) return text;

      // Map segments to reconstruct elements
      return parts.map((part, i) => {
        // Check if this part is a citation like [1]
        const citationMatch = part.match(/^\[(\d+)\]$/);

        if (citationMatch) {
          const citationNum = citationMatch[1];
          const index = parseInt(citationNum, 10) - 1; // 0-indexed

          // CitationBadge component with local hover state for instant feedback
          return (
            <CitationBadge
              key={i}
              index={index}
              citationNum={citationNum}
              messageId={message.id || ''}
              hasSources={hasSources || false}
              sources={message.sources}
              citedIndices={citedIndices}
              openCitations={openCitations}
              setHoveredCitationIndex={setHoveredCitationIndex}
            />
          );
        }

        // Regular text segment - check if it precedes a citation
        const nextPart = parts[i + 1];
        const nextMatch = nextPart?.match(/^\[(\d+)\]$/);

        if (nextMatch) {
          const nextIndex = parseInt(nextMatch[1], 10) - 1;
          return (
            <CitationText
              key={i}
              text={part}
              precedesCitationIndex={nextIndex}
              messageId={message.id || ''}
            />
          );
        }

        return <span key={i}>{part}</span>;
      });
    };

    return {
      ...markdownComponents,
      p: ({ node, children, ...props }: any) => {
        const processedChildren = React.Children.map(children, (child) => {
          if (typeof child === 'string') {
            return renderWithCitations(child);
          }
          return child;
        });

        return (
          <p className="mb-4 last:mb-0 leading-relaxed" {...props}>
            {processedChildren}
          </p>
        );
      },
      li: ({ node, children, ...props }: any) => {
        const processedChildren = React.Children.map(children, (child) => {
          if (typeof child === 'string') {
            return renderWithCitations(child);
          }
          return child;
        });
        return <li className="pl-1" {...props}>{processedChildren}</li>;
      }
    };
  }, [setHoveredCitationIndex, hasSources, message.id, message.sources, openCitations, citedIndices]);

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

  // IntersectionObserver: Auto-update citations when scrolling with Citations tab open
  React.useEffect(() => {
    if (!hasSources || !messageRef.current) return;

    // Only observe if Citations tab is open
    if (!isSourcesPanelOpen || sourcesPanelTab !== 'citations') return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
            // This message is now prominently visible - update citations
            if (message.id && message.sources) {
              setCitations(message.id, message.sources as any, citedIndices);
            }
          }
        });
      },
      {
        root: null, // viewport
        threshold: 0.5, // Trigger when 50% visible
        rootMargin: '-100px 0px -100px 0px' // Focus on center of viewport
      }
    );

    observer.observe(messageRef.current);

    return () => observer.disconnect();
  }, [hasSources, isSourcesPanelOpen, sourcesPanelTab, message.id, message.sources, citedIndices, setCitations]);

  return (
    <motion.div
      ref={messageRef}
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
            components={components}
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
            {hasSources && (
              <button
                onClick={() => openCitations(message.id || `msg-${index}`, message.sources as unknown as CitationItem[], citedIndices)}
                className="p-1.5 hover:bg-white/10 rounded-md text-text-secondary hover:text-white transition-colors cursor-pointer"
                title="View Citations"
              >
                <BookMarked className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
