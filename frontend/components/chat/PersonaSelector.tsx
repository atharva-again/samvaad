import { Check, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useInputBarStore } from "@/lib/stores/useInputBarStore";
import { cn } from "@/lib/utils";

interface PersonaSelectorProps {
	className?: string;
	sideOffset?: number;
}

export function PersonaSelector({
	className,
	sideOffset = 16,
}: PersonaSelectorProps) {
	const { persona, setPersona } = useInputBarStore();
	const personas = ["default", "tutor", "coder", "friend", "expert"];

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button
					size="icon"
					type="button"
					variant="ghost"
					className={cn(
						"rounded-full w-10 h-10 text-text-secondary hover:bg-white/10 transition-colors",
						className,
					)}
				>
					<User className="w-5 h-5" />
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent
				align="end"
				side="top" // Ensure consistency
				sideOffset={sideOffset}
				className="w-48 bg-black/90 backdrop-blur-xl border-white/10 text-white mb-2"
			>
				<DropdownMenuLabel>Agent Persona</DropdownMenuLabel>
				<DropdownMenuSeparator className="bg-white/10" />
				{personas.map((p) => (
					<DropdownMenuItem
						key={p}
						onClick={() => setPersona(p)}
						className="cursor-pointer hover:bg-white/10 focus:bg-white/10 focus:text-white"
					>
						<span className="capitalize flex-1">{p}</span>
						{persona === p && <Check className="w-4 h-4 text-emerald-400" />}
					</DropdownMenuItem>
				))}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
