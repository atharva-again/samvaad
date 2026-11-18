"use client";

import { lazy, Suspense, useEffect } from "react";
import { AppMockup } from "@/components/landing/AppMockup";
import { Features } from "@/components/landing/Features";
import { Footer } from "@/components/landing/Footer";
import { Hero } from "@/components/landing/Hero";
import { Navbar } from "@/components/landing/Navbar";
import { useAuth } from "@/contexts/AuthContext";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { useInputBarStore } from "@/lib/stores/useInputBarStore";
import { useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

const ChatWorkspace = lazy(() =>
  import("@/components/chat/ChatWorkspace").then((module) => ({
    default: module.ChatWorkspace,
  })),
);

function LandingPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  const opacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);
  const scale = useTransform(scrollYProgress, [0, 0.2], [1, 0.98]);

  return (
    <div
      ref={containerRef}
      className="min-h-screen text-white selection:bg-signal/30 selection:text-white font-sans overflow-x-hidden antialiased"
    >
      <Navbar />

      <main className="relative z-10 bg-[#030303] mb-[500px] md:mb-[600px] shadow-2xl">
        <Hero opacity={opacity} scale={scale} />
        <AppMockup />
        <Features />
      </main>

      <Footer />
    </div>
  );
}

export default function Home() {
  const { user, isLoading } = useAuth();
  const { prepareNewConversation } = useConversationStore();
  const { setHasInteracted } = useInputBarStore();

  useEffect(() => {
    if (user) {
      prepareNewConversation();
      setHasInteracted(false);
    }
  }, [user, prepareNewConversation, setHasInteracted]);

  if (isLoading) return null;

  if (user) {
    return (
      <Suspense fallback={null}>
        <ChatWorkspace />
      </Suspense>
    );
  }

  return <LandingPage />;
}
