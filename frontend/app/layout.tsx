import type { Metadata } from "next";
import { 
	Outfit, 
	Playfair_Display, 
	Gloria_Hallelujah,
	Cinzel,
	Roboto_Slab,
	Ribeye,
	Rowdies,
	Goudy_Bookletter_1911,
	Bai_Jamjuree
} from "next/font/google";
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

const gloria = Gloria_Hallelujah({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-gloria",
  display: "swap",
});

const cinzel = Cinzel({
  subsets: ["latin"],
  variable: "--font-cinzel",
  display: "swap",
});

const robotoSlab = Roboto_Slab({
  subsets: ["latin"],
  variable: "--font-roboto-slab",
  display: "swap",
});

const ribeye = Ribeye({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-ribeye",
  display: "swap",
});

const rowdies = Rowdies({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-rowdies",
  display: "swap",
});

const goudy = Goudy_Bookletter_1911({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-goudy",
  display: "swap",
});

const baiJamjuree = Bai_Jamjuree({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-bai-jamjuree",
  display: "swap",
});


const geistSans = { variable: "--font-geist-sans" };
const geistMono = { variable: "--font-geist-mono" };

export const metadata: Metadata = {
	title: "Samvaad | Conversational Intelligence",
	description: "A fluid, multimodal AI interface.",
};

export default function RootLayout({
	children: children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en" className="dark">
			<body
				className={`${geistSans.variable} ${geistMono.variable} ${outfit.variable} ${playfair.variable} ${gloria.variable} ${cinzel.variable} ${robotoSlab.variable} ${ribeye.variable} ${rowdies.variable} ${goudy.variable} ${baiJamjuree.variable} antialiased bg-void text-text-primary min-h-screen selection:bg-signal/30 text-base md:text-lg leading-relaxed`}
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
