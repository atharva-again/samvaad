import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Trash2 } from "lucide-react";
import React from "react";
import { Button } from "@/components/ui/button";

interface DeleteConfirmModalProps {
	isOpen: boolean;
	onClose: () => void;
	onConfirm: () => void;
	isDeleting?: boolean;
	title?: string;
	itemName?: string;
	description?: string;
}

export function DeleteConfirmModal({
	isOpen,
	onClose,
	onConfirm,
	isDeleting = false,
	title = "Delete Conversation",
	itemName,
	description,
}: DeleteConfirmModalProps) {
	// Handle escape key
	React.useEffect(() => {
		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape" && isOpen && !isDeleting) {
				onClose();
			}
		};
		window.addEventListener("keydown", handleEscape);
		return () => window.removeEventListener("keydown", handleEscape);
	}, [isOpen, isDeleting, onClose]);

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
						onClick={() => !isDeleting && onClose()}
					/>

					{/* Modal */}
					<motion.div
						initial={{ scale: 0.95, opacity: 0 }}
						animate={{ scale: 1, opacity: 1 }}
						exit={{ scale: 0.95, opacity: 0 }}
						transition={{ type: "spring", stiffness: 400, damping: 30 }}
						className="relative bg-[#0A0A0A] border border-white/10 rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl"
					>
						<div className="p-6">
							<div className="flex flex-col items-center text-center gap-4">
								{/* Icon */}
								<div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center shrink-0">
									<Trash2 className="w-6 h-6 text-red-500" />
								</div>

								{/* Content */}
								<div className="flex-1 w-full">
									<h3 className="text-lg font-medium text-white">{title}</h3>
									{itemName && (
										<div className="mt-3 px-3 py-2 bg-white/5 rounded-lg border border-white/5">
											<p className="text-sm text-white/80 truncate font-medium">
												{itemName}
											</p>
										</div>
									)}
									<p className="text-sm text-text-secondary mt-3">
										{description ||
											"This action cannot be undone. All messages in this conversation will be permanently deleted."}
									</p>
								</div>
							</div>

							{/* Buttons */}
							<div className="grid grid-cols-2 gap-3 mt-6">
								<Button
									variant="ghost"
									onClick={onClose}
									disabled={isDeleting}
									className="w-full text-text-secondary hover:text-white bg-white/5 hover:bg-white/10"
								>
									Cancel
								</Button>
								<Button
									onClick={onConfirm}
									disabled={isDeleting}
									className="w-full bg-red-600 text-white hover:bg-red-700"
								>
									{isDeleting ? (
										<>
											<Loader2 className="w-4 h-4 mr-2 animate-spin" />
											Deleting...
										</>
									) : (
										"Delete"
									)}
								</Button>
							</div>
						</div>
					</motion.div>
				</div>
			)}
		</AnimatePresence>
	);
}
