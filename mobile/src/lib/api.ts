import axios from "axios";
import { supabase } from "./supabase";

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL || "http://localhost:8001";

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

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  sources?: Record<string, unknown>[];
}

export interface ChatResponse {
  conversation_id: string;
  response: string;
  success: boolean;
  sources?: unknown[];
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
  persona = "default",
  strictMode = false,
  userMessageId?: string,
  assistantMessageId?: string,
  allowedFileIds?: string[] | null
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
    { signal }
  );
  return response.data;
};

export const startVoiceMode = async (
  conversationId?: string,
  sessionId = "default",
  enable_tts = true,
  persona = "default",
  strictMode = false
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

export const textToSpeech = async (text: string, language = "en") => {
  const response = await api.post("/tts", {
    text,
    language,
  });
  return response.data;
};

export const listFiles = async () => {
  const response = await api.get<unknown[]>("/files");
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

interface FilePayload {
  uri: string;
  name: string;
  type: string;
}

interface UploadedFile {
  id: string;
  name: string;
  type: string;
  size: string;
  uploadedAt: string;
  contentHash?: string;
}

interface UploadResponse {
  success: boolean;
  file?: UploadedFile;
  error?: string;
}

export const uploadFile = async (file: FilePayload): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append("file", {
    uri: file.uri,
    name: file.name,
    type: file.type,
  } as unknown as Blob);

  try {
    const response = await api.post("/ingest", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      timeout: 0,
    });
    return {
      success: true,
      file: response.data,
    };
  } catch (error) {
    console.error("Upload error:", error);
    return {
      success: false,
      error: "Upload failed",
    };
  }
};
