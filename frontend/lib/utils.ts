import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

import { uuidv7 } from "uuidv7";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export function generateNewConversationId(): string {
	return uuidv7();
}

/**
 * Basic HTML escaping to prevent XSS in optimistic UI updates
 */
export function sanitizeInput(str: string): string {
	return str
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}

/**
 * Validates if a string is a valid UUID (v4 or v7)
 */
export function isValidUUID(uuid: string): boolean {
	const uuidRegex =
		/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
	return uuidRegex.test(uuid);
}
