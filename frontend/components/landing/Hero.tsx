import { type MotionValue, motion } from "framer-motion";
import { Background } from "./Background";
import { RotatingText } from "./RotatingText";

interface HeroProps {
	opacity: MotionValue<number>;
	scale: MotionValue<number>;
	signInWithGoogle: () => void;
}

export function Hero({ opacity, scale, signInWithGoogle }: HeroProps) {
	const itemVariants = {
		hidden: { opacity: 0, y: 20 },
		visible: {
			opacity: 1,
			y: 0,
			transition: {
				ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
			},
		},
	};

	return (
		<section className="relative w-full overflow-hidden">
			<Background />
			<div className="px-6 pt-32 pb-16 mx-auto max-w-6xl md:pt-40 md:pb-24 lg:pt-48 lg:pb-32 text-center relative z-10">
				<motion.div
					style={{ opacity, scale }}
					className="relative max-w-4xl mx-auto"
				>
					<motion.div
						initial="hidden"
						animate="visible"
						transition={{ staggerChildren: 0.1 }}
					>
						<motion.div
							variants={itemVariants}
							className="inline-flex items-center gap-2 px-3 py-1 mb-8 text-[10px] font-bold uppercase tracking-[0.2em] border rounded-full bg-signal/5 border-signal/20 text-signal/80 shadow-[0_0_20px_rgba(16,185,129,0.1)]"
						>
							<span className="relative flex w-1.5 h-1.5">
								<span className="absolute inline-flex w-full h-full rounded-full opacity-75 animate-ping bg-signal" />
								<span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-signal" />
							</span>
							Beta v1.0
						</motion.div>

						<motion.h1
							variants={itemVariants}
							className="text-4xl tracking-tight leading-[1.15] md:text-6xl lg:text-7xl text-white pb-4"
						>
							<span className="font-bold">Dialogue for</span> <br className="hidden md:block" />
							<RotatingText
								words={[
									"Intelligence.",
									"Curiosity.",
									"Creativity.",
									"Insight.",
									"Discovery.",
									"Innovation.",
									"Understanding.",
									"Wisdom.",
									"Precision.",
									"Clarity.",
									"Singularity.",
								]}
								fonts={[
									"font-roboto-slab font-bold",
									"font-ribeye font-normal text-3xl md:text-5xl lg:text-6xl",
									"font-gloria font-normal text-3xl md:text-5xl lg:text-6xl tracking-widest",
									"font-rowdies font-bold",
									"font-goudy font-normal",
									"font-playfair font-bold",
									"font-outfit font-normal",
									"font-cinzel font-bold",
									"font-playfair font-bold italic",
									"font-bai-jamjuree font-normal tracking-widest",
									"font-plus-jakarta font-bold",
								]}
							/>
						</motion.h1>

						<motion.p
							variants={itemVariants}
							className="mt-6 text-base md:text-lg text-white/50 max-w-2xl mx-auto font-medium leading-relaxed"
						>
							Samvaad bridges the gap between static documents and fluid
							conversations. Experience cited, multimodal intelligence designed
							for the speed of curiosity.
						</motion.p>

						<motion.div
							variants={itemVariants}
							className="flex flex-col items-center justify-center gap-4 mt-10 sm:flex-row"
						>
							<button
								type="button"
								onClick={signInWithGoogle}
								className="group relative w-full px-7 h-[52px] text-base font-bold text-black transition-all bg-white rounded-xl sm:w-auto hover:bg-white/90 hover:shadow-[0_0_30px_rgba(255,255,255,0.2)] active:scale-[0.98] cursor-pointer"
							>
								Start Free
								<div className="absolute inset-0 rounded-xl bg-white blur-md opacity-0 group-hover:opacity-20 transition-opacity pointer-events-none" />
							</button>
							<div className="flex items-center px-4 h-[52px] rounded-xl bg-white/[0.03] border border-white/10 backdrop-blur-sm">
								<div className="text-xs font-bold text-white/70">
									Joined by <span className="text-signal">10+</span> learners
								</div>
							</div>
						</motion.div>
					</motion.div>
				</motion.div>

			</div>

			<div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-void to-transparent pointer-events-none z-20" />
		</section>
	);
}
