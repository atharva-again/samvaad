"use client";

import { Room, RoomEvent, Track, type AudioTrack } from "livekit-client";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { LIVEKIT_VOICE_TOPIC, type LiveKitVoiceEvent } from "@samvaad/voice-protocol";
import { API_BASE_URL } from "@/lib/config";
import { type CitationItem, useUIStore } from "@/lib/stores/useUIStore";

export const VoiceEvent = {
  BotConnected: "bot-connected",
  Connected: "connected",
  BotReady: "bot-ready",
  UserStartedSpeaking: "user-started-speaking",
  BotStartedSpeaking: "bot-started-speaking",
  BotStoppedSpeaking: "bot-stopped-speaking",
  AgentListening: "agent-listening",
  Message: "message",
  UserTranscript: "user-transcript",
  BotLlmStarted: "bot-llm-started",
  Disconnected: "disconnected",
  Error: "error",
} as const;

export interface VoiceTranscriptData {
  final: boolean;
  text: string;
  messageId?: string;
}

interface VoiceConnectOptions {
  conversationId: string;
  enableTts: boolean;
  persona: string;
  strictMode: boolean;
}

interface LiveKitVoiceClient {
  connect: (options: VoiceConnectOptions) => Promise<void>;
  disconnect: () => Promise<void>;
  setMicrophoneEnabled: (enabled: boolean) => Promise<void>;
  switchMicrophone: (deviceId: string) => Promise<void>;
  switchSpeaker: (deviceId: string) => Promise<void>;
  activeMicId: string;
  setOutputVolume: (volume: number) => void;
}

type VoiceHandler = (payload?: unknown) => void;

function setAudioElementsVolume(elements: Iterable<HTMLMediaElement>, volume: number): void {
  for (const element of elements) element.volume = volume;
}

interface LiveKitContextValue {
  client: LiveKitVoiceClient;
  subscribe: (event: string, handler: VoiceHandler) => () => void;
}

const LiveKitContext = createContext<LiveKitContextValue | null>(null);

export function useLiveKitClient(): LiveKitVoiceClient | null {
  return useContext(LiveKitContext)?.client ?? null;
}

export function useLiveKitVoiceEvent<T = unknown>(
  event: string,
  handler: (payload: T) => void,
): void {
  const context = useContext(LiveKitContext);
  const handlerRef = useRef(handler);

  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!context) return;
    return context.subscribe(event, (payload) => handlerRef.current(payload as T));
  }, [context, event]);
}

export function LiveKitProvider({ children }: { children: ReactNode }) {
  const roomRef = useRef<Room | null>(null);
  const intentionalDisconnectRef = useRef(false);
  const speakerDeviceIdRef = useRef("");
  const outputVolumeRef = useRef(1);
  const listenersRef = useRef(new Map<string, Set<VoiceHandler>>());
  const audioElementsRef = useRef(new Set<HTMLMediaElement>());
  const previousAgentStateRef = useRef<"listening" | "thinking" | "speaking" | "idle">("idle");
  const [activeMicId, setActiveMicId] = useState("default");
  const { setCitations, setSourcesPanelTab, setPendingVoiceCitations } = useUIStore();

  const emit = useCallback((event: string, payload?: unknown) => {
    for (const listener of listenersRef.current.get(event) ?? []) {
      listener(payload);
    }
  }, []);

  const subscribe = useCallback((event: string, handler: VoiceHandler) => {
    const listeners = listenersRef.current.get(event) ?? new Set<VoiceHandler>();
    listeners.add(handler);
    listenersRef.current.set(event, listeners);
    return () => {
      listeners.delete(handler);
      if (listeners.size === 0) listenersRef.current.delete(event);
    };
  }, []);

  const applyOutputSettings = useCallback(async (deviceId?: string) => {
    for (const element of audioElementsRef.current) {
      element.volume = outputVolumeRef.current;
      const targetDeviceId = deviceId ?? speakerDeviceIdRef.current;
      if (targetDeviceId && "setSinkId" in element && typeof element.setSinkId === "function") {
        await element.setSinkId(targetDeviceId).catch((error: unknown) => {
          console.warn("Unable to switch LiveKit audio output device", error);
        });
      }
    }
  }, []);

  const attachAudioTrack = useCallback(
    (track: AudioTrack) => {
      const element = track.attach();
      element.autoplay = true;
      element.volume = outputVolumeRef.current;
      document.body.appendChild(element);
      audioElementsRef.current.add(element);
      void applyOutputSettings();
    },
    [applyOutputSettings],
  );

  const handleWireEvent = useCallback(
    (event: LiveKitVoiceEvent) => {
      switch (event.type) {
        case "agent_ready":
          emit(VoiceEvent.BotConnected);
          emit(VoiceEvent.BotReady);
          break;
        case "agent_state":
          if (event.state === "speaking") {
            emit(VoiceEvent.BotStartedSpeaking);
          } else if (event.state === "listening") {
            emit(
              previousAgentStateRef.current === "speaking"
                ? VoiceEvent.BotStoppedSpeaking
                : VoiceEvent.AgentListening,
            );
          }
          previousAgentStateRef.current = event.state;
          break;
        case "user_message": {
          emit(VoiceEvent.UserStartedSpeaking);
          const transcript: VoiceTranscriptData = {
            final: true,
            text: event.text,
            messageId: event.message_id,
          };
          emit(VoiceEvent.UserTranscript, transcript);
          emit(VoiceEvent.BotLlmStarted);
          break;
        }
        case "citations": {
          const sources = event.sources as CitationItem[];
          setPendingVoiceCitations(sources);
          setCitations("voice-response", sources);
          setSourcesPanelTab("citations");
          emit(VoiceEvent.Message, {
            message: { type: "citations", sources, turn_id: event.turn_id },
          });
          break;
        }
        case "assistant_message_ready":
          emit(VoiceEvent.Message, {
            message: {
              type: "transcript_ready",
              text: event.text,
              message_id: event.message_id,
              turn_id: event.turn_id,
            },
          });
          break;
        case "assistant_message":
          emit(VoiceEvent.Message, {
            message: {
              type: "transcript",
              text: event.text,
              sources: event.sources,
              message_id: event.message_id,
              turn_id: event.turn_id,
              persisted: event.persisted,
              interrupted: event.interrupted,
              conversation_title: event.conversation_title,
            },
          });
          break;
        case "voice_error":
          emit(VoiceEvent.Error, { message: event.message });
          break;
      }
    },
    [emit, setCitations, setPendingVoiceCitations, setSourcesPanelTab],
  );

  const disconnect = useCallback(async () => {
    const room = roomRef.current;
    if (!room) return;
    intentionalDisconnectRef.current = true;
    roomRef.current = null;
    for (const element of audioElementsRef.current) {
      element.remove();
    }
    audioElementsRef.current.clear();
    await room.disconnect();
  }, []);

  const connect = useCallback(
    async (options: VoiceConnectOptions) => {
      if (roomRef.current) await disconnect();

      const response = await fetch(`${API_BASE_URL}/livekit/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(options),
      });
      if (!response.ok) {
        const result = (await response.json().catch(() => null)) as { error?: string } | null;
        throw new Error(result?.error ?? "Unable to create a voice session");
      }

      const result = (await response.json()) as {
        serverUrl: string;
        participantToken: string;
        roomName: string;
      };
      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;
      intentionalDisconnectRef.current = false;
      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) attachAudioTrack(track as AudioTrack);
      });
      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          for (const element of track.detach()) {
            audioElementsRef.current.delete(element);
            element.remove();
          }
        }
      });
      room.on(RoomEvent.DataReceived, (payload, _participant, _kind, topic) => {
        if (topic !== LIVEKIT_VOICE_TOPIC) return;
        try {
          const event = JSON.parse(new TextDecoder().decode(payload)) as LiveKitVoiceEvent;
          handleWireEvent(event);
        } catch (error) {
          console.error("Invalid LiveKit voice event", error);
        }
      });
      room.on(RoomEvent.Disconnected, (reason) => {
        roomRef.current = null;
        for (const element of audioElementsRef.current) element.remove();
        audioElementsRef.current.clear();
        if (!intentionalDisconnectRef.current) {
          emit(VoiceEvent.Disconnected, reason);
        }
        intentionalDisconnectRef.current = false;
      });

      try {
        await room.connect(result.serverUrl, result.participantToken);
        emit(VoiceEvent.Connected);
        // "default" is a browser sentinel, not a concrete device ID. LiveKit/browser
        // already uses the system default after connect; requesting it explicitly can
        // fail with OverconstrainedError and tear down an otherwise healthy room.
        if (activeMicId && activeMicId !== "default") {
          try {
            await room.switchActiveDevice("audioinput", activeMicId);
          } catch (error) {
            console.warn(
              "[LiveKit] Could not select the preferred microphone; keeping the browser default",
              error,
            );
          }
        }
        await applyOutputSettings();
      } catch (error) {
        roomRef.current = null;
        await room.disconnect().catch(() => undefined);
        throw error;
      }
    },
    [activeMicId, applyOutputSettings, attachAudioTrack, disconnect, emit, handleWireEvent],
  );

  const setMicrophoneEnabled = useCallback(async (enabled: boolean) => {
    const room = roomRef.current;
    if (!room) return;
    await room.localParticipant.setMicrophoneEnabled(enabled);
  }, []);

  const switchMicrophone = useCallback(async (deviceId: string) => {
    setActiveMicId(deviceId);
    const room = roomRef.current;
    if (room) await room.switchActiveDevice("audioinput", deviceId);
  }, []);

  const switchSpeaker = useCallback(
    async (deviceId: string) => {
      speakerDeviceIdRef.current = deviceId;
      await applyOutputSettings(deviceId);
    },
    [applyOutputSettings],
  );

  const setOutputVolume = useCallback((volume: number) => {
    outputVolumeRef.current = volume;
    setAudioElementsVolume(audioElementsRef.current, volume);
  }, []);

  useEffect(
    () => () => {
      for (const element of audioElementsRef.current) element.remove();
      audioElementsRef.current.clear();
      void roomRef.current?.disconnect();
    },
    [],
  );

  const client = useMemo<LiveKitVoiceClient>(
    () => ({
      connect,
      disconnect,
      setMicrophoneEnabled,
      switchMicrophone,
      switchSpeaker,
      activeMicId,
      setOutputVolume,
    }),
    [
      activeMicId,
      connect,
      disconnect,
      setMicrophoneEnabled,
      setOutputVolume,
      switchMicrophone,
      switchSpeaker,
    ],
  );
  const value = useMemo(() => ({ client, subscribe }), [client, subscribe]);

  return <LiveKitContext.Provider value={value}>{children}</LiveKitContext.Provider>;
}
