import axios from "axios";
import { createClient } from "@/utils/supabase/client";

const supabase = createClient();

export const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export const api = axios.create({
	baseURL: API_BASE_URL,
	headers: {
		"Content-Type": "application/json",
	},
});

api.interceptors.request.use(async (config) => {
	const {
		data: { session },
	} = await supabase.auth.getSession();

	if (session?.access_token) {
		config.headers.Authorization = `Bearer ${session.access_token}`;
	}
	return config;
});

import { type CitationItem } from "@/lib/stores/useUIStore";

export interface ChatMessage {
	id?: string;
	role: "user" | "assistant" | "system";
	content: string;
	timestamp?: string;
	sources?: CitationItem[];
}

export interface ChatResponse {
	conversation_id: string;
	response: string;
	success: boolean;
	sources?: any[];
	error?: string;
}

export interface VoiceModeResponse {
	room_url: string;
	token: string | null;
	session_id: string;
	success: boolean;
}

export const sendMessage = async (
	message: string,
	conversationId: string | null = null,
	signal?: AbortSignal,
	persona: string = "default",
	strictMode: boolean = false,
	userMessageId?: string,
	assistantMessageId?: string,
	allowedFileIds?: string[] | null,
) => {
	const response = await api.post<ChatResponse>(
		"/text-mode",
		{
			message,
			conversation_id: conversationId,
			user_message_id: userMessageId,
			assistant_message_id: assistantMessageId,
			persona,
			strict_mode: strictMode,
			allowed_file_ids: allowedFileIds || null,
		},
		{ signal },
	);
	return response.data;
};

export const startVoiceMode = async (
	conversationId?: string, // Existing conversation to continue
	sessionId: string = "default",
	enable_tts: boolean = true,
	persona: string = "default",
	strictMode: boolean = false,
) => {
	const response = await api.post<VoiceModeResponse>("/voice-mode", {
		conversation_id: conversationId,
		session_id: sessionId,
		enable_tts,
		persona,
		strict_mode: strictMode,
	});
	return response.data;
};

export const endVoiceMode = async (roomUrl: string) => {
	try {
		const response = await api.post("/voice-mode/disconnect", {
			room_url: roomUrl,
		});
		return response.data;
	} catch (error) {
		console.error("Failed to end voice mode:", error);
		return { success: false };
	}
};

export const textToSpeech = async (text: string, language: string = "en") => {
	const response = await api.post("/tts", {
		text,
		language,
	});
	return response.data;
};

export const listFiles = async () => {
	const response = await api.get<any[]>("/files");
	return response.data;
};

export const deleteFile = async (fileId: string) => {
	const response = await api.delete(`/files/${fileId}`);
	return response.data;
};

export const batchDeleteFiles = async (fileIds: string[]) => {
	const response = await api.delete("/files/batch", {
		data: { file_ids: fileIds },
	});
	return response.data;
};

export const renameFile = async (fileId: string, newFilename: string) => {
	const response = await api.patch(`/files/${fileId}`, {
		filename: newFilename,
	});
	return response.data;
};

export const uploadFile = async (file: File) => {
	const formData = new FormData();
	formData.append("file", file);

	const response = await api.post("/ingest", formData, {
		headers: {
			"Content-Type": "multipart/form-data",
		},
		// No timeout for large ingest jobs
		timeout: 0,
	});
	return response.data;
};

export interface UserSettings {
	default_strict_mode: boolean;
	default_persona: string;
}

export const getUserSettings = async (): Promise<UserSettings> => {
	const response = await api.get<UserSettings>("/users/settings");
	return response.data;
};

export const updateUserSettings = async (settings: UserSettings): Promise<UserSettings> => {
	const response = await api.put<UserSettings>("/users/settings", settings);
	return response.data;
};

export interface ConversationSettings {
	active_strict_mode: boolean | null;
	active_persona: string | null;
}

export const getConversationSettings = async (conversationId: string): Promise<ConversationSettings> => {
	const response = await api.get<ConversationSettings>(`/conversations/${conversationId}/settings`);
	return response.data;
};

export const updateConversationSettings = async (
	conversationId: string,
	settings: Partial<ConversationSettings>,
): Promise<ConversationSettings> => {
	const response = await api.put<ConversationSettings>(`/conversations/${conversationId}/settings`, settings);
	return response.data;
};
