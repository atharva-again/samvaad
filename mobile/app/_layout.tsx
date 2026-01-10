import "../global.css";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Toaster } from "sonner-native";
import { AuthProvider } from "@/contexts/AuthContext";
import { COLORS } from "@/constants";
import { PipecatProvider } from "@/components/providers/PipecatProvider";

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AuthProvider>
          <PipecatProvider>
            <Stack
              screenOptions={{
                headerShown: false,
                contentStyle: { backgroundColor: COLORS.void },
                animation: "fade",
              }}
            />
            <StatusBar style="light" />
            <Toaster
              theme="dark"
              position="top-center"
              toastOptions={{
                style: {
                  backgroundColor: COLORS.surface,
                  borderColor: "rgba(255,255,255,0.1)",
                  borderWidth: 1,
                },
              }}
            />
          </PipecatProvider>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
