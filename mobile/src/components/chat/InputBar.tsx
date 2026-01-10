import { useState, useRef, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  Keyboard,
  Platform,
  Modal,
  TouchableWithoutFeedback,
} from "react-native";
import { MotiView, AnimatePresence } from "moti";
import {
  Send,
  Mic,
  MessageSquare,
  Square,
  Play,
  X,
  Settings2,
  Shield,
  ShieldAlert,
  ChevronDown,
} from "lucide-react-native";
import * as Haptics from "expo-haptics";
import { COLORS, PERSONAS } from "@/constants";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PersonaSelector } from "./PersonaSelector";
import type { Message } from "@/lib/stores/useConversationStore";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { toast } from "sonner-native";
import {
  usePipecatClient,
  useRTVIClientEvent,
} from "@pipecat-ai/client-react";
import { RTVIEvent, type TranscriptData } from "@pipecat-ai/client-js";
import { API_BASE_URL, endVoiceMode } from "@/lib/api";
import { supabase } from "@/lib/supabase";

interface InputBarProps {
  onSendMessage: (
    message: string,
    persona?: string,
    strictMode?: boolean
  ) => void;
  isLoading?: boolean;
  onStop?: () => void;
  defaultMessage?: string | null;
  onMessageConsumed?: () => void;
  onVoiceMessage?: (message: { role: "user" | "assistant"; content: string }) => void;
  conversationId?: string | null;
  showScrollButton?: boolean;
  onScrollToBottom?: () => void;
}

export function InputBar({
  onSendMessage,
  isLoading,
  onStop,
  defaultMessage,
  onMessageConsumed,
  onVoiceMessage,
  showScrollButton,
  onScrollToBottom,
  conversationId,
}: InputBarProps) {
  const insets = useSafeAreaInsets();
  const { mode, setMode, hasInteracted, setHasInteracted, persona, strictMode, setStrictMode } =
    useUIStore();

  const [message, setMessage] = useState("");
  const [showPersonaSelector, setShowPersonaSelector] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [voiceDuration, setVoiceDuration] = useState(0);
  const [voiceState, setVoiceState] = useState<"listening" | "processing" | "answering" | "error">("listening");
  
  const client = usePipecatClient();
  const textInputRef = useRef<TextInput>(null);
  const currentRoomUrlRef = useRef<string | null>(null);
  const currentBotResponseRef = useRef<string>("");
  const currentUserTranscriptRef = useRef<string>("");

  useEffect(() => {
    if (defaultMessage && onMessageConsumed) {
      setMessage(defaultMessage);
      setTimeout(() => {
        onMessageConsumed();
        textInputRef.current?.focus();
      }, 0);
    }
  }, [defaultMessage, onMessageConsumed]);

  useEffect(() => {
    if (mode === "text" && hasInteracted) {
      setTimeout(() => textInputRef.current?.focus(), 100);
    }
  }, [mode, hasInteracted]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (mode === "voice" && isSessionActive) {
      interval = setInterval(() => {
        setVoiceDuration((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [mode, isSessionActive]);

  useRTVIClientEvent(RTVIEvent.BotReady, () => {
    setIsConnecting(false);
    setVoiceState("listening");
    toast.success("Voice agent ready");
  });

  useRTVIClientEvent(RTVIEvent.Connected, () => {
    const transport = (client as any)?.transport;
    const roomUrl = transport?.roomUrl || transport?._roomUrl || transport?.daily?.roomUrl;
    if (roomUrl) {
      currentRoomUrlRef.current = roomUrl;
    }
  });

  useRTVIClientEvent(RTVIEvent.UserStartedSpeaking, () => {
    setVoiceState("listening");
    currentUserTranscriptRef.current = "";
  });

  useRTVIClientEvent(RTVIEvent.BotStartedSpeaking, () => {
    setVoiceState("answering");
  });

  useRTVIClientEvent(RTVIEvent.BotStoppedSpeaking, () => {
    setVoiceState("listening");
    const fullResponse = currentBotResponseRef.current.trim();
    if (fullResponse) {
      onVoiceMessage?.({ role: "assistant", content: fullResponse });
      currentBotResponseRef.current = "";
    }
  });

  useRTVIClientEvent(RTVIEvent.UserTranscript, (data: TranscriptData) => {
    if (data.final && data.text && data.text.trim()) {
      if (currentUserTranscriptRef.current) currentUserTranscriptRef.current += " ";
      currentUserTranscriptRef.current += data.text.trim();
    }
  });

  useRTVIClientEvent(RTVIEvent.BotLlmStarted, () => {
    setVoiceState("processing");
    const fullUserMessage = currentUserTranscriptRef.current.trim();
    if (fullUserMessage) {
      onVoiceMessage?.({ role: "user", content: fullUserMessage });
      currentUserTranscriptRef.current = "";
    }
  });

  useRTVIClientEvent(RTVIEvent.BotOutput, (data: any) => {
    const text = data?.text || data?.data?.text;
    const spoken = data?.spoken ?? data?.data?.spoken;
    if (spoken && text && text.trim()) {
      if (currentBotResponseRef.current && !currentBotResponseRef.current.endsWith(" ")) {
        currentBotResponseRef.current += " ";
      }
      currentBotResponseRef.current += text.trim();
    }
  });

  useRTVIClientEvent(RTVIEvent.Disconnected, () => {
    const roomUrl = currentRoomUrlRef.current;
    if (roomUrl) {
      endVoiceMode(roomUrl);
      currentRoomUrlRef.current = null;
    }
    setIsSessionActive(false);
    setIsConnecting(false);
    setVoiceDuration(0);
  });

  useRTVIClientEvent(RTVIEvent.Error, (error: any) => {
    console.error("[InputBar] Voice Error:", error);
    setVoiceState("error");
    setIsConnecting(false);
    toast.error("Voice connection error");
  });

  const handleModeSelect = useCallback(
    (selectedMode: "text" | "voice") => {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      setHasInteracted(true);
      setMode(selectedMode);
    },
    [setHasInteracted, setMode]
  );

  const handleSubmit = useCallback(() => {
    if (message.trim() && !isLoading) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      onSendMessage(message.trim(), persona, strictMode);
      setMessage("");
      Keyboard.dismiss();
    }
  }, [message, isLoading, onSendMessage, persona, strictMode]);

  const handleStop = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    onStop?.();
  }, [onStop]);

  const handleStartVoiceSession = useCallback(async () => {
    if (!client) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setIsConnecting(true);
    setVoiceDuration(0);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const authToken = session?.access_token;

      await client.startBotAndConnect({
        endpoint: `${API_BASE_URL}/api/connect`,
        headers: authToken ? new Headers({ Authorization: `Bearer ${authToken}` }) : undefined,
        requestData: {
          session_id: "default",
          enable_tts: true,
          persona: persona,
          strict_mode: strictMode,
          conversation_id: conversationId,
        },
      });

      setIsSessionActive(true);
    } catch (error) {
      console.error("[InputBar] Failed to connect voice:", error);
      setIsConnecting(false);
      toast.error("Failed to start voice session");
    }
  }, [client, persona, strictMode, conversationId]);

  const handleEndVoiceSession = useCallback(async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    if (client) {
      await client.disconnect();
    }
    setIsSessionActive(false);
    setIsConnecting(false);
    setVoiceDuration(0);
  }, [client]);

  const handleToggleStrictMode = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setStrictMode(!strictMode);
    toast.info(strictMode ? "Strict mode disabled" : "Strict mode enabled");
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  if (!hasInteracted) {
    return (
      <View className="w-full px-4 pb-8 pt-4">
        <View className="h-16 bg-black/40 border border-white/10 rounded-full p-1.5 flex-row items-center justify-center gap-1">
          <Pressable
            onPress={() => handleModeSelect("text")}
            className="flex-1 h-full rounded-full flex-row items-center justify-center gap-2 active:bg-white/5"
          >
            <MessageSquare size={20} color={COLORS.textPrimary} />
            <Text className="text-lg font-medium text-white">Text Mode</Text>
          </Pressable>

          <View className="w-px h-6 bg-white/10" />

          <Pressable
            onPress={() => handleModeSelect("voice")}
            className="flex-1 h-full rounded-full flex-row items-center justify-center gap-2 active:bg-white/5"
          >
            <Mic size={20} color={COLORS.textPrimary} />
            <Text className="text-lg font-medium text-white">Voice Mode</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  if (mode === "voice") {
    return (
      <View className="w-full" style={{ paddingBottom: Math.max(insets.bottom, 16) }}>
        <View className="px-4 pb-4 flex-row items-center gap-3">
          <View className="flex-1 h-14 bg-surface/80 border border-white/10 rounded-full flex-row items-center p-1.5 gap-4">
            {!isSessionActive && !isConnecting ? (
              <Pressable
                onPress={handleStartVoiceSession}
                className="flex-1 h-full rounded-full flex-row items-center justify-center gap-2 active:bg-white/5"
              >
                <Play size={20} color={COLORS.textPrimary} />
                <Text className="font-medium text-white">
                  Start Voice Session
                </Text>
              </Pressable>
            ) : (
              <View className="flex-1 flex-row items-center justify-between px-4">
                <View className="flex-row items-center gap-3">
                  <View className="px-4 py-2 rounded-full bg-blue-500/20 border border-blue-500/30">
                    <Text className="font-mono text-lg text-blue-100">
                      {formatTime(voiceDuration)}
                    </Text>
                  </View>
                  <View className="flex-row items-center gap-2">
                    <MotiView
                      from={{ scale: 0.8, opacity: 0.5 }}
                      animate={{ scale: 1.2, opacity: 1 }}
                      transition={{
                        type: "timing",
                        duration: 600,
                        loop: true,
                        repeatReverse: true,
                      }}
                      className={`w-2 h-2 rounded-full ${voiceState === "answering" ? "bg-green-400" : voiceState === "processing" ? "bg-amber-400" : "bg-blue-400"}`}
                    />
                    <Text className="text-sm font-medium text-blue-100 capitalize">
                      {isConnecting ? "Connecting..." : voiceState}
                    </Text>
                  </View>
                </View>

                <View className="flex-row items-center gap-2">
                  <Pressable
                    onPress={() => setShowPersonaSelector(true)}
                    className="p-2 rounded-full active:bg-white/10"
                  >
                    <Settings2 size={18} color={COLORS.textSecondary} />
                  </Pressable>
                  <Pressable
                    onPress={handleEndVoiceSession}
                    className="p-2 rounded-full active:bg-red-500/20"
                  >
                    <X size={20} color="#ef4444" />
                  </Pressable>
                </View>
              </View>
            )}
          </View>

          <Pressable
            onPress={() => setMode("text")}
            className="h-14 w-14 rounded-full bg-black/40 border border-white/10 items-center justify-center active:bg-white/10"
          >
            <MessageSquare size={24} color={COLORS.textPrimary} />
          </Pressable>
        </View>

        <Modal
          visible={showPersonaSelector}
          transparent
          animationType="fade"
          onRequestClose={() => setShowPersonaSelector(false)}
        >
          <TouchableWithoutFeedback onPress={() => setShowPersonaSelector(false)}>
            <View className="flex-1 bg-black/60 justify-center px-6">
              <TouchableWithoutFeedback>
                <View>
                  <PersonaSelector onClose={() => setShowPersonaSelector(false)} />
                </View>
              </TouchableWithoutFeedback>
            </View>
          </TouchableWithoutFeedback>
        </Modal>
      </View>
    );
  }

  return (
    <View className="w-full" style={{ paddingBottom: Math.max(insets.bottom, 16) }}>
      <AnimatePresence>
        {showScrollButton && (
          <MotiView
            from={{ opacity: 0, translateY: 20 }}
            animate={{ opacity: 1, translateY: 0 }}
            exit={{ opacity: 0, translateY: 20 }}
            className="absolute -top-16 right-6 z-50"
          >
            <Pressable
              onPress={onScrollToBottom}
              className="w-10 h-10 rounded-full bg-surface border border-white/10 items-center justify-center shadow-lg active:bg-white/10"
            >
              <ChevronDown size={20} color={COLORS.textPrimary} />
            </Pressable>
          </MotiView>
        )}
      </AnimatePresence>

      <View className="px-4 pt-4">
        <View className="flex-row items-end gap-2 mb-2">
          <Pressable
            onPress={handleToggleStrictMode}
            className={`flex-row items-center gap-1.5 px-3 py-1.5 rounded-full border ${
              strictMode
                ? "bg-amber-500/10 border-amber-500/30"
                : "bg-white/5 border-white/5"
            }`}
          >
            {strictMode ? (
              <ShieldAlert size={14} color="#fbbf24" />
            ) : (
              <Shield size={14} color="rgba(255,255,255,0.4)" />
            )}
            <Text
              className={`text-[10px] font-bold uppercase tracking-wider ${
                strictMode ? "text-amber-400" : "text-white/40"
              }`}
            >
              Strict Mode
            </Text>
          </Pressable>

          <Pressable
            onPress={() => setShowPersonaSelector(true)}
            className="flex-row items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/5"
          >
            <Settings2 size={14} color="rgba(255,255,255,0.4)" />
            <Text className="text-[10px] font-bold uppercase tracking-wider text-white/40">
              Persona: {PERSONAS.find((p) => p.id === persona)?.name}
            </Text>
          </Pressable>
        </View>

        <View className="flex-row items-end gap-3">
          <View className="flex-1 bg-surface/80 border border-white/10 rounded-3xl flex-row items-end min-h-[56px]">
            <TextInput
              ref={textInputRef}
              value={message}
              onChangeText={setMessage}
              placeholder="Ask anything..."
              placeholderTextColor="rgba(255,255,255,0.4)"
              multiline
              maxLength={4000}
              className="flex-1 py-4 pl-5 pr-2 text-base text-white max-h-32"
              style={{ textAlignVertical: "center" }}
              onSubmitEditing={handleSubmit}
              blurOnSubmit={false}
              returnKeyType="default"
            />

            <View className="flex-row items-center gap-1 pr-3 pb-2">
              <AnimatePresence>
                {isLoading ? (
                  <MotiView
                    key="stop"
                    from={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.5, opacity: 0 }}
                  >
                    <Pressable
                      onPress={handleStop}
                      className="w-12 h-12 rounded-full items-center justify-center"
                    >
                      <MotiView
                        from={{ rotate: "0deg" }}
                        animate={{ rotate: "360deg" }}
                        transition={{
                          type: "timing",
                          duration: 1000,
                          loop: true,
                        }}
                        className="absolute w-10 h-10 rounded-full border-2 border-white/10 border-t-white"
                      />
                      <View className="w-8 h-8 rounded-full bg-white/10 items-center justify-center">
                        <Square size={12} color={COLORS.textPrimary} fill={COLORS.textPrimary} />
                      </View>
                    </Pressable>
                  </MotiView>
                ) : (
                  <MotiView
                    key="send"
                    from={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.5, opacity: 0 }}
                  >
                    <Pressable
                      onPress={handleSubmit}
                      disabled={!message.trim()}
                      className={`w-12 h-12 rounded-full items-center justify-center ${
                        message.trim() ? "active:bg-white/10" : "opacity-50"
                      }`}
                    >
                      <Send size={24} color={COLORS.textPrimary} />
                    </Pressable>
                  </MotiView>
                )}
              </AnimatePresence>
            </View>
          </View>

          <Pressable
            onPress={() => setMode("voice")}
            className="h-14 w-14 rounded-full bg-black/40 border border-white/10 items-center justify-center active:bg-white/10"
          >
            <Mic size={24} color={COLORS.textPrimary} />
          </Pressable>
        </View>
      </View>

      <Modal
        visible={showPersonaSelector}
        transparent
        animationType="fade"
        onRequestClose={() => setShowPersonaSelector(false)}
      >
        <TouchableWithoutFeedback onPress={() => setShowPersonaSelector(false)}>
          <View className="flex-1 bg-black/60 justify-center px-6">
            <TouchableWithoutFeedback>
              <View>
                <PersonaSelector onClose={() => setShowPersonaSelector(false)} />
              </View>
            </TouchableWithoutFeedback>
          </View>
        </TouchableWithoutFeedback>
      </Modal>
    </View>
  );
}
