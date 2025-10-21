from __future__ import annotations

import io
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from kokoro import KPipeline

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is part of project deps
    np = None  # type: ignore

try:
    import torch
except ImportError:  # pragma: no cover - torch is part of project deps
    torch = None  # type: ignore


@dataclass(frozen=True)
class VoiceSettings:
    """Configuration describing a Kokoro voice."""

    language: str
    lang_code: str
    voice_name: str


@dataclass(frozen=True)
class TTSConfig:
    """Configuration block for the Kokoro TTS pipeline."""

    voices: Dict[str, VoiceSettings]
    default_language: str = "en"

    @property
    def available_languages(self) -> Iterable[str]:
        return self.voices.keys()


class KokoroTTS:
    """Lightweight wrapper around Kokoro to simplify TTS usage in the pipeline."""

    _LANGUAGE_ALIASES = {
        "en": "en",
        "en-us": "en",
        "english": "en",
        "hi": "hi",
        "hi-in": "hi",
        "hindi": "hi",
    }

    _LANG_CODE_MAPPING = {
        "en": "a",  # American English
        "hi": "h",  # Hindi
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
            else bool(torch and torch.cuda.is_available())
        )

        self._pipeline_cache: Dict[str, KPipeline] = {}
        self._pipeline_lock = threading.Lock()

    def _build_default_config(self) -> TTSConfig:
        voices = {
            "en": VoiceSettings(
                language="en",
                lang_code="a",  # American English
                voice_name="af_heart",  # American female heart
            ),
            "hi": VoiceSettings(
                language="hi",
                lang_code="h",  # Hindi
                voice_name="hf_alpha",  # Hindi female alpha
            ),
        }

        return TTSConfig(voices=voices, default_language="en")

    def available_languages(self) -> Iterable[str]:
        return self._config.available_languages

    def _normalize_language(self, language: Optional[str]) -> str:
        if not language:
            return self._config.default_language

        normalized = language.strip().lower().replace("_", "-")
        return self._LANGUAGE_ALIASES.get(normalized, normalized if normalized in self._config.voices else self._config.default_language)

    def _load_pipeline(self, lang: str) -> KPipeline:
        with self._pipeline_lock:
            if lang in self._pipeline_cache:
                return self._pipeline_cache[lang]

            settings = self._config.voices.get(lang)
            if not settings:
                raise ValueError(f"Unsupported language '{lang}'. Available: {sorted(self._config.voices)}")

            pipeline = KPipeline(repo_id='hexgrad/Kokoro-82M', lang_code=settings.lang_code)
            self._pipeline_cache[lang] = pipeline
            return pipeline

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
        pipeline = self._load_pipeline(lang)
        settings = self._config.voices[lang]

        # Kokoro generates audio at 24kHz
        sample_rate = 24000
        sample_width = 2  # 16-bit
        sample_channels = 1

        # Generate audio
        generator = pipeline(
            text,
            voice=settings.voice_name,
            speed=speed,
        )

        pcm_buffer = bytearray()
        for _, _, audio in generator:
            # Convert to 16-bit PCM bytes
            if np is None:
                raise RuntimeError("numpy is required for KokoroTTS synthesis but is not available")

            audio_int16 = (audio * 32767).numpy().astype(np.int16)
            pcm_buffer.extend(audio_int16.tobytes())

        return bytes(pcm_buffer), sample_rate, sample_width, sample_channels

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