import { useLocalSearchParams } from "expo-router";
import { ChatView } from "@/components/chat/ChatView";

export default function ChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <ChatView conversationId={id} />;
}
