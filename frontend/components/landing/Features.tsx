"use client";

import React, { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check } from "lucide-react";


interface FeaturesProps {
	signInWithGoogle: () => void;
}

export function Features({ signInWithGoogle }: FeaturesProps) {
	const features = [
		{
			title: "Voice-Native",
			description:
				"Ultra-low latency voice mode makes learning as natural as a real conversation. Speak directly to your knowledge base.",
			graphic: <VoiceNativeGraphic />,
		},
		{
			title: "Atomic Citations",
			description:
				"Cross-check all responses with sentence-level citations. Stay safe from hallucinated responses.",
			graphic: <AtomicCitationsGraphic />,
		},
		{
			title: "Universal Ingest",
			description:
				"From high-fidelity PDFs to intricate spreadsheets. We transform static data into interactive dialogues.",
			graphic: <UniversalIngestGraphic />,
		},
		{
			title: "Intelligent Reasoning",
			description:
				"Switch between varying depths of logic and speed. Our engine adapts to your query complexity seamlessly.",
			graphic: <IntelligentReasoningGraphic />,
		},
		{
			title: "Adaptive Personas",
			description:
				"Instantly switch between specialized roles to match your learning style.",
			graphic: <AdaptivePersonasGraphic />,
		},
		{
			title: "Universal Search",
			description:
				"Instantly locate any conversation or document with fuzzy search and granular filtering.",
			graphic: <UniversalSearchGraphic />,
		},
	];

			return (

				<section id="features" className="mt-20">

					<div className="border-l border-r border-b border-white/10 max-w-[1440px] mx-auto overflow-hidden">

						<div className="py-24 px-6 md:px-12 text-center">

							<motion.div

								initial={{ opacity: 0, y: 20 }}

								whileInView={{ opacity: 1, y: 0 }}

								viewport={{ once: true }}

								transition={{ duration: 0.5 }}

							>

																																								<h2 className="text-3xl md:text-5xl font-light tracking-tight text-white mb-6">

																																									Features

																																								</h2>

																																								<p className="text-lg text-white/40 max-w-2xl mx-auto leading-relaxed font-light">

																																									Engineered for the curious mind.

																																								</p>

							</motion.div>

						</div>

					</div>

		

					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 border-l border-white/10 max-w-[1440px] mx-auto">
				{features.map((feature, index) => (
					<motion.div
						key={feature.title}
						initial={{ opacity: 0 }}
						whileInView={{ opacity: 1 }}
						viewport={{ once: true }}
						transition={{ duration: 0.5, delay: index * 0.1 }}
						className="group border-r border-b border-white/10 p-0 flex flex-col min-h-[450px]"
					>
						<div className="aspect-[4/3] w-full overflow-hidden border-b border-white/10 relative">
							{feature.graphic}
						</div>

						<div className="p-10 flex flex-col flex-1">
							<h4 className="text-xl font-medium text-white mb-4 tracking-tight">
								{feature.title}
							</h4>
							<p className="text-sm text-white/40 leading-relaxed max-w-[280px]">
								{feature.description}
							</p>
						</div>
					</motion.div>
				))}
			</div>

			<motion.div
				initial={{ opacity: 0 }}
				whileInView={{ opacity: 1 }}
				viewport={{ once: true }}
				className="border-b border-l border-r border-white/10 max-w-[1440px] mx-auto p-20 text-center"
			>
				<h3 className="text-2xl font-light mb-10 tracking-tight text-white/80">
					Ready to start the <span className="italic">dialogue</span>?
				</h3>
				<button
					type="button"
					onClick={signInWithGoogle}
					className="px-12 py-4 rounded-full border border-white/20 text-white text-sm font-medium hover:bg-white hover:text-black transition-all duration-500 cursor-pointer"
				>
					Get Started Now
				</button>
			</motion.div>
		</section>
	);
}

/* --- Simulation-Grade Graphics --- */

function VoiceNativeGraphic() {
	// "Neural Dialogue" - Instantaneous Exchange
	return (
		<div className="w-full h-full flex items-center justify-center relative bg-void overflow-hidden">
			{/* Connection Line */}
			<div className="absolute w-32 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />

			{/* Left Node (User) */}
			<motion.div
				className="absolute left-[25%] z-10"
				animate={{ scale: [1, 1.05, 1] }}
				transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, delay: 1.5 }}
			>
				<div className="w-12 h-12 rounded-full border border-white/20 bg-white/5 backdrop-blur-sm flex items-center justify-center relative">
					<div className="w-3 h-3 bg-white rounded-full shadow-[0_0_15px_rgba(255,255,255,0.5)]" />
					{/* Impact Ring */}
					<motion.div
						className="absolute inset-0 rounded-full border border-white/50"
						initial={{ scale: 1, opacity: 0 }}
						animate={{ scale: 1.8, opacity: [0, 0.5, 0] }}
						transition={{ duration: 0.6, repeat: Number.POSITIVE_INFINITY, delay: 1.6, repeatDelay: 1.4 }}
					/>
				</div>
			</motion.div>

			{/* Right Node (AI) */}
			<motion.div
				className="absolute right-[25%] z-10"
				animate={{ scale: [1, 1.05, 1] }}
				transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, delay: 0.5 }}
			>
				<div className="w-12 h-12 rounded-full border border-signal/20 bg-signal/5 backdrop-blur-sm flex items-center justify-center relative">
					<div className="w-3 h-3 bg-signal rounded-full shadow-[0_0_15px_rgba(16,185,129,0.4)]" />
					{/* Impact Ring */}
					<motion.div
						className="absolute inset-0 rounded-full border border-signal/50"
						initial={{ scale: 1, opacity: 0 }}
						animate={{ scale: 1.8, opacity: [0, 0.5, 0] }}
						transition={{ duration: 0.6, repeat: Number.POSITIVE_INFINITY, delay: 0.6, repeatDelay: 1.4 }}
					/>
				</div>
			</motion.div>

			{/* User Message (Left to Right) */}
			<motion.div
				className="absolute w-2 h-2 bg-white rounded-full shadow-[0_0_10px_rgba(255,255,255,0.8)]"
				initial={{ left: "25%", opacity: 0 }}
				animate={{
					left: ["25%", "75%"],
					opacity: [0, 1, 1, 0]
				}}
				transition={{
					duration: 0.5,
					repeat: Number.POSITIVE_INFINITY,
					repeatDelay: 1.5,
					ease: "linear"
				}}
			/>

			{/* AI Response (Right to Left) */}
			<motion.div
				className="absolute w-2 h-2 bg-signal rounded-full shadow-[0_0_10px_rgba(16,185,129,0.8)]"
				initial={{ right: "25%", opacity: 0 }}
				animate={{
					right: ["25%", "75%"],
					opacity: [0, 1, 1, 0]
				}}
				transition={{
					duration: 0.5,
					repeat: Number.POSITIVE_INFINITY,
					delay: 1.0,
					repeatDelay: 1.5,
					ease: "linear"
				}}
			/>
		</div>
	);
}

function AtomicCitationsGraphic() {
	// "Citation Linkage" - The tether between thought and source
	return (
		<div className="w-full h-full relative flex items-center justify-center bg-void overflow-hidden">
			{/* Chat Bubble (Top Left) */}
			<motion.div
				className="absolute left-[15%] top-[25%] w-48 p-4 rounded-xl rounded-bl-sm border border-white/10 bg-white/5 backdrop-blur-sm z-10"
				initial={{ y: 20, opacity: 0 }}
				animate={{ y: 0, opacity: 1 }}
				transition={{ duration: 1 }}
			>
				{/* Simulated Text Lines */}
				<div className="space-y-2 mb-2">
					<div className="w-full h-1.5 bg-white/20 rounded-full" />
					<div className="w-3/4 h-1.5 bg-white/20 rounded-full" />
					<div className="flex items-center gap-2">
						<div className="w-1/2 h-1.5 bg-white/20 rounded-full" />
						{/* Citation Badge */}
						<motion.div
							className="w-4 h-4 rounded-full bg-accent flex items-center justify-center relative"
							animate={{ scale: [1, 1.2, 1] }}
							transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, delay: 2 }}
						>
							<div className="w-2 h-2 bg-white rounded-full" />
							{/* Pulse ring from badge */}
							<motion.div
								className="absolute inset-0 rounded-full border border-accent"
								animate={{ scale: [1, 2], opacity: [1, 0] }}
								transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY, delay: 2 }}
							/>
						</motion.div>
					</div>
				</div>
			</motion.div>

			{/* Source Card (Bottom Right) */}
			<motion.div
				className="absolute right-[15%] bottom-[20%] w-44 p-3 rounded-lg border border-accent/20 bg-accent/5 backdrop-blur-sm z-10"
				initial={{ y: 20, opacity: 0 }}
				animate={{ y: 0, opacity: 1 }}
				transition={{ duration: 1, delay: 0.5 }}
			>
				{/* Header */}
				<div className="flex items-center gap-2 mb-3 border-b border-accent/10 pb-2">
					<div className="w-3 h-3 rounded-sm bg-accent/20" />
					<div className="w-16 h-1 bg-accent/20 rounded-full" />
				</div>
				{/* Content */}
				<div className="space-y-2">
					<div className="w-full h-1 bg-accent/10 rounded-full" />
					<div className="w-full h-1 bg-accent/10 rounded-full" />
					{/* Highlighted segment */}
					<motion.div
						className="w-3/4 h-1.5 bg-accent/40 rounded-full relative"
						animate={{ opacity: [0.4, 1, 0.4] }}
						transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, delay: 2 }}
					>
						{/* Glow effect on highlight */}
						<div className="absolute inset-0 bg-accent/20 blur-sm" />
					</motion.div>
					<div className="w-1/2 h-1 bg-accent/10 rounded-full" />
				</div>
			</motion.div>
		</div>
	);
}

function UniversalIngestGraphic() {
	const randomOffsets = React.useMemo(() => ({
		y: (Math.random() - 0.5) * 100,
		rotate: Math.random() * 20 - 10,
	}), []);
	// "The Singularity" - Many inputs, one output
	return (
		<div className="w-full h-full relative flex items-center justify-center bg-void overflow-hidden">
			{/* The Event Horizon (Boundary) */}
			<div className="relative z-10 w-1 bg-purple-500/50 h-24">
				<div className="absolute inset-0 bg-white/80" />
				{/* Pulse ring */}
				<motion.div
					className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-24 bg-purple-500/20 blur-sm rounded-full"
					animate={{ opacity: [0.2, 0.6, 0.2], scaleY: [0.8, 1.2, 0.8] }}
					transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
				/>
			</div>

			{/* Incoming Files (Left) */}
			{[...Array(6)].map((_, i) => (
				<motion.div
					key={`file-${i}`}
					className="absolute left-1/2 top-1/2 w-4 h-5 border border-purple-400/30 bg-purple-500/10 backdrop-blur-[1px] rounded-[2px]"
					initial={{ x: -140, y: randomOffsets.y, opacity: 0, scale: 0.8, rotate: randomOffsets.rotate }}
					animate={{
						x: 0,
						y: 0,
						opacity: [0, 1, 0],
						scale: 0.2,
						rotate: 0
					}}
					transition={{
						duration: 2,
						repeat: Number.POSITIVE_INFINITY,
						delay: i * 0.3,
						ease: "easeIn"
					}}
				>
					{/* Detail lines to make it look like a doc */}
					<div className="absolute top-1 left-1 right-1 h-[1px] bg-purple-400/40" />
					<div className="absolute top-2 left-1 right-1 h-[1px] bg-purple-400/40" />
				</motion.div>
			))}

			{/* Outgoing Ray (Right) */}
			<motion.div
				className="absolute left-1/2 top-1/2 -translate-y-1/2 h-1 bg-gradient-to-r from-white via-purple-400 to-transparent shadow-[0_0_20px_rgba(168,85,247,0.8)] rounded-full"
				initial={{ width: 0, opacity: 0 }}
				animate={{
					width: [0, 150],
					opacity: [0, 1, 0]
				}}
				transition={{
					duration: 1.5,
					repeat: Number.POSITIVE_INFINITY,
					ease: "easeOut",
					delay: 0.2
				}}
			/>

			{/* Impact Flash */}
			<motion.div
				className="absolute z-20 w-12 h-12 bg-purple-100/30 rounded-full blur-xl left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
				animate={{ scale: [0.5, 1.2, 0.5], opacity: [0, 0.5, 0] }}
				transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY }}
			/>
		</div>
	);
}

function IntelligentReasoningGraphic() {
	// "Layered Cogitation" - Ascending Logic
	return (
		<div className="w-full h-full flex items-center justify-center bg-void overflow-hidden perspective-[1000px]">
			<div
				className="relative w-40 h-40"
				style={{
					transformStyle: "preserve-3d",
					transform: "rotateX(60deg) rotateZ(45deg)"
				}}
			>
				{/* Stacked Layers */}
				{[0, 1, 2].map((i) => (
					<motion.div
						key={`layer-${i}`}
						className="absolute inset-0 border border-amber-500/20 bg-amber-500/5 backdrop-blur-[1px] shadow-[0_0_15px_rgba(245,158,11,0.05)]"
						style={{
							transform: `translateZ(${(i - 1) * 60}px)`
						}}
					>
						{/* Grid Pattern on Layer */}
						<div className="absolute inset-0 bg-[linear-gradient(rgba(245,158,11,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(245,158,11,0.1)_1px,transparent_1px)] bg-[size:10px_10px]" />

						{/* Activation Pulse */}
						<motion.div
							className="absolute inset-0 bg-amber-400/20"
							initial={{ opacity: 0 }}
							animate={{ opacity: [0, 0.8, 0] }}
							transition={{
								duration: 2,
								repeat: Number.POSITIVE_INFINITY,
								delay: i * 0.4 + 0.2, // Sequential timing
								ease: "easeOut"
							}}
						/>
					</motion.div>
				))}

				{/* Ascending Beam */}
				<motion.div
					className="absolute w-2 h-2 bg-white rounded-full blur-[2px] shadow-[0_0_10px_rgba(255,255,255,1)]"
					style={{ left: "50%", top: "50%", x: "-50%", y: "-50%" }}
					initial={{ translateZ: -100, opacity: 0 }}
					animate={{
						translateZ: [-100, 100],
						opacity: [0, 1, 1, 0]
					}}
					transition={{
						duration: 2,
						repeat: Number.POSITIVE_INFINITY,
						ease: "linear"
					}}
				/>
			</div>
		</div>
	);
}





function AdaptivePersonasGraphic() {
	// "The Persona Switcher" - Mimics actual UI dropdown
	const personas = [
		{ id: "default", color: "rgba(255,255,255,0.1)" },
		{ id: "tutor", color: "rgba(16,185,129,0.2)" }, // emerald
		{ id: "coder", color: "rgba(59,130,246,0.2)" }, // blue
		{ id: "friend", color: "rgba(244,63,94,0.2)" }, // rose
		{ id: "expert", color: "rgba(245,158,11,0.2)" }  // amber
	];
	const [activePersonaIndex, setActivePersonaIndex] = useState(0);

	useEffect(() => {
		const interval = setInterval(() => {
			setActivePersonaIndex((prevIndex) => (prevIndex + 1) % personas.length);
		}, 4000); // Change persona every 4 seconds
		return () => clearInterval(interval);
	}, [personas.length]);

	const currentPersona = personas[activePersonaIndex];

	return (
		<div className="w-full h-full relative flex items-center justify-center bg-void overflow-hidden">
			{/* Ambient Glow */}
			<motion.div
				className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full blur-[80px]"
				animate={{ backgroundColor: currentPersona.color }}
				transition={{ duration: 1 }}
			/>

			{/* Dropdown Menu - Animated appearance */}
			<motion.div
				className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-48 bg-black/90 backdrop-blur-xl border border-white/10 text-white rounded-xl overflow-hidden shadow-2xl z-10"
				initial={{ opacity: 0, scale: 0.9, y: 10 }}
				animate={{ opacity: [0, 1], scale: [0.9, 1], y: [10, 0] }}
				transition={{
					duration: 0.5,
					delay: 0.5,
					ease: "easeOut"
				}}
						>
							<div className="p-3">
					<div className="text-sm font-semibold mb-2">Agent Persona</div>
					<div className="h-px bg-white/10 mb-2" /> {/* Separator */}
					{personas.map((p, _idx) => (
						<motion.div
							key={p.id}
							className="flex items-center justify-between py-1.5 px-2 rounded-lg text-sm transition-colors"
							animate={{
								backgroundColor: currentPersona.id === p.id ? "rgba(255,255,255,0.1)" : "transparent"
							}}
							transition={{ duration: 0.2 }}
						>
							<span className="capitalize">{p.id}</span>
							<AnimatePresence>
								{currentPersona.id === p.id && (
									<motion.div
										initial={{ opacity: 0, scale: 0.5 }}
										animate={{ opacity: 1, scale: 1 }}
										exit={{ opacity: 0, scale: 0.5 }}
										transition={{ duration: 0.2 }}
									>
										<Check className="w-4 h-4 text-emerald-400" />
									</motion.div>
								)}
							</AnimatePresence>
						</motion.div>
					))}
				</div>
			</motion.div>
		</div>
	);
}

function UniversalSearchGraphic() {
	// "The Omni-Search" - Real UI mimicry
	return (
		<div className="w-full h-full relative flex items-center justify-center bg-void overflow-hidden">
			{/* Background - Blurred Content */}
			<div className="absolute inset-0 grid grid-cols-2 gap-4 p-8 opacity-20 scale-110 blur-sm pointer-events-none">
				<div className="h-32 bg-white/5 rounded-xl border border-white/5" />
				<div className="h-32 bg-white/5 rounded-xl border border-white/5" />
				<div className="h-32 col-span-2 bg-white/5 rounded-xl border border-white/5" />
			</div>

			{/* The Search Modal */}
			<motion.div
				className="relative w-64 bg-[#0A0A0A] border border-white/10 rounded-xl shadow-2xl overflow-hidden flex flex-col"
				initial={{ scale: 0.9, opacity: 0, y: 10 }}
				whileInView={{ scale: 1, opacity: 1, y: 0 }}
				viewport={{ once: true }}
				transition={{ duration: 0.5, delay: 0.2 }}
			>
				{/* Search Bar */}
				<div className="h-10 border-b border-white/10 flex items-center px-3 gap-2">
					<div className="w-3 h-3 rounded-full border border-white/20" />
					<div className="h-1.5 w-24 bg-white/20 rounded-full relative overflow-hidden">
						{/* Typing Effect */}
						<motion.div
							className="absolute inset-0 bg-white/40"
							initial={{ width: 0 }}
							animate={{ width: "100%" }}
							transition={{ duration: 1.5, delay: 1, ease: "linear", repeat: Number.POSITIVE_INFINITY, repeatDelay: 3 }}
						/>
					</div>
				</div>

				{/* Results List */}
				<div className="p-2 space-y-1.5">
					{[
						{ type: "chat", width: "60%" },
						{ type: "file", width: "80%" },
						{ type: "chat", width: "50%" },
						{ type: "file", width: "70%" },
					].map((item, i) => (
						<motion.div
							key={`search-item-${i}`}
							className="h-8 rounded bg-white/5 flex items-center px-2 gap-2 border border-transparent"
							initial={{ opacity: 0, x: -10 }}
							animate={{
								opacity: [0, 1, 1, 0],
								x: [0, 0, 0, 0],
								backgroundColor: ["rgba(255,255,255,0.05)", "rgba(255,255,255,0.05)", i === 1 ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.05)", "rgba(255,255,255,0.05)"]
							}}
							transition={{
								duration: 4,
								times: [0, 0.1, 0.8, 1],
								repeat: Number.POSITIVE_INFINITY,
								delay: 1.5 + (i * 0.1),
								repeatDelay: 0.5
							}}
						>
							<div className={`w-3 h-3 rounded-sm ${item.type === "chat" ? "bg-blue-500/40" : "bg-emerald-500/40"}`} />
							<div className="h-1.5 bg-white/10 rounded-full" style={{ width: item.width }} />
						</motion.div>
					))}
				</div>
			</motion.div>
		</div>
	);
}
