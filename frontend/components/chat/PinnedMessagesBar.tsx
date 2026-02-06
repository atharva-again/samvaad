"use client";

import { Pin, ChevronDown, X } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import type { ChatMessage } from "@/lib/api";
import { getPinnedMessages } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PinnedMessagesModal } from "./PinnedMessagesModal";

interface PinnedMessagesBarProps {
	conversationId: string;
	onMessageClick: (messageId: string) => void;
	refreshTrigger?: number;
}

export function PinnedMessagesBar({
	conversationId,
	onMessageClick,
	refreshTrigger = 0,
}: PinnedMessagesBarProps) {
	const [pinnedMessages, setPinnedMessages] = useState<ChatMessage[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [showAllModal, setShowAllModal] = useState(false);
	const [isVisible, setIsVisible] = useState(true);

	const fetchPinned = useCallback(async () => {
		if (!conversationId) return;
		setIsLoading(true);
		try {
			const messages = await getPinnedMessages(conversationId);
			setPinnedMessages(messages);
		} catch (error) {
			console.error("Failed to fetch pinned messages:", error);
		} finally {
			setIsLoading(false);
		}
	}, [conversationId]);

	useEffect(() => {
		fetchPinned();
	}, [fetchPinned, refreshTrigger]);

	useEffect(() => {
		setIsVisible(true);
	}, [refreshTrigger]);

	if (isLoading || pinnedMessages.length === 0 || !isVisible) {
		return null;
	}

	const latestPinned = pinnedMessages[0];
	const hasMultiple = pinnedMessages.length > 1;

	const handleClick = () => {
		if (latestPinned.id) {
			onMessageClick(latestPinned.id);
		}
	};

	const handleViewAll = (e: React.MouseEvent) => {
		e.stopPropagation();
		setShowAllModal(true);
	};

	const handleDismiss = (e: React.MouseEvent) => {
		e.stopPropagation();
		setIsVisible(false);
	};

	return (
		<>
			<div
				onClick={handleClick}
				className={cn(
					"flex items-center gap-3 px-4 py-3",
					"bg-[#0A0A0A]/90 backdrop-blur-xl",
					"border border-white/10 rounded-2xl",
					"shadow-[0_8px_32px_rgba(0,0,0,0.4)]",
					"cursor-pointer hover:bg-[#0A0A0A] hover:border-white/20",
					"transition-all duration-200",
					"group"
				)}
			>
				<div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
					<Pin className="w-4 h-4 text-white" fill="currentColor" />
				</div>

				<div className="flex-1 min-w-0">
					<p className="text-sm text-text-secondary truncate">
						<span className="font-medium text-text-primary">
							{latestPinned.role === "user" ? "You" : "Assistant"}:
						</span>{" "}
						{latestPinned.content}
					</p>
				</div>

				<div className="flex items-center gap-2 flex-shrink-0">
					{hasMultiple && (
						<button
							onClick={handleViewAll}
							className={cn(
								"flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium",
								"bg-white/10 text-text-secondary hover:bg-white/20 hover:text-white",
								"transition-colors"
							)}
							type="button"
						>
							{pinnedMessages.length} pinned
							<ChevronDown className="w-3 h-3" />
						</button>
					)}
					<button
						onClick={handleDismiss}
						className={cn(
							"p-1.5 rounded-lg",
							"text-text-secondary/60 hover:text-text-secondary hover:bg-white/10",
							"transition-colors"
						)}
						type="button"
					>
						<X className="w-3.5 h-3.5" />
					</button>
				</div>
			</div>

			<PinnedMessagesModal
				isOpen={showAllModal}
				onClose={() => setShowAllModal(false)}
				pinnedMessages={pinnedMessages}
				onMessageClick={(messageId) => {
					onMessageClick(messageId);
					setShowAllModal(false);
				}}
			/>
		</>
	);
}
