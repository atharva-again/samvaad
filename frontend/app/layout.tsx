import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ChatToaster } from "@/components/ui/ChatToaster";
import { PipecatProvider } from "@/components/providers/PipecatProvider";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";

import { WalkthroughController } from "@/components/onboarding/WalkthroughController";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Samvaad | Conversational Intelligence",
  description: "A fluid, multimodal AI interface.",
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-void text-text-primary min-h-screen selection:bg-signal/30 text-base md:text-lg leading-relaxed`}
      >
        <AuthProvider>
          <PipecatProvider>{children}</PipecatProvider>
          <WalkthroughController />
        </AuthProvider>

        <ChatToaster />
      </body>
    </html>
  );
}

