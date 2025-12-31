import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Pencil } from "lucide-react";
import type React from "react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

interface RenameModalProps {
	isOpen: boolean;
	onClose: () => void;
	onConfirm: (newName: string) => void;
	isRenaming?: boolean;
	currentName?: string;
	title?: string;
}

export function RenameModal({
	isOpen,
	onClose,
	onConfirm,
	isRenaming = false,
	currentName = "",
	title = "Rename Conversation",
}: RenameModalProps) {
	const [name, setName] = useState(currentName);
	const inputRef = useRef<HTMLInputElement>(null);

	// Reset and focus when modal opens
	useEffect(() => {
		if (isOpen) {
			setName(currentName);
			// Focus input after animation
			setTimeout(() => inputRef.current?.focus(), 100);
		}
	}, [isOpen, currentName]);

	// Handle escape key
	useEffect(() => {
		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape" && isOpen && !isRenaming) {
				onClose();
			}
		};
		window.addEventListener("keydown", handleEscape);
		return () => window.removeEventListener("keydown", handleEscape);
	}, [isOpen, isRenaming, onClose]);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		if (name.trim() && name !== currentName) {
			onConfirm(name.trim());
		}
	};

	const isValid = name.trim().length > 0 && name.trim() !== currentName;

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
						onClick={() => !isRenaming && onClose()}
					/>

					{/* Modal */}
					<motion.div
						initial={{ scale: 0.95, opacity: 0 }}
						animate={{ scale: 1, opacity: 1 }}
						exit={{ scale: 0.95, opacity: 0 }}
						transition={{ type: "spring", stiffness: 400, damping: 30 }}
						className="relative bg-[#0A0A0A] border border-white/10 rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl"
					>
						<form onSubmit={handleSubmit}>
							<div className="p-6">
								<div className="flex flex-col items-center text-center gap-4">
									{/* Icon */}
									<div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
										<Pencil className="w-5 h-5 text-primary" />
									</div>

									{/* Content */}
									<div className="flex-1 w-full">
										<h3 className="text-lg font-medium text-white">{title}</h3>
										<p className="text-sm text-text-secondary mt-1">
											Enter a new name for this conversation
										</p>
									</div>
								</div>

								{/* Input */}
								<div className="mt-5">
									<input
										ref={inputRef}
										type="text"
										value={name}
										onChange={(e) => setName(e.target.value)}
										disabled={isRenaming}
										placeholder="Conversation name..."
										className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-primary/50 focus:bg-white/[0.07] transition-all disabled:opacity-50"
										maxLength={100}
									/>
									<div className="flex justify-between mt-2 px-1">
										<span className="text-xs text-text-secondary/50">
											{name.length}/100
										</span>
										{name.trim() === currentName && name.trim() !== "" && (
											<span className="text-xs text-text-secondary/50">
												No changes made
											</span>
										)}
									</div>
								</div>

								{/* Buttons */}
								<div className="grid grid-cols-2 gap-3 mt-5">
									<Button
										type="button"
										variant="ghost"
										onClick={onClose}
										disabled={isRenaming}
										className="w-full text-text-secondary hover:text-white bg-white/5 hover:bg-white/10"
									>
										Cancel
									</Button>
									<Button
										type="submit"
										disabled={isRenaming || !isValid}
										className="w-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
									>
										{isRenaming ? (
											<>
												<Loader2 className="w-4 h-4 mr-2 animate-spin" />
												Saving...
											</>
										) : (
											"Save"
										)}
									</Button>
								</div>
							</div>
						</form>
					</motion.div>
				</div>
			)}
		</AnimatePresence>
	);
}
