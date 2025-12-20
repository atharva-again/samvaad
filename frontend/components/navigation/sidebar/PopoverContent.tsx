import React from "react";
import { Conversation } from "@/lib/stores/useConversationStore";
import { GroupedConversations } from "@/hooks/useGroupedConversations";
import { ConversationItem } from "./ConversationItem";

interface PopoverContentProps {
    title: string;
    conversations: Conversation[] | GroupedConversations;
    grouped?: boolean;
    isLoading?: boolean;
    onRename?: (id: string) => void;
    onPin?: (id: string) => void;
    onDelete?: (id: string) => void;
    onMenuOpenChange?: (open: boolean) => void;
}

// Skeleton loader component for loading state
function ConversationSkeleton() {
    return (
        <div className="w-[calc(100%-8px)] mx-1 px-2 py-1.5 rounded-md animate-pulse">
            <div className="h-4 bg-white/10 rounded w-3/4" />
        </div>
    );
}

export function PopoverContent({
    title,
    conversations,
    grouped = false,
    isLoading = false,
    onRename,
    onPin,
    onDelete,
    onMenuOpenChange
}: PopoverContentProps) {
    const totalItems = grouped
        ? (conversations as GroupedConversations).today.length +
        (conversations as GroupedConversations).yesterday.length +
        (conversations as GroupedConversations).previous7Days.length +
        Object.values((conversations as GroupedConversations).months).reduce((sum, arr) => sum + arr.length, 0)
        : (conversations as Conversation[]).length;

    const renderItem = (conv: Conversation) => (
        <ConversationItem
            key={conv.id}
            conversation={conv}
            isActive={false}
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

    // Loading skeleton
    if (isLoading) {
        return (
            <div className="py-2 max-h-[400px] overflow-y-auto">
                <div className="px-3 py-2 text-[11px] font-semibold text-white/60 uppercase tracking-wider border-b border-white/5 mb-1">
                    {title}
                </div>
                <div className="space-y-1 py-1">
                    <ConversationSkeleton />
                    <ConversationSkeleton />
                    <ConversationSkeleton />
                </div>
            </div>
        );
    }

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
                    {/* Monthly groups (older conversations) */}
                    {Object.entries((conversations as GroupedConversations).months)
                        .sort(([a], [b]) => {
                            // Sort by date descending (most recent month first)
                            const parseMonth = (key: string) => {
                                const [month, year] = key.split(' ');
                                const monthIndex = ['January', 'February', 'March', 'April', 'May', 'June',
                                    'July', 'August', 'September', 'October', 'November', 'December'].indexOf(month);
                                return new Date(parseInt(year), monthIndex).getTime();
                            };
                            return parseMonth(b) - parseMonth(a);
                        })
                        .map(([monthKey, convs]) => renderGroup(monthKey, convs))
                    }
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

