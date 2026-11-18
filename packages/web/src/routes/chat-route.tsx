import { useParams } from "@tanstack/react-router";
import { ChatPage } from "@/src/routes/chat";

export default function ChatRoute() {
  const { id } = useParams({ from: "/chat/$id" });
  return <ChatPage conversationId={id} />;
}
