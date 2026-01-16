"use client";

import { motion, useMotionValue, useSpring } from "framer-motion";
import { useEffect } from "react";

export function Background() {
	const mouseX = useMotionValue(0);
	const mouseY = useMotionValue(0);

	const springConfig = { damping: 25, stiffness: 150 };
	const cursorX = useSpring(mouseX, springConfig);
	const cursorY = useSpring(mouseY, springConfig);

	useEffect(() => {
		const handleMouseMove = (e: MouseEvent) => {
			mouseX.set(e.clientX);
			mouseY.set(e.clientY);
		};

		window.addEventListener("mousemove", handleMouseMove);
		return () => window.removeEventListener("mousemove", handleMouseMove);
	}, [mouseX, mouseY]);

	return (
		<div className="absolute inset-0 z-0 pointer-events-none overflow-hidden [mask-image:linear-gradient(to_bottom,black_70%,rgba(0,0,0,0.5)_85%,transparent_100%)]">
			<motion.div
				className="absolute w-[1200px] h-[1200px] rounded-full opacity-60 mix-blend-screen pointer-events-none"
				style={{
					background:
						"radial-gradient(circle at center, rgba(16, 185, 129, 0.2), rgba(59, 130, 246, 0.05), transparent 70%)",
					x: cursorX,
					y: cursorY,
					translateX: "-50%",
					translateY: "-50%",
				}}
			/>

			<motion.div
				animate={{
					x: [0, 150, 0],
					y: [0, -150, 0],
					scale: [1, 1.3, 1],
					rotate: [0, 90, 0],
				}}
				transition={{
					duration: 25,
					repeat: Number.POSITIVE_INFINITY,
					ease: "linear",
				}}
				className="absolute top-[-15%] left-[-10%] w-[60%] h-[60%] bg-signal/20 blur-[140px] rounded-full opacity-40"
			/>
			<motion.div
				animate={{
					x: [0, -180, 0],
					y: [0, 120, 0],
					scale: [1, 1.2, 1],
					rotate: [0, -90, 0],
				}}
				transition={{
					duration: 30,
					repeat: Number.POSITIVE_INFINITY,
					ease: "linear",
				}}
				className="absolute bottom-[5%] right-[-10%] w-[55%] h-[55%] bg-accent/15 blur-[120px] rounded-full opacity-30"
			/>

			<div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-gradient-radial from-signal/10 to-transparent opacity-50" />

			<div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.04] mix-blend-overlay" />

			<div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:64px_64px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_80%,transparent_100%)]" />
		</div>
	);
}
