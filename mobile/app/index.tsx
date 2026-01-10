import { useEffect } from "react";
import { View, Text, Pressable, Dimensions } from "react-native";
import { router } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { MotiView, MotiText, AnimatePresence } from "moti";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import * as Haptics from "expo-haptics";
import { useAuth } from "@/contexts/AuthContext";
import { COLORS } from "@/constants";

const { width } = Dimensions.get("window");

export default function LandingScreen() {
  const { user, isLoading, signInWithGoogle } = useAuth();
  const insets = useSafeAreaInsets();

  useEffect(() => {
    if (user && !isLoading) {
      router.replace("/(app)");
    }
  }, [user, isLoading]);

  if (isLoading) {
    return (
      <View className="flex-1 bg-void items-center justify-center">
        <MotiView
          from={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "timing", duration: 300 }}
        >
          <View className="w-16 h-16 rounded-2xl bg-white items-center justify-center">
            <View className="w-6 h-6 bg-void rounded-md" />
          </View>
        </MotiView>
      </View>
    );
  }

  const handleSignIn = async () => {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await signInWithGoogle();
  };

  return (
    <View className="flex-1 bg-void" style={{ paddingTop: insets.top }}>
      <LinearGradient
        colors={["rgba(16,185,129,0.08)", "transparent"]}
        className="absolute top-0 left-0 right-0 h-[40%]"
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
      />

      <View className="flex-row items-center justify-between px-6 py-4">
        <View className="flex-row items-center gap-2.5">
          <View className="w-8 h-8 rounded-lg bg-white items-center justify-center">
            <View className="w-3.5 h-3.5 bg-void rounded-sm" />
          </View>
          <Text className="text-lg font-bold text-white tracking-tight">
            Samvaad
          </Text>
        </View>
        <Pressable
          onPress={handleSignIn}
          className="px-4 py-2 rounded-full border border-white/10 bg-white/5 active:bg-white/10"
        >
          <Text className="text-sm font-semibold text-white">Launch App</Text>
        </Pressable>
      </View>

      <View className="flex-1 px-6 justify-center items-center">
        <MotiView
          from={{ opacity: 0, translateY: 20 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 600 }}
          className="items-center"
        >
          <View className="flex-row items-center gap-2 px-3 py-1.5 mb-6 rounded-full bg-signal/10 border border-signal/20">
            <View className="w-2 h-2 rounded-full bg-signal" />
            <Text className="text-[10px] font-bold uppercase tracking-widest text-signal/80">
              Beta v1.0
            </Text>
          </View>

          <Text
            className="text-4xl font-bold text-white text-center leading-tight"
            style={{ maxWidth: width * 0.85 }}
          >
            Dialogue with{"\n"}Intelligence.
          </Text>

          <Text className="mt-6 text-base text-white/50 text-center font-medium leading-relaxed px-4">
            Samvaad bridges the gap between static documents and fluid
            conversations. Experience cited, multimodal intelligence.
          </Text>
        </MotiView>

        <MotiView
          from={{ opacity: 0, translateY: 30 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 600, delay: 200 }}
          className="mt-10 w-full items-center"
        >
          <Pressable
            onPress={handleSignIn}
            className="w-full max-w-[280px] py-4 rounded-2xl bg-white active:bg-white/90 items-center"
          >
            <Text className="text-base font-bold text-black">
              Start Free Trial
            </Text>
          </Pressable>

          <View className="flex-row items-center gap-3 mt-6 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10">
            <View className="flex-row">
              {[1, 2, 3].map((i) => (
                <View
                  key={i}
                  className="w-7 h-7 -ml-2 first:ml-0 rounded-full border-2 border-void bg-surface-elevation-2"
                />
              ))}
            </View>
            <Text className="text-xs font-bold text-white/70">
              Joined by <Text className="text-signal">2,400+</Text> learners
            </Text>
          </View>
        </MotiView>
      </View>

      <MotiView
        from={{ opacity: 0, translateY: 40 }}
        animate={{ opacity: 1, translateY: 0 }}
        transition={{ type: "timing", duration: 600, delay: 400 }}
        className="mx-4 mb-8 rounded-3xl border border-white/10 bg-surface overflow-hidden"
        style={{ height: 280 }}
      >
        <View className="flex-1 p-6">
          <View className="flex-row items-center gap-2 mb-4">
            <Ionicons name="chatbubbles-outline" size={16} color="#fff" />
            <Text className="text-xs font-mono uppercase tracking-wider text-white/40">
              Demo Preview
            </Text>
          </View>

          <View className="flex-row justify-end mb-4">
            <View className="px-4 py-2.5 rounded-2xl rounded-tr-sm bg-surface-light border border-white/5 max-w-[80%]">
              <Text className="text-sm text-white/80">
                how are north korean workers using ai
              </Text>
            </View>
          </View>

          <View className="gap-2">
            <View className="flex-row items-center gap-1.5">
              <View className="w-1.5 h-1.5 rounded-full bg-signal" />
              <Text className="text-[9px] font-mono uppercase tracking-widest text-white/40">
                Samvaad
              </Text>
            </View>
            <Text className="text-sm text-white/80 leading-relaxed">
              North Korean workers are using AI to scale fraudulent employment
              at technology companies
              <Text className="text-signal text-[10px] font-bold"> [1]</Text>.
              The actors are completely dependent on AI to function in technical
              roles
              <Text className="text-signal text-[10px] font-bold"> [2]</Text>.
            </Text>
          </View>
        </View>
      </MotiView>

      <View
        className="border-t border-white/5 px-6"
        style={{ paddingBottom: insets.bottom + 16, paddingTop: 16 }}
      >
        <View className="flex-row justify-between items-center">
          <Text className="text-[10px] font-bold tracking-widest uppercase text-white/20">
            © 2026 Samvaad Lab
          </Text>
          <View className="flex-row gap-6">
            <Text className="text-[10px] font-bold tracking-widest uppercase text-white/20">
              Privacy
            </Text>
            <Text className="text-[10px] font-bold tracking-widest uppercase text-white/20">
              Terms
            </Text>
          </View>
        </View>
      </View>
    </View>
  );
}
