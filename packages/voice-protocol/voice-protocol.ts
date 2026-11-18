export const LIVEKIT_VOICE_TOPIC = "samvaad.voice.v1";

export interface VoiceCitation {
  filename: string;
  content_preview: string;
  rerank_score?: number;
  chunk_id?: string;
  metadata?: {
    extra?: {
      page_number?: number;
      breadcrumbs?: string[];
      content_type?: string;
      heading?: string;
    };
  };
}

export type LiveKitVoiceEvent =
  | { type: "agent_ready" }
  | {
      type: "agent_state";
      state: "listening" | "thinking" | "speaking" | "idle";
    }
  | {
      type: "user_message";
      turn_id: string;
      message_id: string;
      text: string;
    }
  | {
      type: "citations";
      turn_id: string;
      sources: VoiceCitation[];
    }
  | {
      type: "assistant_message_ready";
      turn_id: string;
      message_id: string;
      text: string;
    }
  | {
      type: "assistant_message";
      turn_id: string;
      message_id: string;
      text: string;
      sources: VoiceCitation[];
      interrupted: boolean;
      persisted: boolean;
      conversation_title?: string;
    }
  | { type: "voice_error"; message: string };
