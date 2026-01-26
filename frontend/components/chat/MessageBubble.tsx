import { motion } from "framer-motion";
import React from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/api";
import { type CitationItem, useUIStore } from "@/lib/stores/useUIStore";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
	message: ChatMessage;
	index: number;
	onEdit?: (index: number, content: string) => void;
}

// Props type with index signature for react-markdown compatibility
type MarkdownProps = Record<string, unknown> & {
	node?: unknown;
	[key: string]: unknown;
};

const markdownComponents = {
	code(props: MarkdownProps) {
		const { node, inline, className, children, ...rest } = props;
		const match = /language-(\w+)/.exec((className as string) || "");
		return match ? (
			<SyntaxHighlighter
				style={vscDarkPlus}
				language={match[1]}
				PreTag="div"
				{...rest}
			>
				{String(children).replace(/\n$/, "")}
			</SyntaxHighlighter>
		) : (
			<code
				className={cn(
					"bg-white/10 rounded px-1.5 py-0.5 font-mono text-sm",
					className as string,
				)}
				{...rest}
			>
				{children as React.ReactNode}
			</code>
		);
	},
	h1: ({ node, ...props }: MarkdownProps) => (
		<h1 className="text-2xl font-bold mb-4 mt-6 text-white" {...props} />
	),
	h2: ({ node, ...props }: MarkdownProps) => (
		<h2 className="text-xl font-bold mb-3 mt-5 text-white" {...props} />
	),
	h3: ({ node, ...props }: MarkdownProps) => (
		<h3 className="text-lg font-semibold mb-2 mt-4 text-white" {...props} />
	),
	ul: ({ node, ...props }: MarkdownProps) => (
		<ul className="list-disc pl-6 mb-4 space-y-1" {...props} />
	),
	ol: ({ node, ...props }: MarkdownProps) => (
		<ol className="list-decimal pl-6 mb-4 space-y-1" {...props} />
	),
	li: ({ node, ...props }: MarkdownProps) => (
		<li className="pl-1" {...props} />
	),
	p: ({ node, ...props }: MarkdownProps) => (
		<p className="mb-4 last:mb-0 leading-relaxed" {...props} />
	),
	strong: ({ node, ...props }: MarkdownProps) => (
		<strong className="font-bold text-white" {...props} />
	),
	blockquote: ({ node, ...props }: MarkdownProps) => (
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
	sources: CitationItem[];
	citedIndices: number[] | undefined;
	openCitations: (
		messageId: string,
		citations: CitationItem[],
		citedIndices?: number[],
	) => void;
	setHoveredCitationIndex: (
		index: number | null,
		messageId: string | null,
		source?: "bubble" | "panel" | null,
	) => void;
}

function CitationBadge({
	index,
	citationNum,
	messageId,
	hasSources,
	sources,
	citedIndices,
	openCitations,
	setHoveredCitationIndex,
}: CitationBadgeProps) {
	const [isLocalHovered, setIsLocalHovered] = React.useState(false);
	// Also check global store to support reverse highlighting (SourcesPanel -> MessageBubble)
	const { hoveredCitationIndex, hoveredCitationMessageId } = useUIStore();
	const isGlobalHovered =
		hoveredCitationIndex === index && hoveredCitationMessageId === messageId;
	const isHovered = isLocalHovered || isGlobalHovered;

	return (
		<button
			className={cn(
				"inline-flex items-center justify-center min-w-[1.2rem] h-[1.2rem] text-[0.65rem] font-bold rounded-full align-text-top ml-0.5 cursor-pointer transition-all duration-150 select-none border-none bg-transparent",
				isHovered
					? "bg-text-primary text-surface scale-110 shadow-[0_0_10px_rgba(255,255,255,0.3)]"
					: "bg-surface-light border border-white/10 text-text-secondary hover:bg-white/20 hover:text-white",
			)}
			onMouseEnter={() => {
				setIsLocalHovered(true);
				setHoveredCitationIndex(index, messageId, "bubble");
			}}
			onMouseLeave={() => {
				setIsLocalHovered(false);
				setHoveredCitationIndex(null, null);
			}}
			onClick={(e) => {
				e.stopPropagation();
				if (hasSources && messageId && sources) {
					openCitations(
						messageId,
						sources,
						citedIndices,
					);
				}
			}}
			onKeyDown={(e) => {
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault();
					if (hasSources && messageId && sources) {
						openCitations(
							messageId,
							sources,
							citedIndices,
						);
					}
				}
			}}
			type="button"
		>
			{citationNum}
		</button>
	);
}

// Text that precedes a citation - highlights when the citation is hovered
interface CitationTextProps {
	text: string;
	precedesCitationIndex: number;
	messageId: string;
}

function CitationText({
	text,
	precedesCitationIndex,
	messageId,
}: CitationTextProps) {
	const { hoveredCitationIndex, hoveredCitationMessageId } = useUIStore();
	const isHighlighted =
		hoveredCitationIndex === precedesCitationIndex &&
		hoveredCitationMessageId === messageId;

	return (
		<span
			className={cn(
				"transition-all duration-150",
				isHighlighted &&
					"bg-amber-400/30 text-white rounded-sm px-0.5 py-0.5 -mx-0.5",
			)}
		>
			{text}
		</span>
	);
}

import {
	BookMarked,
	Copy,
	Loader2,
	Pencil,
	StopCircle,
	Volume2,
} from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { API_BASE_URL } from "@/lib/api";

export function MessageBubble({ message, index, onEdit }: MessageBubbleProps) {
	const isUser = message.role === "user";
	const [isGenerating, setIsGenerating] = useState(false);
	const [isPlaying, setIsPlaying] = useState(false);
	const audioRef = useRef<HTMLAudioElement | null>(null);
	const messageRef = useRef<HTMLDivElement>(null);

	const {
		openCitations,
		setHoveredCitationIndex,
		sourcesPanelTab,
		setCitations,
		isSourcesPanelOpen,
	} = useUIStore();

	// Check if message has sources for citations button
	const hasSources =
		!isUser &&
		message.sources &&
		Array.isArray(message.sources) &&
		message.sources.length > 0;

	// Extract cited indices from content (e.g. [1], [3] or 【1】, 【3】) to filter the sources panel
	const citedIndices = React.useMemo(() => {
		if (!hasSources) return undefined;
		// Match both Western [N] and Chinese 【N】 brackets
		const matches = message.content.match(/(?:\[(\d+)\]|【(\d+)】)/g);
		if (!matches) return undefined;

		// Extract numbers, subtract 1 (0-indexed), and get unique values
		const indices = new Set<number>();
		matches.forEach((m) => {
			const match = m.match(/(?:\[(\d+)\]|【(\d+)】)/);
			if (match) {
				const num = match[1] || match[2];
				if (num) indices.add(parseInt(num, 10) - 1);
			}
		});

		return Array.from(indices).sort((a, b) => a - b);
	}, [message.content, hasSources]);


	const showCitations = hasSources && citedIndices && citedIndices.length > 0;

	// Memoize markdown components - DO NOT depend on hover state to prevent DOM recreation on hover
	// Hover highlighting is handled via data-attributes and CSS
	const components = React.useMemo(() => {
		// Helper to process text and inject citation badges
		const renderWithCitations = (text: string) => {
			// Regex to find [N] or 【N】 patterns
			const parts = text.split(/(\[\d+\]|【\d+】)/g);

			// If no citations, return text
			if (parts.length === 1) return text;

			// Map segments to reconstruct elements
			let keyCounter = 0;
			return parts.map((part) => {
				// Check if this part is a citation like [1] or 【1】
				const citationMatch = part.match(/^(?:\[(\d+)\]|【(\d+)】)$/);

				if (citationMatch) {
					const citationNum = citationMatch[1] || citationMatch[2];
					const index = parseInt(citationNum, 10) - 1; // 0-indexed

					return (
						<CitationBadge
							key={`citation-${keyCounter++}`}
							index={index}
							citationNum={citationNum}
							messageId={message.id || ""}
							hasSources={hasSources || false}
							sources={message.sources!}
							citedIndices={citedIndices}
							openCitations={openCitations}
							setHoveredCitationIndex={setHoveredCitationIndex}
						/>
					);
				}

				// Regular text segment - check if it precedes a citation
				const nextPart = parts[keyCounter + 1];
				const nextMatch = nextPart?.match(/^(?:\[(\d+)\]|【(\d+)】)$/);

				if (nextMatch) {
					const nextIndex = parseInt(nextMatch[1] || nextMatch[2], 10) - 1;
					return (
						<CitationText
							key={`text-${keyCounter++}`}
							text={part}
							precedesCitationIndex={nextIndex}
							messageId={message.id || ""}
						/>
					);
				}

				return <span key={`span-${keyCounter++}`}>{part}</span>;
			});
		};

		return {
			...markdownComponents,
			p: ({ node, children, ...props }: MarkdownProps) => {
				const processedChildren = React.Children.map(children, (child) => {
					if (typeof child === "string") {
						return renderWithCitations(child);
					}
					return child;
				});

				return (
					<p className="mb-4 last:mb-0 leading-relaxed" {...props}>
						{...(processedChildren as React.ReactNode[])}
					</p>
				);
			},
			li: ({ node, children, ...props }: MarkdownProps) => {
				const processedChildren = React.Children.map(children, (child) => {
					if (typeof child === "string") {
						return renderWithCitations(child);
					}
					return child;
				});
				return (
					<li className="pl-1" {...props}>
						{...(processedChildren as React.ReactNode[])}
					</li>
				);
			},
		};
	}, [
		setHoveredCitationIndex,
		hasSources,
		message.id,
		message.sources,
		openCitations,
		citedIndices,
	]);

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
		if (!showCitations || !messageRef.current) return;

		// Only observe if Citations tab is open
		if (!isSourcesPanelOpen || sourcesPanelTab !== "citations") return;

		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
						// This message is now prominently visible - update citations
						if (message.id && message.sources) {
							setCitations(
								message.id,
								message.sources!,
								citedIndices,
							);
						}
					}
				});
			},
			{
				root: null, // viewport
				threshold: 0.5, // Trigger when 50% visible
				rootMargin: "-100px 0px -100px 0px", // Focus on center of viewport
			},
		);

		observer.observe(messageRef.current);

		return () => observer.disconnect();
	}, [
		showCitations,
		isSourcesPanelOpen,
		sourcesPanelTab,
		message.id,
		message.sources,
		citedIndices,
		setCitations,
	]);

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
					<ReactMarkdown remarkPlugins={[remarkGfm]} components={components as any}>
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
							type="button"
						>
							<Copy className="w-3.5 h-3.5" />
						</button>
						{onEdit && (
							<button
								onClick={() => onEdit(index, message.content)}
								className="p-1.5 hover:bg-white/10 rounded-md text-text-secondary hover:text-white transition-colors cursor-pointer"
								title="Edit"
								type="button"
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
							type="button"
						>
							<Copy className="w-3.5 h-3.5" />
						</button>
						<button
							onClick={handleReadAloud}
							disabled={isGenerating}
							className={cn(
								"p-1.5 hover:bg-white/10 rounded-md text-text-secondary hover:text-white transition-colors cursor-pointer",
								(isGenerating || isPlaying) && "text-accent",
							)}
							title={isPlaying ? "Stop Reading" : "Read Aloud"}
							type="button"
						>
							{isGenerating ? (
								<Loader2 className="w-3.5 h-3.5 animate-spin" />
							) : isPlaying ? (
								<StopCircle className="w-3.5 h-3.5 animate-pulse" />
							) : (
								<Volume2 className="w-3.5 h-3.5" />
							)}
						</button>
					{showCitations && (
							<button
								onClick={() =>
									openCitations(
										message.id || `msg-${index}`,
										message.sources!,
										citedIndices,
									)
								}
								className="p-1.5 hover:bg-white/10 rounded-md text-text-secondary hover:text-white transition-colors cursor-pointer"
								title="View Citations"
								type="button"
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
