from __future__ import annotations

import io
import threading
import wave
import os
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from kokoro_onnx import Kokoro
from kokoro_onnx.config import MAX_PHONEME_LENGTH, SAMPLE_RATE
from huggingface_hub import hf_hub_download

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is part of project deps
    np = None  # type: ignore

from samvaad.utils.gpu_utils import get_device


@dataclass(frozen=True)
class VoiceSettings:
    """Configuration describing a Kokoro voice."""

    language: str
    voice_name: str


@dataclass(frozen=True)
class TTSConfig:
    """Configuration block for the Kokoro TTS pipeline."""

    voices: Dict[str, VoiceSettings]
    default_language: str = "en"

    @property
    def available_languages(self) -> Iterable[str]:
        return self.voices.keys()


class _SpeedAwareKokoro(Kokoro):
    """Kokoro variant that adapts the speed tensor dtype for the active model."""

    def __init__(
        self,
        model_path: str,
        voices_path: str,
        espeak_config=None,
        vocab_config=None,
    ) -> None:
        super().__init__(
            model_path,
            voices_path,
            espeak_config=espeak_config,
            vocab_config=vocab_config,
        )
        self._speed_dtype = self._detect_speed_dtype()

    def _detect_speed_dtype(self):
        if np is None:
            return None

        for input_meta in self.sess.get_inputs():
            if input_meta.name != "speed":
                continue

            ort_type = getattr(input_meta, "type", "")
            if ort_type in {"tensor(float)", "tensor(float32)"}:
                return np.float32
            if ort_type in {"tensor(int32)"}:
                return np.int32

        return np.float32 if np is not None else None

    def _create_audio(self, phonemes, voice, speed):  # type: ignore[override]
        if np is None:
            raise RuntimeError("numpy is required for KokoroTTS but is not available")

        phonemes = phonemes[:MAX_PHONEME_LENGTH]
        tokens = np.array(self.tokenizer.tokenize(phonemes), dtype=np.int64)
        assert len(tokens) <= MAX_PHONEME_LENGTH, (
            f"Context length is {MAX_PHONEME_LENGTH}, but leave room for the pad token 0 at the start & end"
        )

        voice = voice[len(tokens)]
        tokens = [[0, *tokens, 0]]
        if "input_ids" in [i.name for i in self.sess.get_inputs()]:
            speed_dtype = self._speed_dtype or np.float32
            inputs = {
                "input_ids": tokens,
                "style": np.array(voice, dtype=np.float32),
                "speed": np.array([speed], dtype=speed_dtype),
            }
        else:
            inputs = {
                "tokens": tokens,
                "style": voice,
                "speed": np.ones(1, dtype=np.float32) * speed,
            }

        audio = np.asarray(self.sess.run(None, inputs)[0])
        if audio.ndim > 1:
            audio = audio.reshape(-1)
        return audio, SAMPLE_RATE


class KokoroTTS:
    """Lightweight wrapper around Kokoro ONNX for TTS usage in the pipeline."""

    _LANGUAGE_ALIASES = {
        "en": "en-us",
        "en-us": "en-us",
        "english": "en-us",
        "hi": "hi",
        "hi-in": "hi",
        "hindi": "hi",
    }

    def __init__(
        self,
        config: Optional[TTSConfig] = None,
        *,
        prefer_gpu: Optional[bool] = None,
    ) -> None:
        self._config = config or self._build_default_config()

        if not self._config.voices:
            raise ValueError("No Kokoro voices configured. Provide at least one voice.")

        self._prefer_gpu = (
            prefer_gpu
            if prefer_gpu is not None
            else get_device() == 'cuda'
        )

        # Download ONNX model and voices
        self._model_path = hf_hub_download(
            repo_id="onnx-community/Kokoro-82M-v1.0-ONNX",
            filename="onnx/model_fp16.onnx"
        )
        
        # Download voices file from GitHub releases
        import requests
        import tempfile
        
        voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
        voices_response = requests.get(voices_url)
        voices_response.raise_for_status()
        
        # Save voices file to temporary location
        self._voices_path = os.path.join(tempfile.gettempdir(), "kokoro_voices_v1.0.bin")
        with open(self._voices_path, 'wb') as f:
            f.write(voices_response.content)
        
        # Initialize Kokoro ONNX model
        self._kokoro = _SpeedAwareKokoro(self._model_path, self._voices_path)
        
        self._pipeline_lock = threading.Lock()

    def _build_default_config(self) -> TTSConfig:
        voices = {
            "en-us": VoiceSettings(
                language="en-us",
                voice_name="af_heart",  # American female heart
            ),
            "hi": VoiceSettings(
                language="hi",
                voice_name="hf_alpha",  # Hindi female alpha
            ),
        }

        return TTSConfig(voices=voices, default_language="en-us")

    def available_languages(self) -> Iterable[str]:
        return self._config.available_languages

    def _normalize_language(self, language: Optional[str]) -> str:
        if not language:
            return self._config.default_language

        normalized = language.strip().lower().replace("_", "-")
        return self._LANGUAGE_ALIASES.get(normalized, normalized if normalized in self._config.voices else self._config.default_language)

    def synthesize(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, int, int, int]:
        """Generate PCM audio from text.

        Returns a tuple of (pcm_bytes, sample_rate, sample_width, channels).
        """

        if not text or not text.strip():
            raise ValueError("Cannot synthesize empty text.")

        lang = self._normalize_language(language)
        settings = self._config.voices[lang]

        # Generate audio using Kokoro ONNX
        with self._pipeline_lock:
            audio, sample_rate = self._kokoro.create(
                text=text,
                voice=settings.voice_name,
                speed=speed,
                lang=lang
            )

        # Audio properties
        sample_width = 2  # 16-bit
        sample_channels = 1

        # Convert to 16-bit PCM bytes
        if np is None:
            raise RuntimeError("numpy is required for KokoroTTS synthesis but is not available")

        audio_int16 = (audio * 32767).astype(np.int16)
        pcm_bytes = audio_int16.tobytes()

        return pcm_bytes, sample_rate, sample_width, sample_channels

    def synthesize_wav(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, int]:
        """Generate a WAV byte stream for the given text.

        Returns a tuple of (wav_bytes, sample_rate).
        """

        pcm_bytes, sample_rate, sample_width, channels = self.synthesize(
            text,
            language=language,
            speed=speed,
        )

        buffer = io.BytesIO()
        with self._wave_writer(buffer, sample_rate, sample_width, channels) as wav_file:
            wav_file.writeframes(pcm_bytes)

        return buffer.getvalue(), sample_rate

    @staticmethod
    def _wave_writer(buffer: io.BytesIO, sample_rate: int, sample_width: int, channels: int):
        wav_file = wave.open(buffer, "wb")
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        return wav_file


__all__ = ["KokoroTTS", "TTSConfig", "VoiceSettings"]