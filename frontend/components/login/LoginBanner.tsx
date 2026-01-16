"use client";

import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useRef } from "react";
import { Info, Copy, Check } from "lucide-react";

export const LoginBanner = () => {
	const [showTooltip, setShowTooltip] = useState(false);
	const [copied, setCopied] = useState(false);
	const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

	const info = "Café-Singer (1879) by Edgar Degas";

	const copyToClipboard = async () => {
		try {
			await navigator.clipboard.writeText(info);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch (err) {
			console.error("Failed to copy text: ", err);
		}
	};

	const handleMouseEnter = () => {
		if (closeTimeoutRef.current) {
			clearTimeout(closeTimeoutRef.current);
			closeTimeoutRef.current = null;
		}
		setShowTooltip(true);
	};

	const handleMouseLeave = () => {
		closeTimeoutRef.current = setTimeout(() => {
			setShowTooltip(false);
		}, 100);
	};

	return (
		<div className="relative w-full h-full bg-void overflow-hidden">
			<div className="absolute inset-0">
				<Image
					src="https://upload.wikimedia.org/wikipedia/commons/d/d7/Caf%C3%A9_Singer_1879_Edgar_Degas.jpg"
					alt="Café-Singer by Edgar Degas"
					fill
					className="object-cover object-center opacity-100"
					priority
					unoptimized
				/>
			</div>

			<div 
				className="absolute bottom-6 right-6 z-30"
				onMouseEnter={handleMouseEnter}
				onMouseLeave={handleMouseLeave}
			>
				<div className="p-2 rounded-full bg-void/40 backdrop-blur-md border border-white/10 text-white/70 shadow-2xl cursor-help">
					<Info className="w-5 h-5" />
				</div>

				<AnimatePresence>
					{showTooltip && (
						<motion.div
							initial={{ opacity: 0, y: 10, scale: 0.95 }}
							animate={{ opacity: 1, y: 0, scale: 1 }}
							exit={{ opacity: 0, y: 10, scale: 0.95 }}
							className="absolute bottom-full right-0 mb-4 w-64 p-4 rounded-2xl bg-void/80 backdrop-blur-xl border border-white/10 shadow-2xl"
						>
							<div className="flex flex-col gap-3">
								<div className="space-y-1">
									<p className="text-white text-sm font-medium leading-tight">
										Café-Singer
									</p>
									<p className="text-white/50 text-xs uppercase tracking-wider">
										Edgar Degas, 1879
									</p>
								</div>

								<div className="h-px w-full bg-white/5" />

								<button
									type="button"
									onClick={copyToClipboard}
									className="flex items-center justify-between w-full px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/80 hover:text-white transition-colors group/copy cursor-pointer"
								>
									<span className="text-[10px] font-medium uppercase tracking-widest">
										{copied ? "Copied" : "Click to Copy Info"}
									</span>
									{copied ? (
										<Check className="w-3.5 h-3.5 text-signal" />
									) : (
										<Copy className="w-3.5 h-3.5 opacity-50 group-hover/copy:opacity-100 transition-opacity" />
									)}
								</button>
							</div>
							<div className="absolute bottom-[-6px] right-3 w-3 h-3 bg-void/80 rotate-45 border-r border-b border-white/10" />
						</motion.div>
					)}
				</AnimatePresence>
			</div>
		</div>
	);
};
