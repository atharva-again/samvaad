"use client";

import { motion } from "framer-motion";

interface FeaturesProps {
	signInWithGoogle: () => void;
}

export function Features({ signInWithGoogle }: FeaturesProps) {
	return (
		<section className="px-6 py-20 mx-auto max-w-6xl">
			<div className="grid grid-cols-1 gap-6 md:grid-cols-12 md:grid-rows-2 text-left">
				<motion.div
					whileHover={{ y: -3 }}
					className="md:col-span-8 p-8 rounded-[2rem] border border-white/10 bg-white/[0.02] backdrop-blur-xl relative overflow-hidden group"
				>
					<div className="absolute top-0 right-0 p-8">
						<div className="w-12 h-12 rounded-2xl bg-signal/10 border border-signal/20 flex items-center justify-center text-signal group-hover:scale-110 transition-transform duration-500">
							<svg
								className="w-6 h-6"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								role="img"
								aria-label="Microphone"
							>
								<title>Voice Intelligence</title>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
								/>
							</svg>
						</div>
					</div>
					<h3 className="text-2xl font-bold mb-4 text-left tracking-tight">
						Voice-Native Design
					</h3>
					<p className="text-base text-white/40 max-w-md leading-relaxed font-medium text-left">
						Don't just query. Converse. Our engine supports zero-latency voice
						handoff, making knowledge retrieval as natural as a phone call.
					</p>
					<div className="mt-8 h-px bg-gradient-to-r from-white/10 to-transparent" />
				</motion.div>

				<motion.div
					whileHover={{ y: -3 }}
					className="md:col-span-4 p-8 rounded-[2rem] border border-white/10 bg-white/[0.02] backdrop-blur-xl group"
				>
					<div className="w-12 h-12 mb-8 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 group-hover:rotate-6 transition-transform duration-500">
						<svg
							className="w-6 h-6"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							role="img"
							aria-label="Document"
						>
							<title>Verified Sources</title>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								strokeWidth={2}
								d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							/>
						</svg>
					</div>
					<h3 className="text-xl font-bold mb-3 text-left tracking-tight">
						Atomic Citations
					</h3>
					<p className="text-sm text-white/40 leading-relaxed text-left">
						No hallucinations. Every claim is backed by a verifiable source from
						your personal vault.
					</p>
				</motion.div>

				<motion.div
					whileHover={{ y: -3 }}
					className="md:col-span-4 p-8 rounded-[2rem] border border-white/10 bg-white/[0.02] backdrop-blur-xl group"
				>
					<div className="w-12 h-12 mb-8 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 group-hover:-rotate-6 transition-transform duration-500">
						<svg
							className="w-6 h-6"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							role="img"
							aria-label="Upload"
						>
							<title>Format agnostic</title>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								strokeWidth={2}
								d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
							/>
						</svg>
					</div>
					<h3 className="text-xl font-bold mb-3 text-left tracking-tight">
						Universal Ingest
					</h3>
					<p className="text-sm text-white/40 leading-relaxed text-left font-medium">
						From PDFs to spreadsheets. We handle the parsing, you handle the
						insights.
					</p>
				</motion.div>

				<motion.div className="md:col-span-8 p-8 rounded-[2rem] border border-signal/20 bg-gradient-to-br from-signal/10 via-signal/5 to-transparent flex flex-col justify-center relative group overflow-hidden shadow-2xl">
					<div className="absolute -right-20 -bottom-20 w-64 h-64 bg-signal/10 blur-[80px] group-hover:bg-signal/20 transition-colors" />
					<h3 className="text-3xl font-bold mb-4 tracking-tight text-left">
						Ready to break the <br /> barrier of knowledge?
					</h3>
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
	);
}
