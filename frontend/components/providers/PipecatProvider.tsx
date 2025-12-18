"use client";

import React, { ReactNode, useEffect, useState } from "react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { DailyTransport } from "@pipecat-ai/daily-transport";
import { PipecatClientProvider } from "@pipecat-ai/client-react";
import { PipecatClientAudio } from "@pipecat-ai/client-react";

/**
 * PipecatProvider
 *
 * Responsibilities:
 * - Initialize a browser-only DailyTransport and PipecatClient on the client.
 * - Provide the initialized PipecatClient to child components via PipecatClientProvider.
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
              console.debug("[PipecatProvider] Transport state changed:", state);
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
  }, []);

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
