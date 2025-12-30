"use client";

import { useEffect, useState } from "react";
import { Toaster } from "sonner";
import { useUIStore } from "@/lib/stores/useUIStore";

/**
 * ChatToaster - A viewport-aware toast container.
 *
 * Dynamically offsets the horizontal center of toasts based on
 * the state of the sidebar and sources panel, so that toasts
 * appear centered within the visible "chat area" rather than
 * the entire browser window.
 */
export function ChatToaster() {
	const { isSidebarOpen, isSourcesPanelOpen } = useUIStore();
	const [isMobile, setIsMobile] = useState(true); // Default to mobile (no offset)

	// Track screen size for responsive offset
	useEffect(() => {
		const checkMobile = () => setIsMobile(window.innerWidth < 768);
		checkMobile();
		window.addEventListener("resize", checkMobile);
		return () => window.removeEventListener("resize", checkMobile);
	}, []);

	// Calculate the horizontal offset to shift toasts toward the chat area center.
	// On mobile (< md), sidebar is hidden, so no offset needed.
	// Sidebar widths: collapsed = 56px, expanded = 240px
	// Sources panel width: 420px (when open on desktop only)
	let horizontalOffset = 0;
	if (!isMobile) {
		const sidebarWidth = isSidebarOpen ? 240 : 56;
		const sourcesPanelWidth = isSourcesPanelOpen ? 420 : 0;

		// The chat area is offset from the left by the sidebar, and from the right by the sources panel.
		// To center within the chat area, we need to shift the toast by half the difference.
		// Offset = (sidebarWidth - sourcesPanelWidth) / 2
		// Positive offset shifts right, negative shifts left.
		horizontalOffset = (sidebarWidth - sourcesPanelWidth) / 2;
	}

	return (
		<div
			style={{
				position: "fixed",
				top: 0,
				left: "50%",
				transform: `translateX(calc(-50% + ${horizontalOffset}px))`,
				transition: "transform 0.3s ease",
				zIndex: 9999,
				pointerEvents: "none",
			}}
		>
			<Toaster
				position="top-center"
				expand={false}
				toastOptions={{
					style: {
						background: "rgba(10, 10, 10, 0.85)",
						backdropFilter: "blur(16px)",
						border: "1px solid rgba(255, 255, 255, 0.1)",
						color: "#ffffff",
						borderRadius: "12px",
						padding: "10px 20px",
						fontSize: "14px",
						fontWeight: "500",
						width: "fit-content",
						minWidth: "auto",
						display: "flex",
						justifyContent: "center",
						alignItems: "center",
						gap: "10px",
						boxShadow: "0 10px 40px rgba(0, 0, 0, 0.5)",
						pointerEvents: "auto",
					},
					className: "font-sans",
				}}
			/>
		</div>
	);
}
