"use client";

import React, { useState } from "react";
import { Settings, Mic, Speaker, Volume2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { usePipecatClientMediaDevices } from "@pipecat-ai/client-react";

interface VoiceSettingsProps {
    className?: string;
    sideOffset?: number;
    outputVolume?: number;
    onVolumeChange?: (volume: number) => void;
}

export function VoiceSettings({
    className,
    sideOffset = 24,
    outputVolume = 1.0,
    onVolumeChange,
}: VoiceSettingsProps) {
    // Use SDK hook for device management (mic selection)
    const {
        availableCams: _availableCams,
        selectedMic,
        updateMic,
    } = usePipecatClientMediaDevices();

    // Local state for speaker (SDK doesn't manage this directly)
    const [speakers, setSpeakers] = useState<MediaDeviceInfo[]>([]);
    const [mics, setMics] = useState<MediaDeviceInfo[]>([]);
    const [selectedSpeakerId, setSelectedSpeakerId] = useState<string>("");
    const [localVolume, setLocalVolume] = useState(outputVolume);

    // Enumerate devices - labels are only available after permission is granted
    React.useEffect(() => {
        const enumerateDevices = async () => {
            try {
                // First, try to get permission (this may already be granted)
                // This ensures we get device labels
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    // Stop the stream immediately - we just needed permission
                    stream.getTracks().forEach(track => track.stop());
                } catch (permErr) {
                    console.debug("Mic permission not yet granted:", permErr);
                }

                const devices = await navigator.mediaDevices.enumerateDevices();

                // Filter by kind
                const audioInputs = devices.filter(d => d.kind === "audioinput");
                const audioOutputs = devices.filter(d => d.kind === "audiooutput");

                console.debug("[VoiceSettings] Audio inputs:", audioInputs);
                console.debug("[VoiceSettings] Audio outputs:", audioOutputs);

                setMics(audioInputs);
                setSpeakers(audioOutputs);

                if (!selectedSpeakerId && audioOutputs.length > 0) {
                    setSelectedSpeakerId(audioOutputs[0].deviceId);
                }
            } catch (err) {
                console.error("Failed to enumerate devices:", err);
            }
        };

        enumerateDevices();
        navigator.mediaDevices.addEventListener("devicechange", enumerateDevices);
        return () => navigator.mediaDevices.removeEventListener("devicechange", enumerateDevices);
    }, []);

    const handleMicChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        updateMic(e.target.value);
    };

    const handleSpeakerChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setSelectedSpeakerId(e.target.value);
        // Note: Speaker selection typically requires setSinkId on audio elements
    };

    const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const vol = parseFloat(e.target.value);
        setLocalVolume(vol);
        onVolumeChange?.(vol);
    };

    const getVolumePercentage = () => Math.round(localVolume * 100);

    return (
        <Popover>
            <PopoverTrigger asChild>
                <Button
                    size="icon"
                    variant="ghost"
                    className={cn(
                        "rounded-full w-10 h-10 text-text-secondary hover:bg-white/10 transition-colors",
                        className
                    )}
                >
                    <Settings className="w-5 h-5" />
                </Button>
            </PopoverTrigger>
            <PopoverContent
                side="top"
                align="end"
                sideOffset={sideOffset}
                className="w-80 bg-black/95 backdrop-blur-xl border-white/10 text-white p-5 rounded-2xl"
            >
                <div className="space-y-5">
                    {/* Header */}
                    <div className="text-sm font-semibold text-white/90 border-b border-white/10 pb-3">
                        Voice Settings
                    </div>

                    {/* Microphone Selector - Using local enumeration for better labels */}
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-text-secondary flex items-center gap-2">
                            <Mic className="w-3.5 h-3.5" /> Microphone
                        </label>
                        <select
                            value={selectedMic?.deviceId || ""}
                            onChange={handleMicChange}
                            className="w-full text-sm bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent cursor-pointer hover:bg-white/10 transition-colors"
                        >
                            {mics.length === 0 ? (
                                <option value="">No microphones found</option>
                            ) : (
                                mics.map(mic => (
                                    <option key={mic.deviceId} value={mic.deviceId} className="bg-neutral-900">
                                        {mic.label || `Microphone ${mic.deviceId.slice(0, 8)}...`}
                                    </option>
                                ))
                            )}
                        </select>
                    </div>

                    {/* Speaker Selector */}
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-text-secondary flex items-center gap-2">
                            <Speaker className="w-3.5 h-3.5" /> Output Device
                        </label>
                        <select
                            value={selectedSpeakerId}
                            onChange={handleSpeakerChange}
                            className="w-full text-sm bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent cursor-pointer hover:bg-white/10 transition-colors"
                        >
                            {speakers.length === 0 ? (
                                <option value="">No speakers found</option>
                            ) : (
                                speakers.map(spk => (
                                    <option key={spk.deviceId} value={spk.deviceId} className="bg-neutral-900">
                                        {spk.label || `Speaker ${spk.deviceId.slice(0, 5)}`}
                                    </option>
                                ))
                            )}
                        </select>
                    </div>

                    {/* Divider */}
                    <div className="border-t border-white/10" />

                    {/* Volume Slider */}
                    <div className="space-y-3">
                        <label className="text-xs font-medium text-text-secondary flex items-center justify-between">
                            <span className="flex items-center gap-2">
                                <Volume2 className="w-3.5 h-3.5" /> Output Volume
                            </span>
                            <span className="text-white font-semibold bg-white/10 px-2 py-0.5 rounded-md text-xs">
                                {getVolumePercentage()}%
                            </span>
                        </label>

                        {/* Custom Slider Container */}
                        <div className="relative group">
                            {/* Track Background */}
                            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                {/* Filled Track */}
                                <div
                                    className="h-full bg-gradient-to-r from-accent/80 to-accent rounded-full transition-all duration-150"
                                    style={{ width: `${getVolumePercentage()}%` }}
                                />
                            </div>

                            {/* Invisible Range Input */}
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.01"
                                value={localVolume}
                                onChange={handleVolumeChange}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            />

                            {/* Thumb Indicator */}
                            <div
                                className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg border-2 border-accent pointer-events-none transition-all duration-150 group-hover:scale-110"
                                style={{ left: `calc(${getVolumePercentage()}% - 8px)` }}
                            />
                        </div>

                        {/* Volume Presets */}
                        <div className="flex justify-between gap-2 pt-1">
                            {[0, 0.25, 0.5, 0.75, 1].map(preset => (
                                <button
                                    key={preset}
                                    onClick={() => {
                                        setLocalVolume(preset);
                                        onVolumeChange?.(preset);
                                    }}
                                    className={cn(
                                        "flex-1 py-1.5 rounded-md text-xs font-medium transition-all",
                                        Math.abs(localVolume - preset) < 0.05
                                            ? "bg-accent/20 text-accent border border-accent/30"
                                            : "bg-white/5 text-white/60 hover:bg-white/10 hover:text-white/80"
                                    )}
                                >
                                    {preset === 0 ? "Mute" : `${Math.round(preset * 100)}%`}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </PopoverContent>
        </Popover>
    );
}
