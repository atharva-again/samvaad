"use client";

import { PipecatClient } from "@pipecat-ai/client-js";
import {
	PipecatClientAudio,
	PipecatClientProvider,
} from "@pipecat-ai/client-react";
import { DailyTransport } from "@pipecat-ai/daily-transport";
import { type ReactNode, useEffect, useState } from "react";
import { type CitationItem, useUIStore } from "@/lib/stores/useUIStore";

/**
 * PipecatProvider
 *
 * Responsibilities:
 * - Initialize a browser-only DailyTransport and PipecatClient on the client.
 * - Provide the initialized PipecatClient to child components via PipecatClientProvider.
 * - Handle custom server messages (e.g., citations from voice RAG).
 *
 * Notes:
 * - Transport and client initialization must run inside a client-only effect because
 *   they depend on WebRTC/browser APIs.
 * - While initialization is in progress we render children directly to avoid SSR/hydration issues.
 */

interface PipecatProviderProps {
	children: ReactNode;
}

export function PipecatProvider({ children }: PipecatProviderProps) {
	const [client, setClient] = useState<PipecatClient | null>(null);
	const { setCitations, setSourcesPanelTab, setPendingVoiceCitations } =
		useUIStore();

	useEffect(() => {
		// Only run on the client
		let mounted = true;

		// Initialize transport + client
		const initClient = async () => {
			try {
				// DailyTransport relies on browser APIs (getUserMedia / RTCPeerConnection)
				const transport = new DailyTransport();

				// Create Pipecat client with the transport instance.
				// The PipecatClient constructor commonly accepts an options object; using { transport }
				// is the recommended pattern for most transports.
				const created = new PipecatClient({
					transport,
					enableMic: true,
					callbacks: {
						onConnected: () => {
							console.debug("[PipecatProvider] onConnected callback fired");
						},
						onBotReady: () => {
							console.debug("[PipecatProvider] onBotReady callback fired");
						},
						onDisconnected: () => {
							console.debug("[PipecatProvider] onDisconnected callback fired");
						},
						onTransportStateChanged: (state: string) => {
							console.debug(
								"[PipecatProvider] Transport state changed:",
								state,
							);
						},
						// Handle custom server messages (e.g., citations from voice RAG)
						onServerMessage: (data: unknown) => {
							const msg = data as { type?: string; sources?: CitationItem[]; text?: string };
							
						if (msg.type === "citations" && msg.sources) {
							console.debug(
								"[PipecatProvider] Received citations:",
								msg.sources.length,
							);
							setPendingVoiceCitations(msg.sources);
							setCitations("voice-response", msg.sources);
							setSourcesPanelTab("citations");
						} else if (msg.type === "transcript" && msg.text) {
								console.debug(
									"[PipecatProvider] Received transcript with citation markers:",
									msg.text.substring(0, 100),
								);
								// Store transcript in UI store for InputBar to use
								useUIStore.getState().setVoiceTranscript(msg.text);
							}
						},
					},
				});

				if (!mounted) {
					// If component unmounted immediately, attempt to gracefully cleanup if possible.
					// We avoid calling unknown instance methods to keep this safe.
					return;
				}

				setClient(created);
			} catch (err) {
				// Surface errors to console for developer debugging.
				// Do not throw — keep the app usable in text-only mode.
				// The UI will fall back to rendering children without the Pipecat context.
				// Consumers can detect the missing client and show appropriate UI.
				// eslint-disable-next-line no-console
				console.error("Failed to initialize Pipecat client:", err);
			}
		};

		initClient();

		return () => {
			mounted = false;
			// Intentionally not calling client cleanup methods here because the
			// exact API varies across client versions. If you want a graceful
			// shutdown, add explicit cleanup (e.g. client?.destroy()) once a stable
			// client API is chosen.
		};
	}, [
		// Store citations and optionally open the panel
		setCitations,
		setSourcesPanelTab,
		setPendingVoiceCitations,
	]);

	// While the Pipecat client isn't ready, render children directly. This
	// avoids hydration mismatches and keeps the app usable in text-only mode.
	if (!client) {
		return <>{children}</>;
	}

	return (
		<PipecatClientProvider client={client}>
			{/* AudioHandler relies on Pipecat context; include it when client is ready */}
			<PipecatClientAudio />
			{children}
		</PipecatClientProvider>
	);
}
