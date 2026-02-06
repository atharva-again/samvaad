"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Pin, X, MessageCircle } from "lucide-react";
import { useEffect } from "react";
import type { ChatMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface PinnedMessagesModalProps {
	isOpen: boolean;
	onClose: () => void;
	pinnedMessages: ChatMessage[];
	onMessageClick: (messageId: string) => void;
}

export function PinnedMessagesModal({
	isOpen,
	onClose,
	pinnedMessages,
	onMessageClick,
}: PinnedMessagesModalProps) {
	// Handle escape key
	useEffect(() => {
		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape" && isOpen) {
				onClose();
			}
		};
		window.addEventListener("keydown", handleEscape);
		return () => window.removeEventListener("keydown", handleEscape);
	}, [isOpen, onClose]);

	const handleMessageClick = (messageId: string | undefined) => {
		if (messageId) {
			onMessageClick(messageId);
		}
	};

	return (
		<AnimatePresence>
			{isOpen && (
				<div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
					{/* Backdrop */}
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						className="absolute inset-0 bg-black/60 backdrop-blur-sm"
						onClick={onClose}
					/>

					{/* Modal */}
					<motion.div
						initial={{ scale: 0.95, opacity: 0 }}
						animate={{ scale: 1, opacity: 1 }}
						exit={{ scale: 0.95, opacity: 0 }}
						transition={{ type: "spring", stiffness: 400, damping: 30 }}
						className="relative bg-[#0A0A0A] border border-white/10 rounded-2xl w-full max-w-lg max-h-[80vh] overflow-hidden shadow-2xl"
					>
						{/* Header */}
						<div className="flex items-center justify-between p-4 border-b border-white/10">
							<div className="flex items-center gap-2">
								<Pin className="w-4 h-4 text-white" fill="currentColor" />
								<h3 className="text-base font-medium text-white">Pinned Messages</h3>
								<span className="text-xs text-text-secondary bg-white/10 px-2 py-0.5 rounded-full">
									{pinnedMessages.length}
								</span>
							</div>
							<button
								onClick={onClose}
								className="p-2 hover:bg-white/10 rounded-lg transition-colors"
								type="button"
							>
								<X className="w-4 h-4 text-text-secondary" />
							</button>
						</div>

						{/* Messages List */}
						<div className="overflow-y-auto max-h-[60vh] p-4 space-y-3">
							{pinnedMessages.map((message, index) => (
								<div
									key={message.id || index}
									onClick={() => handleMessageClick(message.id)}
									onKeyDown={(e) => {
										if (e.key === "Enter" || e.key === " ") {
											handleMessageClick(message.id);
										}
									}}
									className={cn(
										"group p-4 rounded-xl border border-white/5 bg-white/[0.02] cursor-pointer",
										"hover:bg-white/[0.05] hover:border-white/10 transition-all"
									)}
									tabIndex={0}
									role="button"
								>
									<div className="flex items-start gap-3">
										<div
											className={cn(
												"flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
												message.role === "user"
													? "bg-surface-light"
													: "bg-primary/20"
											)}
										>
											{message.role === "user" ? (
												<span className="text-xs font-medium text-text-primary">You</span>
											) : (
												<MessageCircle className="w-4 h-4 text-primary" />
											)}
										</div>
										<div className="flex-1 min-w-0">
											<div className="text-sm text-text-primary prose prose-invert max-w-none">
												<ReactMarkdown remarkPlugins={[remarkGfm]}>
													{message.content.length > 200
														? `${message.content.slice(0, 200)}...`
														: message.content}
												</ReactMarkdown>
											</div>
											<p className="text-xs text-text-secondary/60 mt-2">
												{message.timestamp
													? new Date(message.timestamp).toLocaleDateString("en-US", {
															month: "short",
															day: "numeric",
															hour: "2-digit",
															minute: "2-digit",
													  })
													: "Unknown date"}
											</p>
										</div>
									</div>
								</div>
							))}
						</div>
					</motion.div>
				</div>
			)}
		</AnimatePresence>
	);
}
