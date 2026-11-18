import { ChatWorkspace } from "@/components/chat/ChatWorkspace";

export function ChatPage({ conversationId }: { conversationId: string }) {
  return <ChatWorkspace conversationId={conversationId} />;
}
