"use client";

import { Github } from "lucide-react";
import { motion, useScroll, useTransform, useMotionValue, useSpring } from "framer-motion";
import { useRef, useEffect } from "react";

export function Footer() {
	const { scrollYProgress } = useScroll();
	const containerRef = useRef<HTMLDivElement>(null);
	
	// Scroll Reveal Effects:
	// Blur: Starts blurry (10px) and focuses (0px) as we reach the bottom
	const textBlur = useTransform(scrollYProgress, [0.85, 1], ["10px", "0px"]);
	// Scale: Starts slightly zoomed out (0.9) and scales to neutral (1)
	const textScale = useTransform(scrollYProgress, [0.85, 1], [0.9, 1]);
	// Opacity: Fades in
	const textOpacity = useTransform(scrollYProgress, [0.85, 1], [0.2, 1]);

	// Mouse Parallax
	const mouseX = useMotionValue(0);
	const mouseY = useMotionValue(0);

	const springConfig = { damping: 20, stiffness: 100, mass: 0.5 };
	const springX = useSpring(mouseX, springConfig);
	const springY = useSpring(mouseY, springConfig);

	const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
		const { left, top, width, height } = e.currentTarget.getBoundingClientRect();
		const x = ((e.clientX - left) - width / 2) / (width / 2);
		const y = ((e.clientY - top) - height / 2) / (height / 2);
		mouseX.set(x * -30);
		mouseY.set(y * -15);
	};

	const handleMouseLeave = () => {
		mouseX.set(0);
		mouseY.set(0);
	};

	return (
		<footer 
			ref={containerRef}
			onMouseMove={handleMouseMove}
			onMouseLeave={handleMouseLeave}
			className="fixed bottom-0 left-0 w-full h-[500px] md:h-[600px] z-0 overflow-hidden bg-black flex flex-col justify-between pt-20 pb-10"
		>
			{/* Vignette Background */}
			<div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_100%,_rgba(255,255,255,0.03),_transparent_70%)] pointer-events-none" />
			
			<div className="mx-auto max-w-4xl px-6 text-center z-10 relative flex-1 flex flex-col justify-start pt-10">
				{/* Quote Section */}
				<p className="mb-10 text-2xl md:text-3xl lg:text-4xl font-[family-name:var(--font-playfair)] font-light text-white/80 leading-relaxed tracking-wide antialiased">
					Intelligence is the dialogue between<br />knowledge and curiosity.
				</p>

				{/* Navigation/Utility Section */}
				<div className="flex flex-col items-center gap-6">
					<a
						href="https://github.com"
						target="_blank"
						rel="noopener noreferrer"
						className="group relative flex items-center justify-center p-2 text-white/40 hover:text-white transition-colors duration-300"
						aria-label="GitHub"
					>
						<span className="absolute inset-0 bg-white/10 rounded-full scale-0 group-hover:scale-100 transition-transform duration-300 ease-out" />
						<Github className="w-6 h-6 relative z-10" />
					</a>
					
					<div className="text-[10px] font-bold tracking-[0.2em] uppercase text-white/20">
						© 2026 Samvaad
					</div>
				</div>
			</div>

			{/* Large Brand Text - Editorial Ghost Outline */}
			<div className="w-full flex justify-center items-end select-none pointer-events-none absolute bottom-0 left-0 overflow-hidden pb-4">
				<motion.div
					style={{ x: springX, y: springY }}
					className="relative"
				>
					<motion.h1 
						style={{ 
							filter: useTransform(textBlur, (v) => `blur(${v})`),
							scale: textScale,
							opacity: textOpacity,
							WebkitTextStroke: "1px rgba(255, 255, 255, 0.15)"
						}}
						className="text-[15vw] md:text-[18vw] leading-[0.8] font-[family-name:var(--font-outfit)] font-bold tracking-tight text-transparent whitespace-nowrap uppercase translate-y-[15%]"
					>
						SAMVAAD
					</motion.h1>
				</motion.div>
			</div>
		</footer>
	);
}