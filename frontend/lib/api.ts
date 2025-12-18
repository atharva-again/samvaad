import axios from "axios";
import { createClient } from "@/utils/supabase/client";

const supabase = createClient();

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
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
) => {
  const response = await api.post<ChatResponse>("/text-mode", {
    message,
    conversation_id: conversationId,
    persona,
    strict_mode: strictMode,
  }, { signal });
  return response.data;
};

export const startVoiceMode = async (
  sessionId: string = "default",
  enable_tts: boolean = true,
  persona: string = "default",
  strictMode: boolean = false,
) => {
  const response = await api.post<VoiceModeResponse>("/voice-mode", {
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
