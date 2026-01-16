import type { Metadata } from "next";
import { Outfit, Playfair_Display } from "next/font/google";
import { PipecatProvider } from "@/components/providers/PipecatProvider";
import { ChatToaster } from "@/components/ui/ChatToaster";
import "./globals.css";

import { WalkthroughController } from "@/components/onboarding/WalkthroughController";
import { AuthProvider } from "@/contexts/AuthContext";

const outfit = Outfit({ 
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  display: "swap",
});

const geistSans = { variable: "--font-geist-sans" };
const geistMono = { variable: "--font-geist-mono" };

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
				className={`${geistSans.variable} ${geistMono.variable} ${outfit.variable} ${playfair.variable} antialiased bg-void text-text-primary min-h-screen selection:bg-signal/30 text-base md:text-lg leading-relaxed`}
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
