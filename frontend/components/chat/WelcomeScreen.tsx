"use client";

import { BookOpen, Paperclip } from "lucide-react";
import type React from "react";
import { useEffect, useRef } from "react";
import { useFileProcessor } from "@/hooks/useFileProcessor";
import { usePlatform } from "@/hooks/usePlatform";
import { useUIStore } from "@/lib/stores/useUIStore";
import { cn } from "@/lib/utils";

export function WelcomeScreen() {
	const { modifier, isMobile } = usePlatform();
	const { toggleSourcesPanel } = useUIStore();
	const { processFiles } = useFileProcessor();
	const fileInputRef = useRef<HTMLInputElement>(null);
	const canvasRef = useRef<HTMLCanvasElement>(null);

	const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
		if (e.target.files && e.target.files.length > 0) {
			await processFiles(Array.from(e.target.files));
			e.target.value = "";
		}
	};

	useEffect(() => {
		const canvas = canvasRef.current;
		if (!canvas) return;

		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		let animationFrameId: number;
		let particles: Particle[] = [];
		const mouse = { x: -1000, y: -1000 };

		const resizeCanvas = () => {
			canvas.width = window.innerWidth;
			canvas.height = window.innerHeight;
			initParticles();
		};

		const handleMouseMove = (e: MouseEvent) => {
			const rect = canvas.getBoundingClientRect();
			mouse.x = e.clientX - rect.left;
			mouse.y = e.clientY - rect.top;
		};

		const handleMouseLeave = () => {
			mouse.x = -1000;
			mouse.y = -1000;
		};

		class Particle {
			x: number;
			y: number;
			vx: number;
			vy: number;
			size: number;
			baseVx: number;
			baseVy: number;

			constructor() {
				this.x = Math.random() * canvas!.width;
				this.y = Math.random() * canvas!.height;
				this.baseVx = (Math.random() - 0.5) * 0.2;
				this.baseVy = (Math.random() - 0.5) * 0.2;
				this.vx = this.baseVx;
				this.vy = this.baseVy;
				this.size = Math.random() * 1.5 + 0.5;
			}

			update() {
				const dx = mouse.x - this.x;
				const dy = mouse.y - this.y;
				const distance = Math.sqrt(dx * dx + dy * dy);
				const maxDistance = 200;

				if (distance < maxDistance) {
					const forceDirectionX = dx / distance;
					const forceDirectionY = dy / distance;
					const force = (maxDistance - distance) / maxDistance;
					const directionX = forceDirectionX * force * 0.05;
					const directionY = forceDirectionY * force * 0.05;

					this.vx += directionX;
					this.vy += directionY;
				} else {
					if (this.vx !== this.baseVx) {
						this.vx += (this.baseVx - this.vx) * 0.02;
					}
					if (this.vy !== this.baseVy) {
						this.vy += (this.baseVy - this.vy) * 0.02;
					}
				}

				this.x += this.vx;
				this.y += this.vy;

				if (this.x < 0 || this.x > canvas!.width) {
					this.vx *= -1;
					this.baseVx *= -1;
				}
				if (this.y < 0 || this.y > canvas!.height) {
					this.vy *= -1;
					this.baseVy *= -1;
				}
			}

			draw() {
				if (!ctx) return;
				ctx.beginPath();
				ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
				ctx.fillStyle = "rgba(255, 255, 255, 0.3)";
				ctx.fill();
			}
		}

		const initParticles = () => {
			particles = [];
			const particleCount = isMobile ? 30 : 50;
			for (let i = 0; i < particleCount; i++) {
				particles.push(new Particle());
			}
		};

		const animate = () => {
			if (!ctx || !canvas) return;
			ctx.clearRect(0, 0, canvas.width, canvas.height);

			for (let i = 0; i < particles.length; i++) {
				particles[i].update();
				particles[i].draw();

				for (let j = i + 1; j < particles.length; j++) {
					const dx = particles[i].x - particles[j].x;
					const dy = particles[i].y - particles[j].y;
					const distance = Math.sqrt(dx * dx + dy * dy);
					const maxDistance = 150;

					if (distance < maxDistance) {
						ctx.beginPath();
						ctx.strokeStyle = `rgba(255, 255, 255, ${
							(1 - distance / maxDistance) * 0.15
						})`;
						ctx.lineWidth = 0.5;
						ctx.moveTo(particles[i].x, particles[i].y);
						ctx.lineTo(particles[j].x, particles[j].y);
						ctx.stroke();
					}
				}

				if (!isMobile) {
					const dx = particles[i].x - mouse.x;
					const dy = particles[i].y - mouse.y;
					const distance = Math.sqrt(dx * dx + dy * dy);
					const maxDistance = 200;

					if (distance < maxDistance) {
						ctx.beginPath();
						ctx.strokeStyle = `rgba(255, 255, 255, ${
							(1 - distance / maxDistance) * 0.2
						})`;
						ctx.lineWidth = 0.5;
						ctx.moveTo(particles[i].x, particles[i].y);
						ctx.lineTo(mouse.x, mouse.y);
						ctx.stroke();
					}
				}
			}

			animationFrameId = requestAnimationFrame(animate);
		};

		window.addEventListener("resize", resizeCanvas);
		if (!isMobile) {
			window.addEventListener("mousemove", handleMouseMove);
			window.addEventListener("mouseleave", handleMouseLeave);
		}
		
		resizeCanvas();
		animate();

		return () => {
			window.removeEventListener("resize", resizeCanvas);
			if (!isMobile) {
				window.removeEventListener("mousemove", handleMouseMove);
				window.removeEventListener("mouseleave", handleMouseLeave);
			}
			cancelAnimationFrame(animationFrameId);
		};
	}, [isMobile]);

	const shortcuts = [
		{
			keys: `${modifier}+A`,
			label: "Attach Files",
			icon: Paperclip,
			action: () => fileInputRef.current?.click(),
		},
		{
			keys: `${modifier}+S`,
			label: "Sources",
			icon: BookOpen,
			action: () => toggleSourcesPanel(),
		},
	];

	return (
		<div className="flex-1 flex flex-col items-center justify-center relative overflow-hidden p-4 md:p-0 bg-background">
			<canvas
				ref={canvasRef}
				className="absolute inset-0 pointer-events-none"
			/>

			<input
				type="file"
				multiple
				ref={fileInputRef}
				className="hidden"
				onChange={handleFileSelect}
			/>

			<div className="relative z-10 flex flex-col items-center text-center max-w-2xl w-full px-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
				<div className="mb-12 space-y-4">
					<h1 className="text-4xl md:text-5xl font-bold tracking-tight text-primary drop-shadow-sm">
						Samvaad
					</h1>
					<p className="text-lg md:text-xl text-muted-foreground font-light tracking-wide max-w-lg mx-auto leading-relaxed">
						Transform your static documents into dynamic conversations
					</p>
				</div>

				<div className="w-full max-w-md">
					<div className="flex items-center gap-4 mb-6">
						<div className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
						<span className="text-[10px] font-bold text-muted-foreground/40 uppercase tracking-[0.2em]">
							Quick Actions
						</span>
						<div className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
					</div>

					<div className="grid grid-cols-2 gap-4">
						{shortcuts.map((shortcut) => (
							<button
								key={shortcut.label}
								onClick={shortcut.action}
								className={cn(
									"group flex items-center justify-between p-3 rounded-xl text-left",
									"bg-card/50 backdrop-blur-sm border border-border/50",
									"hover:bg-accent/50 hover:border-accent",
									"transition-all duration-300 ease-out shadow-sm hover:shadow-md cursor-pointer",
									"focus:outline-none focus:ring-1 focus:ring-ring"
								)}
								type="button"
							>
								<div className="flex items-center gap-3">
									<shortcut.icon className="w-4 h-4 text-foreground/70 group-hover:text-foreground transition-colors shrink-0" />
									<span className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">
										{shortcut.label}
									</span>
								</div>
								{!isMobile && (
									<kbd className="min-w-[1.2rem] h-5 px-1.5 flex items-center justify-center bg-muted/50 rounded text-[10px] font-mono text-muted-foreground/70 font-bold border border-border/50">
										{shortcut.keys}
									</kbd>
								)}
							</button>
						))}
					</div>
				</div>
			</div>
		</div>
	);
}
