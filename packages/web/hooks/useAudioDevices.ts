import { useLiveKitClient } from "@/components/providers/LiveKitProvider";
import { useEffect, useState } from "react";

interface AudioDevices {
  mics: MediaDeviceInfo[];
  speakers: MediaDeviceInfo[];
  selectedMic: MediaDeviceInfo | null;
  selectedSpeakerId: string;
  updateMic: (deviceId: string) => void;
  setSelectedSpeakerId: (deviceId: string) => void;
}

/**
 * Hook to manage audio input/output device enumeration and selection.
 * Centralizes device management logic used across voice settings components.
 */
export function useAudioDevices(): AudioDevices {
  const client = useLiveKitClient();

  const [speakers, setSpeakers] = useState<MediaDeviceInfo[]>([]);
  const [mics, setMics] = useState<MediaDeviceInfo[]>([]);
  const [selectedSpeakerId, setSelectedSpeakerId] = useState<string>("");

  useEffect(() => {
    if (!selectedSpeakerId) return;
    void client?.switchSpeaker(selectedSpeakerId);
  }, [client, selectedSpeakerId]);

  useEffect(() => {
    const enumerateDevices = async () => {
      try {
        // Request mic permission to get device labels
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
          });
          stream.getTracks().forEach((track) => track.stop());
        } catch (permErr) {
          console.debug("Mic permission not yet granted:", permErr);
        }

        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = devices.filter((d) => d.kind === "audioinput");
        const audioOutputs = devices.filter((d) => d.kind === "audiooutput");

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
  }, [selectedSpeakerId]);

  return {
    mics,
    speakers,
    selectedMic: mics.find((mic) => mic.deviceId === client?.activeMicId) ?? mics[0] ?? null,
    selectedSpeakerId,
    updateMic: (deviceId: string) => void client?.switchMicrophone(deviceId),
    setSelectedSpeakerId,
  };
}
