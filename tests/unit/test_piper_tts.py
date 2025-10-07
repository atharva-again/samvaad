import pytest
from unittest.mock import patch, MagicMock, mock_open
import io
import tempfile
from pathlib import Path

# Import modules to test
from backend.pipeline.generation.piper_tts import PiperTTS, TTSConfig, VoiceSettings


class TestPiperTTS:
    """Test PiperTTS class functionality."""

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_init_default_config(self, mock_default_dir, mock_torch):
        """Test initialization with default configuration."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_config.voices = {"en": MagicMock(), "hi": MagicMock()}
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                assert tts._config == mock_config
                assert tts._models_dir == Path("/fake/models")

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_init_custom_config(self, mock_default_dir, mock_torch):
        """Test initialization with custom configuration."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        custom_config = TTSConfig(
            voices={
                "en": VoiceSettings("en", Path("/custom/en.onnx"), Path("/custom/en.json")),
                "es": VoiceSettings("es", Path("/custom/es.onnx"), Path("/custom/es.json")),
            },
            default_language="es"
        )

        with patch('pathlib.Path.exists', return_value=True):
            tts = PiperTTS(config=custom_config)
            assert tts._config == custom_config
            assert tts._config.default_language == "es"

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_init_empty_config_raises_error(self, mock_default_dir, mock_torch):
        """Test that empty config raises ValueError."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        empty_config = TTSConfig(voices={})

        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(ValueError, match="No Piper voices configured"):
                PiperTTS(config=empty_config)

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_init_missing_models_dir_raises_error(self, mock_default_dir, mock_torch):
        """Test that missing models directory raises FileNotFoundError."""
        mock_default_dir.return_value = Path("/nonexistent/models")
        mock_torch.cuda.is_available.return_value = False

        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(FileNotFoundError, match="Piper models directory not found"):
                PiperTTS()

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_init_missing_voice_files_raises_error(self, mock_default_dir, mock_torch):
        """Test that missing voice files raise FileNotFoundError."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_build_config.side_effect = FileNotFoundError("Piper voice models not found for: en, hi. Please download the ONNX models before initializing PiperTTS.")

                with pytest.raises(FileNotFoundError, match="Piper voice models not found"):
                    PiperTTS()

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_init_gpu_preference(self, mock_default_dir, mock_torch):
        """Test GPU preference detection."""
        mock_default_dir.return_value = Path("/fake/models")

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_config.voices = {"en": MagicMock()}
                mock_build_config.return_value = mock_config

                mock_torch.cuda.is_available.return_value = True
                tts = PiperTTS()
                assert tts._prefer_gpu is True

                mock_torch.cuda.is_available.return_value = False
                tts = PiperTTS()
                assert tts._prefer_gpu is False

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_available_languages(self, mock_default_dir, mock_torch):
        """Test getting available languages."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_config.voices = {"en": MagicMock(), "hi": MagicMock(), "es": MagicMock()}
                mock_config.available_languages = ["en", "hi", "es"]
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                languages = list(tts.available_languages())
                assert languages == ["en", "hi", "es"]

    @patch('backend.pipeline.generation.piper_tts.torch')
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
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_normalize_language(self, mock_default_dir, mock_torch, input_lang, expected):
        """Test language normalization with various inputs."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_config.voices = {"en": MagicMock(), "hi": MagicMock()}
                mock_config.default_language = "en"
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                result = tts._normalize_language(input_lang)
                assert result == expected

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperVoice')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_load_voice_caching(self, mock_default_dir, mock_piper_voice, mock_torch):
        """Test voice loading and caching."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        mock_voice = MagicMock()
        mock_piper_voice.load.return_value = mock_voice

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_voice_settings = MagicMock()
                mock_voice_settings.model_path.exists.return_value = True
                mock_voice_settings.config_path.exists.return_value = True
                mock_config.voices = {"en": mock_voice_settings}
                mock_build_config.return_value = mock_config

                tts = PiperTTS()

                # First call should create voice
                voice1 = tts._load_voice("en")
                assert voice1 == mock_voice
                mock_piper_voice.load.assert_called_once()

                # Second call should return cached voice
                mock_piper_voice.reset_mock()
                voice2 = tts._load_voice("en")
                assert voice2 == mock_voice
                mock_piper_voice.load.assert_not_called()  # Should use cache

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_load_voice_unsupported_language(self, mock_default_dir, mock_torch):
        """Test loading voice with unsupported language."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_config.voices = {"en": MagicMock(), "hi": MagicMock()}
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                with pytest.raises(ValueError, match="Unsupported language 'fr'"):
                    tts._load_voice("fr")

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_load_voice_missing_model_file(self, mock_default_dir, mock_torch):
        """Test loading voice with missing model file."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_voice_settings = MagicMock()
                mock_voice_settings.model_path.exists.return_value = False
                mock_voice_settings.config_path.exists.return_value = True
                mock_config.voices = {"en": mock_voice_settings}
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                with pytest.raises(FileNotFoundError, match="Missing Piper model file"):
                    tts._load_voice("en")

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperVoice')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_synthesize_basic(self, mock_default_dir, mock_piper_voice, mock_torch):
        """Test basic text synthesis."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        # Mock voice and synthesis
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_chunk = MagicMock()
        mock_chunk.audio_int16_bytes = b'audio_chunk'
        mock_chunk.sample_rate = 22050
        mock_chunk.sample_width = 2
        mock_chunk.sample_channels = 1
        mock_voice.synthesize.return_value = [mock_chunk]
        mock_piper_voice.load.return_value = mock_voice

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_voice_settings = MagicMock()
                mock_voice_settings.model_path.exists.return_value = True
                mock_voice_settings.config_path.exists.return_value = True
                mock_voice_settings.speaker_id = None
                mock_config.voices = {"en": mock_voice_settings}
                mock_config.default_language = "en"
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                result = tts.synthesize("Hello world")

                pcm_bytes, sample_rate, sample_width, channels = result
                assert pcm_bytes == b'audio_chunk'
                assert sample_rate == 22050
                assert sample_width == 2
                assert channels == 1

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_synthesize_empty_text_raises_error(self, mock_default_dir, mock_torch):
        """Test that empty text raises ValueError."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_config.voices = {"en": MagicMock()}
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                with pytest.raises(ValueError, match="Cannot synthesize empty text"):
                    tts.synthesize("")

                with pytest.raises(ValueError, match="Cannot synthesize empty text"):
                    tts.synthesize("   ")

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperVoice')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    @patch('backend.pipeline.generation.piper_tts.wave')
    def test_synthesize_wav(self, mock_wave, mock_default_dir, mock_piper_voice, mock_torch):
        """Test WAV synthesis."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        # Mock voice and synthesis
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_chunk = MagicMock()
        mock_chunk.audio_int16_bytes = b'pcm_data'
        mock_chunk.sample_rate = 22050
        mock_chunk.sample_width = 2
        mock_chunk.sample_channels = 1
        mock_voice.synthesize.return_value = [mock_chunk]
        mock_piper_voice.load.return_value = mock_voice

        # Mock wave file
        mock_wav_file = MagicMock()
        mock_wave.open.return_value = mock_wav_file
        mock_wav_file.__enter__.return_value = mock_wav_file

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_voice_settings = MagicMock()
                mock_voice_settings.model_path.exists.return_value = True
                mock_voice_settings.config_path.exists.return_value = True
                mock_voice_settings.speaker_id = None
                mock_config.voices = {"en": mock_voice_settings}
                mock_config.default_language = "en"
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                wav_bytes, sample_rate = tts.synthesize_wav("Hello world")

                assert isinstance(wav_bytes, bytes)
                assert sample_rate == 22050
                mock_wav_file.setnchannels.assert_called_with(1)
                mock_wav_file.setsampwidth.assert_called_with(2)
                mock_wav_file.setframerate.assert_called_with(22050)
                mock_wav_file.writeframes.assert_called_with(b'pcm_data')

    @patch('backend.pipeline.generation.piper_tts.torch')
    @patch('backend.pipeline.generation.piper_tts.PiperVoice')
    @patch('backend.pipeline.generation.piper_tts.PiperTTS._default_models_dir')
    def test_synthesize_with_parameters(self, mock_default_dir, mock_piper_voice, mock_torch):
        """Test synthesis with various parameters."""
        mock_default_dir.return_value = Path("/fake/models")
        mock_torch.cuda.is_available.return_value = False

        # Mock voice and synthesis
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_chunk = MagicMock()
        mock_chunk.audio_int16_bytes = b'audio_data'
        mock_chunk.sample_rate = 22050
        mock_chunk.sample_width = 2
        mock_chunk.sample_channels = 1
        mock_voice.synthesize.return_value = [mock_chunk]
        mock_piper_voice.load.return_value = mock_voice

        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(PiperTTS, '_build_default_config') as mock_build_config:
                mock_config = MagicMock()
                mock_voice_settings = MagicMock()
                mock_voice_settings.model_path.exists.return_value = True
                mock_voice_settings.config_path.exists.return_value = True
                mock_voice_settings.speaker_id = 1
                mock_config.voices = {"en": mock_voice_settings}
                mock_build_config.return_value = mock_config

                tts = PiperTTS()
                result = tts.synthesize(
                    "Hello",
                    language="en",
                    volume=0.8,
                    length_scale=1.2,
                    noise_scale=0.5,
                    noise_w_scale=0.3
                )

                pcm_bytes, sample_rate, sample_width, channels = result
                assert pcm_bytes == b'audio_data'

                # Verify SynthesisConfig was created with correct parameters
                call_args = mock_voice.synthesize.call_args
                syn_config = call_args[1]['syn_config']
                assert syn_config.speaker_id == 1
                assert syn_config.length_scale == 1.2
                assert syn_config.noise_scale == 0.5
                assert syn_config.noise_w_scale == 0.3
                assert syn_config.normalize_audio is True
                assert syn_config.volume == 0.8

    def test_wave_writer_static_method(self):
        """Test the static wave writer method."""
        buffer = io.BytesIO()
        sample_rate, sample_width, channels = 44100, 2, 1

        with PiperTTS._wave_writer(buffer, sample_rate, sample_width, channels) as wav_file:
            wav_file.writeframes(b'test_data')

        # Verify buffer contains WAV data
        wav_data = buffer.getvalue()
        assert len(wav_data) > 0
        assert wav_data.startswith(b'RIFF')  # WAV file header

    def test_default_models_dir(self):
        """Test default models directory resolution."""
        actual_path = PiperTTS._default_models_dir()
        assert actual_path.name == "piper"
        assert actual_path.parent.name == "models"
        # Should be under the project root
        assert "samvaad" in str(actual_path)