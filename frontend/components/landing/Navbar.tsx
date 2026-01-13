"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface NavbarProps {
	signInWithGoogle: () => void;
}

export function Navbar({ signInWithGoogle }: NavbarProps) {
	const [scrolled, setScrolled] = useState(false);

	useEffect(() => {
		const handleScroll = () => {
			setScrolled(window.scrollY > 20);
		};
		window.addEventListener("scroll", handleScroll);
		return () => window.removeEventListener("scroll", handleScroll);
	}, []);

	return (
		<nav
			className={cn(
				"fixed left-0 right-0 z-[100] transition-all duration-300 ease-out flex justify-center",
				scrolled ? "top-4 sm:top-6" : "top-0",
			)}
		>
			<div
				className={cn(
					"grid grid-cols-[1fr_auto_1fr] items-center transition-all duration-300 ease-out",
					scrolled
						? "w-[90%] sm:w-[500px] rounded-full bg-surface/80 border border-white/10 shadow-lg shadow-black/20 backdrop-blur-md px-4 py-2"
						: "w-full max-w-6xl px-4 sm:px-6 py-4 border-b border-transparent bg-transparent",
				)}
			>
				<div className={cn("flex items-center gap-2 group cursor-default select-none", scrolled && "ml-2")}>
					<div className="relative flex flex-col">
						<span
							className={cn(
								"font-medium tracking-tight transition-all duration-300",
								scrolled ? "text-sm text-text-secondary" : "text-lg text-text-primary",
							)}
						>
							Samvaad
						</span>
					</div>
				</div>

				<div className="flex items-center gap-6">
					<Link
						href="#features"
						className={cn(
							"text-sm font-medium transition-colors hover:text-white hidden sm:block",
							scrolled ? "text-text-secondary" : "text-text-secondary"
						)}
					>
						Features
					</Link>
					
					<Link
						href="https://github.com/atharva-again/samvaad"
						target="_blank"
						className={cn(
							"text-sm font-medium transition-colors hover:text-white",
							scrolled ? "text-text-secondary" : "text-text-secondary"
						)}
					>
						Github
					</Link>
				</div>

				<div className="flex items-center justify-end">
					<Button
						onClick={signInWithGoogle}
						variant={scrolled ? "secondary" : "outline"}
						size={scrolled ? "sm" : "default"}
						className={cn(
							"rounded-full transition-all duration-300 font-medium",
							scrolled
								? "h-8 px-4 text-xs bg-white/10 hover:bg-white/15 border-transparent text-white"
								: "bg-white/5 hover:bg-white/10 border-white/10 text-text-primary",
						)}
					>
						Launch App
					</Button>
				</div>
			</div>
		</nav>
	);
}
