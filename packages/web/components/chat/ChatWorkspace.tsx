import { ChatView } from "@/components/chat/ChatView";
import { SourcesPanel } from "@/components/chat/SourcesPanel";
import { IconNavRail } from "@/components/navigation/IconNavRail";

export function ChatWorkspace({ conversationId }: { conversationId?: string }) {
  return (
    <main className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
      <div className="hidden md:flex h-full shrink-0">
        <IconNavRail />
      </div>
      <ChatView conversationId={conversationId} />
      <SourcesPanel />
    </main>
  );
}
