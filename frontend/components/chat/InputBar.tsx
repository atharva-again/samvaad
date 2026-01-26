"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Mic,
  SendHorizontal,
  MessageSquare,
  X,
  Play,
  Square,
} from "lucide-react";
import { ActionTooltip } from "@/components/ui/action-tooltip";
import { StrictModeToggle } from "@/components/chat/StrictModeToggle";
import { PersonaSelector } from "@/components/chat/PersonaSelector";
import { VoiceSettings } from "@/components/chat/VoiceSettings";
import { MobileVoiceControls } from "@/components/chat/MobileVoiceControls";
import { MobileTextControls } from "@/components/chat/MobileTextControls";
import { motion, AnimatePresence } from "framer-motion";
import {
  usePipecatClient,
  useRTVIClientEvent,
  VoiceVisualizer,
} from "@pipecat-ai/client-react";
import { RTVIEvent, TranscriptData } from "@pipecat-ai/client-js";
import { ChatMessage, API_BASE_URL } from "@/lib/api";

import { Button } from "@/components/ui/button";
import { useUIStore } from "@/lib/stores/useUIStore";
import { useInputBarStore } from "@/lib/stores/useInputBarStore";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { cn } from "@/lib/utils";
import { endVoiceMode } from "@/lib/api";
import { toast } from "sonner";
import { AttachmentButton } from "./AttachmentButton";
import { usePlatform } from "@/hooks/usePlatform";
import { useFileProcessor } from "@/hooks/useFileProcessor";
import { createClient } from "@/utils/supabase/client";

interface InputBarProps {
  onSendMessage: (message: string, persona?: string, strictMode?: boolean) => void;
  isLoading?: boolean;
  onStop?: () => void;
  defaultMessage?: string | null;
  onMessageConsumed?: () => void;
  onVoiceMessage?: (message: ChatMessage) => void;
  conversationId?: string | null;
}

export function InputBar({ onSendMessage, isLoading, onStop, defaultMessage, onMessageConsumed, onVoiceMessage, conversationId }: InputBarProps) {
	const { pendingConversationId } = useConversationStore();
  const USE_MOCK_BACKEND = false; // Toggle this to true for mock backend
  const {
    toggleSourcesPanel,
    consumePendingVoiceCitations,
    setPendingVoiceCitations,
    consumeVoiceTranscript,
    lastVoiceCitations,
  } = useUIStore();

  const {
    mode,
    setMode,
    hasInteracted,
    setHasInteracted,
    strictMode,
    persona,
    enableTTS,
    isSessionActive,
    setSessionActive,
    isConnecting,
    setConnecting,
    voiceState,
    setVoiceState,
    errorMessage,
    setErrorMessage,
    voiceDuration,
    setVoiceDuration,
    incrementVoiceDuration,
    isPTTActive,
    setIsPTTActive,
    currentRoomUrl,
    setCurrentRoomUrl,
    endSession,
    setError,
  } = useInputBarStore();

  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const currentRoomUrlRef = useRef<string | null>(null); // Ref for event handler access
  const currentBotResponseRef = useRef<string>(""); // Ref to aggregate bot sentences (filtered, for fallback)
  const currentBotLlmTextRef = useRef<string>(""); // Ref to aggregate raw LLM text (with citation markers)
  const currentUserTranscriptRef = useRef<string>(""); // Ref to aggregate user transcripts
  const assistantMessageSentRef = useRef(false);
  const { processFiles } = useFileProcessor();

  // Sync ref with store value for event handler access
  useEffect(() => {
    currentRoomUrlRef.current = currentRoomUrl;
  }, [currentRoomUrl]);

  // Handle initial mode selection
  const handleModeSelect = (selectedMode: "text" | "voice") => {
    console.debug("[InputBar] mode selected:", selectedMode);
    setHasInteracted(true);
    setMode(selectedMode);
  };

  // Keyboard Shortcuts (Alt+T, Alt+V, Alt+A)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Voice Mode (Alt + V)
      if (e.altKey && (e.code === 'KeyV')) {
        e.preventDefault();
        handleModeSelect("voice");
      }
      // Text Mode (Alt + T)
      if (e.altKey && (e.code === 'KeyT')) {
        e.preventDefault();
        handleModeSelect("text");

        // Force focus if already in text mode or switching to it
        if (mode === "text") {
          setTimeout(() => textareaRef.current?.focus(), 0);
        }
      }

      // Upload Files (Alt + A) - Allow on initial screen too (e.altKey check matches global)
      if (e.altKey && (e.code === 'KeyA')) {
        e.preventDefault();
        fileInputRef.current?.click();
      }

      // Sources Panel (Alt + S)
      if (e.altKey && (e.code === 'KeyS')) {
        e.preventDefault();
        toggleSourcesPanel();
      }

      // Sources Panel (Alt + S)
      if (e.altKey && (e.code === 'KeyS')) {
        e.preventDefault();
        toggleSourcesPanel();
      }


    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setMode, mode]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      await processFiles(files);
      // Auto-open panel to show progress? User request implied opening file explorer.
      // Once files are selected, we should probably ensure the panel is open to show headers/progress
      // but InputBar manages SourcesPanel visibility?
      // We can use setSourcesPanelOpen(true) if we want.
      // For now, just process.

      // Reset input
      e.target.value = "";
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  useEffect(() => {
    if (defaultMessage && onMessageConsumed) {
      console.debug("[InputBar] Loading default message for edit:", defaultMessage);
      setMessage(defaultMessage);

      // We must allow the state to update before we tell the parent we consumed it.
      // Although React state updates are batched, sometimes the parent re-render 
      // with null might happen too fast if not synchronized.
      // However, the main issue might be that the textarea height needs to adjust.

      // Defer consuming slightly to ensure UI updates first? 
      // Actually, standard practice is to consume immediately. 
      // But let's check if the state is actually persisting.

      // Let's call onMessageConsumed in the next tick to be safe.
      setTimeout(() => {
        onMessageConsumed();
        // Auto-focus the textarea
        if (textareaRef.current) {
          textareaRef.current.focus();
          // Optional: Move cursor to end
          textareaRef.current.setSelectionRange(
            textareaRef.current.value.length,
            textareaRef.current.value.length
          );
        }
      }, 0);
    }
  }, [defaultMessage, onMessageConsumed]);

  // Auto-resize when message changes programmatically
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = textarea.scrollHeight + "px";
    }
  }, [message]);

  // Auto-focus when switching to Text Mode
  useEffect(() => {
    if (mode === "text" && textareaRef.current) {
      // Small timeout to ensure the element is painted and ready to receive focus
      // especially if there's an animation
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
    }
  }, [mode, hasInteracted]);

  const client = usePipecatClient();

  const updateRoomUrl = (url: string | null) => {
    setCurrentRoomUrl(url);
    currentRoomUrlRef.current = url;
  };

  // Handle Spacebar PTT for V2T mode
  useEffect(() => {
    if (mode === "voice" && !enableTTS && isSessionActive) {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.code === "Space" && !e.repeat && !isPTTActive) {
          e.preventDefault(); // Prevent scrolling
          setIsPTTActive(true);
          client?.enableMic(true);
        }
      };

      const handleKeyUp = (e: KeyboardEvent) => {
        if (e.code === "Space" && isPTTActive) {
          e.preventDefault();
          setIsPTTActive(false);
          client?.enableMic(false);
        }
      };

      window.addEventListener("keydown", handleKeyDown);
      window.addEventListener("keyup", handleKeyUp);
      return () => {
        window.removeEventListener("keydown", handleKeyDown);
        window.removeEventListener("keyup", handleKeyUp);
      };
    }
  }, [mode, enableTTS, isSessionActive, isPTTActive, client]);

  // Initial Logic: If V2T mode, mute mic initially upon connection
  useEffect(() => {
    if (isSessionActive && !isConnecting && client) {
      if (!enableTTS) {
        // V2T Mode: Start Muted (PTT only)
        client.enableMic(false);
        toast.info("Hold Spacebar to talk");
      } else {
        // V2V Mode: Start Unmuted (VAD)
        client.enableMic(true);
      }
    }
  }, [isSessionActive, isConnecting, enableTTS, client]);

  // Handle browser/tab close - cleanup Daily room
  useEffect(() => {
    const handleBeforeUnload = () => {
      const roomUrl = currentRoomUrlRef.current;
      if (roomUrl && isSessionActive) {
        console.debug("[InputBar] beforeunload - cleaning up room:", roomUrl);
        // Use sendBeacon for reliable delivery during page unload
        navigator.sendBeacon(
          `${API_BASE_URL}/voice-mode/disconnect-beacon`,
          JSON.stringify({ room_url: roomUrl })
        );
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isSessionActive]);


  useRTVIClientEvent(RTVIEvent.BotConnected, () => {
    console.debug("[InputBar] RTVIEvent.BotConnected");
  });

  // Capture room URL when connected (for cleanup with startBotAndConnect)
  useRTVIClientEvent(RTVIEvent.Connected, () => {
    console.debug("[InputBar] RTVIEvent.Connected");
    // Try to get room URL from client's transport - try multiple property paths
    try {
      const transport = client?.transport as any;
      // DailyTransport exposes roomUrl via different paths depending on version
      const roomUrl =
        transport?.roomUrl ||
        transport?._roomUrl ||
        transport?.daily?.roomUrl ||
        transport?._daily?.roomUrl ||
        transport?.properties?.url ||
        (typeof transport?.getRoomUrl === 'function' ? transport.getRoomUrl() : null);

      console.debug("[InputBar] Transport room URL:", roomUrl);
      console.debug("[InputBar] Transport object keys:", transport ? Object.keys(transport) : "N/A");

      if (roomUrl) {
        updateRoomUrl(roomUrl);
      } else {
        console.warn("[InputBar] Could not extract room URL from transport");
      }
    } catch (e) {
      console.warn("[InputBar] Could not get room URL from transport:", e);
    }
  });

  useRTVIClientEvent(RTVIEvent.BotReady, () => {
    console.debug("[InputBar] RTVIEvent.BotReady - setting isConnecting to false");
    setConnecting(false);
    setVoiceState("listening"); // Start in listening state
    toast.success("Voice agent ready");
  });

  const handleStartSession = async () => {
    // If mocking
    if (USE_MOCK_BACKEND) {
      setVoiceDuration(0);
      setConnecting(true);
      setTimeout(() => {
        setConnecting(false);
        setSessionActive(true);
        toast.success("Voice agent ready (MOCK)");
      }, 1500);
      return;
    }

    if (!client) {
      console.debug("[InputBar] cannot join yet: Pipecat client not initialized");
      return;
    }

    setConnecting(true);
    setVoiceDuration(0);

	const activeConversationId = conversationId || pendingConversationId;
	if (!activeConversationId) {
		toast.error("No conversation ID available");
		setConnecting(false);
		return;
	}

    try {
      // Request mic permission
      if (typeof navigator !== "undefined" && navigator.mediaDevices?.getUserMedia) {
        try {
          await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (permErr) {
          console.warn("[InputBar] microphone permission denied", permErr);
          toast.error("Microphone permission denied. Please enable the mic to use Voice Mode.");
          setMode("text");
          setConnecting(false);
          return;
        }
      }

      // Use SDK's startBotAndConnect - handles client-ready/bot-ready handshake properly
      console.debug("[InputBar] Calling startBotAndConnect...");

      // Get auth token for API request
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const authToken = session?.access_token;

      await client.startBotAndConnect({
        endpoint: `${API_BASE_URL}/api/connect`,
        headers: authToken ? new Headers({ Authorization: `Bearer ${authToken}` }) : undefined,
        requestData: {
          session_id: "default",
			conversation_id: activeConversationId,
          enable_tts: enableTTS,
          persona: persona,
          strict_mode: strictMode,
        },
      });

      console.debug("[InputBar] startBotAndConnect completed successfully");
      console.debug("[InputBar] Client state after connect:", client?.state);

      // Store room URL from transport for cleanup (accessed via client)
      // Note: With startBotAndConnect, room URL is managed internally
      // We'll extract it from the client if needed for cleanup

      setSessionActive(true);

      // Safety timeout - if still connecting after 30 seconds, trigger error state
      setTimeout(() => {
        const isStillConnecting = useInputBarStore.getState().isConnecting;
        if (isStillConnecting) {
          setError("Connection timed out");
          setVoiceDuration(0);
        }
      }, 30000);

    } catch (error) {
      console.error("[InputBar] Failed to connect voice mode:", error);
      // Show error in voice capsule if still in voice mode
      setErrorMessage("Failed to connect");
      setVoiceState("error");
      setConnecting(false);
      // Keep isSessionActive true so error UI shows - user can retry from there
    }
  };

  // Handle Enter key for Voice Mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (mode === "voice" && !isSessionActive && !isConnecting && e.key === "Enter") {
        e.preventDefault();
        handleStartSession();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mode, isSessionActive, isConnecting]);

  useEffect(() => {
    // Cleanup on unmount or mode switch/mock toggle
    if (USE_MOCK_BACKEND && mode === "voice") {
      // Mock auto-logic removed. Now manual.
    }

    // If switching OUT of voice mode, disconnect
    if (mode === "text" && (client || isSessionActive)) {
      (async () => {
        try {
          if (client) await client.disconnect();
        } catch (err) { console.warn(err); }
        setSessionActive(false);
        setConnecting(false);
      })();
    }
  }, [mode, client, isSessionActive, setSessionActive, setConnecting]);

  // Debugging: log when the client object changes so we can trace readiness.
  useEffect(() => {
    console.debug("[InputBar] Pipecat client changed:", client);
    if (!client) {
      console.debug(
        "[InputBar] Pipecat client not ready yet - UI will wait before joining rooms.",
      );
    } else {
      console.debug("[InputBar] Pipecat client ready.");
    }
  }, [client]);

  // RTVI event handlers: keep hooks usage stable, but add debug logs inside handlers.
  useRTVIClientEvent(RTVIEvent.UserStartedSpeaking, (evt?: any) => {
    console.debug("[InputBar] RTVIEvent.UserStartedSpeaking", evt);
    setVoiceState("listening");
    // Clear the user transcript aggregator for a new utterance
    currentUserTranscriptRef.current = "";
  });

  useRTVIClientEvent(RTVIEvent.BotStartedSpeaking, (evt?: any) => {
    console.debug("[InputBar] RTVIEvent.BotStartedSpeaking", evt);
    setVoiceState("answering");
    // Note: Do NOT clear aggregator here - bot-output events with spoken:true
    // arrive BEFORE this event fires, so we'd lose the already-aggregated text
  });

  useRTVIClientEvent(RTVIEvent.BotStoppedSpeaking, (evt?: any) => {
    console.debug("[InputBar] RTVIEvent.BotStoppedSpeaking", evt);
    setVoiceState("listening");

    const rawLlmText = currentBotLlmTextRef.current.trim();
    const transcriptText = consumeVoiceTranscript();

    if (assistantMessageSentRef.current) {
      currentBotLlmTextRef.current = "";
      currentBotResponseRef.current = "";
      return;
    }

    const pendingCitations = consumePendingVoiceCitations();
    let sources = pendingCitations.length > 0 ? pendingCitations : undefined;

    if (!sources) {
      const hasMarkers = /\[\d+\]/.test(rawLlmText || transcriptText || "");
      if (hasMarkers && lastVoiceCitations.length > 0) {
        sources = lastVoiceCitations;
      }
    }

    if (rawLlmText) {
      console.debug("[InputBar] Sending raw LLM text with citation markers:", rawLlmText.substring(0, 100));
      onVoiceMessage?.({ 
        role: "assistant", 
        content: rawLlmText,
        sources
      });
    } else if (transcriptText) {
      onVoiceMessage?.({
        role: "assistant",
        content: transcriptText,
        sources
      });
    } else {
      // Fallback to aggregated BotOutput if raw LLM text not available
      const fullResponse = currentBotResponseRef.current.trim();
      if (fullResponse) {
        console.debug("[InputBar] Fallback: Sending filtered bot response:", fullResponse);
        onVoiceMessage?.({ 
          role: "assistant", 
          content: fullResponse,
          sources
        });
      }
    }
    
    assistantMessageSentRef.current = true;
    currentBotLlmTextRef.current = "";
    currentBotResponseRef.current = "";
  });

  useRTVIClientEvent(RTVIEvent.Message, (data: any) => {
    const message = data?.message || data?.data || data;
    if (message?.type === "citations" && Array.isArray(message.sources)) {
      console.debug("[InputBar] Received citations from RTVI:", message.sources.length);
      setPendingVoiceCitations(message.sources);

      const state = useConversationStore.getState();
      const lastAssistant = [...state.messages]
        .reverse()
        .find((m) => m.role === "assistant");

      if (lastAssistant && (!lastAssistant.sources || lastAssistant.sources.length === 0)) {
        state.updateMessage(lastAssistant.id, { sources: message.sources });
      }
    }
    if (message?.type === "transcript" && message.text && !assistantMessageSentRef.current) {
      const pendingCitations = consumePendingVoiceCitations();
      let sources = pendingCitations.length > 0 ? pendingCitations : undefined;
      if (!sources) {
        const hasMarkers = /\[\d+\]/.test(message.text);
        if (hasMarkers && lastVoiceCitations.length > 0) {
          sources = lastVoiceCitations;
        }
      }
      onVoiceMessage?.({ role: "assistant", content: message.text, sources });
      assistantMessageSentRef.current = true;
      currentBotLlmTextRef.current = "";
      currentBotResponseRef.current = "";
    }
  });

  // Voice transcript handlers - capture transcripts to display in chat
  useRTVIClientEvent(RTVIEvent.UserTranscript, (data: TranscriptData) => {
    console.debug("[InputBar] RTVIEvent.UserTranscript:", data);
    // Aggregate final transcripts - don't send immediately
    // The complete message will be sent when bot starts responding
    if (data.final && data.text && data.text.trim()) {
      // Add space between segments if there's already content
      if (currentUserTranscriptRef.current) {
        currentUserTranscriptRef.current += " ";
      }
      currentUserTranscriptRef.current += data.text.trim();
      console.debug("[InputBar] Aggregated user text:", currentUserTranscriptRef.current);
    }
  });

  useRTVIClientEvent(RTVIEvent.BotLlmStarted, () => {
    console.debug("[InputBar] RTVIEvent.BotLlmStarted");
    setVoiceState("processing");
    
    // Reset LLM text aggregator for new response
    currentBotLlmTextRef.current = "";
    currentBotResponseRef.current = "";
    assistantMessageSentRef.current = false;
    
    const fullUserMessage = currentUserTranscriptRef.current.trim();
    if (fullUserMessage) {
      console.debug("[InputBar] Sending aggregated user message:", fullUserMessage);
      onVoiceMessage?.({ role: "user", content: fullUserMessage });
      currentUserTranscriptRef.current = "";
    }
  });

  // Capture raw LLM output (with citation markers) - this is the unfiltered text
  useRTVIClientEvent(RTVIEvent.BotLlmText, (data: any) => {
    const text = data?.text || data?.data?.text;
    if (text) {
      currentBotLlmTextRef.current += text;
      console.debug("[InputBar] RTVIEvent.BotLlmText - aggregated raw LLM text:", currentBotLlmTextRef.current.substring(0, 100));
    }
  });

  // Capture bot's spoken output (filtered, no markers) - used as fallback
  useRTVIClientEvent(RTVIEvent.BotOutput, (data: any) => {
    const text = data?.text || data?.data?.text;
    const spoken = data?.spoken ?? data?.data?.spoken;

    if (spoken && text && text.trim()) {
      const trimmedText = text.trim();
      if (currentBotResponseRef.current && !currentBotResponseRef.current.endsWith(" ")) {
        currentBotResponseRef.current += " ";
      }
      currentBotResponseRef.current += trimmedText;
    }
  });

  // Handle disconnection (bot left, error, or user disconnect)
  useRTVIClientEvent(RTVIEvent.Disconnected, () => {
    const roomUrl = currentRoomUrlRef.current;
    console.debug("[InputBar] RTVIEvent.Disconnected - resetting session state, roomUrl:", roomUrl);

    // Clean up Daily room if we have a URL (atomic check-and-clear to prevent duplicates)
    if (roomUrl) {
      // Clear immediately to prevent duplicate cleanup from handleDisconnect
      updateRoomUrl(null);
      console.debug("[InputBar] Cleaning up Daily room on disconnect event");
      endVoiceMode(roomUrl).then(result => {
        console.debug("[InputBar] endVoiceMode result (from Disconnected event):", result);
      });
    }

    // If we were in an active session and it wasn't a user-initiated disconnect,
    // show error state instead of silently closing
    if (isSessionActive && voiceState !== "error") {
      setErrorMessage("Connection lost");
      setVoiceState("error");
      setConnecting(false);
      // Keep isSessionActive true so error UI shows
    } else {
      setSessionActive(false);
      setConnecting(false);
      setVoiceDuration(0);
    }
  });

  // Handle connection errors from backend
  useRTVIClientEvent(RTVIEvent.Error, (error: any) => {
    console.error("[InputBar] RTVIEvent.Error:", error);

    // Categorize error and set appropriate message
    let message = "Connection error";
    const errorStr = JSON.stringify(error).toLowerCase();

    if (errorStr.includes("timeout") || errorStr.includes("timed out")) {
      message = "Connection timed out";
    } else if (errorStr.includes("network") || errorStr.includes("disconnected")) {
      message = "Network connection lost";
    } else if (errorStr.includes("microphone") || errorStr.includes("permission")) {
      message = "Microphone access required";
    } else if (errorStr.includes("rate") || errorStr.includes("limit")) {
      message = "Too many requests";
    } else if (errorStr.includes("service") || errorStr.includes("unavailable")) {
      message = "Service unavailable";
    }

    setErrorMessage(message);
    setVoiceState("error");
    setConnecting(false);
    // Keep session "active" so error UI shows in the voice bar
    // User can retry or close from there
  });



  const handleDisconnect = async () => {
    const roomUrl = currentRoomUrlRef.current;
    if (roomUrl) {
      updateRoomUrl(null);
      await endVoiceMode(roomUrl);
    }
    try {
      if (client) await client.disconnect();
    } catch (err) {
      console.warn("[InputBar] disconnect error:", err);
    }
    endSession();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message, persona, strictMode);
      setMessage("");
    }
  };

  // Voice Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (mode === "voice" && isSessionActive) {
      interval = setInterval(() => {
        incrementVoiceDuration();
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [mode, isSessionActive, incrementVoiceDuration]);

  // Format seconds to MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")} `;
  };







  const { modifier, isMobile } = usePlatform();

  // 1. Main / Initial Bar / Mode Switcher
  if (!hasInteracted) {
    return (
      <div className="w-full max-w-3xl mx-auto p-4 mb-20 md:mb-10 mt-auto pb-safe">
        <div className="flex items-center justify-center gap-3">
          <input
            type="file"
            multiple
            ref={fileInputRef}
            className="hidden"
            onChange={handleFileSelect}
          />

          <div className="h-16 w-full max-w-lg bg-black/40 backdrop-blur-2xl border border-white/10 rounded-full p-1.5 flex items-center justify-center gap-1 shadow-2xl ring-1 ring-white/5">
            {/* Text Mode Option */}
            <button
              onClick={() => handleModeSelect("text")}
              className="relative flex-1 h-full rounded-full flex items-center justify-center gap-2 transition-all duration-300 group hover:bg-white/5 text-white cursor-pointer"
            >
              <MessageSquare className="w-5 h-5 transition-colors text-white" />
              <span className="text-lg font-medium">Text Mode</span>
              <ActionTooltip label="Text Mode" shortcut={`${modifier}+T`} side="top" />
            </button>

            {/* Vertical Divider */}
            <div className="w-px h-6 bg-white/10 mx-1" />

            {/* Voice Mode Option */}
            <button
              onClick={() => handleModeSelect("voice")}
              className="relative flex-1 h-full rounded-full flex items-center justify-center gap-2 transition-all duration-300 group hover:bg-white/5 text-white cursor-pointer"
            >
              <Mic className="w-5 h-5 transition-colors text-white" />
              <span className="text-lg font-medium">Voice Mode</span>
              <ActionTooltip label="Voice Mode" shortcut={`${modifier}+V`} side="top" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 2. Text Mode Bar
  if (mode === "text") {
    return (
      <div className="w-full max-w-3xl mx-auto p-4 mb-20 md:mb-10 mt-auto pb-safe">
        <div className="flex items-end gap-3">
          {/* Attachment Button - Hidden on mobile */}
          <div className="hidden md:block">
            <AttachmentButton
              onUploadClick={triggerFileInput}
              onViewFilesClick={toggleSourcesPanel}
            />
          </div>
          <input
            type="file"
            multiple
            ref={fileInputRef}
            className="hidden"
            onChange={handleFileSelect}
          />



          <form
            onSubmit={handleSubmit}
            className="flex-1 bg-surface/80 backdrop-blur-md border border-white/10 rounded-[32px] shadow-lg transition-all focus-within:ring-1 focus-within:ring-white/20 flex flex-row items-end min-h-[3.5rem] md:min-h-[4rem] overflow-hidden md:overflow-visible"
          >
            <textarea
              ref={(el) => {
                // Determine if we need to auto-focus on first mount
                const isMounting = !textareaRef.current && el;
                textareaRef.current = el;
                if (el) {
                  el.style.height = "auto";
                  el.style.height = el.scrollHeight + "px";
                  // If we just mounted and mode is text, we might want to focus
                  // But the useEffect handles that.
                }
              }}
              value={message}
              onChange={(e) => {
                setMessage(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = e.target.scrollHeight + "px";
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder={isMobile ? "Ask anything..." : "Find answers to your curiosity"}
              rows={1}
              className="flex-1 bg-transparent border-none py-3 md:py-4 pl-4 md:pl-6 pr-2 text-lg focus:outline-none placeholder:text-text-secondary/50 resize-none overflow-hidden max-h-[200px] overflow-y-auto min-h-[3.5rem] md:min-h-[4rem]"
            />

            <div className="flex items-center gap-0.5 md:gap-1 pr-2 md:pr-3 pb-1 md:pb-2 shrink-0">
              <Button
                type={isLoading ? "button" : "submit"}
                size="icon"
                variant="ghost"
                disabled={!isLoading && !message.trim()}
                onClick={(e) => {
                  if (isLoading && onStop) {
                    e.preventDefault();
                    onStop();
                  }
                }}
                className="rounded-full w-12 h-12 text-text-primary hover:bg-transparent overflow-hidden"
              >
                <AnimatePresence mode="wait">
                  {isLoading ? (
                    <motion.div
                      key="stop"
                      initial={{ scale: 0.5, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.5, opacity: 0 }}
                      className="relative w-full h-full flex items-center justify-center group/stop"
                    >
                      {/* Spinning Spinner */}
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                        className="absolute inset-2 rounded-full border-2 border-white/10 border-t-white"
                      />

                      {/* Stop Icon - Morph/Hover effect */}
                      <div className="relative w-8 h-8 rounded-full bg-white/10 group-hover/stop:bg-red-500/20 flex items-center justify-center transition-colors duration-300 backdrop-blur-sm">
                        <Square className="w-3 h-3 fill-white text-white group-hover/stop:scale-90 transition-transform" />
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="send"
                      initial={{ scale: 0.5, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.5, opacity: 0 }}
                      className="w-full h-full flex items-center justify-center hover:bg-white/10 rounded-full transition-colors"
                    >
                      <SendHorizontal className="w-6 h-6" />
                    </motion.div>
                  )}
                </AnimatePresence>
              </Button>

              <div className="w-px h-6 bg-white/10 mx-1" />

              {/* Desktop Controls */}
              <div className="hidden md:flex items-center gap-1">
                <StrictModeToggle />
                <PersonaSelector />
              </div>

              {/* Mobile Controls */}
              <div className="flex md:hidden">
                <MobileTextControls />
              </div>
            </div>
          </form>

          <Button
            type="button"
            size="icon"
            className="relative group h-14 w-14 md:h-16 md:w-16 rounded-full bg-black/40 backdrop-blur-2xl border border-white/10 hover:bg-white/10 text-text-primary shadow-lg shrink-0"
            onClick={() => setMode("voice")}
          >
            <Mic className="w-6 h-6" />
            <ActionTooltip label="Voice Mode" shortcut={`${modifier}+V`} side="top" />
          </Button>
        </div >
      </div >

    );
  }

  // 3. Voice Mode Bar (Listening & Answering)
  return (
    <div className="w-full max-w-3xl mx-auto p-4 mb-20 md:mb-10 mt-auto pb-safe">
      <div className="flex items-center gap-3">
        {/* Attachment Button - Hidden on mobile */}
        <div className="hidden md:block">
          <AttachmentButton
            onUploadClick={triggerFileInput}
            onViewFilesClick={toggleSourcesPanel}
          />
        </div>
        <input
          type="file"
          multiple
          ref={fileInputRef}
          className="hidden"
          onChange={handleFileSelect}
        />

        {/* Main Voice Control Bar */}
        <div className="flex-1 h-14 md:h-16 bg-surface/80 backdrop-blur-md border border-white/10 rounded-full shadow-2xl flex items-center p-1.5 gap-4 relative ring-1 ring-white/5">
          {/* Dynamic Background Glow */}
          <div
            className={cn(
              "absolute inset-0 opacity-10 transition-colors duration-500 pointer-events-none",
              (!isSessionActive || isConnecting) ? "bg-transparent" : voiceState === "listening" ? "bg-accent" : "bg-transparent",
            )}
          />

          {/* Waveform / Status Area OR Start Button */}
          {!isSessionActive && !isConnecting ? (
            <div className="flex-1 flex items-center justify-center relative z-10 w-full h-full">
              <Button
                variant="ghost"
                className="w-full h-full rounded-full bg-transparent hover:bg-white/5 text-white font-medium flex items-center justify-center gap-2 transition-all duration-300"
                onClick={handleStartSession}
              >
                <Play className="w-5 h-5 fill-current" />
                <span>Start Voice Session</span>
              </Button>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div
                className={cn(
                  "flex items-center justify-center gap-3 px-6 py-2 rounded-full transition-all duration-500 min-w-[360px] relative z-10",
                  isConnecting
                    ? "bg-white/5 text-text-primary border border-white/5"
                    : voiceState === "listening"
                      ? "bg-blue-500/20 border-blue-500/30 text-blue-100"
                      : voiceState === "processing"
                        ? "bg-amber-500/20 border-amber-500/30 text-amber-100"
                        : voiceState === "error"
                          ? "bg-red-500/20 border-red-500/30 text-red-100"
                          : "bg-emerald-500/20 border-emerald-500/30 text-emerald-100"
                )}
              >
                <span className="font-mono text-lg font-medium tracking-wider opacity-90">
                  {formatTime(voiceDuration)}
                </span>

                {/* Status Text */}
                <div className="flex items-center gap-2 ml-1">
                  {isConnecting ? (
                    <>
                      <div className="w-2 h-2 rounded-full bg-white/50 animate-pulse" />
                      <span className="text-sm font-medium">Connecting..</span>
                    </>
                  ) : voiceState === "listening" ? (
                    <>
                      <VoiceVisualizer
                        participantType="local"
                        backgroundColor="transparent"
                        barColor="#60a5fa"
                        barWidth={2}
                        barGap={1}
                        barMaxHeight={14}
                      />
                      <span className="text-sm font-medium">Listening..</span>
                    </>
                  ) : voiceState === "processing" ? (
                    <>
                      <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                      <span className="text-sm font-medium">Processing..</span>
                    </>
                  ) : voiceState === "error" ? (
                    <>
                      <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span className="text-sm font-medium">{errorMessage}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          // Clean up old room first
                          const roomUrl = currentRoomUrlRef.current;
                          if (roomUrl) {
                            endVoiceMode(roomUrl);
                            updateRoomUrl(null);
                          }
                          // Reset state and retry
                          setVoiceState("listening");
                          setErrorMessage("");
                          setSessionActive(false);
                          // Small delay then restart
                          setTimeout(() => {
                            handleStartSession();
                          }, 100);
                        }}
                        className="ml-2 px-2 py-0.5 text-xs font-medium bg-red-500/30 hover:bg-red-500/50 rounded transition-colors"
                      >
                        Retry
                      </button>
                    </>
                  ) : (
                    <>
                      <VoiceVisualizer
                        participantType="bot"
                        backgroundColor="transparent"
                        barColor="#34d399"
                        barWidth={2}
                        barGap={1}
                        barMaxHeight={14}
                      />
                      <span className="text-sm font-medium">Answering..</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Spacer - Only show when session active to push controls right. When inactive, let StartButton take full width to center. */}
          {/* Spacer - Removed because flex-1 wrapper on Status handles centering/pushing */}

            {/* Controls */}
            <div className="flex items-center gap-1 md:gap-2 pr-2 relative z-10 max-w-full justify-end">
              <div className="w-px h-4 bg-white/10 mx-1" />

              {/* Desktop Controls */}
              <div className="hidden md:flex items-center gap-2">
                <StrictModeToggle />
                <PersonaSelector />
                <VoiceSettings />
              </div>

            {/* Mobile Controls (Menu) */}
            <div className="flex md:hidden">
              <MobileVoiceControls />
            </div>



            {(isSessionActive || isConnecting) && (
              <Button
                size="icon"
                variant="ghost"
                className="rounded-full w-10 h-10 text-text-secondary hover:bg-red-500/10 hover:text-red-500 transition-colors"
                onClick={handleDisconnect}
                title="End Session"
              >
                <X className="w-5 h-5" />
              </Button>
            )}
          </div>
        </div>

        {/* Switch to Text Button */}
        <Button
          type="button"
          size="icon"
          className="relative group h-14 w-14 md:h-16 md:w-16 rounded-full bg-black/40 backdrop-blur-2xl border border-white/10 hover:bg-white/10 text-text-primary shadow-lg shrink-0"
          onClick={() => setMode("text")}
        >
          <MessageSquare className="w-6 h-6" />
          <ActionTooltip label="Text Mode" shortcut={`${modifier}+T`} side="top" />
        </Button>
      </div>
    </div >
  );
}
