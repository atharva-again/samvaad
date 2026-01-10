export const PERSONAS = [
  { id: "default", name: "Default" },
  { id: "tutor", name: "Tutor" },
  { id: "coder", name: "Coder" },
  { id: "friend", name: "Friend" },
  { id: "expert", name: "Expert" },
  { id: "quizzer", name: "Quizzer" },
] as const;

export type PersonaId = (typeof PERSONAS)[number]["id"];

export const capitalize = (s: string): string =>
  s.charAt(0).toUpperCase() + s.slice(1);

export const COLORS = {
  void: "#030303",
  surface: "#121212",
  surfaceLight: "#1a1a1a",
  signal: "#10b981",
  accent: "#3b82f6",
  textPrimary: "#f3f4f6",
  textSecondary: "#9ca3af",
  white: "#ffffff",
  black: "#000000",
  error: "#ef4444",
  success: "#22c55e",
  warning: "#f59e0b",
} as const;
