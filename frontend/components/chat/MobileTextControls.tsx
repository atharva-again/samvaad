"use client";

import { Brain, Settings, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { capitalize, PERSONAS } from "@/lib/constants";
import { useInputBarStore } from "@/lib/stores/useInputBarStore";
import { cn } from "@/lib/utils";

interface MobileTextControlsProps {
	className?: string;
	sideOffset?: number;
}

export function MobileTextControls({
	className,
	sideOffset = 16,
}: MobileTextControlsProps) {
	const { strictMode, toggleStrictMode, persona, setPersona } = useInputBarStore();
	return (
		<Popover>
			<PopoverTrigger asChild>
				<Button
					size="icon"
					variant="ghost"
					className={cn(
						"rounded-full w-12 h-12 text-text-primary hover:bg-white/10 transition-colors",
						className,
					)}
				>
					<Settings className="w-6 h-6" />
				</Button>
			</PopoverTrigger>
			<PopoverContent
				side="top"
				align="end"
				sideOffset={sideOffset}
				alignOffset={-12}
				className="w-[90vw] max-w-[320px] bg-black/95 backdrop-blur-xl border-white/10 text-white p-5 rounded-2xl shadow-2xl shadow-black/50"
			>
				<div className="space-y-6">
					<div className="flex items-center justify-between border-b border-white/10 pb-3">
						<span className="text-sm font-semibold text-white/90">
							Chat Settings
						</span>
					</div>

					{/* Strict Mode Toggle */}
					<div className="grid grid-cols-1 gap-3">
						<button
							type="button"
							onClick={toggleStrictMode}
							className={cn(
								"flex flex-col items-start gap-2 p-3 rounded-xl border transition-all relative overflow-hidden",
								strictMode
									? "bg-white/10 border-white/20 text-white"
									: "bg-transparent border-white/5 text-text-secondary hover:bg-white/5",
							)}
						>
							<div className="flex items-center gap-3 w-full">
								<div
									className={cn(
										"p-2 rounded-lg transition-colors bg-white/5 text-white/80",
									)}
								>
									<Brain className="w-4 h-4" />
								</div>
								<div className="flex flex-col items-start">
									<span
										className={cn(
											"text-xs font-semibold",
											strictMode ? "text-white" : "text-text-secondary",
										)}
									>
										{strictMode ? "Strict Mode" : "Hybrid Mode"}
									</span>
									<span className="text-[10px] text-white/40">
										{strictMode ? "Sources Only" : "Sources + GK"}
									</span>
								</div>
							</div>
						</button>
					</div>

					{/* Persona Selector (Chips) */}
					<div className="space-y-3">
						<div className="text-xs font-medium text-text-secondary flex items-center gap-2">
							<User className="w-3.5 h-3.5" /> Persona
						</div>
						<div className="flex flex-wrap gap-2">
							{PERSONAS.map((p) => (
								<button
									type="button"
									key={p}
									onClick={() => setPersona(p)}
									className={cn(
										"px-3 py-1.5 rounded-full text-xs font-medium border transition-all flex items-center gap-1.5",
										persona === p
											? "bg-white text-black border-white"
											: "bg-transparent text-text-secondary border-white/10 hover:border-white/20",
									)}
								>
									{capitalize(p)}
								</button>
							))}
						</div>
					</div>
				</div>
			</PopoverContent>
		</Popover>
	);
}
