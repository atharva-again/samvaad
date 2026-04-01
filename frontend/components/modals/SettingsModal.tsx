"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
	LogOut,
	Settings as SettingsIcon,
	User,
	X,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/contexts/AuthContext";
import { useSettingsStore } from "@/lib/stores/useSettingsStore";
import { useInputBarStore } from "@/lib/stores/useInputBarStore";
import { cn } from "@/lib/utils";

interface SettingsModalProps {
	isOpen: boolean;
	onClose: () => void;
}

type Tab = "general" | "account";

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
	const [activeTab, setActiveTab] = useState<Tab>("general");
	const { user, signOut } = useAuth();

	// Global settings
	const { settings, updateSettings, loadSettings, isLoading, error } = useSettingsStore();
	const { syncFromGlobalSettings } = useInputBarStore();

	// Local state for editing (to avoid saving on every change)
	const [localStrictMode, setLocalStrictMode] = useState<boolean>(false);
	const [localPersona, setLocalPersona] = useState<string>("default");

	const [pendingFields, setPendingFields] = useState<{ strictMode: boolean; persona: boolean }>({
		strictMode: false,
		persona: false,
	});

	// Load settings when modal opens
	useEffect(() => {
		if (isOpen) {
			setActiveTab("general");
			loadSettings().catch(console.error);
		}
	}, [isOpen, loadSettings]);

	useEffect(() => {
		if (settings && !pendingFields.strictMode && !pendingFields.persona) {
			setLocalStrictMode(settings.default_strict_mode);
			setLocalPersona(settings.default_persona);
			syncFromGlobalSettings(settings.default_strict_mode, settings.default_persona);
		}
	}, [settings, syncFromGlobalSettings, pendingFields.strictMode, pendingFields.persona]);

	useEffect(() => {
		if (!settings) return;

		const strictModeChanged = localStrictMode !== settings.default_strict_mode;
		const personaChanged = localPersona !== settings.default_persona;

		setPendingFields({ strictMode: strictModeChanged, persona: personaChanged });

		const timeoutId = setTimeout(async () => {
			if (!strictModeChanged && !personaChanged) return;

			try {
				await updateSettings({
					default_strict_mode: localStrictMode,
					default_persona: localPersona,
				});
				syncFromGlobalSettings(localStrictMode, localPersona);
				setPendingFields({ strictMode: false, persona: false });
			} catch (error) {
				console.error("Failed to save settings:", error);
			}
		}, 500);

		return () => clearTimeout(timeoutId);
	}, [localStrictMode, localPersona, settings, updateSettings, syncFromGlobalSettings]);

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === "Escape" && isOpen) {
				onClose();
			} else if (e.key === "Tab" && isOpen) {
				e.preventDefault();
				setActiveTab((prev) => {
					switch (prev) {
						case "general":
							return "account";
						case "account":
							return "general";
						default:
							return "general";
					}
				});
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [isOpen, onClose]);



	return (
		<AnimatePresence>
			{isOpen && (
				<div className="fixed inset-0 z-[200] flex items-center justify-center p-4 sm:p-6">
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						transition={{ duration: 0.2 }}
						className="absolute inset-0 bg-black/60 backdrop-blur-sm"
						onClick={onClose}
					/>

					<motion.div
						initial={{ scale: 0.95, opacity: 0, y: 10 }}
						animate={{ scale: 1, opacity: 1, y: 0 }}
						exit={{ scale: 0.95, opacity: 0, y: 10 }}
						transition={{ type: "spring", stiffness: 350, damping: 25 }}
						className="relative w-full max-w-2xl bg-[#0A0A0A] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[500px]"
						role="dialog"
						aria-modal="true"
						aria-label="Settings"
					>
						<div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
							<div className="flex items-center gap-2 text-white/90 font-semibold">
								<SettingsIcon className="w-5 h-5" />
								<span>Settings</span>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="p-1 hover:bg-white/10 rounded-md transition-colors cursor-pointer"
							>
								<X className="w-4 h-4 text-white/40" />
							</button>
						</div>

						<div className="flex items-center gap-1 px-4 py-2 border-b border-white/5 shrink-0 overflow-x-auto">
							<button
								type="button"
								onClick={() => setActiveTab("general")}
								className={cn(
									"px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-2 cursor-pointer",
									activeTab === "general"
										? "bg-white/10 text-white"
										: "text-white/50 hover:text-white/70 hover:bg-white/5",
								)}
							>
								<SettingsIcon className="w-3.5 h-3.5" />
								General
							</button>
							<button
								type="button"
								onClick={() => setActiveTab("account")}
								className={cn(
									"px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-2 cursor-pointer",
									activeTab === "account"
										? "bg-white/10 text-white"
										: "text-white/50 hover:text-white/70 hover:bg-white/5",
								)}
							>
								<User className="w-3.5 h-3.5" />
								Account
							</button>
						</div>

						<div className="flex-1 overflow-y-auto p-6 md:p-8 min-h-0">
							<AnimatePresence mode="wait">
								{activeTab === "general" && (
									<motion.div
										key="general"
										initial={{ opacity: 0, x: 10 }}
										animate={{ opacity: 1, x: 0 }}
										exit={{ opacity: 0, x: -10 }}
										transition={{ duration: 0.2 }}
										className="space-y-8"
									>
										<div>
											<h2 className="text-xl font-semibold text-white mb-1">
												General Settings
											</h2>
											<p className="text-sm text-white/40">
												Customize your chat experience.
											</p>
										</div>

										<div className="space-y-6">
											{!settings && isLoading && (
												<div className="text-sm text-white/60">Loading settings...</div>
											)}
											{settings && (
												<>
											<div className="space-y-3">
												<div className="flex items-start gap-4">
													<div className="flex-1 space-y-1">
														<div className="text-sm font-medium text-white">
															Default Response Mode
														</div>
													<div className="text-xs text-white/40">
														{localStrictMode
															? "Answers using only your provided sources for maximum accuracy"
															: "Uses your sources plus general knowledge for comprehensive answers"}
													</div>
													{isLoading && pendingFields.strictMode && (
														<div className="text-xs text-blue-400">Saving...</div>
													)}
													{error && pendingFields.strictMode && (
														<div className="text-xs text-red-400">Failed to save: {error}</div>
													)}
													</div>
													<DropdownMenu>
														<DropdownMenuTrigger asChild>
															<button
																type="button"
																className="appearance-none bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-white/20 cursor-pointer hover:bg-white/10 transition-colors flex items-center gap-2 min-w-[100px]"
															>
																<span className="capitalize">
																	{localStrictMode ? "Strict" : "Hybrid"}
																</span>
																<svg
																	width="10"
																	height="6"
																	viewBox="0 0 10 6"
																	fill="none"
																	xmlns="http://www.w3.org/2000/svg"
																	aria-hidden="true"
																	className="text-white/40"
																>
																	<path
																		d="M1 1L5 5L9 1"
																		stroke="currentColor"
																		strokeWidth="1.5"
																		strokeLinecap="round"
																		strokeLinejoin="round"
																	/>
																</svg>
															</button>
														</DropdownMenuTrigger>
														<DropdownMenuContent
															align="end"
															className="w-48 bg-black/90 backdrop-blur-xl border-white/10 text-white z-[300]"
														>
															<DropdownMenuLabel>Choose Mode</DropdownMenuLabel>
															<DropdownMenuSeparator className="bg-white/10" />
															<DropdownMenuItem
																onClick={() => setLocalStrictMode(false)}
																className="cursor-pointer hover:bg-white/10 focus:bg-white/10 focus:text-white"
															>
																<span>Hybrid</span>
																{!localStrictMode && (
																	<svg
																		width="16"
																		height="16"
																		viewBox="0 0 16 16"
																		fill="none"
																		xmlns="http://www.w3.org/2000/svg"
																		className="text-emerald-400 ml-auto"
																		aria-hidden="true"
																	>
																		<path
																			d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 0 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"
																			fill="currentColor"
																		/>
																	</svg>
																)}
															</DropdownMenuItem>
															<DropdownMenuItem
																onClick={() => setLocalStrictMode(true)}
																className="cursor-pointer hover:bg-white/10 focus:bg-white/10 focus:text-white"
															>
																<span>Strict</span>
																{localStrictMode && (
																	<svg
																		width="16"
																		height="16"
																		viewBox="0 0 16 16"
																		fill="none"
																		xmlns="http://www.w3.org/2000/svg"
																		className="text-emerald-400 ml-auto"
																		aria-hidden="true"
																	>
																		<path
																			d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 0 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"
																			fill="currentColor"
																		/>
																	</svg>
																)}
															</DropdownMenuItem>
														</DropdownMenuContent>
													</DropdownMenu>
												</div>
											</div>

											<div className="space-y-3">
												<div className="flex items-start gap-4">
												<div className="flex-1 space-y-1">
													<div className="text-sm font-medium text-white">
														Default AI Persona
													</div>
													<div className="text-xs text-white/40">
														{localPersona === "default" && "Balanced personality for general conversations"}
														{localPersona === "tutor" && "Educational and explanatory approach"}
														{localPersona === "coder" && "Technical and programming-focused"}
														{localPersona === "friend" && "Casual and conversational tone"}
														{localPersona === "expert" && "Professional and authoritative responses"}
													</div>
													{isLoading && pendingFields.persona && (
														<div className="text-xs text-blue-400">Saving...</div>
													)}
													{error && pendingFields.persona && (
														<div className="text-xs text-red-400">Failed to save: {error}</div>
													)}
												</div>
													<DropdownMenu>
														<DropdownMenuTrigger asChild>
															<button
																type="button"
																className="appearance-none bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-white/20 cursor-pointer hover:bg-white/10 transition-colors flex items-center gap-2 min-w-[100px]"
															>
																<span className="capitalize">{localPersona}</span>
																<svg
																	width="10"
																	height="6"
																	viewBox="0 0 10 6"
																	fill="none"
																	xmlns="http://www.w3.org/2000/svg"
																	aria-hidden="true"
																	className="text-white/40"
																>
																	<path
																		d="M1 1L5 5L9 1"
																		stroke="currentColor"
																		strokeWidth="1.5"
																		strokeLinecap="round"
																		strokeLinejoin="round"
																	/>
																</svg>
															</button>
														</DropdownMenuTrigger>
														<DropdownMenuContent
															align="end"
															className="w-48 bg-black/90 backdrop-blur-xl border-white/10 text-white z-[300]"
														>
															<DropdownMenuLabel>Choose Persona</DropdownMenuLabel>
															<DropdownMenuSeparator className="bg-white/10" />
															{["default", "tutor", "coder", "friend", "expert"].map((p) => (
																<DropdownMenuItem
																	key={p}
																	onClick={() => setLocalPersona(p)}
																	className="cursor-pointer hover:bg-white/10 focus:bg-white/10 focus:text-white capitalize"
																>
																	<span>{p}</span>
																	{localPersona === p && (
																		<svg
																			width="16"
																			height="16"
																			viewBox="0 0 16 16"
																			fill="none"
																			xmlns="http://www.w3.org/2000/svg"
																			className="text-emerald-400 ml-auto"
																			aria-hidden="true"
																		>
																			<path
																				d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 0 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"
																				fill="currentColor"
																			/>
																		</svg>
																	)}
																</DropdownMenuItem>
															))}
														</DropdownMenuContent>
													</DropdownMenu>
												</div>
											</div>
												</>
											)}
										</div>
									</motion.div>
								)}

								{activeTab === "account" && (
									<motion.div
										key="account"
										initial={{ opacity: 0, x: 10 }}
										animate={{ opacity: 1, x: 0 }}
										exit={{ opacity: 0, x: -10 }}
										transition={{ duration: 0.2 }}
										className="space-y-8"
									>
										<div>
											<h2 className="text-xl font-semibold text-white mb-1">
												Account
											</h2>
											<p className="text-sm text-white/40">
												Manage your account settings.
											</p>
										</div>

										<div className="space-y-6">
											<div className="p-4 rounded-xl bg-white/5 border border-white/5 flex items-center gap-4 relative">
												{user?.user_metadata?.avatar_url ? (
													<img
														src={user.user_metadata.avatar_url}
														alt="Profile"
														className="w-12 h-12 rounded-full object-cover"
													/>
												) : (
													<div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
														{user?.email?.[0].toUpperCase() || "U"}
													</div>
												)}
												<div className="flex-1 min-w-0">
													<div className="text-sm font-medium text-white truncate">
														{user?.email || "User"}
													</div>
													<div className="text-xs text-white/40">
														Free Plan
													</div>
												</div>
												<button
													type="button"
													onClick={() => {
														signOut();
														onClose();
													}}
													className="group p-2 text-white/30 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-300 cursor-pointer"
												>
													<LogOut className="w-[18px] h-[18px] transition-transform group-hover:scale-110" />
												</button>
											</div>
										</div>
									</motion.div>
								)}
							</AnimatePresence>
						</div>

						<div className="flex items-center justify-between px-4 py-2.5 border-t border-white/5 bg-white/[0.02] shrink-0">
							<div className="flex items-center gap-4 text-[10px] text-white/30">
								<span className="flex items-center gap-1">
									<kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono">
										Tab
									</kbd>
									<span className="ml-1">switch tabs</span>
								</span>
								<span className="flex items-center gap-1">
									<kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono">
										esc
									</kbd>
									<span className="ml-1">close</span>
								</span>
							</div>
						</div>
					</motion.div>
				</div>
			)}
		</AnimatePresence>
	);
}
