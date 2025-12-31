import { AudioLines, Slash } from "lucide-react";
import { ActionTooltip } from "@/components/ui/action-tooltip";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface TTSToggleProps {
	enableTTS: boolean;
	setEnableTTS: (value: boolean) => void;
	className?: string;
}

export function TTSToggle({
	enableTTS,
	setEnableTTS,
	className,
}: TTSToggleProps) {
	return (
		<Button
			size="icon"
			type="button"
			variant="ghost"
			onClick={() => setEnableTTS(!enableTTS)}
			className={cn(
				"rounded-full w-10 h-10 transition-colors relative group hover:bg-white/10",
				// When TTS is disabled (V2T), we consider it the "State with Slash", similar to Strict Mode.
				// So !enableTTS -> Slash -> primary color? Or keep it simple.
				// User asked to remove green bg.
				!enableTTS ? "text-text-primary" : "text-text-secondary",
				className,
			)}
		>
			<div className="relative">
				{/* Base Icon: AudioLines (VTV) */}
				<AudioLines className="w-5 h-5" />

				{/* Slash Overlay: Show when TTS is DISABLED (V2T) */}
				{!enableTTS && (
					<div className="absolute inset-0 flex items-center justify-center">
						<Slash className="w-5 h-5 rotate-90 scale-125 stroke-[1.5px]" />
					</div>
				)}
			</div>
			<ActionTooltip
				label={
					enableTTS
						? "Voice-to-Voice: Agent speaks responses"
						: "Voice-to-Text: Agent replies with text only"
				}
				side="top"
			/>
		</Button>
	);
}
