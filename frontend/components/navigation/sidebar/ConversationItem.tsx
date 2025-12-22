import React, { useState } from "react";
import Link from "next/link";
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
    onRename?: (newTitle: string) => void;
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
    onToggleSelect
}: ConversationItemProps) {
    const [showMenu, setShowMenu] = useState(false);
    const [isHovered, setIsHovered] = useState(false);

    // Inline Renaming State
    const [isEditing, setIsEditing] = useState(false);
    const [editTitle, setEditTitle] = useState(conversation.title);
    const inputRef = React.useRef<HTMLInputElement>(null);

    React.useEffect(() => {
        if (isEditing) {
            inputRef.current?.focus();
            inputRef.current?.select();
        }
    }, [isEditing]);

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

    const handleRenameSubmit = async () => {
        if (!editTitle.trim() || editTitle === conversation.title) {
            setIsEditing(false);
            setEditTitle(conversation.title);
            return;
        }
        await onRename?.(editTitle);
        setIsEditing(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleRenameSubmit();
        } else if (e.key === 'Escape') {
            setIsEditing(false);
            setEditTitle(conversation.title);
        }
    };

    // Checkbox Component
    const Checkbox = () => (
        <div className={cn(
            "w-4 h-4 rounded border flex items-center justify-center transition-all",
            isSelected
                ? "bg-blue-500 border-blue-500"
                : "border-white/30 group-hover:border-white/50"
        )}>
            {isSelected && <div className="w-2 h-2 bg-white rounded-[1px]" />}
        </div>
    );

    return (
        <div
            className="relative group w-full"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            onClick={handleClick}
        >
            {isEditing ? (
                <div className={cn(
                    "flex items-center text-left py-1.5 text-[13px] rounded-md bg-white/10",
                    isInsidePopover
                        ? "w-[calc(100%-8px)] mx-1 px-2"
                        : "ml-9 w-[calc(100%-36px)] pl-2 pr-8"
                )}>
                    {isSelectMode && (
                        <div className="mr-3 shrink-0">
                            <Checkbox />
                        </div>
                    )}
                    <input
                        ref={inputRef}
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={handleRenameSubmit}
                        onKeyDown={handleKeyDown}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full bg-transparent border-none outline-none text-white p-0 m-0 leading-none h-auto truncate"
                    />
                </div>
            ) : (
                <Link
                    href={isSelectMode ? "#" : `/chat/${conversation.id}`}
                    onClick={e => isSelectMode && e.preventDefault()}
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
                                : (isInsidePopover ? "text-white/70 group-hover:text-white group-hover:bg-white/5" : "text-white/60 group-hover:text-white group-hover:bg-white/5"),
                        isSelectMode && isSelected && "bg-white/10"
                    )}
                >
                    {isSelectMode && (
                        <div className="mr-3 shrink-0">
                            <Checkbox />
                        </div>
                    )}
                    <span className="truncate">{conversation.title}</span>
                </Link>
            )}

            {/* Three-dot menu button - Hidden in select mode and editing mode */}
            {!isSelectMode && !isEditing && (
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
                                setIsEditing(true);
                                setEditTitle(conversation.title);
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
            )}
        </div>
    );
}
