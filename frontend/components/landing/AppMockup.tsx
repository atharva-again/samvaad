"use client";

import { motion } from "framer-motion";
import {
	ChevronLeft,
	FolderOpen,
	History,
	MessageSquare,
	MessageSquarePlus,
	Mic,
	Pin,
	Plus,
	Search,
	X,
} from "lucide-react";

export function AppMockup() {
	return (
		<motion.div
			initial={{ opacity: 0, y: 60 }}
			whileInView={{ opacity: 1, y: 0 }}
			viewport={{ once: true }}
			transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
			className="relative mt-20 perspective-[1500px] w-full max-w-5xl mx-auto"
		>
			<div className="absolute -inset-4 bg-white/5 blur-[100px] opacity-10 pointer-events-none" />

			<div className="relative overflow-hidden border border-white/10 bg-[#080808] rounded-2xl shadow-2xl flex h-[450px] md:h-[600px] lg:h-[650px] rotate-x-[1deg] hover:rotate-x-0 transition-transform duration-700 antialiased">
				<aside className="w-16 md:w-20 border-r border-white/5 flex flex-col items-center py-6 gap-6 bg-[#0a0a0a] shrink-0">
					<div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center mb-4">
						<div className="text-sm font-bold text-white tracking-tighter">
							S
						</div>
					</div>
					<div className="flex flex-col items-center gap-6">
						<Search className="w-5 h-5 text-white/40" />
						<MessageSquarePlus className="w-5 h-5 text-white/40" />
						<div className="p-1.5 rounded-lg bg-white/5 border border-white/10 shadow-sm">
							<FolderOpen className="w-5 h-5 text-white/60" />
						</div>
						<Pin className="w-5 h-5 text-white/20" />
						<History className="w-5 h-5 text-white/20" />
					</div>
					<div className="mt-auto pb-6 flex flex-col gap-6 items-center">
						<div className="relative w-8 h-8 rounded-full bg-white/10 ring-1 ring-white/20 shadow-sm" />
						<div className="p-1.5 rounded-full border border-white/5 bg-white/5">
							<ChevronLeft className="w-4 h-4 text-white/30" />
						</div>
					</div>
				</aside>

				<div className="flex-1 flex flex-col bg-void relative min-w-0">
					<div className="flex-1 p-6 md:p-10 space-y-12 text-left overflow-y-auto overflow-x-hidden scrollbar-none">
						<div className="space-y-6 opacity-30">
							<div className="flex flex-col gap-2 max-w-[85%] ml-auto items-end">
								<div className="px-5 py-2.5 rounded-2xl rounded-tr-sm bg-[#1a1a1a] border border-white/10 shadow-sm w-48 h-8 animate-pulse" />
							</div>
						</div>

						<div className="space-y-6">
							<motion.div
								initial={{ opacity: 0, y: 10 }}
								whileInView={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.5 }}
								className="flex flex-col gap-4"
							>
								<div className="flex items-center gap-2 ml-1">
									<div className="w-2 h-2 rounded-full bg-white/40 shadow-[0_0_8px_rgba(255,255,255,0.2)]" />
									<span className="text-[10px] md:text-xs font-black text-white/60 tracking-[0.25em] uppercase font-mono">
										SAMVAAD
									</span>
								</div>
								<div className="max-w-full lg:max-w-[95%] space-y-3">
									<div className="h-3 w-[90%] bg-white/10 rounded-full animate-pulse" />
									<div className="h-3 w-[95%] bg-white/10 rounded-full animate-pulse delay-75" />
									<div className="h-3 w-[85%] bg-white/10 rounded-full animate-pulse delay-150" />
									<div className="h-3 w-[40%] bg-white/10 rounded-full animate-pulse delay-200" />
								</div>
							</motion.div>
						</div>
					</div>

					<div className="p-8 bg-transparent flex justify-center mt-auto text-left">
						<div className="w-full max-w-lg h-14 bg-[#0a0a0a] rounded-full border border-white/10 flex items-center p-1.5 shadow-2xl relative">
							<div className="flex-1 flex items-center justify-center gap-3 px-6 h-full bg-white/5 rounded-full border border-white/5 shadow-sm relative group cursor-pointer transition-all">
								<MessageSquare className="w-4 h-4 text-white/60" />
								<span className="text-[11px] md:text-xs font-bold text-white uppercase tracking-wider">
									Text Mode
								</span>
							</div>
							<div className="flex-1 flex items-center justify-center gap-3 px-6 h-full group cursor-pointer transition-all">
								<Mic className="w-4 h-4 text-white/30" />
								<span className="text-[11px] md:text-xs font-bold text-white/30 uppercase tracking-wider">
									Voice Mode
								</span>
							</div>
						</div>
					</div>
				</div>

				<div className="w-64 border-l border-white/5 bg-[#0a0a0a] hidden lg:flex flex-col shrink-0">
					<header className="p-5 border-b border-white/5 flex justify-between items-center text-left">
						<div>
							<h4 className="text-xs font-bold text-white tracking-wide uppercase">
								Sources
							</h4>
						</div>
						<div className="p-1.5 rounded-full hover:bg-white/5 transition-colors">
							<X className="w-3.5 h-3.5 text-white/20" />
						</div>
					</header>

					<div className="p-4 space-y-8 text-left">
						<div className="flex bg-[#111] rounded-xl p-1 border border-white/5 text-center">
							<div className="flex-1 text-[10px] font-bold py-1.5 px-2 rounded-lg bg-white/5 text-white/60 text-center border border-white/5 transition-colors">
								KB
							</div>
							<div className="flex-1 text-[10px] font-bold py-1.5 px-2 text-white/20 text-center transition-colors">
								Citations
							</div>
						</div>

						<div className="space-y-4">
							<div className="text-[10px] font-bold text-white/20 uppercase tracking-[0.2em] px-1">
								Active{" "}
								<span className="ml-1 text-white/10 tracking-normal">(1)</span>
							</div>

							<div className="bg-[#0c0c0c] rounded-2xl border border-white/10 p-5 flex flex-col gap-4 shadow-inner">
								<div className="h-3 w-3/4 bg-white/10 rounded-full animate-pulse" />
								<div className="h-2 w-1/2 bg-white/5 rounded-full animate-pulse" />
							</div>
						</div>
					</div>

					<div className="mt-auto p-5 border-t border-white/5 text-center">
						<button
							type="button"
							className="group w-full py-3 rounded-xl bg-white text-black text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-gray-100 transition-all shadow-lg"
						>
							<Plus className="w-4 h-4" />
							Add Source
						</button>
					</div>
				</div>
			</div>
		</motion.div>
	);
}
