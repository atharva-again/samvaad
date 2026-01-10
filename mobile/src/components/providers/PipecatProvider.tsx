import { PipecatClient } from "@pipecat-ai/client-js";
import { PipecatClientProvider } from "@pipecat-ai/client-react";
import { RNDailyTransport } from "@pipecat-ai/react-native-daily-transport";
import { type ReactNode, useEffect, useState, useCallback } from "react";
import { useUIStore, type CitationItem } from "@/lib/stores/useUIStore";
import { useConversationStore } from "@/lib/stores/useConversationStore";

interface PipecatProviderProps {
  children: ReactNode;
}

export function PipecatProvider({ children }: PipecatProviderProps) {
  const [client, setClient] = useState<PipecatClient | null>(null);
  const { setCitations, setSourcesPanelTab, setActiveVoiceConversationId } = useUIStore();
  const { addMessageToUI } = useConversationStore();

  useEffect(() => {
    let mounted = true;

    const initClient = async () => {
      try {
        const transport = new RNDailyTransport();

        const created = new PipecatClient({
          transport,
          enableMic: true,
          callbacks: {
            onConnected: () => {
              console.debug("[PipecatProvider] Connected");
            },
            onDisconnected: () => {
              console.debug("[PipecatProvider] Disconnected");
              setActiveVoiceConversationId(null);
            },
            onTransportStateChanged: (state: string) => {
              console.debug("[PipecatProvider] State:", state);
            },
            onTranscript: (transcript: { text: string; final: boolean; role: string }) => {
              if (transcript.final) {
                console.debug("[PipecatProvider] Transcript:", transcript.text);
              }
            },
            onBotMessage: (message: any) => {
            },
            onServerMessage: (data: any) => {
              const msg = data as { type?: string; sources?: CitationItem[]; conversation_id?: string };
              if (msg.type === "citations" && msg.sources) {
                setCitations("voice-response", msg.sources);
              }
              if (msg.conversation_id) {
                 setActiveVoiceConversationId(msg.conversation_id);
              }
            },
          },
        });

        if (!mounted) return;
        setClient(created);
      } catch (err) {
        console.error("Failed to initialize Pipecat mobile client:", err);
      }
    };

    initClient();

    return () => {
      mounted = false;
    };
  }, [setCitations, setActiveVoiceConversationId]);

  if (!client) {
    return <>{children}</>;
  }

  return (
    <PipecatClientProvider client={client}>
      {children}
    </PipecatClientProvider>
  );
}
