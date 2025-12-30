"use client";

import { useParams } from "next/navigation";
import { ChatView } from "@/components/chat/ChatView";
import { SourcesPanel } from "@/components/chat/SourcesPanel";
import { IconNavRail } from "@/components/navigation/IconNavRail";

export default function ChatPage() {
	const params = useParams();
	const conversationId = params.id as string;

	return (
		<main className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
			{/* Grok-style Icon Navigation Rail - Always visible on desktop */}
			<div className="hidden md:flex h-full shrink-0">
				<IconNavRail />
			</div>

			{/* Main Content Area */}
			<ChatView conversationId={conversationId} />

			{/* Sources Panel */}
			<SourcesPanel />
		</main>
	);
}
