import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
	messages: ChatMessage[];
	isLoading?: boolean;
	onEdit?: (index: number, content: string) => void;
	scrollToMessageId?: string | null;
	onPinToggle?: () => void;
}

export function MessageList({ messages, isLoading, onEdit, scrollToMessageId, onPinToggle }: MessageListProps) {
	const bottomRef = useRef<HTMLDivElement>(null);
	const messageRefs = useRef<Map<string, HTMLDivElement>>(new Map());

	// Scroll to bottom only when new messages are added, not on hover/re-renders
	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: "smooth" });
	}, []);

	useEffect(() => {
		if (scrollToMessageId) {
			const element = messageRefs.current.get(scrollToMessageId);
			if (element) {
				element.scrollIntoView({ behavior: "smooth", block: "center" });
			}
		}
	}, [scrollToMessageId]);

	const setMessageRef = (id: string | undefined) => (el: HTMLDivElement | null) => {
		if (id && el) {
			messageRefs.current.set(id, el);
		}
	};

	return (
		<div className="flex-1 w-full max-w-3xl mx-auto px-6 md:px-4 py-8 overflow-y-auto">
			{messages.map((msg, index) => (
				<div key={msg.id || `message-${index}`} ref={setMessageRef(msg.id)}>
					<MessageBubble
						message={msg}
						index={index}
						onEdit={onEdit}
						onPinToggle={onPinToggle}
					/>
				</div>
			))}

			{isLoading && (
				<div className="flex justify-start mb-6">
					<div className="max-w-[85%] md:max-w-[70%] pl-0">
						<div className="flex items-center gap-2 mb-1 opacity-50">
							<div className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
							<span className="text-xs font-mono uppercase tracking-wider">
								Samvaad
							</span>
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
