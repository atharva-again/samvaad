import React, { useState } from "react";
import { MoreVertical, Pencil, Pin, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Conversation } from "@/lib/stores/useConversationStore";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ConversationItemProps {
    conversation: Conversation;
    isActive: boolean;
    onSelect: () => void;
    onRename?: () => void;
    onPin?: () => void;
    onDelete?: () => void;
    isInsidePopover?: boolean;
    onMenuOpenChange?: (open: boolean) => void;
}

export function ConversationItem({
    conversation,
    isActive,
    onSelect,
    onRename,
    onPin,
    onDelete,
    isInsidePopover = false,
    onMenuOpenChange
}: ConversationItemProps) {
    const [showMenu, setShowMenu] = useState(false);
    const [isHovered, setIsHovered] = useState(false);

    const handleOpenChange = (open: boolean) => {
        setShowMenu(open);
        onMenuOpenChange?.(open);
    };

    return (
        <div
            className="relative group w-full"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <button
                onClick={onSelect}
                className={cn(
                    "text-left py-1.5 text-[13px] truncate transition-colors cursor-pointer",
                    // If inside popover OR collapsed (though collapsed items aren't rendered here? No, they are hidden), use standard pill.
                    // If expanded sidebar (not inside popover), use ml-11 to align with H of History.
                    isInsidePopover
                        ? "w-[calc(100%-8px)] mx-1 px-2 rounded-md"
                        : "ml-9 w-[calc(100%-36px)] pl-2 pr-8 rounded-md",
                    isActive
                        ? "bg-white/10 text-white"
                        : showMenu
                            ? "bg-white/5 text-white"
                            : (isInsidePopover ? "text-white/70 group-hover:text-white group-hover:bg-white/5" : "text-white/60 group-hover:text-white group-hover:bg-white/5")
                )}
            >
                {conversation.title}
            </button>

            {/* Three-dot menu button */}
            <DropdownMenu onOpenChange={handleOpenChange}>
                <DropdownMenuTrigger asChild>
                    <button
                        onClick={(e) => e.stopPropagation()}
                        className={cn(
                            "absolute top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center rounded-md transition-opacity outline-none",
                            isInsidePopover ? "right-2" : "right-1",
                            isHovered || showMenu ? "opacity-100" : "opacity-0",
                            "hover:bg-white/10 text-white/50 hover:text-white cursor-pointer"
                        )}
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
                        <Pin className="w-4 h-4" />
                        {conversation.isPinned ? 'Unpin' : 'Pin'}
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
        </div>
    );
}
