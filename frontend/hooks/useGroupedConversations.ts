import { useMemo } from "react";
import type { Conversation } from "@/lib/stores/useConversationStore";

export interface GroupedConversations {
	pinned: Conversation[];
	today: Conversation[];
	yesterday: Conversation[];
	previous7Days: Conversation[];
	// Monthly buckets for older conversations (key format: "Month Year", e.g., "December 2024")
	months: { [key: string]: Conversation[] };
}

// Helper to get month-year key from a date
const getMonthKey = (date: Date): string => {
	const months = [
		"January",
		"February",
		"March",
		"April",
		"May",
		"June",
		"July",
		"August",
		"September",
		"October",
		"November",
		"December",
	];
	return `${months[date.getMonth()]} ${date.getFullYear()}`;
};

export function useGroupedConversations(
	conversations: Conversation[],
	searchQuery: string = "",
) {
	return useMemo<GroupedConversations>(() => {
		const groups: GroupedConversations = {
			pinned: [],
			today: [],
			yesterday: [],
			previous7Days: [],
			months: {},
		};

		// All dates use browser's local timezone
		const now = new Date();
		const today = new Date(
			now.getFullYear(),
			now.getMonth(),
			now.getDate(),
		).getTime();
		const yesterday = today - 86400000;
		const lastWeek = today - 7 * 86400000;

		// Filter by search query first
		const filtered = conversations.filter((c) =>
			c.title.toLowerCase().includes(searchQuery.toLowerCase()),
		);

		filtered.forEach((conv) => {
			if (conv.isPinned) {
				groups.pinned.push(conv);
				// Note: Intentionally NOT returning here so pinned items also appear in history
			}

			const convDate = new Date(conv.updatedAt || conv.createdAt);
			const timestamp = convDate.getTime();

			if (timestamp >= today) {
				groups.today.push(conv);
			} else if (timestamp >= yesterday) {
				groups.yesterday.push(conv);
			} else if (timestamp >= lastWeek) {
				groups.previous7Days.push(conv);
			} else {
				// Group by month for older conversations
				const monthKey = getMonthKey(convDate);
				if (!groups.months[monthKey]) {
					groups.months[monthKey] = [];
				}
				groups.months[monthKey].push(conv);
			}
		});

		return groups;
	}, [conversations, searchQuery]);
}
