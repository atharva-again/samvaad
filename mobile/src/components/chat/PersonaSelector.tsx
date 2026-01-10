import { View, Text, Pressable, ScrollView } from "react-native";
import { MotiView, AnimatePresence } from "moti";
import { User, GraduationCap, Code, Heart, Star, HelpCircle, X } from "lucide-react-native";
import { useUIStore } from "@/lib/stores/useUIStore";
import { COLORS, PERSONAS } from "@/constants";
import * as Haptics from "expo-haptics";

interface PersonaSelectorProps {
  onClose?: () => void;
}

const personaIcons: Record<string, any> = {
  default: User,
  tutor: GraduationCap,
  coder: Code,
  friend: Heart,
  expert: Star,
  quizzer: HelpCircle,
};

export function PersonaSelector({ onClose }: PersonaSelectorProps) {
  const { persona: selectedPersona, setPersona } = useUIStore();

  const handleSelect = (id: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setPersona(id);
    onClose?.();
  };

  return (
    <View className="bg-surface rounded-3xl p-4 border border-white/10 shadow-2xl">
      <View className="flex-row items-center justify-between mb-4">
        <Text className="text-white font-bold text-lg">Choose Persona</Text>
        {onClose && (
          <Pressable onPress={onClose} className="p-1 rounded-full active:bg-white/10">
            <X size={20} color={COLORS.textSecondary} />
          </Pressable>
        )}
      </View>

      <View className="flex-row flex-wrap gap-2">
        {PERSONAS.map((p) => {
          const Icon = personaIcons[p.id] || User;
          const isSelected = selectedPersona === p.id;

          return (
            <Pressable
              key={p.id}
              onPress={() => handleSelect(p.id)}
              className={`flex-row items-center gap-2 px-3 py-2 rounded-xl border ${
                isSelected
                  ? "bg-indigo-500/20 border-indigo-500/40"
                  : "bg-white/5 border-transparent"
              }`}
              style={{ width: "48%" }}
            >
              <Icon size={16} color={isSelected ? COLORS.accent : COLORS.textSecondary} />
              <Text
                className={`text-sm font-medium ${
                  isSelected ? "text-white" : "text-white/60"
                }`}
              >
                {p.name}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}
