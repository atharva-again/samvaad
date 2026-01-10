import { useRef, useEffect, useCallback } from "react";
import { View, Text } from "react-native";
import { FlashList } from "@shopify/flash-list";
import { MotiView } from "moti";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "@/lib/stores/useConversationStore";

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
  onEdit?: (index: number, content: string) => void;
  onRegenerate?: (index: number) => void;
  listRef?: React.RefObject<any>;
  onScroll?: (event: any) => void;
}

function LoadingIndicator() {
  return (
    <MotiView
      from={{ opacity: 0, translateY: 10 }}
      animate={{ opacity: 1, translateY: 0 }}
      className="mb-4 items-start"
    >
      <View className="pl-0">
        <View className="flex-row items-center gap-2 mb-1 opacity-50">
          <View className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
          <Text className="text-xs font-mono uppercase tracking-wider text-white">
            Samvaad
          </Text>
        </View>
        <View className="flex-row gap-1 h-4 items-center">
          <MotiView
            from={{ scale: 0.8, opacity: 0.5 }}
            animate={{ scale: 1.2, opacity: 1 }}
            transition={{
              type: "timing",
              duration: 400,
              loop: true,
              repeatReverse: true,
              delay: 0,
            }}
            className="w-1.5 h-1.5 bg-white/20 rounded-full"
          />
          <MotiView
            from={{ scale: 0.8, opacity: 0.5 }}
            animate={{ scale: 1.2, opacity: 1 }}
            transition={{
              type: "timing",
              duration: 400,
              loop: true,
              repeatReverse: true,
              delay: 150,
            }}
            className="w-1.5 h-1.5 bg-white/20 rounded-full"
          />
          <MotiView
            from={{ scale: 0.8, opacity: 0.5 }}
            animate={{ scale: 1.2, opacity: 1 }}
            transition={{
              type: "timing",
              duration: 400,
              loop: true,
              repeatReverse: true,
              delay: 300,
            }}
            className="w-1.5 h-1.5 bg-white/20 rounded-full"
          />
        </View>
      </View>
    </MotiView>
  );
}

export function MessageList({ messages, isLoading, onEdit, listRef: externalListRef, onScroll }: MessageListProps) {
  const internalListRef = useRef<FlashList<Message>>(null);
  const listRef = externalListRef || internalListRef;

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        listRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages.length, listRef]);

  const renderItem = useCallback(
    ({ item, index }: { item: Message; index: number }) => (
      <MessageBubble
        message={item}
        index={index}
        onEdit={onEdit}
        onRegenerate={onRegenerate}
      />
    ),
    [onEdit, onRegenerate]
  );

  const keyExtractor = useCallback(
    (item: Message, index: number) => item.id || `message-${index}`,
    []
  );

  const ListFooter = useCallback(() => {
    if (!isLoading) return null;
    return <LoadingIndicator />;
  }, [isLoading]);

  return (
    <View className="flex-1 w-full max-w-3xl mx-auto px-4 py-4">
      <FlashList
        ref={listRef}
        data={messages}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        estimatedItemSize={100}
        ListFooterComponent={ListFooter}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingBottom: 16 }}
        onScroll={onScroll}
        scrollEventThrottle={16}
      />
    </View>
  );
}
