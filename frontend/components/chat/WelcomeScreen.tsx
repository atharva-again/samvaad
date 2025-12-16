"use client";

import React, { useRef } from "react";
import { MessageSquare, Mic, Paperclip, BookOpen, Shield, Sparkles } from "lucide-react";
import { usePlatform } from "@/hooks/usePlatform";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/stores/useUIStore";
import { useFileProcessor } from "@/hooks/useFileProcessor";

export function WelcomeScreen() {
    const { modifier, isMobile } = usePlatform();
    const { setMode, toggleSourcesPanel, setHasInteracted } = useUIStore();
    const { processFiles } = useFileProcessor();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleAttachClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            await processFiles(Array.from(e.target.files));
            e.target.value = "";
        }
    };

    const handleShortcut = (mode: 'text' | 'voice') => {
        setMode(mode);
        setHasInteracted(true);
    };

    const shortcuts = [
        { keys: `${modifier}+T`, label: "Text Mode", icon: MessageSquare, action: () => handleShortcut("text") },
        { keys: `${modifier}+V`, label: "Voice Mode", icon: Mic, action: () => handleShortcut("voice") },
        { keys: `${modifier}+A`, label: "Attach Files", icon: Paperclip, action: () => fileInputRef.current?.click() },
        { keys: `${modifier}+S`, label: "Sources", icon: BookOpen, action: () => toggleSourcesPanel() },
    ];

    const features = [
        { icon: Sparkles, label: "Instant answers from your document library" },
        { icon: Mic, label: "Fluid voice interactions with real-time transcription" },
    ];

    return (
        <div className="flex-1 flex flex-col items-center justify-center relative overflow-hidden p-4 md:p-0">
            {/* Hidden File Input for Attach Shortcut */}
            <input
                type="file"
                multiple
                ref={fileInputRef}
                className="hidden"
                onChange={handleFileSelect}
            />

            {/* Background Glow - Responsive size */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] md:w-[500px] md:h-[500px] bg-indigo-500/5 rounded-full blur-[80px] md:blur-[100px] pointer-events-none" />

            <div className="relative z-10 flex flex-col items-center text-center max-w-2xl w-full px-4 animate-in fade-in slide-in-from-bottom-4 duration-700">

                {/* Brand / Title - Responsive sizes */}
                <div className="mb-8 md:mb-8 space-y-3">
                    <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-white to-white/60 drop-shadow-sm">
                        Samvaad
                    </h1>
                    <p className="text-lg md:text-xl text-text-secondary font-light tracking-wide max-w-lg mx-auto leading-relaxed">
                        Transform your static documents into <span className="text-indigo-400/90 font-normal"><br className="hidden md:block" />dynamic conversations</span>
                    </p>
                </div>

                {/* Features list - Clean Design - Responsive */}
                <div className="flex flex-col gap-3 mb-8 md:mb-10 w-full max-w-md mx-auto">
                    {features.map((feature, i) => (
                        <div key={i} className="flex items-center gap-3 px-2 py-1 group select-none">
                            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500/20 group-hover:text-indigo-300 transition-all duration-300 shadow-sm border border-indigo-500/10 shrink-0">
                                <feature.icon className="w-4 h-4" />
                            </div>
                            <span className="text-sm md:text-base text-text-secondary/80 font-medium group-hover:text-text-primary/90 transition-colors text-left leading-tight">
                                {feature.label}
                            </span>
                        </div>
                    ))}
                </div>

                {/* Shortcuts Grid - Responsive */}
                <div className="w-full max-w-lg">
                    <div className="flex items-center gap-4 mb-4">
                        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                        <span className="text-[10px] font-bold text-text-secondary/40 uppercase tracking-[0.2em]">
                            Quick Actions
                        </span>
                        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        {shortcuts.map((shortcut, i) => (
                            <button
                                key={i}
                                onClick={shortcut.action}
                                className={cn(
                                    "group flex items-center justify-between p-3 rounded-xl text-left",
                                    "bg-surface/40 backdrop-blur-md border border-white/5",
                                    "hover:bg-white/10 hover:border-white/10",
                                    "transition-all duration-300 ease-out shadow-lg cursor-pointer ring-0 focus:outline-none focus:ring-1 focus:ring-white/20"
                                )}
                            >
                                <div className="flex items-center gap-3">
                                    <shortcut.icon className="w-4 h-4 text-indigo-400/70 group-hover:text-indigo-300 transition-colors shrink-0" />
                                    <span className="text-sm font-medium text-text-secondary group-hover:text-white transition-colors">
                                        {shortcut.label}
                                    </span>
                                </div>
                                {!isMobile && (
                                    <div className="hidden md:flex gap-1">
                                        {/* Display keys visually */}
                                        <kbd className="min-w-[1.2rem] h-5 px-1.5 flex items-center justify-center bg-black/40 rounded-md text-[10px] font-mono text-text-secondary/80 font-bold border border-white/10">
                                            {shortcut.keys}
                                        </kbd>
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Mobile Hint */}
                <div className="mt-6 md:hidden">
                    <p className="text-xs text-white/30 italic">
                        PS: You can swipe left to quickly access the sources panel and add more documents.
                    </p>
                </div>
            </div>
        </div>
    );
}
