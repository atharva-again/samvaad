import React from "react";
import { Conversation } from "@/lib/stores/useConversationStore";
import { GroupedConversations } from "@/hooks/useGroupedConversations";
import { ConversationItem } from "./ConversationItem";

interface PopoverContentProps {
    title: string;
    conversations: Conversation[] | GroupedConversations;
    grouped?: boolean;
    onSelect: (id: string) => void;
    onRename?: (id: string) => void;
    onPin?: (id: string) => void;
    onDelete?: (id: string) => void;
    onMenuOpenChange?: (open: boolean) => void;
}

export function PopoverContent({
    title,
    conversations,
    grouped = false,
    onSelect,
    onRename,
    onPin,
    onDelete,
    onMenuOpenChange
}: PopoverContentProps) {
    const totalItems = grouped
        ? (conversations as GroupedConversations).today.length +
        (conversations as GroupedConversations).yesterday.length +
        (conversations as GroupedConversations).previous7Days.length +
        (conversations as GroupedConversations).older.length
        : (conversations as Conversation[]).length;

    const renderItem = (conv: Conversation) => (
        <ConversationItem
            key={conv.id}
            conversation={conv}
            isActive={false}
            onSelect={() => onSelect(conv.id)}
            onRename={() => onRename?.(conv.id)}
            onPin={() => onPin?.(conv.id)}
            onDelete={() => onDelete?.(conv.id)}
            isInsidePopover={true}
            onMenuOpenChange={onMenuOpenChange}
        />
    );

    const renderGroup = (label: string, items: Conversation[]) => {
        if (items.length === 0) return null;
        return (
            <div key={label}>
                <div className="px-3 py-1.5 text-[11px] font-medium text-white/40 uppercase tracking-wider">
                    {label}
                </div>
                {items.slice(0, 5).map(renderItem)}
            </div>
        );
    };

    return (
        <div className="py-2 max-h-[400px] overflow-y-auto">
            <div className="px-3 py-2 text-[11px] font-semibold text-white/60 uppercase tracking-wider border-b border-white/5 mb-1">
                {title}
            </div>
            {grouped ? (
                <>
                    {renderGroup("Today", (conversations as GroupedConversations).today)}
                    {renderGroup("Yesterday", (conversations as GroupedConversations).yesterday)}
                    {renderGroup("Previous 7 Days", (conversations as GroupedConversations).previous7Days)}
                    {renderGroup("Older", (conversations as GroupedConversations).older)}
                </>
            ) : (
                (conversations as Conversation[]).length > 0
                    ? (conversations as Conversation[]).map(renderItem)
                    : <div className="px-3 py-4 text-[13px] text-white/30 text-center">No items</div>
            )}
            {totalItems > 10 && (
                <button className="w-[calc(100%-8px)] px-2 py-2 mx-1 rounded-md text-[13px] text-white/50 hover:text-white hover:bg-white/5 text-left border-t border-white/5 mt-1 cursor-pointer">
                    See all
                </button>
            )}
        </div>
    );
}
