"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { ScribbleOverlay } from "./ScribbleOverlay";
import { usePlatform } from "@/hooks/usePlatform";
import { useUIStore } from "@/lib/stores/useUIStore";

// Steps ordered for linear flow (sidebar top→bottom, then center input)
const getSteps = (isMac: boolean) => {
    const alt = isMac ? "⌥" : "Alt";
    const cmd = isMac ? "⌘" : "Ctrl";

    return [
        {
            targetId: "walkthrough-search-trigger",
            text: "Instantly search across all your conversations and uploaded files",
            shortcut: `${cmd}+K`,
        },
        {
            targetId: "walkthrough-new-chat",
            text: "Start a fresh conversation with your AI assistant",
            shortcut: `${alt}+N`,
        },
        {
            targetId: "walkthrough-sources-trigger",
            text: "View and manage your sources",
            shortcut: `${alt}+S`,
            action: "openSources", // Special action to open sources panel
        },
        {
            targetId: "walkthrough-kb-tab",
            text: "Upload and manage your documents to build a personal knowledge base. Your knowledge base is shared across chats.",
            shortcut: undefined,
        },
        {
            targetId: "walkthrough-citations-tab",
            text: "View AI-retrieved sources and citations for each response",
            shortcut: undefined,
            action: "closeSources", // Close panel after this step
        },
        {
            targetId: "walkthrough-text-mode",
            text: "Type your questions here for text-based conversation",
            shortcut: `${alt}+T`,
        },
        {
            targetId: "walkthrough-voice-mode",
            text: "Switch to voice for hands-free, real-time conversation",
            shortcut: `${alt}+V`,
        },
    ];
};

export function WalkthroughController() {
    const { hasSeenWalkthrough, markWalkthroughSeen, isLoading, user } = useAuth();
    const { isMac } = usePlatform();
    const { setSourcesPanelOpen } = useUIStore();
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [mounted, setMounted] = useState(false);
    const [isVisible, setIsVisible] = useState(true);

    const STEPS = getSteps(isMac);

    useEffect(() => {
        setMounted(true);
    }, []);

    // TESTING MODE: Disabled hasSeenWalkthrough check
    if (!mounted || isLoading || !user || !isVisible) {
        return null;
    }

    const handleNext = () => {
        const currentStep = STEPS[currentStepIndex];

        // Handle special actions before moving to next step
        if (currentStep.action === "openSources") {
            setSourcesPanelOpen(true);
            // Small delay to let panel animate in
            setTimeout(() => {
                setCurrentStepIndex((prev) => prev + 1);
            }, 300);
            return;
        }

        if (currentStep.action === "closeSources") {
            setSourcesPanelOpen(false);
        }

        if (currentStepIndex < STEPS.length - 1) {
            setCurrentStepIndex((prev) => prev + 1);
        } else {
            handleComplete();
        }
    };

    const handleComplete = () => {
        setSourcesPanelOpen(false); // Ensure panel is closed
        setIsVisible(false);
        markWalkthroughSeen();
    };

    const currentStep = STEPS[currentStepIndex];

    if (!currentStep) return null;

    // Skip steps where target doesn't exist
    if (typeof document !== "undefined" && !document.getElementById(currentStep.targetId)) {
        if (currentStepIndex < STEPS.length - 1) {
            setTimeout(() => setCurrentStepIndex((prev) => prev + 1), 50);
        } else {
            handleComplete();
        }
        return null;
    }

    return (
        <ScribbleOverlay
            targetId={currentStep.targetId}
            text={currentStep.text}
            shortcut={currentStep.shortcut}
            onNext={handleNext}
            onSkip={handleComplete}
            isLastStep={currentStepIndex === STEPS.length - 1}
            stepNumber={currentStepIndex + 1}
            totalSteps={STEPS.length}
        />
    );
}
