import pytest
from unittest.mock import patch, MagicMock, mock_open
import io
from pathlib import Path

# Import modules to test
from backend.pipeline.generation.kokoro_tts import KokoroTTS, TTSConfig, VoiceSettings


class TestKokoroTTS:
    """Test KokoroTTS class functionality."""

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    def test_init_default_config(self, mock_torch):
        """Test initialization with default configuration."""
        mock_torch.cuda.is_available.return_value = False
        tts = KokoroTTS()
        assert tts._config is not None
        assert "en" in tts._config.voices
        assert "hi" in tts._config.voices
        assert tts._config.default_language == "en"

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    def test_init_custom_config(self, mock_torch):
        """Test initialization with custom configuration."""
        mock_torch.cuda.is_available.return_value = False
        custom_config = TTSConfig(
            voices={
                "en": VoiceSettings("en", "a", "af_heart"),
                "es": VoiceSettings("es", "b", "ef_dora"),
            },
            default_language="es"
        )
        tts = KokoroTTS(config=custom_config)
        assert tts._config == custom_config
        assert tts._config.default_language == "es"

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    def test_init_empty_config_raises_error(self, mock_torch):
        """Test that empty config raises ValueError."""
        mock_torch.cuda.is_available.return_value = False
        empty_config = TTSConfig(voices={})
        with pytest.raises(ValueError, match="No Kokoro voices configured"):
            KokoroTTS(config=empty_config)

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    def test_init_gpu_preference(self, mock_torch):
        """Test GPU preference detection."""
        mock_torch.cuda.is_available.return_value = True
        tts = KokoroTTS()
        assert tts._prefer_gpu is True

        mock_torch.cuda.is_available.return_value = False
        tts = KokoroTTS()
        assert tts._prefer_gpu is False

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    def test_available_languages(self, mock_torch):
        """Test getting available languages."""
        mock_torch.cuda.is_available.return_value = False
        tts = KokoroTTS()
        languages = list(tts.available_languages())
        assert "en" in languages
        assert "hi" in languages

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    @pytest.mark.parametrize("input_lang,expected", [
        ("en", "en"),
        ("en-us", "en"),
        ("english", "en"),
        ("hi", "hi"),
        ("hi-in", "hi"),
        ("hindi", "hi"),
        ("EN", "en"),
        (" en ", "en"),
        ("en_US", "en"),
        (None, "en"),
        ("", "en"),
        ("unknown", "en"),  # Falls back to default
    ])
    def test_normalize_language(self, mock_torch, input_lang, expected):
        """Test language normalization with various inputs."""
        mock_torch.cuda.is_available.return_value = False
        tts = KokoroTTS()
        result = tts._normalize_language(input_lang)
        assert result == expected

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    @patch('backend.pipeline.generation.kokoro_tts.KPipeline')
    def test_load_pipeline_caching(self, mock_kpipeline, mock_torch):
        """Test pipeline loading and caching."""
        mock_torch.cuda.is_available.return_value = False
        mock_pipeline = MagicMock()
        mock_kpipeline.return_value = mock_pipeline

        tts = KokoroTTS()

        # First call should create pipeline
        pipeline1 = tts._load_pipeline("en")
        assert pipeline1 == mock_pipeline
        mock_kpipeline.assert_called_once_with(lang_code="a")

        # Second call should return cached pipeline
        mock_kpipeline.reset_mock()
        pipeline2 = tts._load_pipeline("en")
        assert pipeline2 == mock_pipeline
        mock_kpipeline.assert_not_called()  # Should use cache

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    def test_load_pipeline_unsupported_language(self, mock_torch):
        """Test loading pipeline with unsupported language."""
        mock_torch.cuda.is_available.return_value = False
        tts = KokoroTTS()
        with pytest.raises(ValueError, match="Unsupported language 'fr'"):
            tts._load_pipeline("fr")

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    @patch('backend.pipeline.generation.kokoro_tts.KPipeline')
    @patch('backend.pipeline.generation.kokoro_tts.np')
    def test_synthesize_basic(self, mock_np, mock_kpipeline, mock_torch):
        """Test basic text synthesis."""
        mock_torch.cuda.is_available.return_value = False
        mock_np.int16 = MagicMock()
        # Mock numpy array
        mock_audio_array = MagicMock()
        mock_audio_array.__mul__ = MagicMock(return_value=mock_audio_array)
        mock_audio_array.numpy.return_value = MagicMock()
        mock_audio_array.numpy.return_value.astype.return_value = MagicMock()
        mock_audio_array.numpy.return_value.astype.return_value.tobytes.return_value = b'audio_data'

        # Mock generator
        mock_generator = [("", "", mock_audio_array)]
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_generator
        mock_kpipeline.return_value = mock_pipeline

        tts = KokoroTTS()
        result = tts.synthesize("Hello world")

        pcm_bytes, sample_rate, sample_width, channels = result
        assert pcm_bytes == b'audio_data'
        assert sample_rate == 24000
        assert sample_width == 2
        assert channels == 1

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    def test_synthesize_empty_text_raises_error(self, mock_torch):
        """Test that empty text raises ValueError."""
        mock_torch.cuda.is_available.return_value = False
        tts = KokoroTTS()
        with pytest.raises(ValueError, match="Cannot synthesize empty text"):
            tts.synthesize("")

        with pytest.raises(ValueError, match="Cannot synthesize empty text"):
            tts.synthesize("   ")

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    @patch('backend.pipeline.generation.kokoro_tts.KPipeline')
    @patch('backend.pipeline.generation.kokoro_tts.np')
    @patch('backend.pipeline.generation.kokoro_tts.wave')
    def test_synthesize_wav(self, mock_wave, mock_np, mock_kpipeline, mock_torch):
        """Test WAV synthesis."""
        mock_torch.cuda.is_available.return_value = False
        mock_np.int16 = MagicMock()
        # Mock numpy array
        mock_audio_array = MagicMock()
        mock_audio_array.__mul__ = MagicMock(return_value=mock_audio_array)
        mock_audio_array.numpy.return_value = MagicMock()
        mock_audio_array.numpy.return_value.astype.return_value = MagicMock()
        mock_audio_array.numpy.return_value.astype.return_value.tobytes.return_value = b'pcm_data'

        # Mock generator
        mock_generator = [("", "", mock_audio_array)]
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_generator
        mock_kpipeline.return_value = mock_pipeline

        # Mock wave file
        mock_wav_file = MagicMock()
        mock_wave.open.return_value = mock_wav_file
        mock_wav_file.__enter__.return_value = mock_wav_file

        tts = KokoroTTS()
        wav_bytes, sample_rate = tts.synthesize_wav("Hello world")

        assert isinstance(wav_bytes, bytes)
        assert sample_rate == 24000
        mock_wav_file.setnchannels.assert_called_with(1)
        mock_wav_file.setsampwidth.assert_called_with(2)
        mock_wav_file.setframerate.assert_called_with(24000)
        mock_wav_file.writeframes.assert_called_with(b'pcm_data')

    @patch('backend.pipeline.generation.kokoro_tts.torch')
    @patch('backend.pipeline.generation.kokoro_tts.KPipeline')
    @patch('backend.pipeline.generation.kokoro_tts.np')
    def test_synthesize_with_language_and_speed(self, mock_np, mock_kpipeline, mock_torch):
        """Test synthesis with specific language and speed."""
        mock_torch.cuda.is_available.return_value = False
        mock_np.int16 = MagicMock()
        # Mock numpy array
        mock_audio_array = MagicMock()
        mock_audio_array.__mul__ = MagicMock(return_value=mock_audio_array)
        mock_audio_array.numpy.return_value = MagicMock()
        mock_audio_array.numpy.return_value.astype.return_value = MagicMock()
        mock_audio_array.numpy.return_value.astype.return_value.tobytes.return_value = b'audio_data'

        # Mock generator
        mock_generator = [("", "", mock_audio_array)]
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_generator
        mock_kpipeline.return_value = mock_pipeline

        tts = KokoroTTS()
        result = tts.synthesize("Hello", language="hi", speed=1.5)

        # Verify Hindi pipeline was used
        mock_kpipeline.assert_called_with(lang_code="h")
        # Verify speed parameter was passed
        mock_pipeline.assert_called_with("Hello", voice="hf_alpha", speed=1.5)

    def test_wave_writer_static_method(self):
        """Test the static wave writer method."""
        buffer = io.BytesIO()
        sample_rate, sample_width, channels = 44100, 2, 1

        with KokoroTTS._wave_writer(buffer, sample_rate, sample_width, channels) as wav_file:
            wav_file.writeframes(b'test_data')

        # Verify buffer contains WAV data
        wav_data = buffer.getvalue()
        assert len(wav_data) > 0
        assert wav_data.startswith(b'RIFF')  # WAV file header