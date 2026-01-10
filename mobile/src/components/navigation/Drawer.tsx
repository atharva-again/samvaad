import { View, Text, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MotiView } from "moti";
import { MessageSquare, Plus, Pin, Trash2, Search, Settings, X } from "lucide-react-native";
import { useConversationStore, type Conversation } from "@/lib/stores/useConversationStore";
import { COLORS } from "@/constants";
import { router } from "expo-router";
import * as Haptics from "expo-haptics";
import { formatTimeAgo, truncateText } from "@/lib/utils";
import { useUIStore } from "@/lib/stores/useUIStore";

export function Drawer() {
  const { conversations, currentConversationId, setCurrentConversation, startNewChat, deleteConversation, togglePinConversation } = useConversationStore();
  const { toggleSidebar } = useUIStore();

  const handleNewChat = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    startNewChat();
    toggleSidebar();
    router.push("/(app)");
  };

  const handleSelectConversation = (id: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setCurrentConversation(id);
    toggleSidebar();
    router.push(`/(app)/chat/${id}`);
  };

  const handleDelete = (id: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    deleteConversation(id);
  };

  const handleTogglePin = (id: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    togglePinConversation(id);
  };

  return (
    <SafeAreaView className="flex-1 bg-surface border-r border-white/10">
      <View className="flex-1 px-4 pt-4">
        <View className="flex-row items-center justify-between mb-6">
          <View className="flex-row items-center gap-2">
            <Text className="text-xl font-bold text-white">Samvaad</Text>
          </View>
          <View className="flex-row items-center gap-1">
            <Pressable onPress={() => {}} className="p-2 rounded-full active:bg-white/10">
              <Search size={20} color={COLORS.textSecondary} />
            </Pressable>
            <Pressable onPress={toggleSidebar} className="p-2 rounded-full active:bg-white/10">
              <X size={20} color={COLORS.textSecondary} />
            </Pressable>
          </View>
        </View>


        <Pressable
          onPress={handleNewChat}
          className="flex-row items-center justify-center gap-2 p-4 mb-6 rounded-xl bg-indigo-500/10 border border-indigo-500/20 active:bg-indigo-500/20"
        >
          <Plus size={20} color={COLORS.accent} />
          <Text className="text-base font-semibold text-white">New Chat</Text>
        </Pressable>

        <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
          {conversations.length === 0 ? (
            <View className="items-center justify-center py-12">
              <MessageSquare size={32} color="rgba(255,255,255,0.1)" />
              <Text className="text-white/30 text-sm mt-4">No conversations yet</Text>
            </View>
          ) : (
            <View className="gap-2">
              {conversations.map((conv) => (
                <MotiView
                  key={conv.id}
                  from={{ opacity: 0, translateX: -10 }}
                  animate={{ opacity: 1, translateX: 0 }}
                  className={`flex-row items-center gap-3 p-3 rounded-xl border ${
                    currentConversationId === conv.id
                      ? "bg-white/10 border-white/10"
                      : "bg-transparent border-transparent"
                  }`}
                >
                  <Pressable
                    onPress={() => handleSelectConversation(conv.id)}
                    className="flex-1 flex-row items-center gap-3"
                  >
                    <View className={`w-8 h-8 rounded-lg items-center justify-center ${
                      conv.isPinned ? "bg-amber-500/20" : "bg-white/5"
                    }`}>
                      <MessageSquare size={16} color={conv.isPinned ? "#fbbf24" : COLORS.textSecondary} />
                    </View>
                    <View className="flex-1">
                      <Text
                        className={`text-sm font-medium ${
                          currentConversationId === conv.id ? "text-white" : "text-white/70"
                        }`}
                        numberOfLines={1}
                      >
                        {conv.title}
                      </Text>
                      <Text className="text-[10px] text-white/40 mt-0.5">
                        {formatTimeAgo(conv.updatedAt || conv.createdAt)}
                      </Text>
                    </View>
                  </Pressable>

                  <View className="flex-row items-center gap-1">
                    <Pressable
                      onPress={() => handleTogglePin(conv.id)}
                      className="p-1.5 rounded-md active:bg-white/10"
                    >
                      <Pin size={14} color={conv.isPinned ? "#fbbf24" : "rgba(255,255,255,0.2)"} />
                    </Pressable>
                    <Pressable
                      onPress={() => handleDelete(conv.id)}
                      className="p-1.5 rounded-md active:bg-red-500/10"
                    >
                      <Trash2 size={14} color="rgba(239, 68, 68, 0.4)" />
                    </Pressable>
                  </View>
                </MotiView>
              ))}
            </View>
          )}
        </ScrollView>

        <View className="pt-4 border-t border-white/10">
          <Pressable
            onPress={() => {}}
            className="flex-row items-center gap-3 p-3 mb-2 rounded-xl active:bg-white/5"
          >
            <Settings size={20} color={COLORS.textSecondary} />
            <Text className="text-sm font-medium text-white/70">Settings</Text>
          </Pressable>
        </View>
      </View>
    </SafeAreaView>
  );
}
