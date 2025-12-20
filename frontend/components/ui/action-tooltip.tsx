"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { usePlatform } from "@/hooks/usePlatform";

interface ActionTooltipProps {
    label: string;
    /**
     * Keyboard shortcut to display. Use platform-agnostic syntax:
     * - "Alt+S" will display as "Option+S" on Mac, "Alt+S" on Windows/Linux
     * - "Mod+K" will display as "Cmd+K" on Mac, "Ctrl+K" on Windows/Linux
     */
    shortcut?: string;
    side?: "left" | "right" | "top" | "bottom";
    className?: string;
    children?: React.ReactNode;
}

/**
 * A sleek, high-info tooltip component used for action hints.
 * Automatically adapts keyboard shortcuts to the user's platform.
 */
export function ActionTooltip({
    label,
    shortcut,
    side = "left",
    className
}: ActionTooltipProps) {
    const { isMac } = usePlatform();

    // Normalize shortcut for the current platform
    const normalizedShortcut = React.useMemo(() => {
        if (!shortcut) return undefined;
        
        let result = shortcut;
        
        if (isMac) {
            // Replace Alt → Option, Mod → Cmd, Ctrl → Ctrl (Mac has Ctrl too)
            result = result.replace(/\bAlt\b/gi, "Option");
            result = result.replace(/\bMod\b/gi, "Cmd");
        } else {
            // Replace Mod → Ctrl on Windows/Linux
            result = result.replace(/\bMod\b/gi, "Ctrl");
        }
        
        return result;
    }, [shortcut, isMac]);

    // Positioning styles based on 'side'
    const positionStyles = {
        left: "right-full mr-4 top-1/2 -translate-y-1/2 translate-x-2 group-hover:translate-x-0",
        right: "left-full ml-4 top-1/2 -translate-y-1/2 -translate-x-2 group-hover:translate-x-0",
        top: "bottom-full mb-6 left-1/2 -translate-x-1/2 translate-y-2 group-hover:translate-y-0",
        bottom: "top-full mt-4 left-1/2 -translate-x-1/2 -translate-y-2 group-hover:translate-y-0"
    };

    return (
        <div
            className={cn(
                "absolute bg-black/90 text-white text-xs font-medium px-3 py-1.5 rounded-lg",
                "opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none whitespace-nowrap",
                "flex items-center gap-2 border border-white/10 shadow-xl z-50",
                positionStyles[side],
                className
            )}
        >
            <span>{label}</span>
            {normalizedShortcut && (
                <span className="text-white/40 bg-white/10 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider font-mono">
                    {normalizedShortcut}
                </span>
            )}
        </div>
    );
}

