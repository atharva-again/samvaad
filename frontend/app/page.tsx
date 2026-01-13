"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { 
	FolderOpen, 
	MessageSquarePlus, 
	Search, 
	Pin, 
	History, 
	ChevronLeft,
	MessageSquare,
	Mic,
	Plus,
	X
} from "lucide-react";
import { useRef } from "react";
import { ChatView } from "@/components/chat/ChatView";
import { SourcesPanel } from "@/components/chat/SourcesPanel";
import { IconNavRail } from "@/components/navigation/IconNavRail";
import { useAuth } from "@/contexts/AuthContext";

function LandingPage({ signInWithGoogle }: { signInWithGoogle: () => void }) {
	const containerRef = useRef<HTMLDivElement>(null);
	const { scrollYProgress } = useScroll({
		target: containerRef,
		offset: ["start start", "end end"],
	});

	const opacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);
	const scale = useTransform(scrollYProgress, [0, 0.2], [1, 0.98]);

	return (
		<div ref={containerRef} className="min-h-screen bg-void text-white selection:bg-signal/30 selection:text-white font-sans overflow-x-hidden antialiased">
			<div className="fixed inset-0 z-0 pointer-events-none">
				<div className="absolute top-[-10%] left-[-5%] w-[40%] h-[40%] bg-signal/10 blur-[120px] rounded-full opacity-50" />
				<div className="absolute bottom-[10%] right-[-5%] w-[35%] h-[35%] bg-purple-600/5 blur-[100px] rounded-full opacity-30" />
				<div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.02] mix-blend-overlay" />
			</div>

			<nav className="fixed top-0 left-0 right-0 z-[100] border-b border-white/[0.05] bg-void/60 backdrop-blur-xl px-4 sm:px-6">
				<div className="flex items-center justify-between py-3 mx-auto max-w-6xl">
					<div className="flex items-center gap-2.5 group cursor-pointer">
						<span className="text-lg font-bold tracking-tight">Samvaad</span>
					</div>
					<button
						type="button"
						onClick={signInWithGoogle}
						className="px-4 py-1.5 text-sm font-semibold transition-all border rounded-full border-white/10 bg-white/5 hover:bg-white/10 active:scale-95"
					>
						Launch App
					</button>
				</div>
			</nav>

			<main className="relative z-10 pt-16">
				<section className="px-6 py-16 mx-auto max-w-6xl md:py-24 lg:py-32 overflow-hidden text-center">
					<motion.div 
						style={{ opacity, scale }}
						className="relative max-w-4xl mx-auto"
					>
						<div className="inline-flex items-center gap-2 px-3 py-1 mb-8 text-[10px] font-bold uppercase tracking-[0.2em] border rounded-full bg-signal/5 border-signal/20 text-signal/80">
							<span className="relative flex w-1.5 h-1.5">
								<span className="absolute inline-flex w-full h-full rounded-full opacity-75 animate-ping bg-signal" />
								<span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-signal" />
							</span>
							Beta v1.0
						</div>
						
						<h1 className="text-4xl font-bold tracking-tight leading-[1.15] md:text-6xl lg:text-7xl bg-clip-text text-transparent bg-gradient-to-b from-white via-white to-white/50 pb-4">
							Dialogue with <br className="hidden md:block" /> Intelligence.
						</h1>
						
						<p className="mt-6 text-base md:text-lg text-white/50 max-w-2xl mx-auto font-medium leading-relaxed">
							Samvaad bridges the gap between static documents and fluid conversations. Experience cited, multimodal intelligence designed for the speed of curiosity.
						</p>

						<div className="flex flex-col items-center justify-center gap-4 mt-10 sm:flex-row">
							<button
								type="button"
								onClick={signInWithGoogle}
								className="w-full px-7 py-3.5 text-base font-bold text-black transition-all bg-white rounded-xl sm:w-auto hover:bg-white/90 hover:shadow-lg active:scale-[0.98]"
							>
								Start Free Trial
							</button>
							<div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/10 backdrop-blur-sm">
								<div className="flex -space-x-2">
									{[1, 2, 3].map((i) => (
										<div key={i} className="w-7 h-7 border-2 rounded-full border-void bg-surface-elevation-2 flex items-center justify-center overflow-hidden">
											<div className="w-full h-full bg-gradient-to-tr from-white/10 to-white/5" />
										</div>
									))}
								</div>
								<div className="text-xs font-bold text-white/70">
									Joined by <span className="text-signal">2,400+</span> learners
								</div>
							</div>
						</div>
					</motion.div>

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
									<div className="text-sm font-bold text-white tracking-tighter">S</div>
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
												<span className="text-[10px] md:text-xs font-black text-white/60 tracking-[0.25em] uppercase font-mono">SAMVAAD</span>
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
											<span className="text-[11px] md:text-xs font-bold text-white uppercase tracking-wider">Text Mode</span>
										</div>
										<div className="flex-1 flex items-center justify-center gap-3 px-6 h-full group cursor-pointer transition-all">
											<Mic className="w-4 h-4 text-white/30" />
											<span className="text-[11px] md:text-xs font-bold text-white/30 uppercase tracking-wider">Voice Mode</span>
										</div>
									</div>
								</div>
							</div>
							
							<div className="w-64 border-l border-white/5 bg-[#0a0a0a] hidden lg:flex flex-col shrink-0">
								<header className="p-5 border-b border-white/5 flex justify-between items-center text-left">
									<div>
										<h4 className="text-xs font-bold text-white tracking-wide uppercase">Sources</h4>
									</div>
									<div className="p-1.5 rounded-full hover:bg-white/5 transition-colors">
										<X className="w-3.5 h-3.5 text-white/20" />
									</div>
								</header>
								
								<div className="p-4 space-y-8 text-left">
									<div className="flex bg-[#111] rounded-xl p-1 border border-white/5 text-center">
										<div className="flex-1 text-[10px] font-bold py-1.5 px-2 rounded-lg bg-white/5 text-white/60 text-center border border-white/5 transition-colors">KB</div>
										<div className="flex-1 text-[10px] font-bold py-1.5 px-2 text-white/20 text-center transition-colors">Citations</div>
									</div>

									<div className="space-y-4">
										<div className="text-[10px] font-bold text-white/20 uppercase tracking-[0.2em] px-1">Active <span className="ml-1 text-white/10 tracking-normal">(1)</span></div>
										
										<div className="bg-[#0c0c0c] rounded-2xl border border-white/10 p-5 flex flex-col gap-4 shadow-inner">
											<div className="h-3 w-3/4 bg-white/10 rounded-full animate-pulse" />
											<div className="h-2 w-1/2 bg-white/5 rounded-full animate-pulse" />
										</div>
									</div>
								</div>

								<div className="mt-auto p-5 border-t border-white/5 text-center">
									<button type="button" className="group w-full py-3 rounded-xl bg-white text-black text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-gray-100 transition-all shadow-lg">
										<Plus className="w-4 h-4" />
										Add Source
									</button>
								</div>
							</div>
						</div>
					</motion.div>
				</section>

				<section className="px-6 py-20 mx-auto max-w-6xl">
					<div className="grid grid-cols-1 gap-6 md:grid-cols-12 md:grid-rows-2 text-left">
						<motion.div 
							whileHover={{ y: -3 }}
							className="md:col-span-8 p-8 rounded-[2rem] border border-white/10 bg-white/[0.02] backdrop-blur-xl relative overflow-hidden group"
						>
							<div className="absolute top-0 right-0 p-8">
								<div className="w-12 h-12 rounded-2xl bg-signal/10 border border-signal/20 flex items-center justify-center text-signal group-hover:scale-110 transition-transform duration-500">
									<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" role="img" aria-label="Microphone">
										<title>Voice Intelligence</title>
										<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
									</svg>
								</div>
							</div>
							<h3 className="text-2xl font-bold mb-4 text-left tracking-tight">Voice-Native Design</h3>
							<p className="text-base text-white/40 max-w-md leading-relaxed font-medium text-left">Don't just query. Converse. Our engine supports zero-latency voice handoff, making knowledge retrieval as natural as a phone call.</p>
							<div className="mt-8 h-px bg-gradient-to-r from-white/10 to-transparent" />
						</motion.div>

						<motion.div 
							whileHover={{ y: -3 }}
							className="md:col-span-4 p-8 rounded-[2rem] border border-white/10 bg-white/[0.02] backdrop-blur-xl group"
						>
							<div className="w-12 h-12 mb-8 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 group-hover:rotate-6 transition-transform duration-500">
								<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" role="img" aria-label="Document">
									<title>Verified Sources</title>
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
							</div>
							<h3 className="text-xl font-bold mb-3 text-left tracking-tight">Atomic Citations</h3>
							<p className="text-sm text-white/40 leading-relaxed text-left">No hallucinations. Every claim is backed by a verifiable source from your personal vault.</p>
						</motion.div>

						<motion.div 
							whileHover={{ y: -3 }}
							className="md:col-span-4 p-8 rounded-[2rem] border border-white/10 bg-white/[0.02] backdrop-blur-xl group"
						>
							<div className="w-12 h-12 mb-8 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 group-hover:-rotate-6 transition-transform duration-500">
								<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" role="img" aria-label="Upload">
									<title>Format agnostic</title>
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
								</svg>
							</div>
							<h3 className="text-xl font-bold mb-3 text-left tracking-tight">Universal Ingest</h3>
							<p className="text-sm text-white/40 leading-relaxed text-left font-medium">From PDFs to spreadsheets. We handle the parsing, you handle the insights.</p>
						</motion.div>

						<motion.div 
							className="md:col-span-8 p-8 rounded-[2rem] border border-signal/20 bg-gradient-to-br from-signal/10 via-signal/5 to-transparent flex flex-col justify-center relative group overflow-hidden shadow-2xl"
						>
							<div className="absolute -right-20 -bottom-20 w-64 h-64 bg-signal/10 blur-[80px] group-hover:bg-signal/20 transition-colors" />
							<h3 className="text-3xl font-bold mb-4 tracking-tight text-left">Ready to break the <br /> barrier of knowledge?</h3>
							<div className="flex flex-wrap gap-4 text-left items-center">
								<button 
									type="button"
									onClick={signInWithGoogle}
									className="px-8 py-3.5 rounded-xl bg-white text-black font-extrabold transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg"
								>
									Get Started Now
								</button>
								<div className="flex items-center gap-2 text-xs font-bold text-white/50 uppercase tracking-widest text-left">
									<div className="w-1.5 h-1.5 rounded-full bg-signal shadow-[0_0_6px_rgba(20,241,149,0.5)]" />
									Free Public Beta
								</div>
							</div>
						</motion.div>
					</div>
				</section>
			</main>

			<footer className="relative z-10 px-6 py-16 border-t border-white/[0.05] mx-auto max-w-6xl">
				<div className="flex flex-col md:flex-row justify-between items-start gap-12 mb-16 text-left antialiased">
					<div className="max-w-xs space-y-4">
						<div className="flex items-center gap-2.5">
							<span className="text-lg font-bold tracking-tight">Samvaad</span>
						</div>
						<p className="text-base text-white/30 leading-relaxed italic text-left">
							"Intelligence is the dialogue between knowledge and curiosity."
						</p>
					</div>
					<div className="grid grid-cols-2 gap-16 text-left">
						<div className="space-y-4 text-left">
							<div className="text-[10px] font-bold uppercase tracking-widest text-white/20 text-left">Product</div>
							<ul className="space-y-3 text-sm text-white/40 font-medium text-left">
								<li className="hover:text-white cursor-pointer transition-colors text-left">Features</li>
								<li className="hover:text-white cursor-pointer transition-colors text-left">Security</li>
							</ul>
						</div>
						<div className="space-y-4 text-left">
							<div className="text-[10px] font-bold uppercase tracking-widest text-white/20 text-left">Legal</div>
							<ul className="space-y-3 text-sm text-white/40 font-medium text-left">
								<li className="hover:text-white cursor-pointer transition-colors text-left">Privacy</li>
								<li className="hover:text-white cursor-pointer transition-colors text-left">Terms</li>
							</ul>
						</div>
					</div>
				</div>
				<div className="flex flex-col md:flex-row justify-between items-center gap-4 pt-8 border-t border-white/[0.05] text-white/20 text-[10px] font-bold tracking-[0.2em] uppercase antialiased">
					<div>© 2026 Samvaad Lab</div>
					<div className="flex gap-6">
						<span className="hover:text-white cursor-pointer transition-colors text-left">Twitter</span>
						<span className="hover:text-white cursor-pointer transition-colors text-left">GitHub</span>
					</div>
				</div>
			</footer>
		</div>
	);
}

export default function Home() {
	const { user, isLoading, signInWithGoogle } = useAuth();

	if (isLoading) return null;

	if (user) {
		return (
			<main className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
				<div className="hidden md:flex h-full shrink-0">
					<IconNavRail />
				</div>
				<ChatView />
				<SourcesPanel />
			</main>
		);
	}

	return <LandingPage signInWithGoogle={signInWithGoogle} />;
}
