import { Brain, Slash } from "lucide-react";
import { ActionTooltip } from "@/components/ui/action-tooltip";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface StrictModeToggleProps {
	strictMode: boolean;
	setStrictMode: (value: boolean) => void;
	className?: string; // Allow overriding classes if needed
}

export function StrictModeToggle({
	strictMode,
	setStrictMode,
	className,
}: StrictModeToggleProps) {
	return (
		<Button
			size="icon"
			type="button"
			variant="ghost"
			onClick={() => setStrictMode(!strictMode)}
			className={cn(
				"rounded-full w-10 h-10 transition-colors relative group hover:bg-white/10",
				strictMode ? "text-text-primary" : "text-text-secondary",
				className,
			)}
		>
			<div className="relative">
				<Brain className="w-5 h-5" />
				{strictMode && (
					<div className="absolute inset-0 flex items-center justify-center">
						<Slash className="w-5 h-5 rotate-90 scale-125 stroke-[1.5px]" />
					</div>
				)}
			</div>
			<ActionTooltip
				label={
					strictMode
						? "Strict Mode: Answers using ONLY your sources"
						: "Hybrid Mode: Uses sources + general knowledge"
				}
				side="top"
			/>
		</Button>
	);
}
