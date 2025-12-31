"use client";

import { Brain, Mic, Settings, Speaker, User, Volume2 } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { useAudioDevices } from "@/hooks/useAudioDevices";
import { capitalize, PERSONAS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface MobileVoiceControlsProps {
	className?: string;
	sideOffset?: number;
	enableTTS: boolean;
	setEnableTTS: (value: boolean) => void;
	strictMode: boolean;
	setStrictMode: (value: boolean) => void;
	persona: string;
	setPersona: (value: string) => void;
	outputVolume?: number;
	onVolumeChange?: (volume: number) => void;
}

export function MobileVoiceControls({
	className,
	sideOffset = 16,
	enableTTS,
	setEnableTTS,
	strictMode,
	setStrictMode,
	persona,
	setPersona,
	outputVolume = 1.0,
	onVolumeChange,
}: MobileVoiceControlsProps) {
	const {
		mics,
		speakers,
		selectedMic,
		selectedSpeakerId,
		updateMic,
		setSelectedSpeakerId,
	} = useAudioDevices();

	const [localVolume, setLocalVolume] = useState(outputVolume);

	const handleMicChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
		updateMic(e.target.value);
	};

	const handleSpeakerChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
		setSelectedSpeakerId(e.target.value);
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
						"rounded-full w-10 h-10 text-white hover:bg-white/10 transition-colors",
						className,
					)}
				>
					<Settings className="w-5 h-5" />
				</Button>
			</PopoverTrigger>
			<PopoverContent
				side="top"
				align="end"
				sideOffset={sideOffset}
				alignOffset={-12}
				className="w-[90vw] max-w-[320px] bg-black/95 backdrop-blur-xl border-white/10 text-white p-5 rounded-2xl shadow-2xl shadow-black/50"
			>
				<div className="space-y-6 max-h-[60vh] overflow-y-auto pr-1">
					<div className="flex items-center justify-between border-b border-white/10 pb-3">
						<span className="text-sm font-semibold text-white/90">
							Voice Settings
						</span>
					</div>

					{/* Quick Toggles Grid */}
					<div className="grid grid-cols-2 gap-3">
						{/* Strict Mode Toggle */}
						<button
							onClick={() => setStrictMode(!strictMode)}
							className={cn(
								"flex flex-col items-start gap-2 p-3 rounded-xl border transition-all relative overflow-hidden",
								strictMode
									? "bg-white/10 border-white/20 text-white"
									: "bg-transparent border-white/5 text-text-secondary hover:bg-white/5",
							)}
							type="button"
						>
							<div
								className={cn(
									"p-2 rounded-lg transition-colors bg-white/5 text-white/80",
								)}
							>
								<Brain className="w-4 h-4" />
							</div>
							<div className="flex flex-col items-start">
								<span
									className={cn(
										"text-xs font-semibold",
										strictMode ? "text-white" : "text-text-secondary",
									)}
								>
									{strictMode ? "Strict Mode" : "Hybrid Mode"}
								</span>
								<span className="text-[10px] text-white/40">
									{strictMode ? "Sources Only" : "Sources + GK"}
								</span>
							</div>
						</button>
					</div>

					{/* Persona Selector (Chips) */}
					<div className="space-y-3">
						<div className="text-xs font-medium text-text-secondary flex items-center gap-2">
							<User className="w-3.5 h-3.5" /> Persona
						</div>
						<div className="flex flex-wrap gap-2">
							{PERSONAS.map((p) => (
								<button
									key={p}
									onClick={() => setPersona(p)}
									className={cn(
										"px-3 py-1.5 rounded-full text-xs font-medium border transition-all flex items-center gap-1.5",
										persona === p
											? "bg-white text-black border-white"
											: "bg-transparent text-text-secondary border-white/10 hover:border-white/20",
									)}
									type="button"
								>
									{capitalize(p)}
								</button>
							))}
						</div>
					</div>

					{/* Devices Section */}
					<div className="space-y-4 pt-2 border-t border-white/10">
						{/* Mic */}
						<div className="space-y-2">
							<label htmlFor="mic-select" className="text-xs font-medium text-text-secondary flex items-center gap-2">
								<Mic className="w-3.5 h-3.5" /> Microphone
							</label>
							<div className="relative">
								<select
									id="mic-select"
									value={selectedMic?.deviceId || ""}
									onChange={handleMicChange}
									className="w-full text-sm bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent cursor-pointer appearance-none"
								>
									{mics.length === 0 ? (
										<option value="">No mics found</option>
									) : (
										mics.map((mic) => (
											<option
												key={mic.deviceId}
												value={mic.deviceId}
												className="bg-neutral-900"
											>
												{mic.label || `Mic ${mic.deviceId.slice(0, 5)}...`}
											</option>
										))
									)}
								</select>
								<div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none opacity-50">
									<svg
										width="10"
										height="6"
										viewBox="0 0 10 6"
										fill="none"
										xmlns="http://www.w3.org/2000/svg"
										aria-hidden="true"
									>
										<path
											d="M1 1L5 5L9 1"
											stroke="currentColor"
											strokeWidth="1.5"
											strokeLinecap="round"
											strokeLinejoin="round"
										/>
									</svg>
								</div>
							</div>
						</div>

						{/* Speaker */}
						<div className="space-y-2">
							<label htmlFor="speaker-select" className="text-xs font-medium text-text-secondary flex items-center gap-2">
								<Speaker className="w-3.5 h-3.5" /> Output Device
							</label>
							<div className="relative">
								<select
									id="speaker-select"
									value={selectedSpeakerId}
									onChange={handleSpeakerChange}
									className="w-full text-sm bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent cursor-pointer appearance-none"
								>
									{speakers.length === 0 ? (
										<option value="">No speakers found</option>
									) : (
										speakers.map((spk) => (
											<option
												key={spk.deviceId}
												value={spk.deviceId}
												className="bg-neutral-900"
											>
												{spk.label || `Speaker ${spk.deviceId.slice(0, 5)}...`}
											</option>
										))
									)}
								</select>
								<div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none opacity-50">
									<svg
										width="10"
										height="6"
										viewBox="0 0 10 6"
										fill="none"
										xmlns="http://www.w3.org/2000/svg"
										aria-hidden="true"
									>
										<path
											d="M1 1L5 5L9 1"
											stroke="currentColor"
											strokeWidth="1.5"
											strokeLinecap="round"
											strokeLinejoin="round"
										/>
									</svg>
								</div>
							</div>
						</div>

						{/* Volume */}
						<div className="space-y-3">
							<div className="flex items-center justify-between">
								<label htmlFor="volume-input" className="text-xs font-medium text-text-secondary flex items-center gap-2">
									<Volume2 className="w-3.5 h-3.5" /> Volume
								</label>
								<span className="text-xs font-medium text-white/50">
									{getVolumePercentage()}%
								</span>
							</div>
							<input
								id="volume-input"
								type="range"
								min="0"
								max="1"
								step="0.01"
								value={localVolume}
								onChange={handleVolumeChange}
								className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white"
							/>
						</div>
					</div>
				</div>
			</PopoverContent>
		</Popover>
	);
}
