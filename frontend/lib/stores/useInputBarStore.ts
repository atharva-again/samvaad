import { create } from "zustand";
import { persist } from "zustand/middleware";

export type VoiceState = "listening" | "processing" | "answering" | "error";

interface InputBarState {
	// Mode Selection
	mode: "text" | "voice";
	hasInteracted: boolean;

	// Shared Settings (Text & Voice) - now loaded from global settings
	strictMode: boolean;
	persona: string;

	// Voice Mode Settings
	enableTTS: boolean;
	outputVolume: number;

	// Voice Session State
	isSessionActive: boolean;
	isConnecting: boolean;
	voiceState: VoiceState;
	errorMessage: string;
	voiceDuration: number;
	isPTTActive: boolean;
	currentRoomUrl: string | null;

	// Actions - Mode
	setMode: (mode: "text" | "voice") => void;
	setHasInteracted: (hasInteracted: boolean) => void;

	// Actions - Shared Settings
	setStrictMode: (strictMode: boolean) => void;
	toggleStrictMode: () => void;
	setPersona: (persona: string) => void;

	// Actions - Voice Settings
	setEnableTTS: (enableTTS: boolean) => void;
	setOutputVolume: (volume: number) => void;

	// Actions - Voice Session
	setSessionActive: (active: boolean) => void;
	setConnecting: (connecting: boolean) => void;
	setVoiceState: (state: VoiceState) => void;
	setErrorMessage: (message: string) => void;
	setVoiceDuration: (duration: number) => void;
	incrementVoiceDuration: () => void;
	setIsPTTActive: (active: boolean) => void;
	setCurrentRoomUrl: (url: string | null) => void;

	// Compound Actions
	startSession: () => void;
	endSession: () => void;
	setError: (message: string) => void;
	clearError: () => void;
	resetVoiceSession: () => void;

	// Settings sync
	syncFromGlobalSettings: (globalStrictMode: boolean, globalPersona: string) => void;
}

export const useInputBarStore = create<InputBarState>()(
	persist(
		(set) => ({
			// Mode Selection
			mode: "text",
			hasInteracted: false,

			// Shared Settings (Text & Voice) - initialized with defaults, synced from global settings
			strictMode: false,
			persona: "default",

			// Voice Mode Settings
			enableTTS: true,
			outputVolume: 1.0,

			// Voice Session State
			isSessionActive: false,
			isConnecting: false,
			voiceState: "listening",
			errorMessage: "",
			voiceDuration: 0,
			isPTTActive: false,
			currentRoomUrl: null,

			// Actions - Mode
			setMode: (mode) => set({ mode }),
			setHasInteracted: (hasInteracted) => set({ hasInteracted }),

			// Actions - Shared Settings
			setStrictMode: (strictMode) => set({ strictMode }),
			toggleStrictMode: () => set((state) => ({ strictMode: !state.strictMode })),
			setPersona: (persona) => set({ persona }),

			// Actions - Voice Settings
			setEnableTTS: (enableTTS) => set({ enableTTS }),
			setOutputVolume: (outputVolume) => set({ outputVolume }),

			// Actions - Voice Session
			setSessionActive: (isSessionActive) => set({ isSessionActive }),
			setConnecting: (isConnecting) => set({ isConnecting }),
			setVoiceState: (voiceState) => set({ voiceState }),
			setErrorMessage: (errorMessage) => set({ errorMessage }),
			setVoiceDuration: (voiceDuration) => set({ voiceDuration }),
			incrementVoiceDuration: () =>
				set((state) => ({ voiceDuration: state.voiceDuration + 1 })),
			setIsPTTActive: (isPTTActive) => set({ isPTTActive }),
			setCurrentRoomUrl: (currentRoomUrl) => set({ currentRoomUrl }),

			// Compound Actions
			startSession: () =>
				set({
					isSessionActive: true,
					isConnecting: false,
					voiceState: "listening",
					errorMessage: "",
				}),
			endSession: () =>
				set({
					isSessionActive: false,
					isConnecting: false,
					voiceDuration: 0,
					voiceState: "listening",
					errorMessage: "",
					isPTTActive: false,
					currentRoomUrl: null,
				}),
			setError: (errorMessage) =>
				set({
					voiceState: "error",
					errorMessage,
					isConnecting: false,
				}),
			clearError: () =>
				set({
					voiceState: "listening",
					errorMessage: "",
				}),
			resetVoiceSession: () =>
				set({
					isSessionActive: false,
					isConnecting: false,
					voiceState: "listening",
					errorMessage: "",
					voiceDuration: 0,
					isPTTActive: false,
					currentRoomUrl: null,
				}),

			// Settings sync action
			syncFromGlobalSettings: (globalStrictMode: boolean, globalPersona: string) =>
				set({ strictMode: globalStrictMode, persona: globalPersona }),
		}),
		{
			name: "samvaad-inputbar-store",
			partialize: (state) => ({
				// Only persist user preferences, not runtime state
				enableTTS: state.enableTTS,
				outputVolume: state.outputVolume,
			}),
		},
	),
);
