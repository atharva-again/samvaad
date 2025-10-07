from __future__ import annotations

import io
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from piper import PiperVoice
from piper.config import SynthesisConfig

try:
    import torch
except ImportError:  # pragma: no cover - torch is part of project deps
    torch = None  # type: ignore


@dataclass(frozen=True)
class VoiceSettings:
    """Configuration describing a Piper voice."""

    language: str
    model_path: Path
    config_path: Path
    speaker_id: Optional[int] = None


@dataclass(frozen=True)
class TTSConfig:
    """Configuration block for the Piper TTS pipeline."""

    voices: Dict[str, VoiceSettings]
    default_language: str = "en"

    @property
    def available_languages(self) -> Iterable[str]:
        return self.voices.keys()


class PiperTTS:
    """Lightweight wrapper around Piper to simplify TTS usage in the pipeline."""

    _LANGUAGE_ALIASES = {
        "en": "en",
        "en-us": "en",
        "english": "en",
        "hi": "hi",
        "hi-in": "hi",
        "hindi": "hi",
    }

    def __init__(
        self,
        config: Optional[TTSConfig] = None,
        *,
        models_dir: Optional[Path | str] = None,
        prefer_gpu: Optional[bool] = None,
    ) -> None:
        self._models_dir = Path(models_dir or self._default_models_dir()).resolve()
        if not self._models_dir.exists():
            raise FileNotFoundError(
                f"Piper models directory not found at '{self._models_dir}'."
            )

        self._config = config or self._build_default_config()

        if not self._config.voices:
            raise ValueError("No Piper voices configured. Provide at least one voice.")

        self._prefer_gpu = (
            prefer_gpu
            if prefer_gpu is not None
            else bool(torch and torch.cuda.is_available())
        )

        self._voice_cache: Dict[str, PiperVoice] = {}
        self._voice_lock = threading.Lock()

    @staticmethod
    def _default_models_dir() -> Path:
        root = Path(__file__).resolve().parents[2]
        return root / "models" / "piper"

    def _build_default_config(self) -> TTSConfig:
        voices = {
            "en": VoiceSettings(
                language="en",
                model_path=self._models_dir / "en_US" / "en_US-lessac-medium.onnx",
                config_path=self._models_dir / "en_US" / "en_US-lessac-medium.onnx.json",
            ),
            "hi": VoiceSettings(
                language="hi",
                model_path=self._models_dir / "hi_IN" / "hi_IN-pratham-medium.onnx",
                config_path=self._models_dir / "hi_IN" / "hi_IN-pratham-medium.onnx.json",
            ),
        }

        missing = [name for name, info in voices.items() if not info.model_path.exists()]
        if missing:
            joined = ", ".join(missing)
            raise FileNotFoundError(
                f"Piper voice models not found for: {joined}. "
                "Please download the ONNX models before initializing PiperTTS."
            )

        return TTSConfig(voices=voices, default_language="en")

    def available_languages(self) -> Iterable[str]:
        return self._config.available_languages

    def _normalize_language(self, language: Optional[str]) -> str:
        if not language:
            return self._config.default_language

        normalized = language.strip().lower().replace("_", "-")
        return self._LANGUAGE_ALIASES.get(normalized, normalized if normalized in self._config.voices else self._config.default_language)

    def _load_voice(self, lang: str) -> PiperVoice:
        with self._voice_lock:
            if lang in self._voice_cache:
                return self._voice_cache[lang]

            settings = self._config.voices.get(lang)
            if not settings:
                raise ValueError(f"Unsupported language '{lang}'. Available: {sorted(self._config.voices)}")

            if not settings.model_path.exists():
                raise FileNotFoundError(f"Missing Piper model file: {settings.model_path}")
            if not settings.config_path.exists():
                raise FileNotFoundError(f"Missing Piper config file: {settings.config_path}")

            voice = PiperVoice.load(
                settings.model_path,
                config_path=settings.config_path,
                use_cuda=self._prefer_gpu,
            )
            self._voice_cache[lang] = voice
            return voice

    def synthesize(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        volume: float = 1.0,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w_scale: Optional[float] = None,
    ) -> Tuple[bytes, int, int, int]:
        """Generate PCM audio from text.

        Returns a tuple of (pcm_bytes, sample_rate, sample_width, channels).
        """

        if not text or not text.strip():
            raise ValueError("Cannot synthesize empty text.")

        lang = self._normalize_language(language)
        voice = self._load_voice(lang)
        speaker_id = self._config.voices[lang].speaker_id

        syn_config = SynthesisConfig(
            speaker_id=speaker_id,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w_scale=noise_w_scale,
            normalize_audio=True,
            volume=volume,
        )

        pcm_buffer = bytearray()
        sample_rate = voice.config.sample_rate
        sample_width = 2
        sample_channels = 1

        for chunk in voice.synthesize(text, syn_config=syn_config):
            pcm_buffer.extend(chunk.audio_int16_bytes)
            sample_rate = chunk.sample_rate
            sample_width = chunk.sample_width
            sample_channels = chunk.sample_channels

        return bytes(pcm_buffer), sample_rate, sample_width, sample_channels

    def synthesize_wav(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        volume: float = 1.0,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w_scale: Optional[float] = None,
    ) -> Tuple[bytes, int]:
        """Generate a WAV byte stream for the given text.

        Returns a tuple of (wav_bytes, sample_rate).
        """

        pcm_bytes, sample_rate, sample_width, channels = self.synthesize(
            text,
            language=language,
            volume=volume,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w_scale=noise_w_scale,
        )

        buffer = io.BytesIO()
        with self._wave_writer(buffer, sample_rate, sample_width, channels) as wav_file:
            wav_file.writeframes(pcm_bytes)

        return buffer.getvalue(), sample_rate

    @staticmethod
    def _wave_writer(buffer: io.BytesIO, sample_rate: int, sample_width: int, channels: int):
        import wave

        wav_file = wave.open(buffer, "wb")
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        return wav_file


__all__ = ["PiperTTS", "TTSConfig", "VoiceSettings"]
