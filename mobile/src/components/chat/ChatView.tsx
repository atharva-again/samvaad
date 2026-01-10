import { useState, useRef, useCallback, useMemo, useEffect } from "react";
import { View, ActivityIndicator, Text, Pressable, KeyboardAvoidingView, Platform } from "react-native";
import { router } from "expo-router";
import { toast } from "sonner-native";
import { uuidv7 } from "uuidv7";
import { Menu, Search as SearchIcon, Share2 } from "lucide-react-native";
import { MessageList } from "./MessageList";
import { WelcomeScreen } from "./WelcomeScreen";
import { InputBar } from "./InputBar";
import { useConversationStore, type Message } from "@/lib/stores/useConversationStore";
import { useUIStore } from "@/lib/stores/useUIStore";
import { sendMessage } from "@/lib/api";
import { COLORS } from "@/constants";
import { useSafeAreaInsets } from "react-native-safe-area-context";

interface ChatViewProps {
  conversationId?: string;
}

export function ChatView({ conversationId }: ChatViewProps) {
  const insets = useSafeAreaInsets();
  const {
    currentConversationId,
    messages: storeMessages,
    isLoadingMessages,
    isStreaming,
    setIsStreaming,
    addMessage,
    addMessageToUI,
    setCurrentConversation,
    clearMessages,
    truncateMessagesAt,
    addConversationOptimistic,
    updateConversationId,
    loadConversation,
  } = useConversationStore();

  const { allowedSourceIds, isVoiceSessionActive, activeVoiceConversationId, toggleSidebar } =
    useUIStore();

  const messages = useMemo<Message[]>(() => storeMessages, [storeMessages]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const prevConversationIdRef = useRef<string | undefined>(undefined);
  const voiceConversationIdRef = useRef<string | null>(null);
  const listRef = useRef<any>(null);

  const [editMessageContent, setEditMessageContent] = useState<string | null>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  const handleScrollToBottom = useCallback(() => {
    listRef.current?.scrollToEnd({ animated: true });
    setShowScrollButton(false);
  }, []);

  const handleScroll = useCallback((event: any) => {
    const { layoutMeasurement, contentOffset, contentSize } = event.nativeEvent;
    const isCloseToBottom =
      layoutMeasurement.height + contentOffset.y >= contentSize.height - 200;
    setShowScrollButton(!isCloseToBottom);
  }, []);

  useEffect(() => {
    const isNavigating = conversationId !== prevConversationIdRef.current;
    if (isNavigating && conversationId) {
      const storeCurrentId = useConversationStore.getState().currentConversationId;
      const isCurrentConversationUrlUpdate = storeCurrentId === conversationId;

      const shouldSkipReset =
        isCurrentConversationUrlUpdate ||
        isVoiceSessionActive ||
        activeVoiceConversationId === conversationId;

      if (!shouldSkipReset) {
        useUIStore.getState().setHasInteracted(false);
        voiceConversationIdRef.current = null;
      }
    }
    prevConversationIdRef.current = conversationId;
  }, [conversationId, isVoiceSessionActive, activeVoiceConversationId]);

  useEffect(() => {
    if (conversationId && !isVoiceSessionActive) {
      loadConversation(conversationId);
    }
  }, [conversationId, loadConversation, isVoiceSessionActive]);

  useEffect(() => {
    if (!conversationId) {
      if (currentConversationId || storeMessages.length > 0) {
        clearMessages();
      }
    }
  }, [conversationId, clearMessages, currentConversationId, storeMessages.length]);

  const handleSendMessage = useCallback(
    async (text: string, persona: string = "default", strictMode: boolean = false) => {
      const isNewConversation = !conversationId && !currentConversationId;
      const newConversationId = isNewConversation ? uuidv7() : null;

      if (isNewConversation && newConversationId) {
        addConversationOptimistic(
          newConversationId,
          text.slice(0, 50) + (text.length > 50 ? "..." : "")
        );
        setCurrentConversation(newConversationId);
        router.replace(`/chat/${newConversationId}`);
      }

      const activeConversationId =
        conversationId || currentConversationId || newConversationId;

      const userMessageId = uuidv7();
      const assistantMessageId = uuidv7();

      addMessage(
        {
          id: userMessageId,
          role: "user",
          content: text,
          createdAt: new Date().toISOString(),
        },
        activeConversationId ?? undefined
      );
      setIsStreaming(true);

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      try {
        const data = await sendMessage(
          text,
          activeConversationId,
          abortController.signal,
          persona,
          strictMode,
          userMessageId,
          assistantMessageId,
          allowedSourceIds ? Array.from(allowedSourceIds) : null
        );

        if (data.success) {
          if (
            newConversationId &&
            data.conversation_id &&
            data.conversation_id !== newConversationId
          ) {
            updateConversationId(newConversationId, data.conversation_id);
            router.replace(`/chat/${data.conversation_id}`);
          }

          addMessage(
            {
              id: assistantMessageId,
              role: "assistant",
              content: data.response,
              sources: data.sources,
              createdAt: new Date().toISOString(),
            },
            activeConversationId ?? undefined
          );
        } else {
          toast.error(data.error || "Failed to get response");
        }
      } catch (error: unknown) {
        const err = error as { name?: string; code?: string };
        if (err.name === "CanceledError" || err.code === "ERR_CANCELED") {
          console.debug("Request canceled via stop button");
        } else {
          console.error("Error calling text-mode:", error);
          toast.error("Something went wrong. Please try again.");
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [
      conversationId,
      currentConversationId,
      addConversationOptimistic,
      setCurrentConversation,
      addMessage,
      setIsStreaming,
      updateConversationId,
      allowedSourceIds,
    ]
  );

  const handleStop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }, [setIsStreaming]);

  const handleVoiceMessage = useCallback(
    async (message: { role: "user" | "assistant" | "system"; content: string; sources?: unknown[] }) => {
      if (!message.content || !message.content.trim()) {
        return;
      }

      const storeState = useConversationStore.getState();
      const activeConversationId = conversationId || storeState.currentConversationId;

      const isFirstUserMessage =
        !voiceConversationIdRef.current &&
        message.role === "user" &&
        !activeConversationId;

      let targetConversationId = activeConversationId;
      if (isFirstUserMessage) {
        const title =
          message.content.slice(0, 50) + (message.content.length > 50 ? "..." : "");

        const newId = await useConversationStore.getState().createConversation(title, "voice");
        targetConversationId = newId;
        voiceConversationIdRef.current = newId;

        if (!conversationId) {
          router.replace(`/chat/${newId}`);
        }
      }

      addMessageToUI({
        id: uuidv7(),
        role: message.role,
        content: message.content,
        createdAt: new Date().toISOString(),
        sources: (message.sources as Record<string, unknown>[]) || undefined,
      });
    },
    [conversationId, addMessageToUI]
  );

  const handleEditMessage = useCallback(
    (index: number, content: string) => {
      truncateMessagesAt(index);
      setEditMessageContent(content);
    },
    [truncateMessagesAt]
  );

  const handleRegenerate = useCallback(
    (index: number) => {
      const userMessage = storeMessages[index - 1];
      if (userMessage && userMessage.role === "user") {
        truncateMessagesAt(index);
        handleSendMessage(userMessage.content, persona, strictMode);
      }
    },
    [storeMessages, truncateMessagesAt, handleSendMessage, persona, strictMode]
  );

  if (isLoadingMessages) {
    return (
      <View className="flex-1 items-center justify-center">
        <ActivityIndicator size="large" color={COLORS.accent} />
        <Text className="text-white/30 text-sm mt-4">Loading conversation...</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      className="flex-1 bg-void"
      style={{ paddingTop: insets.top }}
    >
      <View className="h-14 flex-row items-center justify-between px-4 border-b border-white/5">
        <Pressable
          onPress={toggleSidebar}
          className="p-2 -ml-2 rounded-full active:bg-white/10"
        >
          <Menu size={24} color={COLORS.textPrimary} />
        </Pressable>

        <View className="flex-1 items-center">
          <Text className="text-white font-semibold text-base" numberOfLines={1}>
            {messages.length === 0 ? "Samvaad" : (useConversationStore.getState().conversations.find(c => c.id === (conversationId || currentConversationId))?.title || "Chat")}
          </Text>
        </View>

        <View className="flex-row items-center gap-1">
          <Pressable className="p-2 rounded-full active:bg-white/10">
            <SearchIcon size={20} color={COLORS.textSecondary} />
          </Pressable>
          <Pressable className="p-2 -mr-2 rounded-full active:bg-white/10">
            <Share2 size={20} color={COLORS.textSecondary} />
          </Pressable>
        </View>
      </View>

      {messages.length === 0 ? (
        <WelcomeScreen />
      ) : (
        <MessageList
          messages={messages}
          isLoading={isStreaming}
          onEdit={handleEditMessage}
          onRegenerate={handleRegenerate}
          listRef={listRef}
          onScroll={handleScroll}
        />
      )}
      <InputBar
        onSendMessage={handleSendMessage}
        isLoading={isStreaming}
        onStop={handleStop}
        defaultMessage={editMessageContent}
        onMessageConsumed={() => setEditMessageContent(null)}
        onVoiceMessage={handleVoiceMessage}
        conversationId={currentConversationId}
        showScrollButton={showScrollButton}
        onScrollToBottom={handleScrollToBottom}
      />
    </KeyboardAvoidingView>
  );
}
