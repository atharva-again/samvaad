"use client";

import React, { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { createPortal } from "react-dom";

interface ScribbleOverlayProps {
    targetId: string;
    text: string;
    shortcut?: string;
    onNext: () => void;
    onSkip: () => void;
    isLastStep: boolean;
    stepNumber: number;
    totalSteps: number;
}

interface Position {
    x: number;
    y: number;
    width: number;
    height: number;
}

function calculateTooltipPosition(target: Position, viewport: { width: number; height: number }) {
    const tooltipWidth = 320;
    const tooltipHeight = 180;
    const padding = 20;

    const targetCenterX = target.x + target.width / 2;
    const targetCenterY = target.y + target.height / 2;

    // Check if target is in the center area of the screen (like mode switcher)
    const isInCenterX = targetCenterX > viewport.width * 0.3 && targetCenterX < viewport.width * 0.7;
    const isInBottomHalf = targetCenterY > viewport.height * 0.5;

    let tooltipX: number;
    let tooltipY: number;
    let arrowDirection: "left" | "right" | "top" | "bottom";

    if (isInCenterX) {
        // For center elements, prefer top/bottom placement
        tooltipX = targetCenterX - tooltipWidth / 2;

        if (isInBottomHalf) {
            // Place above
            tooltipY = target.y - tooltipHeight - padding;
            arrowDirection = "bottom";
        } else {
            // Place below
            tooltipY = target.y + target.height + padding;
            arrowDirection = "top";
        }
    } else if (targetCenterX < viewport.width / 2) {
        // Target is on left side, place tooltip to the right
        tooltipX = target.x + target.width + padding;
        tooltipY = targetCenterY - tooltipHeight / 2;
        arrowDirection = "left";
    } else {
        // Target is on right side, place tooltip to the left
        tooltipX = target.x - tooltipWidth - padding;
        tooltipY = targetCenterY - tooltipHeight / 2;
        arrowDirection = "right";
    }

    // Clamp to viewport
    tooltipX = Math.max(padding, Math.min(tooltipX, viewport.width - tooltipWidth - padding));
    tooltipY = Math.max(padding, Math.min(tooltipY, viewport.height - tooltipHeight - padding));

    // Calculate how much the tooltip shifted due to clamping
    // We want the arrow to point to targetCenter, relative to the *clamped* tooltip position.

    // Default centers (50%)
    let arrowX: string | number = "50%";
    let arrowY: string | number = "50%";

    // Adjust arrow position to point back to target
    if (arrowDirection === "left" || arrowDirection === "right") {
        // Vertical offset: targetCenterY relative to tooltipY
        const relativeY = targetCenterY - tooltipY;
        arrowY = Math.max(10, Math.min(tooltipHeight - 10, relativeY));
    } else {
        // Horizontal offset: targetCenterX relative to tooltipX
        const relativeX = targetCenterX - tooltipX;
        arrowX = Math.max(10, Math.min(tooltipWidth - 10, relativeX));
    }

    return { x: tooltipX, y: tooltipY, arrowDirection, arrowX, arrowY };
}

export function ScribbleOverlay({
    targetId,
    text,
    shortcut,
    onNext,
    onSkip,
    isLastStep,
    stepNumber,
    totalSteps
}: ScribbleOverlayProps) {
    const [position, setPosition] = useState<Position | null>(null);
    const [mounted, setMounted] = useState(false);
    const [viewport, setViewport] = useState({ width: 0, height: 0 });

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onNext();
        } else if (e.key === "s" || e.key === "S" || e.key === "Escape") {
            e.preventDefault();
            onSkip();
        }
    }, [onNext, onSkip]);

    useEffect(() => {
        setMounted(true);
        window.addEventListener("keydown", handleKeyDown);

        const updatePosition = () => {
            const element = document.getElementById(targetId);
            if (element) {
                const rect = element.getBoundingClientRect();
                setPosition({
                    x: rect.left,
                    y: rect.top,
                    width: rect.width,
                    height: rect.height,
                });
            } else {
                setPosition(null);
            }
            setViewport({
                width: window.innerWidth,
                height: window.innerHeight,
            });
        };

        updatePosition();
        window.addEventListener("resize", updatePosition);
        window.addEventListener("scroll", updatePosition);
        const interval = setInterval(updatePosition, 300);

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
            window.removeEventListener("resize", updatePosition);
            window.removeEventListener("scroll", updatePosition);
            clearInterval(interval);
        };
    }, [targetId, handleKeyDown]);

    if (!mounted || typeof document === "undefined" || !position) return null;

    const tooltip = calculateTooltipPosition(position, viewport);
    const spotlightRadius = Math.max(position.width, position.height) / 2 + 16;

    return createPortal(
        <AnimatePresence>
            <div className="fixed inset-0 z-[9999]">
                {/* Backdrop */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0"
                    onClick={onNext}
                    style={{
                        cursor: "pointer",
                        background: `radial-gradient(circle at ${position.x + position.width / 2}px ${position.y + position.height / 2}px, transparent ${spotlightRadius}px, rgba(0,0,0,0.75) ${spotlightRadius + 80}px)`,
                    }}
                />

                {/* Ring */}
                <motion.div
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    className="absolute pointer-events-none rounded-xl"
                    style={{
                        left: position.x - 6,
                        top: position.y - 6,
                        width: position.width + 12,
                        height: position.height + 12,
                        boxShadow: "0 0 0 1px rgba(255,255,255,0.4)",
                    }}
                />

                {/* Clean Glass Tooltip */}
                <motion.div
                    layout
                    initial={{ opacity: 0, scale: 0.96, y: 6 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.96 }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    className="absolute pointer-events-auto"
                    style={{ left: tooltip.x, top: tooltip.y, width: 320 }}
                >
                    <div
                        className="rounded-2xl p-5"
                        style={{
                            background: "rgba(30, 30, 30, 0.9)",
                            backdropFilter: "blur(24px)",
                            WebkitBackdropFilter: "blur(24px)",
                            border: "1px solid rgba(255, 255, 255, 0.1)",
                        }}
                    >
                        {/* Progress bar */}
                        <div className="flex items-center gap-1.5 mb-4">
                            {Array.from({ length: totalSteps }).map((_, i) => (
                                <div
                                    key={i}
                                    className="h-1 flex-1 rounded-full"
                                    style={{
                                        background: i < stepNumber
                                            ? "rgba(255,255,255,0.7)"
                                            : "rgba(255,255,255,0.15)",
                                    }}
                                />
                            ))}
                        </div>

                        {/* Content */}
                        <p className="text-white/90 text-[15px] leading-relaxed mb-2">
                            {text}
                        </p>

                        {/* Shortcut */}
                        {shortcut && (
                            <p className="text-white/40 text-[13px] mb-4">
                                Shortcut: <span className="text-white/60 font-mono text-[12px] bg-white/10 px-1.5 py-0.5 rounded">{shortcut}</span>
                            </p>
                        )}

                        {/* Actions */}
                        <div className="flex items-center justify-between mt-4">
                            <button
                                onClick={onSkip}
                                className="flex items-center gap-2 text-[13px] text-white/40 hover:text-white/70 transition-colors cursor-pointer"
                            >
                                <kbd className="w-5 h-5 rounded bg-white/10 flex items-center justify-center text-[11px] font-mono">S</kbd>
                                <span>Skip</span>
                            </button>

                            <button
                                onClick={onNext}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium cursor-pointer"
                                style={{
                                    background: "rgba(255,255,255,0.1)",
                                    border: "1px solid rgba(255,255,255,0.15)",
                                    color: "rgba(255,255,255,0.9)",
                                }}
                            >
                                <span>{isLastStep ? "Done" : "Next"}</span>
                                <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-[10px] font-mono">↵</kbd>
                            </button>
                        </div>
                    </div>

                    {/* Arrow */}
                    <div
                        className="absolute w-3 h-3 transform rotate-45"
                        style={{
                            background: "rgba(30, 30, 30, 0.9)",
                            ...(tooltip.arrowDirection === "left" && {
                                left: -6,
                                top: tooltip.arrowY, // Dynamic Y
                                marginTop: -6,
                                borderLeft: "1px solid rgba(255,255,255,0.1)",
                                borderBottom: "1px solid rgba(255,255,255,0.1)"
                            }),
                            ...(tooltip.arrowDirection === "right" && {
                                right: -6,
                                top: tooltip.arrowY, // Dynamic Y
                                marginTop: -6,
                                borderRight: "1px solid rgba(255,255,255,0.1)",
                                borderTop: "1px solid rgba(255,255,255,0.1)"
                            }),
                            ...(tooltip.arrowDirection === "top" && {
                                top: -6,
                                left: tooltip.arrowX, // Dynamic X
                                marginLeft: -6,
                                borderLeft: "1px solid rgba(255,255,255,0.1)",
                                borderTop: "1px solid rgba(255,255,255,0.1)"
                            }),
                            ...(tooltip.arrowDirection === "bottom" && {
                                bottom: -6,
                                left: tooltip.arrowX, // Dynamic X
                                marginLeft: -6,
                                borderRight: "1px solid rgba(255,255,255,0.1)",
                                borderBottom: "1px solid rgba(255,255,255,0.1)"
                            }),
                        }}
                    />
                </motion.div>
            </div>
        </AnimatePresence>,
        document.body
    );
}
