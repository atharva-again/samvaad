import { View, Text, Pressable, Platform } from "react-native";
import { MotiView } from "moti";
import Markdown from "react-native-markdown-display";
import { Copy, Volume2, BookMarked, Square, RefreshCcw } from "lucide-react-native";
import * as Clipboard from "expo-clipboard";
import * as Haptics from "expo-haptics";
import { useState, useMemo, useCallback } from "react";
import { toast } from "sonner-native";
import { COLORS } from "@/constants";
import { useUIStore, type CitationItem } from "@/lib/stores/useUIStore";
import type { Message } from "@/lib/stores/useConversationStore";

interface MessageBubbleProps {
  message: Message;
  index: number;
  onEdit?: (index: number, content: string) => void;
  onRegenerate?: (index: number) => void;
}

export function MessageBubble({ message, index, onEdit, onRegenerate }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [showActions, setShowActions] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  const { openCitations } = useUIStore();

  const hasSources =
    !isUser &&
    message.sources &&
    Array.isArray(message.sources) &&
    message.sources.length > 0;

  const citedIndices = useMemo(() => {
    if (!hasSources) return undefined;
    const matches = message.content.match(/(?:\[(\d+)\]|【(\d+)】)/g);
    if (!matches) return undefined;

    const indices = new Set<number>();
    matches.forEach((m) => {
      const match = m.match(/(?:\[(\d+)\]|【(\d+)】)/);
      if (match) {
        const num = match[1] || match[2];
        if (num) indices.add(parseInt(num, 10) - 1);
      }
    });

    return Array.from(indices).sort((a, b) => a - b);
  }, [message.content, hasSources]);

  const processedContent = useMemo(() => {
    return message.content.replace(/【(\d+)】/g, "[$1]");
  }, [message.content]);

  const handleCopy = useCallback(async () => {
    await Clipboard.setStringAsync(message.content);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    toast.success("Copied to clipboard");
  }, [message.content]);

  const handleReadAloud = useCallback(async () => {
    if (isPlaying) {
      setIsPlaying(false);
      return;
    }
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setIsPlaying(true);
    setTimeout(() => setIsPlaying(false), 3000);
    toast.info("TTS coming soon");
  }, [isPlaying]);

  const handleShowCitations = useCallback(() => {
    if (hasSources && message.id && message.sources) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      openCitations(
        message.id,
        message.sources as unknown as CitationItem[],
        citedIndices
      );
    }
  }, [hasSources, message.id, message.sources, citedIndices, openCitations]);

  const markdownStyles = useMemo(
    () => ({
      body: {
        color: isUser ? COLORS.textPrimary : COLORS.textSecondary,
        fontSize: 16,
        lineHeight: 24,
      },
      heading1: {
        color: COLORS.textPrimary,
        fontSize: 24,
        fontWeight: "700" as const,
        marginBottom: 12,
        marginTop: 16,
      },
      heading2: {
        color: COLORS.textPrimary,
        fontSize: 20,
        fontWeight: "700" as const,
        marginBottom: 10,
        marginTop: 14,
      },
      heading3: {
        color: COLORS.textPrimary,
        fontSize: 18,
        fontWeight: "600" as const,
        marginBottom: 8,
        marginTop: 12,
      },
      paragraph: {
        marginBottom: 12,
        lineHeight: 24,
      },
      list_item: {
        marginBottom: 4,
      },
      bullet_list: {
        marginBottom: 12,
      },
      ordered_list: {
        marginBottom: 12,
      },
      code_inline: {
        backgroundColor: "rgba(255, 255, 255, 0.1)",
        borderRadius: 4,
        paddingHorizontal: 6,
        paddingVertical: 2,
        fontFamily: "monospace",
        fontSize: 14,
      },
      code_block: {
        backgroundColor: "rgba(0, 0, 0, 0.3)",
        borderRadius: 8,
        padding: 12,
        fontFamily: "monospace",
        fontSize: 14,
        marginVertical: 8,
      },
      fence: {
        backgroundColor: "rgba(0, 0, 0, 0.3)",
        borderRadius: 8,
        padding: 12,
        fontFamily: "monospace",
        fontSize: 14,
        marginVertical: 8,
      },
      blockquote: {
        borderLeftWidth: 4,
        borderLeftColor: COLORS.signal,
        paddingLeft: 12,
        marginVertical: 8,
        opacity: 0.8,
      },
      strong: {
        color: COLORS.textPrimary,
        fontWeight: "700" as const,
      },
      link: {
        color: COLORS.accent,
        textDecorationLine: "underline" as const,
      },
    }),
    [isUser]
  );

  return (
    <MotiView
      from={{ opacity: 0, translateY: 10 }}
      animate={{ opacity: 1, translateY: 0 }}
      transition={{ type: "timing", duration: 300 }}
      className={`mb-4 ${isUser ? "items-end" : "items-start"}`}
    >
      <Pressable
        onLongPress={() => {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          setShowActions(!showActions);
        }}
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-surface border border-white/10 rounded-br-sm"
            : "bg-transparent pl-0 rounded-bl-sm"
        }`}
      >
        {!isUser && (
          <View className="flex-row items-center gap-2 mb-1 opacity-50">
            <View className="w-1.5 h-1.5 rounded-full bg-signal" />
            <Text className="text-xs font-mono uppercase tracking-wider text-white">
              Samvaad
            </Text>
          </View>
        )}

        <Markdown style={markdownStyles}>{processedContent}</Markdown>

        {showActions && (
          <MotiView
            from={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex-row gap-2 mt-3 pt-3 border-t border-white/10"
          >
            <Pressable
              onPress={handleCopy}
              className="p-2 rounded-lg bg-white/5 active:bg-white/10"
            >
              <Copy size={16} color={COLORS.textSecondary} />
            </Pressable>

            {!isUser && (
              <>
                <Pressable
                  onPress={handleReadAloud}
                  className="p-2 rounded-lg bg-white/5 active:bg-white/10"
                >
                  {isPlaying ? (
                    <Square size={16} color={COLORS.accent} />
                  ) : (
                    <Volume2 size={16} color={COLORS.textSecondary} />
                  )}
                </Pressable>

                {onRegenerate && (
                  <Pressable
                    onPress={() => {
                      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                      onRegenerate(index);
                    }}
                    className="p-2 rounded-lg bg-white/5 active:bg-white/10"
                  >
                    <RefreshCcw size={16} color={COLORS.textSecondary} />
                  </Pressable>
                )}

                {hasSources && (
                  <Pressable
                    onPress={handleShowCitations}
                    className="p-2 rounded-lg bg-white/5 active:bg-white/10"
                  >
                    <BookMarked size={16} color={COLORS.textSecondary} />
                  </Pressable>
                )}
              </>
            )}
          </MotiView>
        )}
      </Pressable>
    </MotiView>
  );
}
