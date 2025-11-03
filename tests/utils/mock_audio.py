"""Mock audio utilities for testing voice-related functionality."""

import numpy as np
from typing import Tuple, Optional
from unittest.mock import MagicMock, Mock


def generate_fake_audio_data(
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    channels: int = 1,
    amplitude: int = 5000
) -> bytes:
    """
    Generate fake audio data as raw PCM bytes.
    
    Args:
        duration_seconds: Duration of audio in seconds
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        amplitude: Amplitude of the generated sine wave
        
    Returns:
        Raw PCM audio data as bytes (int16)
    """
    num_samples = int(duration_seconds * sample_rate)
    # Generate simple sine wave
    t = np.linspace(0, duration_seconds, num_samples)
    frequency = 440  # A4 note
    audio = (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.int16)
    
    if channels > 1:
        audio = np.repeat(audio[:, np.newaxis], channels, axis=1)
    
    return audio.tobytes()


def generate_silence(
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    channels: int = 1
) -> bytes:
    """
    Generate silent audio data.
    
    Args:
        duration_seconds: Duration of silence in seconds
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        
    Returns:
        Silent PCM audio data as bytes (int16)
    """
    num_samples = int(duration_seconds * sample_rate)
    audio = np.zeros(num_samples, dtype=np.int16)
    
    if channels > 1:
        audio = np.repeat(audio[:, np.newaxis], channels, axis=1)
    
    return audio.tobytes()


def create_mock_sounddevice():
    """
    Create a mock sounddevice module for testing.
    
    Returns:
        Mock sounddevice module with common methods
    """
    mock_sd = MagicMock()
    
    # Mock RawInputStream
    mock_stream = MagicMock()
    mock_stream.read.return_value = (generate_fake_audio_data(0.02), None)  # 20ms frame
    mock_stream.start.return_value = None
    mock_stream.stop.return_value = None
    mock_stream.close.return_value = None
    
    mock_sd.RawInputStream.return_value = mock_stream
    
    # Mock play/wait
    mock_sd.play.return_value = None
    mock_sd.wait.return_value = None
    
    # Mock query_devices
    mock_sd.query_devices.return_value = [
        {'name': 'Mock Device', 'max_input_channels': 2, 'max_output_channels': 2}
    ]
    
    return mock_sd, mock_stream


def create_mock_webrtcvad():
    """
    Create a mock webrtcvad module for testing.
    
    Returns:
        Mock webrtcvad module with Vad class
    """
    mock_vad_module = MagicMock()
    mock_vad_instance = MagicMock()
    
    # Default: detect speech in all frames
    mock_vad_instance.is_speech.return_value = True
    
    mock_vad_module.Vad.return_value = mock_vad_instance
    
    return mock_vad_module, mock_vad_instance


def create_speech_silence_pattern(
    speech_frames: int = 10,
    silence_frames: int = 5,
    frame_duration_ms: int = 20,
    sample_rate: int = 16000
) -> Tuple[list, list]:
    """
    Create a pattern of speech and silence frames for testing VAD.
    
    Args:
        speech_frames: Number of frames with speech
        silence_frames: Number of frames with silence
        frame_duration_ms: Duration of each frame in milliseconds
        sample_rate: Sample rate in Hz
        
    Returns:
        Tuple of (audio_frames, is_speech_flags)
    """
    frame_size = int(sample_rate * frame_duration_ms / 1000)
    audio_frames = []
    is_speech_flags = []
    
    # Add speech frames
    for _ in range(speech_frames):
        audio_frames.append(
            np.frombuffer(
                generate_fake_audio_data(
                    duration_seconds=frame_duration_ms / 1000,
                    sample_rate=sample_rate
                ),
                dtype=np.int16
            )
        )
        is_speech_flags.append(True)
    
    # Add silence frames
    for _ in range(silence_frames):
        audio_frames.append(
            np.frombuffer(
                generate_silence(
                    duration_seconds=frame_duration_ms / 1000,
                    sample_rate=sample_rate
                ),
                dtype=np.int16
            )
        )
        is_speech_flags.append(False)
    
    return audio_frames, is_speech_flags


class MockAudioStream:
    """Mock audio stream that returns predefined frames."""
    
    def __init__(self, frames: list, sample_rate: int = 16000):
        """
        Initialize mock stream with predefined frames.
        
        Args:
            frames: List of numpy arrays representing audio frames
            sample_rate: Sample rate in Hz
        """
        self.frames = frames
        self.sample_rate = sample_rate
        self.frame_index = 0
        self.is_started = False
    
    def read(self, frame_size: int):
        """Read next frame from the stream."""
        if self.frame_index >= len(self.frames):
            raise RuntimeError("No more frames available")
        
        frame = self.frames[self.frame_index]
        self.frame_index += 1
        return (frame, None)
    
    def start(self):
        """Start the stream."""
        self.is_started = True
    
    def stop(self):
        """Stop the stream."""
        self.is_started = False
    
    def close(self):
        """Close the stream."""
        self.is_started = False


class MockVAD:
    """Mock VAD that returns predefined speech detection results."""
    
    def __init__(self, is_speech_pattern: list):
        """
        Initialize mock VAD with predefined pattern.
        
        Args:
            is_speech_pattern: List of booleans indicating speech detection
        """
        self.is_speech_pattern = is_speech_pattern
        self.call_index = 0
    
    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        """Check if frame contains speech."""
        if self.call_index >= len(self.is_speech_pattern):
            # Default to silence after pattern ends
            return False
        
        result = self.is_speech_pattern[self.call_index]
        self.call_index += 1
        return result
