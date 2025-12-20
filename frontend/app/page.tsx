"use client";

import { IconNavRail } from "@/components/navigation/IconNavRail";
import { ChatView } from "@/components/chat/ChatView";
import { SourcesPanel } from "@/components/chat/SourcesPanel";

export default function Home() {
  return (
    <main className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
      {/* Grok-style Icon Navigation Rail - Always visible on desktop */}
      <div className="hidden md:flex h-full shrink-0">
        <IconNavRail />
      </div>

      {/* Main Content Area - No conversationId means new chat */}
      <ChatView />

      {/* Sources Panel */}
      <SourcesPanel />
    </main>
  );
}
