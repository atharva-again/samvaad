"use client";

import { type MotionValue, motion } from "framer-motion";

interface HeroProps {
	signInWithGoogle: () => void;
	opacity: MotionValue<number>;
	scale: MotionValue<number>;
}

export function Hero({ signInWithGoogle, opacity, scale }: HeroProps) {
	return (
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
					Samvaad bridges the gap between static documents and fluid
					conversations. Experience cited, multimodal intelligence designed for
					the speed of curiosity.
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
								<div
									key={i}
									className="w-7 h-7 border-2 rounded-full border-void bg-surface-elevation-2 flex items-center justify-center overflow-hidden"
								>
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
		</section>
	);
}
