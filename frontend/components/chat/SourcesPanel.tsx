import { AnimatePresence, motion } from "framer-motion";
import {
	AlertTriangle,
	CheckSquare,
	ChevronLeft,
	Eye,
	EyeOff,
	File,
	FileAudio,
	FileCode,
	FileImage,
	FileSpreadsheet,
	FileText,
	FileVideo,
	Loader2,
	Pencil,
	Search,
	Square,
	Trash2,
	UploadCloud,
	X,
} from "lucide-react";
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { ActionTooltip, TooltipWrapper } from "@/components/ui/action-tooltip";
import { Button } from "@/components/ui/button";
import { useFileProcessor } from "@/hooks/useFileProcessor";
import { usePlatform } from "@/hooks/usePlatform";
import { batchDeleteFiles, deleteFile, renameFile } from "@/lib/api";
import { filesCache } from "@/lib/cache/filesCache";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { useUIStore } from "@/lib/stores/useUIStore";

// Helper function to get icon based on file type
const getFileIcon = (type: string) => {
	const iconMap: Record<string, React.ReactNode> = {
		PDF: <FileText className="w-5 h-5" />,
		DOCX: <FileText className="w-5 h-5" />,
		DOC: <FileText className="w-5 h-5" />,
		TXT: <FileText className="w-5 h-5" />,
		AUDIO: <FileAudio className="w-5 h-5" />,
		MP3: <FileAudio className="w-5 h-5" />,
		WAV: <FileAudio className="w-5 h-5" />,
		IMAGE: <FileImage className="w-5 h-5" />,
		PNG: <FileImage className="w-5 h-5" />,
		JPG: <FileImage className="w-5 h-5" />,
		JPEG: <FileImage className="w-5 h-5" />,
		GIF: <FileImage className="w-5 h-5" />,
		VIDEO: <FileVideo className="w-5 h-5" />,
		MP4: <FileVideo className="w-5 h-5" />,
		MOV: <FileVideo className="w-5 h-5" />,
		CODE: <FileCode className="w-5 h-5" />,
		JS: <FileCode className="w-5 h-5" />,
		TS: <FileCode className="w-5 h-5" />,
		PY: <FileCode className="w-5 h-5" />,
		CSV: <FileSpreadsheet className="w-5 h-5" />,
		XLSX: <FileSpreadsheet className="w-5 h-5" />,
		XLS: <FileSpreadsheet className="w-5 h-5" />,
	};
	return iconMap[type.toUpperCase()] || <File className="w-5 h-5" />;
};

// Helper for time ago
const getTimeAgo = (dateString: string) => {
	if (!dateString || dateString === "Uploading...") return "Just now";
	const date = new Date(dateString);
	const now = new Date();
	const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

	let interval = seconds / 31536000;
	if (interval > 1) return `${Math.floor(interval)} years ago`;
	interval = seconds / 2592000;
	if (interval > 1) return `${Math.floor(interval)} months ago`;
	interval = seconds / 86400;
	if (interval > 1) return `${Math.floor(interval)} days ago`;
	interval = seconds / 3600;
	if (interval > 1) return `${Math.floor(interval)} hours ago`;
	interval = seconds / 60;
	if (interval > 1) return `${Math.floor(interval)} minutes ago`;
	return "Just now";
};

export function SourcesPanel() {
	const { isMobile } = usePlatform();
	const {
		isSourcesPanelOpen,
		toggleSourcesPanel,
		sources,
		setSources,
		removeSource,
		removeSources,
		updateSource,
		hasFetchedSources,
		setHasFetchedSources,
		setSourcesPanelOpen,
		sourcesSearchQuery,
		setSourcesSearchQuery,

		// Tab & Citations State
		sourcesPanelTab,
		setSourcesPanelTab,
		currentCitations,
		citationsMessageId,
		hoveredCitationIndex,
		setHoveredCitationIndex,
		citedIndices,
		clearCitations,
		hoverSource,

		// Duplicates (Global State)
		pendingDuplicates,
		setPendingDuplicates,
		showDuplicateModal,
		setShowDuplicateModal,

		// Selection Mode (Batch Delete)
		// isSelectionMode removed from destructure - we derive it now
		selectedSourceIds,
		toggleSelectionMode,
		toggleSourceSelection,
		selectAllSources,
		clearSourceSelection,

		// RAG Source Whitelist
		allowedSourceIds,
		toggleAllowedSource,
		allowAllSources,
		enableSources,
		disableSources,
	} = useUIStore();

	// Auto-derive selection mode
	const isSelectionMode = selectedSourceIds.size > 0;

	const { processFiles, handleReplaceDuplicates, refreshSources } =
		useFileProcessor();

	const fileInputRef = React.useRef<HTMLInputElement>(null);
	const searchInputRef = React.useRef<HTMLInputElement>(null);
	const [deletingIds, setDeletingIds] = React.useState<Set<string>>(new Set());
	const [isBatchDeleting, setIsBatchDeleting] = React.useState(false);
	const [editingId, setEditingId] = React.useState<string | null>(null);
	const [editingName, setEditingName] = React.useState("");
	const [editingExtension, setEditingExtension] = React.useState("");
	const renameInputRef = React.useRef<HTMLInputElement>(null);
	const citationsContainerRef = React.useRef<HTMLDivElement>(null);

	// Scroll citations to top when hovering from chat bubble
	React.useEffect(() => {
		if (
			hoveredCitationIndex !== null &&
			hoverSource === "bubble" &&
			citationsContainerRef.current
		) {
			citationsContainerRef.current.scrollTo({ top: 0, behavior: "smooth" });
		}
	}, [hoveredCitationIndex, hoverSource]);

	const filteredSources = sources.filter((file) =>
		file.name.toLowerCase().includes(sourcesSearchQuery.toLowerCase()),
	);

	const [_isLoading, _setIsLoading] = React.useState(false);
	const [isDragging, setIsDragging] = React.useState(false);
	const [isFetchingInfo, setIsFetchingInfo] = React.useState(
		!hasFetchedSources,
	);

	React.useEffect(() => {
		if (hasFetchedSources && isFetchingInfo) {
			setIsFetchingInfo(false);
		}
	}, [hasFetchedSources, isFetchingInfo]);

	React.useEffect(() => {
		const init = async () => {
			if (!hasFetchedSources && isSourcesPanelOpen) {
				setIsFetchingInfo(true);
				await refreshSources();
				setIsFetchingInfo(false);
			}
		};
		init();
	}, [isSourcesPanelOpen, hasFetchedSources, refreshSources]);

	// Back button handling for mobile
	React.useEffect(() => {
		if (!isMobile || !isSourcesPanelOpen) return;

		// Push a state so back button doesn't leave the page
		window.history.pushState({ panel: "sources" }, "");

		const handlePopState = () => {
			// If user presses back, close the panel
			setSourcesPanelOpen(false);
		};

		window.addEventListener("popstate", handlePopState);

		return () => {
			window.removeEventListener("popstate", handlePopState);
			// If we're closing manually (not via popstate), we might want to revert the history?
			// Checking this reliably is tricky, so we'll leave the history entry for now safety.
		};
	}, [isSourcesPanelOpen, isMobile, setSourcesPanelOpen]);

	const handleUploadClick = () => {
		fileInputRef.current?.click();
	};

	// processFiles and handleReplaceDuplicates now come from useFileProcessor

	// --- DRAG & DROP LOGIC ---
	const dragCounter = React.useRef(0);

	const handleDragEnter = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		dragCounter.current += 1;
		if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
			setIsDragging(true);
		}
	};

	const handleDragLeave = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		dragCounter.current -= 1;
		// Only hide if we have left the window (counter 0)
		if (dragCounter.current <= 0) {
			setIsDragging(false);
			dragCounter.current = 0;
		}
	};

	const handleDragOver = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
	};

	const handleDrop = async (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(false);
		dragCounter.current = 0;

		if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
			const files = Array.from(e.dataTransfer.files);
			console.log("Files dropped (Global):", files.length);

			await processFiles(files);
		}
	};

	React.useEffect(() => {
		window.addEventListener(
			"dragenter",
			handleDragEnter as unknown as EventListener,
		);
		window.addEventListener(
			"dragleave",
			handleDragLeave as unknown as EventListener,
		);
		window.addEventListener(
			"dragover",
			handleDragOver as unknown as EventListener,
		);
		window.addEventListener("drop", handleDrop as unknown as EventListener);

		return () => {
			window.removeEventListener(
				"dragenter",
				handleDragEnter as unknown as EventListener,
			);
			window.removeEventListener(
				"dragleave",
				handleDragLeave as unknown as EventListener,
			);
			window.removeEventListener(
				"dragover",
				handleDragOver as unknown as EventListener,
			);
			window.removeEventListener(
				"drop",
				handleDrop as unknown as EventListener,
			);
		};
	}, [handleDragEnter, handleDragLeave, handleDragOver, handleDrop]); // Dependencies for potential closure issues

	const handleFileChange = async (
		event: React.ChangeEvent<HTMLInputElement>,
	) => {
		const files = Array.from(event.target.files || []);
		if (files.length > 0) {
			if (!isSourcesPanelOpen) setSourcesPanelOpen(true);
			await processFiles(files);
		}
	};

	// Keyboard Shortcut (Alt + S)
	React.useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.altKey && e.code === "KeyS") {
				e.preventDefault();
				toggleSourcesPanel();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [toggleSourcesPanel]);

	return (
		<>
			{/* Only show Overlay if dragging. Renders globally fixed. */}
			<AnimatePresence>
				{isDragging && (
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex flex-col items-center justify-center pointer-events-none transition-all duration-300 supports-[backdrop-filter]:bg-black/50"
					>
						<motion.div
							initial={{ scale: 0.9, opacity: 0, y: 20 }}
							animate={{ scale: 1, opacity: 1, y: 0 }}
							exit={{ scale: 0.95, opacity: 0, y: 10 }}
							transition={{ type: "spring", stiffness: 300, damping: 30 }}
							className="relative bg-[#0A0A0A] border border-white/10 rounded-3xl p-10 max-w-md w-full shadow-2xl flex flex-col items-center gap-6 overflow-hidden"
						>
							{/* Decorative Background Gradient */}
							<div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-32 bg-accent/20 blur-[80px] rounded-full pointer-events-none" />

							{/* Icon Group */}
							<div className="relative w-24 h-24 mb-2">
								<div className="absolute inset-0 bg-accent/10 rounded-full blur-xl animate-pulse" />
								<div className="relative w-full h-full bg-gradient-to-b from-white/10 to-transparent rounded-full flex items-center justify-center border border-white/5 shadow-inner">
									<UploadCloud className="w-10 h-10 text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.3)]" />
								</div>
							</div>

							{/* Typography */}
							<div className="text-center space-y-3 relative z-10">
								<h3 className="text-3xl font-bold text-white tracking-tight">
									Drop files to upload
								</h3>
								<p className="text-text-secondary text-base leading-relaxed px-4">
									Instantly analyze documents, images, and audio files with your
									voice agent.
								</p>
							</div>

							{/* Supported formats hint */}
							<div className="flex gap-3 mt-2">
								{["PDF", "DOCX", "TXT", "MD", "JSON", "CSV"].map((ext) => (
									<span
										key={ext}
										className="px-3 py-1 bg-white/5 border border-white/5 rounded-full text-xs font-medium text-text-secondary uppercase tracking-wider"
									>
										{ext}
									</span>
								))}
							</div>
						</motion.div>
					</motion.div>
				)}
			</AnimatePresence>

			{/* Duplicate Confirmation Modal */}
			<AnimatePresence>
				{showDuplicateModal && (
					<div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
						<motion.div
							initial={{ opacity: 0 }}
							animate={{ opacity: 1 }}
							exit={{ opacity: 0 }}
							className="absolute inset-0 bg-black/60 backdrop-blur-sm"
							onClick={() => setShowDuplicateModal(false)}
						/>
						<motion.div
							initial={{ scale: 0.95, opacity: 0 }}
							animate={{ scale: 1, opacity: 1 }}
							exit={{ scale: 0.95, opacity: 0 }}
							className="relative bg-[#0A0A0A] border border-white/10 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl"
						>
							<div className="p-6">
								<div className="flex flex-col items-center text-center gap-4">
									<div className="w-12 h-12 rounded-full bg-yellow-500/10 flex items-center justify-center shrink-0 mb-1">
										<AlertTriangle className="w-6 h-6 text-yellow-500" />
									</div>
									<div className="flex-1 w-full">
										<h3 className="text-lg font-medium text-white">
											{pendingDuplicates.length > 1
												? "Duplicate Files Found"
												: "Duplicate File Found"}
										</h3>
										<p className="text-sm text-text-secondary mt-1">
											{pendingDuplicates.length > 1
												? "The following files already exist in your sources."
												: "The following file already exists in your sources."}
											<br></br>Do you want to replace{" "}
											{pendingDuplicates.length > 1 ? "them" : "it"}?
										</p>
										<div className="mt-6 bg-white/5 rounded-lg border border-white/5 max-h-48 overflow-y-auto custom-scrollbar text-left">
											{pendingDuplicates.map((item) => (
												<div
													key={item.file.name}
													className="px-3 py-2 text-sm text-white/90 border-b border-white/5 last:border-0 flex items-center gap-2"
												>
													<File className="w-4 h-4 text-text-secondary shrink-0" />
													<div className="flex items-center gap-2 truncate text-xs sm:text-sm">
														<span className="text-red-300 line-through decoration-white/20">
															{item.match.name}
														</span>
														<span className="text-text-secondary">→</span>
														<span className="text-green-300">
															{item.file.name}
														</span>
													</div>
												</div>
											))}
										</div>
									</div>
								</div>
								<div className="grid grid-cols-2 gap-3 mt-6">
									<Button
										variant="ghost"
										onClick={() => {
											setShowDuplicateModal(false);
											setPendingDuplicates([]);
										}}
										className="w-full text-text-secondary hover:text-white bg-white/5 hover:bg-white/10"
									>
										Cancel
									</Button>
									<Button
										onClick={handleReplaceDuplicates}
										className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
									>
										Replace {pendingDuplicates.length > 1 ? "All" : ""}
									</Button>
								</div>
							</div>
						</motion.div>
					</div>
				)}
			</AnimatePresence>

			{/* Persistent Toggle (Visible when closed) - Mobile only */}
			<AnimatePresence>
				{!isSourcesPanelOpen && isMobile && (
					<motion.div
						initial={{ opacity: 0, x: 20 }}
						animate={{ opacity: 1, x: 0 }}
						exit={{ opacity: 0, x: 20 }}
						className="fixed right-0 top-1/2 -translate-y-1/2 z-30"
					>
						<button
							onClick={toggleSourcesPanel}
							className="h-12 w-1.5 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-l-full cursor-pointer transition-all duration-300 hover:w-6 flex items-center justify-center group overflow-visible relative border-none bg-transparent"
							type="button"
						>
							<ChevronLeft className="w-3 h-3 text-white/50 group-hover:text-white opacity-0 group-hover:opacity-100 transition-all duration-300 relative z-10" />
						</button>
					</motion.div>
				)}
			</AnimatePresence>

			<AnimatePresence mode="wait">
				{isSourcesPanelOpen && (
					<motion.div
						initial={
							isMobile ? { x: "100%", opacity: 1 } : { width: 0, opacity: 0 }
						}
						animate={
							isMobile ? { x: 0, opacity: 1 } : { width: 420, opacity: 1 }
						}
						exit={
							isMobile ? { x: "100%", opacity: 1 } : { width: 0, opacity: 0 }
						}
						transition={{
							type: "spring",
							stiffness: 300,
							damping: 30,
							mass: 0.8,
						}}
						className="fixed top-[60px] left-0 bottom-0 w-full md:static md:h-full border-l border-white/5 bg-[#050505] md:bg-[#050505]/80 backdrop-blur-3xl flex flex-col shrink-0 overflow-hidden z-50 md:z-40 shadow-2xl"
					>
						<div
							className={`w-full md:w-[420px] flex flex-col h-full bg-gradient-to-b from-white/[0.02] to-transparent transition-colors duration-300`}
						>
							{/* Hidden Input */}
							<input
								type="file"
								multiple
								ref={fileInputRef}
								className="hidden"
								onChange={handleFileChange}
							/>

							{/* Header */}
							<div className="flex items-center justify-between px-6 md:px-8 py-6 md:py-8">
								<div>
									<h2 className="text-xl font-medium text-white tracking-tight flex items-center gap-2">
										Sources
									</h2>
									<p className="text-sm text-text-secondary mt-1 font-light tracking-wide">
										See and Manage Context Sources
									</p>
								</div>
								<Button
									size="icon"
									variant="ghost"
									onClick={toggleSourcesPanel}
									className="text-text-secondary hover:text-white hover:bg-white/5 rounded-full w-10 h-10 transition-all duration-300"
								>
									<X className="w-5 h-5" />
								</Button>
							</div>

							{/* Tab Buttons */}
							<div className="px-6 md:px-8 pb-4">
								<div className="flex bg-white/5 rounded-xl p-1 border border-white/5">
									<button
										id="walkthrough-kb-tab"
										onClick={() => setSourcesPanelTab("knowledge-base")}
										className={`flex-1 py-2 px-3 text-sm font-medium rounded-lg transition-all duration-200 cursor-pointer ${
											sourcesPanelTab === "knowledge-base"
												? "bg-white/10 text-white"
												: "text-text-secondary hover:text-white"
										}`}
										type="button"
									>
										Knowledge Base
									</button>
									<button
										id="walkthrough-citations-tab"
										onClick={() => setSourcesPanelTab("citations")}
										className={`flex-1 py-2 px-3 text-sm font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
											sourcesPanelTab === "citations"
												? "bg-white/10 text-white"
												: "text-text-secondary hover:text-white"
										}`}
										type="button"
									>
										Citations
										{currentCitations.length > 0 && (
											<span className="bg-accent text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[1.2rem] flex items-center justify-center">
												{currentCitations.length}
											</span>
										)}
									</button>
								</div>
							</div>

							{/* Search (only for Knowledge Base tab) */}
							{sourcesPanelTab === "knowledge-base" && (
								<div className="px-6 md:px-8 pb-6">
									<div className="relative group">
										<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50 group-focus-within:text-white transition-colors" />
										<input
											ref={searchInputRef}
											type="text"
											placeholder="Search sources..."
											value={sourcesSearchQuery}
											onChange={(e) => setSourcesSearchQuery(e.target.value)}
											data-sources-search
											className="w-full bg-white/5 border border-white/5 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-text-secondary/50 focus:outline-none focus:bg-white/10 focus:border-white/20 transition-all font-light"
										/>
									</div>
								</div>
							)}

							{/* Tab Content */}
							{sourcesPanelTab === "knowledge-base" ? (
								/* Knowledge Base Tab - File List */
								<div className="flex-1 overflow-y-auto px-4 md:px-6 pb-6 space-y-2 custom-scrollbar">
									{/* Header with Selection Mode Toggle */}
									<div className="flex items-center justify-between px-2 pb-2">
										<div className="flex items-center gap-2">
											<span className="text-xs font-medium text-text-secondary/60 uppercase tracking-widest">
												Active Sources
											</span>
										</div>
										<div className="flex items-center gap-2">
											{/* Active Sources Count (Always visible when not selecting or when selecting but no selection) */}
											{selectedSourceIds.size === 0 && sources.length > 0 && (
												<span className="text-[10px] bg-white/10 text-white/90 px-2 py-0.5 rounded-full font-medium">
													{allowedSourceIds
														? allowedSourceIds.size
														: sources.length}
													/{sources.length}
												</span>
											)}
											{/* Show Delete + Select All only when there are selections */}
											{selectedSourceIds.size > 0 && (
												<>
													<TooltipWrapper
														label="Enable source"
														side="bottom"
														className="flex items-center justify-center"
													>
														<Button
															size="icon"
															variant="ghost"
															onClick={(e: React.MouseEvent) => {
																e.stopPropagation();
																const ids = Array.from(selectedSourceIds);
																enableSources(ids);
																clearSourceSelection();
																toast.success(
																	"Selected sources enabled for RAG",
																);
															}}
															className="h-7 w-7 text-white/70 hover:text-white hover:bg-white/10 rounded-lg"
														>
															<Eye className="w-3.5 h-3.5" />
														</Button>
													</TooltipWrapper>

													<TooltipWrapper
														label="Disable source"
														side="bottom"
														className="flex items-center justify-center"
													>
														<Button
															size="icon"
															variant="ghost"
															onClick={(e: React.MouseEvent) => {
																e.stopPropagation();
																const ids = Array.from(selectedSourceIds);
																disableSources(ids);
																clearSourceSelection();
																toast.success(
																	"Selected sources disabled for RAG",
																);
															}}
															className="h-7 w-7 text-white/70 hover:text-white hover:bg-white/10 rounded-lg"
														>
															<EyeOff className="w-3.5 h-3.5" />
														</Button>
													</TooltipWrapper>
													<Button
														size="sm"
														variant="ghost"
														onClick={
															selectedSourceIds.size === filteredSources.length
																? clearSourceSelection
																: selectAllSources
														}
														className="h-7 px-2 text-xs text-text-secondary hover:text-white"
													>
														{selectedSourceIds.size === filteredSources.length
															? "Deselect All"
															: "Select All"}
													</Button>
													<Button
														size="icon"
														variant="ghost"
														disabled={isBatchDeleting}
														onClick={async () => {
															const ids = Array.from(selectedSourceIds);
															setIsBatchDeleting(true);
															try {
																await batchDeleteFiles(ids);
																const userId =
																	useConversationStore.getState().userId;
																if (userId) {
																	for (const id of ids) {
																		await filesCache.deleteFile(id, userId);
																	}
																}
																removeSources(ids);
																toast.success(`${ids.length} files deleted`);
																clearSourceSelection();
															} catch (err) {
																console.error(err);
																toast.error("Failed to delete files");
															} finally {
																setIsBatchDeleting(false);
															}
														}}
														className="h-7 w-7 text-red-400 hover:text-red-300 hover:bg-red-500/20"
													>
														{isBatchDeleting ? (
															<Loader2 className="w-3.5 h-3.5 animate-spin" />
														) : (
															<Trash2 className="w-3.5 h-3.5" />
														)}
													</Button>
												</>
											)}
										</div>
									</div>

									{isFetchingInfo ? (
										<div className="space-y-3 pt-2">
											{["skeleton1", "skeleton2", "skeleton3"].map((skeletonId, i) => (
												<motion.div
													key={skeletonId}
													initial={{ opacity: 0, y: 10 }}
													animate={{ opacity: 1, y: 0 }}
													transition={{ delay: i * 0.1 }}
													className="flex items-center gap-4 p-4 rounded-2xl bg-white/[0.01] border border-white/[0.02]"
												>
													<div className="w-12 h-12 rounded-xl bg-white/5 animate-pulse" />
													<div className="flex-1 space-y-2">
														<div className="h-4 w-24 bg-white/5 rounded-md animate-pulse" />
														<div className="h-3 w-16 bg-white/5 rounded-md animate-pulse" />
													</div>
												</motion.div>
											))}
										</div>
									) : filteredSources.length === 0 ? (
										<div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
											<div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
												<File className="w-5 h-5 text-white/20" />
											</div>
											<div>
												<p className="text-sm font-medium text-white/60">
													No sources yet
												</p>
												<p className="text-xs text-text-secondary/40 mt-1 max-w-[200px]">
													Upload documents to give your agent more context.
												</p>
											</div>
										</div>
									) : (
										filteredSources.map((file) => {
											const idStr = String(file.id);
											const isSelected = selectedSourceIds.has(idStr);
											const isAllowed =
												allowedSourceIds === null ||
												allowedSourceIds.has(idStr);
											const isEditing = editingId === idStr;

											return (
												<div
													key={file.id}
													className={`group relative flex items-center gap-3 p-4 rounded-2xl border transition-all duration-300 cursor-pointer ${
														isSelected
															? "bg-accent/5 border-accent/20"
															: !isAllowed
																? "bg-white/[0.01] border-white/[0.02] opacity-50"
																: "bg-white/[0.02] border-white/[0.03] hover:bg-white/[0.04] hover:border-white/10"
													}`}
													onClick={() => {
														if (isSelectionMode) {
															toggleSourceSelection(idStr);
														}
													}}
													onKeyDown={(e) => {
														if ((e.key === 'Enter' || e.key === ' ') && isSelectionMode) {
															e.preventDefault();
															toggleSourceSelection(idStr);
														}
													}}
													role="button"
													tabIndex={0}
												>
													{/* Icon / Checkbox area - hover shows checkbox, click toggles selection */}
													<div
														className={`w-10 h-10 rounded-xl bg-gradient-to-br from-white/5 to-transparent border border-white/5 flex items-center justify-center transition-all duration-200 shadow-inner relative shrink-0 cursor-pointer ${!isAllowed ? "opacity-50" : ""}`}
														onClick={(e) => {
															e.stopPropagation();
															toggleSourceSelection(idStr);
														}}
														onKeyDown={(e) => {
															if (e.key === 'Enter' || e.key === ' ') {
																e.preventDefault();
																e.stopPropagation();
																toggleSourceSelection(idStr);
															}
														}}
														role="button"
														tabIndex={0}
													>
														{file.status === "uploading" ? (
															<div className="absolute inset-0 bg-black/50 rounded-xl flex items-center justify-center backdrop-blur-sm z-10">
																<Loader2 className="w-4 h-4 animate-spin text-white" />
															</div>
														) : isSelectionMode || isSelected ? (
															/* Always show checkbox in selection mode or if selected */
															isSelected ? (
																<CheckSquare className="w-5 h-5 text-accent" />
															) : (
																<Square className="w-5 h-5 text-text-secondary/40" />
															)
														) : (
															/* Show icon normally, checkbox on hover */
															<>
																<div className="group-hover:hidden text-text-secondary">
																	{getFileIcon(file.type)}
																</div>
																<div className="hidden group-hover:block">
																	<Square className="w-5 h-5 text-text-secondary/60" />
																</div>
															</>
														)}
													</div>

													{/* Info */}
													<div className="flex-1 min-w-0 flex flex-col gap-0.5 pr-2 group-hover:pr-28 transition-[padding] duration-200">
														{isEditing ? (
															<div className="flex items-center">
																<input
																	ref={renameInputRef}
																	type="text"
																	value={editingName}
																	onChange={(e) =>
																		setEditingName(e.target.value)
																	}
																	onBlur={async () => {
																		const finalName =
																			editingName.trim() + editingExtension;

																		if (
																			editingName.trim() &&
																			finalName !== file.name
																		) {
																			try {
																				await renameFile(idStr, finalName);
																				updateSource(file.id, {
																					name: finalName,
																				});
																				toast.success("File renamed");
																			} catch (err) {
																				console.error(err);
																				toast.error("Failed to rename file");
																			}
																		}
																		setEditingId(null);
																	}}
																	onKeyDown={(e) => {
																		if (e.key === "Enter") {
																			(e.target as HTMLInputElement).blur();
																		} else if (e.key === "Escape") {
																			setEditingId(null);
																		}
																	}}
																	onClick={(e) => e.stopPropagation()}
																	className="text-sm font-medium text-white bg-white/10 border border-white/20 rounded px-2 py-0.5 focus:outline-none focus:border-accent min-w-0 flex-1"
																/>
																{file.name.includes(".") && (
																	<span className="text-sm text-text-secondary ml-1 select-none">
																		{file.name.slice(
																			file.name.lastIndexOf("."),
																		)}
																	</span>
																)}
															</div>
														) : (
															<div className="flex items-center gap-1.5 min-w-0">
																<h4 className="text-sm font-medium text-white/90 truncate group-hover:text-white transition-colors tracking-tight">
																	{file.name}
																</h4>
																{selectedSourceIds.size > 0 && (
																	<div
																		title={
																			isAllowed ? "RAG Enabled" : "RAG Disabled"
																		}
																	>
																		{isAllowed ? (
																			<Eye className="w-3 h-3 text-white/40 shrink-0" />
																		) : (
																			<EyeOff className="w-3 h-3 text-white/20 shrink-0" />
																		)}
																	</div>
																)}
															</div>
														)}
														<div className="flex items-center gap-2 text-xs text-text-secondary/70 group-hover:opacity-0 transition-opacity font-mono whitespace-nowrap overflow-hidden">
															{file.status === "uploading" ? (
																<span className="text-blue-400 flex items-center gap-1">
																	Uploading...
																</span>
															) : (
																<>
																	<span>{file.type}</span>
																	<span className="w-0.5 h-0.5 rounded-full bg-white/20" />
																	<span className="truncate">
																		Uploaded {getTimeAgo(file.uploadedAt)}
																	</span>
																</>
															)}
														</div>
													</div>

													{/* Actions (visible when no selections) */}
													{selectedSourceIds.size === 0 && (
														<div className="flex items-center gap-1 opacity-100 md:opacity-0 group-hover:opacity-100 transition-all duration-300 absolute right-4">
															{/* RAG Toggle Button */}
															<TooltipWrapper
																label={
																	isAllowed ? "Disable source" : "Enable source"
																}
																side="top"
															>
																<Button
																	size="icon"
																	variant="ghost"
																	onClick={(e) => {
																		e.stopPropagation();
																		toggleAllowedSource(idStr);
																	}}
																	className={`h-8 w-8 rounded-lg ${
																		isAllowed
																			? "text-white opacity-100"
																			: "text-white/40 hover:text-white"
																	}`}
																>
																	{isAllowed ? (
																		<Eye className="w-4 h-4" />
																	) : (
																		<EyeOff className="w-4 h-4" />
																	)}
																</Button>
															</TooltipWrapper>
															{/* Rename Button */}
															<Button
																size="icon"
																variant="ghost"
																onClick={(e) => {
																	e.stopPropagation();
																	setEditingId(idStr);
																	const lastDot = file.name.lastIndexOf(".");
																	const baseName =
																		lastDot !== -1
																			? file.name.slice(0, lastDot)
																			: file.name;
																	const extension =
																		lastDot !== -1
																			? file.name.slice(lastDot)
																			: "";
																	setEditingName(baseName);
																	setEditingExtension(extension);
																}}
																className="h-8 w-8 text-text-secondary hover:text-white hover:bg-white/10 rounded-lg"
															>
																<Pencil className="w-3.5 h-3.5" />
															</Button>
															{/* Delete Button */}
															<Button
																size="icon"
																variant="ghost"
																disabled={deletingIds.has(idStr)}
																onClick={async (e) => {
																	e.stopPropagation();
																	try {
																		const userId =
																			useConversationStore.getState().userId;

																		setDeletingIds((prev) =>
																			new Set(prev).add(idStr),
																		);
																		await deleteFile(idStr);

																		if (userId) {
																			await filesCache.deleteFile(
																				idStr,
																				userId,
																			);
																		}

																		removeSource(file.id);
																		toast.success(`${file.name} removed`);
																	} catch (err) {
																		console.error(err);
																		toast.error("Failed to delete file");
																	} finally {
																		setDeletingIds((prev) => {
																			const next = new Set(prev);
																			next.delete(idStr);
																			return next;
																		});
																	}
																}}
																className="h-8 w-8 text-text-secondary hover:text-red-400 hover:bg-red-500/10 rounded-lg"
															>
																{deletingIds.has(idStr) ? (
																	<Loader2 className="w-3.5 h-3.5 animate-spin" />
																) : (
																	<Trash2 className="w-3.5 h-3.5" />
																)}
															</Button>
														</div>
													)}
												</div>
											);
										})
									)}
								</div>
							) : (
								/* Citations Tab - RAG Chunks */
								<div
									ref={citationsContainerRef}
									className="flex-1 overflow-y-auto px-4 md:px-6 pb-6 space-y-3 custom-scrollbar"
								>
									{currentCitations.length === 0 ? (
										<div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
											<div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
												<FileText className="w-5 h-5 text-white/20" />
											</div>
											<div>
												<p className="text-sm font-medium text-white/60">
													No citations
												</p>
												<p className="text-xs text-text-secondary/40 mt-1 max-w-[200px]">
													Click the citations button on a message to see its
													sources.
												</p>
											</div>
										</div>
									) : (
										<>
											<div className="flex items-center justify-between px-2 pb-2">
												<span className="text-xs font-medium text-text-secondary/60 uppercase tracking-widest">
													Retrieved Chunks
												</span>
											</div>
											<AnimatePresence mode="popLayout">
												{/* Sort citations: hovered one goes to top, BUT NOT if hovering from panel (avoids race condition) */}
												{[...currentCitations]
													.map((citation, originalIndex) => ({
														citation,
														originalIndex,
													}))
													.filter(
														({ originalIndex }) =>
															!citedIndices ||
															citedIndices.length === 0 ||
															citedIndices.includes(originalIndex),
													)
													.sort((a, b) => {
														// Only sort if the hover came from the chat bubble
														// If hovering within panel, keep original order to prevent items jumping under cursor
														if (hoverSource === "bubble") {
															if (hoveredCitationIndex === a.originalIndex)
																return -1;
															if (hoveredCitationIndex === b.originalIndex)
																return 1;
														}
														return a.originalIndex - b.originalIndex; // Otherwise keep original order
													})
													.map(({ citation, originalIndex }) => {
														const isHovered =
															hoveredCitationIndex === originalIndex;

														return (
															<motion.div
																key={
																	citation.chunk_id ||
																	`citation-${originalIndex}`
																}
																layout
																layoutId={`citation-${citationsMessageId}-${originalIndex}`}
																initial={{ opacity: 0, y: 10 }}
																animate={{ opacity: 1, y: 0 }}
																exit={{ opacity: 0, scale: 0.95 }}
																transition={{
																	layout: {
																		type: "spring",
																		stiffness: 500,
																		damping: 30,
																	},
																	opacity: { duration: 0.15 },
																}}
																onMouseEnter={() =>
																	setHoveredCitationIndex(
																		originalIndex,
																		citationsMessageId,
																		"panel",
																	)
																}
																onMouseLeave={() =>
																	setHoveredCitationIndex(null, null)
																}
																className={`group/card rounded-2xl border transition-all duration-200 cursor-pointer ${
																	isHovered
																		? "bg-accent/10 border-accent/40 shadow-[0_0_20px_rgba(var(--accent-rgb),0.15)] scale-[1.01] ring-1 ring-accent/20"
																		: "bg-white/[0.02] border-white/[0.05] hover:bg-white/[0.04] opacity-60"
																}`}
															>
																{/* Card Header: Metadata Bar */}
																<div className="px-4 py-3 border-b border-white/[0.03] bg-white/[0.02] flex flex-col gap-2">
																	{/* Top Row: Filename + Breadcrumbs */}
																	<div className="flex items-center justify-between gap-3">
																		<div className="flex items-center gap-2 min-w-0">
																			{/* Source number badge */}
																			<span className="shrink-0 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold rounded-full bg-surface-light border border-white/10 text-text-secondary">
																				{originalIndex + 1}
																			</span>
																			<div className="relative group flex-1 min-w-0">
																				<h4 className="text-sm font-medium text-white/90 truncate leading-none">
																					{(citation as any).metadata?.extra
																						?.breadcrumbs?.length > 0
																						? [
																								citation.filename,
																								...(citation as any).metadata
																									.extra.breadcrumbs,
																							].join(" / ")
																						: citation.filename}
																				</h4>
																				<ActionTooltip
																					label={
																						(citation as any).metadata?.extra
																							?.breadcrumbs?.length > 0
																							? [
																									citation.filename,
																									...(citation as any).metadata
																										.extra.breadcrumbs,
																								].join(" / ")
																							: citation.filename
																					}
																					side="bottom"
																					className="mt-1 pointer-events-none duration-0 whitespace-normal max-w-[450px] text-center leading-snug"
																				/>
																			</div>
																		</div>
																	</div>

																	{/* Bottom Row: Badges (Monochromatic) */}
																	<div className="flex items-center gap-2 text-[10px] text-white/50 font-mono min-w-0 overflow-visible">
																		{/* Page Badge */}
																		{(citation as any).metadata?.extra
																			?.page_number && (
																			<div className="relative group flex items-center">
																				<span className="bg-white/5 text-white/60 px-1.5 py-0.5 rounded border border-white/5 whitespace-nowrap">
																					Pg{" "}
																					{
																						(citation as any).metadata.extra
																							.page_number
																					}
																				</span>
																				<ActionTooltip
																					label="Page in source document"
																					side="top"
																					className="mb-2 left-0 -translate-x-0"
																				/>
																			</div>
																		)}

																		{/* Score Badge (Moved here) */}
																		{citation.rerank_score && (
																			<div className="relative group flex items-center">
																				<span className="bg-white/5 text-white/60 px-1.5 py-0.5 rounded border border-white/5 whitespace-nowrap">
																					{Math.round(
																						citation.rerank_score * 100,
																					)}
																					%
																				</span>
																				<ActionTooltip
																					label="Relevance to your query"
																					side="top"
																					className="mb-2"
																				/>
																			</div>
																		)}

																		{/* Type Badge */}
																		{(citation as any).metadata?.extra
																			?.content_type === "table" && (
																			<span className="bg-white/5 text-white/60 px-1.5 py-0.5 rounded border border-white/5 flex items-center gap-1 whitespace-nowrap">
																				<FileSpreadsheet className="w-3 h-3" />{" "}
																				Table
																			</span>
																		)}
																	</div>
																</div>

																{/* Card Body: Content */}
																<div className="px-4 py-3">
																	<div className="text-sm text-text-secondary/80 leading-relaxed font-light prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-1 prose-headings:text-sm prose-headings:font-semibold prose-ul:my-1 prose-pre:bg-black/20 prose-pre:p-2 prose-pre:rounded-md">
																		<ReactMarkdown remarkPlugins={[remarkGfm]}>
																			{citation.content_preview}
																		</ReactMarkdown>
																	</div>
																</div>
															</motion.div>
														);
													})}
											</AnimatePresence>
										</>
									)}
								</div>
							)}

							{/* Footer */}
							<div
								className={`px-6 pt-6 relative ${isMobile ? "pb-[150px] pb-safe" : "pb-11"}`}
							>
								{/* Gradient Fade */}
								<div className="absolute top-0 left-0 right-0 h-12 -mt-12 bg-gradient-to-t from-[#050505] to-transparent pointer-events-none" />

								<Button
									onClick={handleUploadClick}
									className="w-full h-14 bg-white text-black hover:bg-white/90 hover:scale-[1.01] transition-all duration-300 rounded-2xl font-semibold text-base shadow-[0_0_20px_rgba(255,255,255,0.1)] flex items-center justify-center gap-2 group relative"
								>
									<span className="text-xl leading-none font-light">+</span> Add
									Source
									<ActionTooltip
										label="Add Source"
										shortcut="Alt+A"
										side="top"
									/>
								</Button>
							</div>
						</div>
					</motion.div>
				)}
			</AnimatePresence>
		</>
	);
}
