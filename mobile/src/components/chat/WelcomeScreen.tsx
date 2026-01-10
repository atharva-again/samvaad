import { View, Text, Pressable } from "react-native";
import { MotiView } from "moti";
import { Sparkles, Mic, MessageSquare, BookOpen, Paperclip } from "lucide-react-native";
import { useUIStore } from "@/lib/stores/useUIStore";
import { COLORS } from "@/constants";
import * as Haptics from "expo-haptics";
import { router } from "expo-router";

interface QuickAction {
  icon: typeof MessageSquare;
  label: string;
  action: () => void;
}

export function WelcomeScreen() {
  const { setMode, setHasInteracted } = useUIStore();

  const handleModeSelect = (mode: "text" | "voice") => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setMode(mode);
    setHasInteracted(true);
  };

  const handleOpenSources = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    router.push("/sources");
  };

  const quickActions: QuickAction[] = [
    {
      icon: MessageSquare,
      label: "Text Mode",
      action: () => handleModeSelect("text"),
    },
    {
      icon: Mic,
      label: "Voice Mode",
      action: () => handleModeSelect("voice"),
    },
    {
      icon: Paperclip,
      label: "Attach Files",
      action: handleOpenSources,
    },
    {
      icon: BookOpen,
      label: "Sources",
      action: handleOpenSources,
    },
  ];

  const features = [
    { icon: Sparkles, label: "Instant answers from your document library" },
    { icon: Mic, label: "Fluid voice interactions with real-time transcription" },
  ];

  return (
    <View className="flex-1 items-center justify-center px-6">
      <View className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-indigo-500/5 rounded-full blur-3xl" />

      <MotiView
        from={{ opacity: 0, translateY: 20 }}
        animate={{ opacity: 1, translateY: 0 }}
        transition={{ type: "timing", duration: 700 }}
        className="items-center w-full max-w-lg"
      >
        <View className="mb-8 items-center">
          <Text className="text-4xl font-bold tracking-tight text-white mb-3">
            Samvaad
          </Text>
          <Text className="text-lg text-white/60 font-light text-center leading-relaxed">
            Transform your static documents into{"\n"}
            <Text className="text-indigo-400">dynamic conversations</Text>
          </Text>
        </View>

        <View className="w-full mb-8">
          {features.map((feature, index) => (
            <MotiView
              key={feature.label}
              from={{ opacity: 0, translateX: -20 }}
              animate={{ opacity: 1, translateX: 0 }}
              transition={{ type: "timing", duration: 500, delay: index * 100 }}
              className="flex-row items-center gap-3 py-2"
            >
              <View className="w-8 h-8 rounded-lg bg-indigo-500/10 items-center justify-center border border-indigo-500/10">
                <feature.icon size={16} color={COLORS.accent} />
              </View>
              <Text className="flex-1 text-sm text-white/70 font-medium">
                {feature.label}
              </Text>
            </MotiView>
          ))}
        </View>

        <View className="flex-row items-center w-full mb-4">
          <View className="flex-1 h-px bg-white/10" />
          <Text className="px-4 text-[10px] font-bold text-white/40 uppercase tracking-widest">
            Quick Actions
          </Text>
          <View className="flex-1 h-px bg-white/10" />
        </View>

        <View className="flex-row flex-wrap w-full gap-3">
          {quickActions.map((action, index) => (
            <MotiView
              key={action.label}
              from={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "timing", duration: 400, delay: index * 50 }}
              className="flex-1 min-w-[45%]"
            >
              <Pressable
                onPress={action.action}
                className="flex-row items-center gap-3 p-4 rounded-xl bg-surface/40 border border-white/5 active:bg-white/10"
              >
                <action.icon size={18} color={COLORS.accent} />
                <Text className="text-sm font-medium text-white/80">
                  {action.label}
                </Text>
              </Pressable>
            </MotiView>
          ))}
        </View>

        <Text className="mt-6 text-xs text-white/30 italic text-center">
          Swipe from the right edge to access sources panel
        </Text>
      </MotiView>
    </View>
  );
}
