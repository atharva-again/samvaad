"use client";

import { useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { ChatView } from "@/components/chat/ChatView";
import { SourcesPanel } from "@/components/chat/SourcesPanel";
import { AppMockup } from "@/components/landing/AppMockup";
import { Features } from "@/components/landing/Features";
import { Footer } from "@/components/landing/Footer";
import { Hero } from "@/components/landing/Hero";
import { Navbar } from "@/components/landing/Navbar";
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
		<div
			ref={containerRef}
			className="min-h-screen text-white selection:bg-signal/30 selection:text-white font-sans overflow-x-hidden antialiased"
		>
			<Navbar signInWithGoogle={signInWithGoogle} />

			<main className="relative z-10 bg-[#030303] mb-[500px] md:mb-[600px] shadow-2xl">
				<Hero
					signInWithGoogle={signInWithGoogle}
					opacity={opacity}
					scale={scale}
				/>
				<AppMockup />
				<Features signInWithGoogle={signInWithGoogle} />
			</main>

			<Footer />
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
