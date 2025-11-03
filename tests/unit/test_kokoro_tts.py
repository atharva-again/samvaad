import pytest
from unittest.mock import patch, MagicMock, mock_open, call
import io
from pathlib import Path
import numpy as np

# Import modules to test
from samvaad.pipeline.generation.kokoro_tts import KokoroTTS, TTSConfig, VoiceSettings


class TestKokoroTTS:
    """Test KokoroTTS class functionality."""

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_init_default_config(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro):
        """Test initialization with default configuration."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        tts = KokoroTTS()
        assert tts._config is not None
        assert "en-us" in tts._config.voices
        assert "hi" in tts._config.voices
        assert tts._config.default_language == "en-us"

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_init_custom_config(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro):
        """Test initialization with custom configuration."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        custom_config = TTSConfig(
            voices={
                "en": VoiceSettings("en", "af_heart"),
                "es": VoiceSettings("es", "ef_dora"),
            },
            default_language="es"
        )
        tts = KokoroTTS(config=custom_config)
        assert tts._config == custom_config
        assert tts._config.default_language == "es"

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_init_empty_config_raises_error(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro):
        """Test that empty config raises ValueError."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        empty_config = TTSConfig(voices={})
        with pytest.raises(ValueError, match="No Kokoro voices configured"):
            KokoroTTS(config=empty_config)

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_init_gpu_preference(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro):
        """Test GPU preference detection."""
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        mock_get_device.return_value = 'cuda'
        tts = KokoroTTS()
        assert tts._prefer_gpu is True

        mock_get_device.return_value = 'cpu'
        tts = KokoroTTS()
        assert tts._prefer_gpu is False

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_available_languages(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro):
        """Test getting available languages."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        tts = KokoroTTS()
        languages = list(tts.available_languages())
        assert "en-us" in languages
        assert "hi" in languages

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    @pytest.mark.parametrize("input_lang,expected", [
        ("en", "en-us"),
        ("en-us", "en-us"),
        ("english", "en-us"),
        ("hi", "hi"),
        ("hi-in", "hi"),
        ("hindi", "hi"),
        ("EN", "en-us"),
        (" en ", "en-us"),
        ("en_US", "en-us"),
        (None, "en-us"),
        ("", "en-us"),
        ("unknown", "en-us"),  # Falls back to default
    ])
    def test_normalize_language(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro, input_lang, expected):
        """Test language normalization with various inputs."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        tts = KokoroTTS()
        result = tts._normalize_language(input_lang)
        assert result == expected

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_kokoro_initialization(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro):
        """Test that Kokoro instance is created during initialization."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        mock_kokoro_instance = MagicMock()
        mock_kokoro.return_value = mock_kokoro_instance

        tts = KokoroTTS()

        # Verify Kokoro was initialized with model and voices paths
        mock_kokoro.assert_called_once()
        assert tts._kokoro is not None

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_unsupported_language_uses_default(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro):
        """Test that unsupported language falls back to default."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        tts = KokoroTTS()
        result = tts._normalize_language("fr")
        assert result == "en-us"  # Should fall back to default

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_synthesize_basic(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro_class):
        """Test basic text synthesis."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        # Mock numpy array
        mock_audio_array = np.array([0.1, 0.2, -0.1], dtype=np.float32)

        # Mock Kokoro instance
        mock_kokoro_instance = MagicMock()
        mock_kokoro_instance.create.return_value = (mock_audio_array, 24000)
        mock_kokoro_class.return_value = mock_kokoro_instance

        tts = KokoroTTS()
        result = tts.synthesize("Hello world")

        pcm_bytes, sample_rate, sample_width, channels = result
        assert isinstance(pcm_bytes, bytes)
        assert sample_rate == 24000
        assert sample_width == 2
        assert channels == 1

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_synthesize_empty_text_raises_error(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro):
        """Test that empty text raises ValueError."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        tts = KokoroTTS()
        with pytest.raises(ValueError, match="Cannot synthesize empty text"):
            tts.synthesize("")

        with pytest.raises(ValueError, match="Cannot synthesize empty text"):
            tts.synthesize("   ")

    @patch('samvaad.pipeline.generation.kokoro_tts.wave')
    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_synthesize_wav(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro_class, mock_wave):
        """Test WAV synthesis."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        # Mock numpy array
        mock_audio_array = np.array([0.1, 0.2, -0.1], dtype=np.float32)

        # Mock Kokoro instance
        mock_kokoro_instance = MagicMock()
        mock_kokoro_instance.create.return_value = (mock_audio_array, 24000)
        mock_kokoro_class.return_value = mock_kokoro_instance

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

    @patch('samvaad.pipeline.generation.kokoro_tts._SpeedAwareKokoro')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.path.exists')
    @patch('samvaad.pipeline.generation.kokoro_tts.os.makedirs')
    @patch('samvaad.pipeline.generation.kokoro_tts.open', new_callable=mock_open)
    @patch('requests.get')
    @patch('samvaad.pipeline.generation.kokoro_tts.hf_hub_download')
    @patch('samvaad.pipeline.generation.kokoro_tts.get_device')
    def test_synthesize_with_language_and_speed(self, mock_get_device, mock_hf_download, mock_requests, mock_file, mock_makedirs, mock_exists, mock_kokoro_class):
        """Test synthesis with specific language and speed."""
        mock_get_device.return_value = 'cpu'
        mock_hf_download.return_value = '/fake/model.onnx'
        mock_exists.return_value = True
        
        # Mock numpy array
        mock_audio_array = np.array([0.1, 0.2, -0.1], dtype=np.float32)

        # Mock Kokoro instance
        mock_kokoro_instance = MagicMock()
        mock_kokoro_instance.create.return_value = (mock_audio_array, 24000)
        mock_kokoro_class.return_value = mock_kokoro_instance

        tts = KokoroTTS()
        result = tts.synthesize("Hello", language="hi", speed=1.5)

        # Verify create method was called with correct parameters
        mock_kokoro_instance.create.assert_called_once()
        call_args = mock_kokoro_instance.create.call_args
        assert call_args.kwargs['speed'] == 1.5
        assert call_args.kwargs['lang'] == 'hi'

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