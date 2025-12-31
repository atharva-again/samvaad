import { MoreVertical, Pencil, Pin, Trash2 } from "lucide-react";
import Link from "next/link";
import type React from "react";
import { useState } from "react";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Conversation } from "@/lib/stores/useConversationStore";
import { cn } from "@/lib/utils";

interface ConversationItemProps {
	conversation: Conversation;
	isActive: boolean;
	onRename?: () => void;
	onPin?: () => void;
	onDelete?: () => void;
	isInsidePopover?: boolean;
	onMenuOpenChange?: (open: boolean) => void;

	// Selection Props
	isSelectMode?: boolean;
	isSelected?: boolean;
	onToggleSelect?: () => void;
}

export function ConversationItem({
	conversation,
	isActive,
	onRename,
	onPin,
	onDelete,
	isInsidePopover = false,
	onMenuOpenChange,
	isSelectMode = false,
	isSelected = false,
	onToggleSelect,
}: ConversationItemProps) {
	const [showMenu, setShowMenu] = useState(false);
	const [isHovered, setIsHovered] = useState(false);

	const handleOpenChange = (open: boolean) => {
		setShowMenu(open);
		onMenuOpenChange?.(open);
	};

	const handleClick = (e: React.MouseEvent) => {
		if (isSelectMode) {
			e.preventDefault();
			e.stopPropagation();
			onToggleSelect?.();
		}
	};

	// Checkbox Component
	const Checkbox = () => (
		<div
			className={cn(
				"w-4 h-4 rounded border flex items-center justify-center transition-all",
				isSelected
					? "bg-blue-500 border-blue-500"
					: "border-white/30 group-hover:border-white/50",
			)}
		>
			{isSelected && <div className="w-2 h-2 bg-white rounded-[1px]" />}
		</div>
	);

	return (
		<div
			className="relative group w-full"
			onMouseEnter={() => setIsHovered(true)}
			onMouseLeave={() => setIsHovered(false)}
			onClick={handleClick}
			onKeyDown={(e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					e.preventDefault();
					handleClick(e as unknown as React.MouseEvent);
				}
			}}
			role="button"
			tabIndex={0}
		>
			<Link
				href={isSelectMode ? "#" : `/chat/${conversation.id}`}
				onClick={(e) => isSelectMode && e.preventDefault()}
				className={cn(
					"flex items-center text-left py-1.5 text-[13px] truncate transition-colors cursor-pointer",
					// Layout adaptations for select mode
					isInsidePopover
						? "w-[calc(100%-8px)] mx-1 px-2 rounded-md"
						: "ml-9 w-[calc(100%-36px)] pl-2 pr-8 rounded-md",
					isActive && !isSelectMode
						? "bg-white/10 text-white"
						: showMenu
							? "bg-white/5 text-white"
							: isInsidePopover
								? "text-white/70 group-hover:text-white group-hover:bg-white/5"
								: "text-white/60 group-hover:text-white group-hover:bg-white/5",
					isSelectMode && isSelected && "bg-white/10",
				)}
			>
				{isSelectMode && (
					<div className="mr-3 shrink-0">
						<Checkbox />
					</div>
				)}
				<span className="truncate">{conversation.title}</span>
			</Link>

			{/* Three-dot menu button - Hidden in select mode */}
			{!isSelectMode && (
				<DropdownMenu onOpenChange={handleOpenChange}>
					<DropdownMenuTrigger asChild>
						<button
							onClick={(e) => e.stopPropagation()}
							className={cn(
								"absolute top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center rounded-md transition-opacity outline-none",
								isInsidePopover ? "right-2" : "right-1",
								isHovered || showMenu ? "opacity-100" : "opacity-0",
								"hover:bg-white/10 text-white/50 hover:text-white cursor-pointer",
							)}
							type="button"
						>
							<MoreVertical className="w-3.5 h-3.5" />
						</button>
					</DropdownMenuTrigger>
					<DropdownMenuContent
						align="end"
						className="w-40 bg-[#0F0F0F] border-white/10 text-white z-[200]"
					>
						<DropdownMenuItem
							onClick={(e) => {
								e.stopPropagation();
								onRename?.();
							}}
							className="gap-2 text-[13px] text-white/70 focus:text-white focus:bg-white/10 cursor-pointer"
						>
							<Pencil className="w-4 h-4" />
							Rename
						</DropdownMenuItem>
						<DropdownMenuItem
							onClick={(e) => {
								e.stopPropagation();
								onPin?.();
							}}
							className="gap-2 text-[13px] text-white/70 focus:text-white focus:bg-white/10 cursor-pointer"
						>
							<Pin
								className="w-4 h-4"
								fill={conversation.isPinned ? "currentColor" : "none"}
							/>
							{conversation.isPinned ? "Unpin" : "Pin"}
						</DropdownMenuItem>
						<DropdownMenuItem
							onClick={(e) => {
								e.stopPropagation();
								onDelete?.();
							}}
							className="gap-2 text-[13px] text-red-400 focus:text-red-300 focus:bg-white/10 cursor-pointer"
						>
							<Trash2 className="w-4 h-4 text-red-400" />
							Delete
						</DropdownMenuItem>
					</DropdownMenuContent>
				</DropdownMenu>
			)}
		</div>
	);
}
