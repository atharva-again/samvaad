import { useMemo } from "react";
import { Conversation } from "@/lib/stores/useConversationStore";

export interface GroupedConversations {
    pinned: Conversation[];
    today: Conversation[];
    yesterday: Conversation[];
    previous7Days: Conversation[];
    older: Conversation[];
}

export function useGroupedConversations(conversations: Conversation[], searchQuery: string = "") {
    return useMemo<GroupedConversations>(() => {
        const groups: GroupedConversations = {
            pinned: [],
            today: [],
            yesterday: [],
            previous7Days: [],
            older: []
        };

        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const yesterday = today - 86400000;
        const lastWeek = today - 7 * 86400000;

        // Filter by search query first
        const filtered = conversations.filter(c =>
            c.title.toLowerCase().includes(searchQuery.toLowerCase())
        );

        filtered.forEach(conv => {
            if (conv.isPinned) {
                groups.pinned.push(conv);
                // Note: Intentionally NOT returning here so pinned items also appear in history
                // per recent UX requirements.
            }

            const date = new Date(conv.updatedAt || conv.createdAt).getTime();
            if (date >= today) groups.today.push(conv);
            else if (date >= yesterday) groups.yesterday.push(conv);
            else if (date >= lastWeek) groups.previous7Days.push(conv);
            else groups.older.push(conv);
        });

        return groups;
    }, [conversations, searchQuery]);
}
