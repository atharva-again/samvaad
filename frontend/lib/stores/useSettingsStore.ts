import { create } from "zustand";
import { getUserSettings, updateUserSettings, type UserSettings } from "@/lib/api";

interface SettingsStore {
	// State
	settings: UserSettings | null;
	isLoading: boolean;
	error: string | null;

	// Actions
	loadSettings: () => Promise<void>;
	updateSettings: (settings: Partial<UserSettings>) => Promise<void>;
	setSettings: (settings: UserSettings) => void;
	setLoading: (loading: boolean) => void;
	setError: (error: string | null) => void;
	reset: () => void;
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
	// Initial state
	settings: null,
	isLoading: false,
	error: null,

	// Actions
	loadSettings: async () => {
		try {
			set({ isLoading: true, error: null });
			const settings = await getUserSettings();
			set({ settings, isLoading: false });
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : "Failed to load settings";
			set({ error: errorMessage, isLoading: false });
			throw error;
		}
	},

	updateSettings: async (updates: Partial<UserSettings>) => {
		try {
			set({ isLoading: true, error: null });
			const currentSettings = get().settings;
			if (!currentSettings) {
				throw new Error("No settings loaded");
			}

			const newSettings = { ...currentSettings, ...updates };
			const savedSettings = await updateUserSettings(newSettings);
			set({ settings: savedSettings, isLoading: false });
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : "Failed to update settings";
			set({ error: errorMessage, isLoading: false });
			throw error;
		}
	},

	setSettings: (settings: UserSettings) => set({ settings }),

	setLoading: (loading: boolean) => set({ isLoading: loading }),

	setError: (error: string | null) => set({ error }),

	reset: () => set({ settings: null, isLoading: false, error: null }),
}));