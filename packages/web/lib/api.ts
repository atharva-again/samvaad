import { API_BASE_URL } from "@/lib/config";

type ApiRequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const baseUrl = API_BASE_URL.replace(/\/+$/, "");
  const requestUrl = new URL(`${baseUrl}/${path.replace(/^\/+/, "")}`);
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value !== undefined) requestUrl.searchParams.set(key, String(value));
  }

  const headers = new Headers();
  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    if (options.body instanceof FormData) {
      body = options.body;
    } else {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(options.body);
    }
  }

  const response = await fetch(requestUrl, {
    method: options.method ?? "GET",
    credentials: "include",
    headers,
    body,
    signal: options.signal,
  });

  let responseBody: unknown;
  if (response.status !== 204) {
    const text = await response.text();
    if (text) {
      responseBody = response.headers.get("content-type")?.includes("json")
        ? JSON.parse(text)
        : text;
    }
  }

  if (!response.ok) {
    const errorBody =
      responseBody && typeof responseBody === "object"
        ? (responseBody as Record<string, unknown>)
        : undefined;
    const message =
      (errorBody?.message as string | undefined) ??
      (errorBody?.error as string | undefined) ??
      (errorBody?.detail as string | undefined) ??
      `Request failed with status ${response.status}`;
    throw new ApiError(response.status, responseBody, message);
  }

  return responseBody as T;
}

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
  conversation_title?: string;
  error?: string;
}

export interface FileUploadResponse {
  file_id?: string;
  size_bytes?: number;
  created_at?: string;
  content_hash?: string;
  error?: string | null;
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
  return apiRequest<ChatResponse>("/text-mode", {
    method: "POST",
    signal,
    body: {
      message,
      conversation_id: conversationId,
      user_message_id: userMessageId,
      assistant_message_id: assistantMessageId,
      persona,
      strict_mode: strictMode,
      allowed_file_ids: allowedFileIds || null,
    },
  });
};

export const textToSpeech = async (text: string, language: string = "en") => {
  return apiRequest("/tts", {
    method: "POST",
    body: { text, language },
  });
};

export const listFiles = async () => {
  return apiRequest<any[]>("/files");
};

export const deleteFile = async (fileId: string) => {
  return apiRequest(`/files/${fileId}`, { method: "DELETE" });
};

export const batchDeleteFiles = async (fileIds: string[]) => {
  return apiRequest("/files/batch", {
    method: "DELETE",
    body: { file_ids: fileIds },
  });
};

export const renameFile = async (fileId: string, newFilename: string) => {
  return apiRequest(`/files/${fileId}`, {
    method: "PATCH",
    body: { filename: newFilename },
  });
};

export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<FileUploadResponse>("/ingest", {
    method: "POST",
    body: formData,
  });
};

export interface UserSettings {
  default_strict_mode: boolean;
  default_persona: string;
}

export const getUserSettings = async (): Promise<UserSettings> => {
  return apiRequest<UserSettings>("/users/settings");
};

export const updateUserSettings = async (settings: UserSettings): Promise<UserSettings> => {
  return apiRequest<UserSettings>("/users/settings", {
    method: "PUT",
    body: settings,
  });
};

export interface ConversationSettings {
  active_strict_mode: boolean | null;
  active_persona: string | null;
}

export const getConversationSettings = async (
  conversationId: string,
): Promise<ConversationSettings> => {
  return apiRequest<ConversationSettings>(`/conversations/${conversationId}/settings`);
};

export const updateConversationSettings = async (
  conversationId: string,
  settings: Partial<ConversationSettings>,
): Promise<ConversationSettings> => {
  return apiRequest<ConversationSettings>(`/conversations/${conversationId}/settings`, {
    method: "PUT",
    body: settings,
  });
};
