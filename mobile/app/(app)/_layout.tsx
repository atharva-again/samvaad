import { useEffect } from "react";
import { Stack, router } from "expo-router";
import { View, Pressable } from "react-native";
import { useAuth } from "@/contexts/AuthContext";
import { COLORS } from "@/constants";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { useUIStore } from "@/lib/stores/useUIStore";
import { Drawer } from "@/components/navigation/Drawer";
import { MotiView, AnimatePresence } from "moti";

export default function AppLayout() {
  const { user, isLoading } = useAuth();
  const fetchConversations = useConversationStore((s) => s.fetchConversations);
  const { isSidebarOpen, toggleSidebar } = useUIStore();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/");
    }
  }, [user, isLoading]);

  useEffect(() => {
    if (user) {
      fetchConversations();
    }
  }, [user, fetchConversations]);

  if (isLoading || !user) {
    return null;
  }

  return (
    <View className="flex-1 bg-void">
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: COLORS.void },
          animation: "slide_from_right",
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="chat/[id]" />
        <Stack.Screen
          name="sources"
          options={{
            presentation: "modal",
            animation: "slide_from_bottom",
          }}
        />
        <Stack.Screen
          name="search"
          options={{
            presentation: "transparentModal",
            animation: "fade",
          }}
        />
      </Stack>

      <AnimatePresence>
        {isSidebarOpen && (
          <View className="absolute inset-0 z-40">
            <MotiView
              from={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60"
            >
              <Pressable className="flex-1" onPress={toggleSidebar} />
            </MotiView>
            <MotiView
              from={{ translateX: -300 }}
              animate={{ translateX: 0 }}
              exit={{ translateX: -300 }}
              transition={{ type: "timing", duration: 300 }}
              className="absolute top-0 bottom-0 left-0 w-[80%] max-w-[300px]"
            >
              <Drawer />
            </MotiView>
          </View>
        )}
      </AnimatePresence>
    </View>
  );
}
