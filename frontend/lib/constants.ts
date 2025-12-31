/**
 * Centralized constants for the frontend application.
 */

/** Available persona options for AI interactions */
export const PERSONAS = [
	"default",
	"tutor",
	"coder",
	"friend",
	"expert",
	"quizzer",
] as const;
export type Persona = (typeof PERSONAS)[number];

/** Capitalize first letter of a string */
export const capitalize = (s: string): string =>
	s.charAt(0).toUpperCase() + s.slice(1);
