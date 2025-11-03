"""Tests for VoiceMode class."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch, Mock, call
from samvaad.pipeline.retrieval.voice_mode import VoiceMode
from tests.utils.mock_audio import (
    MockAudioStream,
    MockVAD,
    generate_fake_audio_data,
    generate_silence,
    create_speech_silence_pattern
)


@pytest.mark.unit
class TestVoiceMode:
    """Test VoiceMode class functionality."""
    
    def test_initialization(self):
        """Test VoiceMode initialization."""
        voice_mode = VoiceMode()
        
        assert voice_mode.conversation_manager is not None
        assert voice_mode.whisper_model is None
        assert voice_mode.tts_engine is None
        assert voice_mode.stream is None
        assert voice_mode.vad is None
        assert not voice_mode.running
        assert voice_mode.sample_rate == 16000
        assert voice_mode.frame_duration_ms == 20
    
    def test_initialization_with_callbacks(self):
        """Test initialization with progress callbacks."""
        callbacks = {'progress': MagicMock()}
        voice_mode = VoiceMode(progress_callbacks=callbacks)
        
        assert voice_mode.progress_callbacks == callbacks
    
    @patch('samvaad.pipeline.retrieval.voice_mode.KokoroTTS')
    @patch('samvaad.pipeline.retrieval.voice_mode.initialize_whisper_model')
    def test_preload_models(self, mock_whisper_init, mock_tts):
        """Test preloading Whisper and TTS models."""
        mock_whisper = MagicMock()
        mock_whisper_init.return_value = mock_whisper
        mock_tts_instance = MagicMock()
        mock_tts.return_value = mock_tts_instance
        
        voice_mode = VoiceMode()
        voice_mode.preload_models()
        
        assert voice_mode.whisper_model == mock_whisper
        assert voice_mode.tts_engine == mock_tts_instance
        mock_whisper_init.assert_called_once_with(model_size="small", device="auto", silent=False)
        mock_tts.assert_called_once()
    
    @patch('samvaad.pipeline.retrieval.voice_mode.initialize_whisper_model')
    def test_preload_models_whisper_failure(self, mock_whisper_init):
        """Test preload handles Whisper initialization failure."""
        mock_whisper_init.side_effect = Exception("Whisper load failed")
        
        voice_mode = VoiceMode()
        
        # Should not raise exception
        voice_mode.preload_models()
        
        assert voice_mode.whisper_model is None
    
    @patch('samvaad.pipeline.retrieval.voice_mode.initialize_whisper_model')
    def test_initialize_whisper_only(self, mock_whisper_init):
        """Test initializing only Whisper model."""
        mock_whisper = MagicMock()
        mock_whisper_init.return_value = mock_whisper
        
        voice_mode = VoiceMode()
        voice_mode.initialize_whisper_only(silent=True)
        
        assert voice_mode.whisper_model == mock_whisper
        mock_whisper_init.assert_called_once_with(model_size="small", device="auto", silent=True)
    
    @patch('samvaad.pipeline.retrieval.voice_mode.initialize_whisper_model')
    def test_initialize_whisper_only_failure(self, mock_whisper_init):
        """Test Whisper initialization failure."""
        mock_whisper_init.return_value = None
        
        voice_mode = VoiceMode()
        voice_mode.initialize_whisper_only(silent=True)
        
        assert voice_mode.whisper_model is None
    
    @patch('sys.modules', {'sounddevice': MagicMock(), 'webrtcvad': MagicMock()})
    def test_initialize_audio(self, mock_sounddevice, mock_webrtcvad):
        """Test audio initialization with mocked sounddevice."""
        mock_sd = MagicMock()
        mock_stream = MagicMock()
        mock_sd.RawInputStream.return_value = mock_stream
        
        mock_vad_module = MagicMock()
        mock_vad = MagicMock()
        mock_vad_module.Vad.return_value = mock_vad
        
        with patch.dict('sys.modules', {'sounddevice': mock_sd, 'webrtcvad': mock_vad_module}):
            voice_mode = VoiceMode()
            voice_mode.initialize_audio()
            
            assert voice_mode.stream == mock_stream
            assert voice_mode.vad == mock_vad
            mock_stream.start.assert_called_once()
    
    @patch('sys.modules', {'sounddevice': MagicMock()})
    def test_initialize_audio_failure(self, mock_sounddevice):
        """Test audio initialization handles failure."""
        mock_sd = MagicMock()
        mock_sd.RawInputStream.side_effect = Exception("No audio device")
        
        with patch.dict('sys.modules', {'sounddevice': mock_sd}):
            voice_mode = VoiceMode()
            
            with pytest.raises(Exception, match="No audio device"):
                voice_mode.initialize_audio()
    
    def test_cleanup_audio(self):
        """Test audio cleanup."""
        mock_stream = MagicMock()
        
        voice_mode = VoiceMode()
        voice_mode.stream = mock_stream
        voice_mode.cleanup_audio()
        
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert voice_mode.stream is None
    
    def test_cleanup_audio_with_exception(self):
        """Test audio cleanup handles exceptions gracefully."""
        mock_stream = MagicMock()
        mock_stream.stop.side_effect = Exception("Stream error")
        
        voice_mode = VoiceMode()
        voice_mode.stream = mock_stream
        
        # Should not raise exception
        voice_mode.cleanup_audio()
        
        assert voice_mode.stream is None
    
    def test_cleanup_audio_no_stream(self):
        """Test cleanup when no stream exists."""
        voice_mode = VoiceMode()
        
        # Should not raise exception
        voice_mode.cleanup_audio()
        
        assert voice_mode.stream is None
    
    def test_listen_for_speech_no_audio_initialized(self):
        """Test listen_for_speech returns None when audio not initialized."""
        voice_mode = VoiceMode()
        
        audio, transcription = voice_mode.listen_for_speech()
        
        assert audio is None
        assert transcription is None
    
    @patch('sys.modules', {'sounddevice': MagicMock(), 'webrtcvad': MagicMock()})
    def test_listen_for_speech_with_speech_detected(self, mock_sounddevice, mock_webrtcvad):
        """Test listen_for_speech when speech is detected."""
        # Create speech pattern: 10 speech frames followed by 5 silence frames
        audio_frames, is_speech_flags = create_speech_silence_pattern(
            speech_frames=10,
            silence_frames=5
        )
        
        mock_stream = MockAudioStream(audio_frames)
        mock_vad = MockVAD(is_speech_flags)
        mock_whisper = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Hello world"
        mock_whisper.transcribe.return_value = ([mock_segment], None)
        
        voice_mode = VoiceMode()
        voice_mode.stream = mock_stream
        voice_mode.vad = mock_vad
        voice_mode.whisper_model = mock_whisper
        
        audio_data, transcription = voice_mode.listen_for_speech(
            timeout_seconds=5,
            silence_duration=0.1,  # Short silence duration for test
            silent=True
        )
        
        assert audio_data is not None
        assert transcription == "Hello world"
        assert isinstance(audio_data, bytes)
    
    @patch('sys.modules', {'sounddevice': MagicMock(), 'webrtcvad': MagicMock()})
    def test_listen_for_speech_timeout_no_speech(self, mock_sounddevice, mock_webrtcvad):
        """Test listen_for_speech timeout when no speech detected."""
        # All silence frames
        audio_frames, is_speech_flags = create_speech_silence_pattern(
            speech_frames=0,
            silence_frames=10
        )
        
        mock_stream = MockAudioStream(audio_frames)
        mock_vad = MockVAD(is_speech_flags)
        
        voice_mode = VoiceMode()
        voice_mode.stream = mock_stream
        voice_mode.vad = mock_vad
        
        audio_data, transcription = voice_mode.listen_for_speech(
            timeout_seconds=0.5,  # Short timeout
            silent=True,
            do_transcription=False
        )
        
        assert audio_data is None
        assert transcription is None
    
    @patch('sys.modules', {'sounddevice': MagicMock(), 'webrtcvad': MagicMock()})
    def test_listen_for_speech_without_transcription(self, mock_sounddevice, mock_webrtcvad):
        """Test listen_for_speech without transcription."""
        audio_frames, is_speech_flags = create_speech_silence_pattern(
            speech_frames=5,
            silence_frames=3
        )
        
        mock_stream = MockAudioStream(audio_frames)
        mock_vad = MockVAD(is_speech_flags)
        
        voice_mode = VoiceMode()
        voice_mode.stream = mock_stream
        voice_mode.vad = mock_vad
        
        audio_data, transcription = voice_mode.listen_for_speech(
            timeout_seconds=5,
            silence_duration=0.1,
            silent=True,
            do_transcription=False
        )
        
        assert audio_data is not None
        assert transcription is None
    
    @patch('samvaad.pipeline.retrieval.voice_mode.rag_query_pipeline')
    @patch('samvaad.pipeline.retrieval.voice_mode.clean_transcription')
    def test_process_query(self, mock_clean, mock_rag):
        """Test processing a query through RAG."""
        mock_clean.return_value = "What is AI?"
        mock_rag.return_value = {"answer": "AI is Artificial Intelligence."}
        
        voice_mode = VoiceMode()
        result = voice_mode.process_query("what is ai", "en")
        
        assert result['response'] == "AI is Artificial Intelligence."
        assert result['language'] == "en"
        assert 'query_time' in result
        mock_clean.assert_called_once_with("what is ai")
        mock_rag.assert_called_once()
    
    @patch('samvaad.pipeline.retrieval.voice_mode.clean_transcription')
    def test_process_query_empty_transcription(self, mock_clean):
        """Test processing empty transcription."""
        voice_mode = VoiceMode()
        result = voice_mode.process_query("", "en")
        
        assert "No speech detected" in result['response']
        assert result['language'] == "en"
    
    @patch('samvaad.pipeline.retrieval.voice_mode.rag_query_pipeline')
    @patch('samvaad.pipeline.retrieval.voice_mode.clean_transcription')
    def test_process_query_rag_failure(self, mock_clean, mock_rag):
        """Test processing query when RAG fails."""
        mock_clean.return_value = "test query"
        mock_rag.side_effect = Exception("RAG pipeline error")
        
        voice_mode = VoiceMode()
        result = voice_mode.process_query("test query", "en")
        
        assert "Processing failed" in result['response']
        assert "RAG pipeline error" in result['response']
    
    @patch('samvaad.pipeline.retrieval.voice_mode.play_audio_response')
    @patch('samvaad.pipeline.retrieval.voice_mode.strip_markdown')
    def test_speak_response(self, mock_strip, mock_play):
        """Test speaking a response."""
        mock_strip.return_value = "Plain text response"
        mock_tts = MagicMock()
        
        voice_mode = VoiceMode()
        voice_mode.tts_engine = mock_tts
        voice_mode.speak_response("**Bold** response", "en")
        
        mock_strip.assert_called_once_with("**Bold** response")
        mock_play.assert_called_once_with("Plain text response", "en", tts_engine=mock_tts)
    
    def test_handle_command_exit_commands(self):
        """Test handling exit commands."""
        voice_mode = VoiceMode()
        
        for cmd in ['stop', 'exit', 'quit', 'goodbye']:
            result = voice_mode.handle_command(cmd)
            assert result is False
    
    @patch('samvaad.pipeline.retrieval.voice_mode.play_audio_response')
    def test_handle_command_clear_history(self, mock_play):
        """Test handling clear history command."""
        voice_mode = VoiceMode()
        voice_mode.tts_engine = MagicMock()
        voice_mode.conversation_manager.add_user_message("Test message")
        
        result = voice_mode.handle_command("clear history")
        
        assert result is True
        # Should have system message about clearing
        assert any('cleared' in msg.content.lower() 
                  for msg in voice_mode.conversation_manager.messages)
    
    @patch('samvaad.pipeline.retrieval.voice_mode.play_audio_response')
    def test_handle_command_status(self, mock_play):
        """Test handling status command."""
        voice_mode = VoiceMode()
        voice_mode.tts_engine = MagicMock()
        voice_mode.conversation_manager.add_user_message("Message 1")
        voice_mode.conversation_manager.add_user_message("Message 2")
        
        result = voice_mode.handle_command("status")
        
        assert result is True
        mock_play.assert_called_once()
    
    def test_handle_command_unknown(self):
        """Test handling unknown command returns True."""
        voice_mode = VoiceMode()
        
        result = voice_mode.handle_command("unknown command")
        
        assert result is True
    
    @patch('samvaad.pipeline.retrieval.voice_mode.initialize_whisper_model')
    def test_run_without_whisper(self, mock_whisper):
        """Test run exits if Whisper not initialized."""
        mock_whisper.return_value = None
        
        voice_mode = VoiceMode()
        voice_mode.run()
        
        # Should exit early without Whisper
        assert voice_mode.whisper_model is None
