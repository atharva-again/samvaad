"""
Voice Mode for Samvaad
Provides end-to-end voice interaction capabilities with ASR, RAG processing, and TTS.
"""

from __future__ import annotations

import os
import sys
import time
import json
import wave
import contextlib
import warnings
import logging
import argparse
from collections import deque
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich import box

# Suppress ALSA environment variables globally
os.environ['ALSA_PCM_CARD'] = '0'
os.environ['ALSA_PCM_DEVICE'] = '0'
os.environ['ALSA_CARD'] = '0'
os.environ['ALSA_DEVICE'] = '0'
os.environ['ALSA_NO_ERROR_MSGS'] = '1'
os.environ['ALSA_LOG_LEVEL'] = '0'
os.environ['ALSA_DEBUG'] = '0'

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Suppress warnings before any imports
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*deprecated.*")

# Suppress Whisper and other library logging
logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("whisper").setLevel(logging.ERROR)
logging.getLogger("llama_cpp").setLevel(logging.ERROR)
logging.getLogger("llama").setLevel(logging.ERROR)
logging.getLogger().setLevel(logging.WARNING)


from samvaad.pipeline.retrieval.query import rag_query_pipeline
from samvaad.pipeline.generation.kokoro_tts import KokoroTTS  
from samvaad.utils.clean_markdown import strip_markdown
from samvaad.utils.gpu_utils import get_device

def play_audio_response(text: str = None, language: str | None = None, pcm: bytes = None, sample_rate: int = None, sample_width: int = None, channels: int = None, mode: str = 'both') -> Optional[Tuple[bytes, int, int, int, str]]:
    """Generate and/or play an audio response for the provided text."""
    if mode not in ['generate', 'play', 'both']:
        raise ValueError("mode must be 'generate', 'play', or 'both'")

    if mode in ['generate', 'both']:
        if not text or not text.strip():
            return None

        # Skip audio generation in CI environments
        if os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CONTINUOUS_INTEGRATION') == 'true':
            print("🔇 Skipping audio generation in CI environment")
            return None

        try:
            tts_engine = KokoroTTS()
            
            pcm, sample_rate, sample_width, channels = tts_engine.synthesize(
                text, language=language, speed=1.0
            )

            # Save audio to file
            os.makedirs("data/audio_responses", exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"data/audio_responses/response_kokoro_{timestamp}.wav"
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm)
            print(f"Audio response saved to: {filename}")

            if mode == 'generate':
                return pcm, sample_rate, sample_width, channels, filename
        except Exception as exc:
            print(f"⚠️ Failed to generate audio response: {exc}")
            return None

    if mode in ['play', 'both']:
        if pcm is None:
            return None

        # Skip audio playback in CI environments or if sounddevice not available
        if os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CONTINUOUS_INTEGRATION') == 'true':
            print("🔇 Skipping audio playback in CI environment")
            return None

        try:
            import sounddevice as sd
        except ImportError:
            print("⚠️ sounddevice is not installed; skipping audio playback.")
            return None

        try:
            audio_array = np.frombuffer(pcm, dtype=np.int16)
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)
            audio_float = audio_array.astype(np.float32) / 32768.0
            sd.play(audio_float, samplerate=sample_rate)
            sd.wait()
        except Exception as exc:
            print(f"⚠️ Failed to play audio response: {exc}")
            return None

    return None

def clean_transcription(text: str) -> str:
    """Clean up speech recognition transcription using Gemini."""
    if not text or not text.strip():
        return text

    if not hasattr(clean_transcription, "_client"):
        try:
            from google import genai
            from google.genai import types
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                print("⚠️ GEMINI_API_KEY not set")
                return text
            clean_transcription._client = genai.Client(api_key=api_key)
            clean_transcription._types = types
        except Exception as e:
            print(f"⚠️ Failed to initialize Gemini: {e}")
            return text

    try:
        prompt = f"""Clean and summarize this speech transcription 
                    for RAG retrieval.
                    Preserve intent and keywords. Correct typos and common mispronunciations (e.g., 'Ensopic' likely means 'Anthropic').
                    Single sentence, same language/style: {text}"""
        
        response = clean_transcription._client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=clean_transcription._types.GenerateContentConfig(
                temperature=0.1, max_output_tokens=256,
                thinking_config=clean_transcription._types.ThinkingConfig(thinking_budget=0)
            ),
        )
        cleaned = response.text.strip().strip('"').strip("'")
        return cleaned if cleaned else text
    except Exception as e:
        print(f"⚠️ Gemini cleaning failed: {e}")
        return text

def initialize_whisper_model(model_size: str = "small", device: str = "auto", silent: bool = False):
    """Initialize Faster Whisper model."""
    try:
        from faster_whisper import WhisperModel
        if device == "auto":
            device = "cuda" if get_device() == 'cuda' else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        if not silent:
            print(f"🔄 Loading Whisper ({model_size}) on {device}...")
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        if not silent:
            print("✅ Whisper ready.")
        return model
    except Exception as e:
        if not silent:
            print(f"❌ Whisper init failed: {e}")
        return None
    except Exception as e:
        if not silent:
            print(f"❌ Whisper init failed: {e}")
        return None

class ConversationMessage:
    """Represents a conversation message."""
    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None, metadata: Optional[Dict[str, Any]] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )

class ConversationManager:
    """Manages conversation history and state."""
    def __init__(self, max_history: int = 50, context_window: int = 10):
        self.messages: List[ConversationMessage] = []
        self.max_history = max_history
        self.context_window = context_window
        self.settings = {
            'language': 'en',
            'model': 'gemini-2.5-flash',
            'voice_activity_detection': True,
            'auto_save': True
        }
        self.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.is_active = False

    def start_conversation(self) -> None:
        self.is_active = True
        self.add_system_message("Conversation started.")

    def end_conversation(self) -> None:
        self.is_active = False
        self.add_system_message("Conversation ended.")

    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        message = ConversationMessage('user', content, metadata=metadata)
        self.messages.append(message)
        self._trim_history()

    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        message = ConversationMessage('assistant', content, metadata=metadata)
        self.messages.append(message)
        self._trim_history()

    def add_system_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        message = ConversationMessage('system', content, metadata=metadata)
        self.messages.append(message)
        self._trim_history()

    def get_context(self) -> str:
        recent = self.messages[-self.context_window:] if self.messages else []
        return "\n".join(f"{msg.role.title()}: {msg.content}" for msg in recent)

    def get_messages_for_prompt(self) -> List[Dict[str, str]]:
        recent = self.messages[-self.context_window:] if self.messages else []
        return [{'role': msg.role, 'content': msg.content} for msg in recent if msg.role in ['user', 'assistant', 'system']]

    def clear_history(self) -> None:
        self.messages = []
        self.add_system_message("History cleared.")

    def _trim_history(self) -> None:
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

class VoiceMode:
    """Continuous voice conversation mode."""

    def __init__(self, progress_callbacks=None):
        self.conversation_manager = ConversationManager()
        self.whisper_model = None
        self.stream = None
        self.vad = None
        self.running = False
        self.inactivity_timeout = 10
        self.progress_callbacks = progress_callbacks or {}
        self.sample_rate = 16000
        self.frame_duration_ms = 20

    def preload_models(self):
        """Preload ML models."""
        try:
            self.initialize_whisper_only(silent=True)
        except Exception as e:
            print(f"⚠️ Whisper preload failed: {e}")
        

    def initialize_whisper_only(self, silent: bool = False):
        """Initialize Whisper model."""
        self.whisper_model = initialize_whisper_model(model_size="small", device="auto", silent=silent)
        if not self.whisper_model and not silent:
            print("❌ Whisper init failed.")

    def initialize_audio(self):
        """Initialize audio input."""
        frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        with contextlib.redirect_stderr(open(os.devnull, 'w')):
            try:
                import sounddevice as sd
                import webrtcvad
                self.vad = webrtcvad.Vad(3)  # Most restrictive VAD for silence detection  
                self.stream = sd.RawInputStream(
                    samplerate=self.sample_rate,
                    blocksize=frame_size,
                    dtype='int16',
                    channels=1
                )
                self.stream.start()
            except Exception as e:
                print(f"❌ Audio init failed: {e}")
                raise

    def cleanup_audio(self):
        """Clean up audio resources."""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            finally:
                self.stream = None

    def listen_for_speech(self, timeout_seconds: int = 5, silent: bool = False, do_transcription: bool = True) -> Tuple[Union[str, bytes], str]:
        """Listen for speech and optionally transcribe it."""
        def is_frame_silent(frame_bytes, threshold=0.01):
            audio = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio**2))
            return rms < threshold
        
        if not silent:
            print("🎤 Listening for speech...")
        
        # Audio parameters
        rate = self.sample_rate
        frame_ms = self.frame_duration_ms
        frame_samples = int(rate * frame_ms / 1000)
        frame_bytes_size = frame_samples * 2  # 16-bit
        
        # Buffers
        pre_speech_buffer = deque(maxlen=25)  # 500ms buffer
        recorded_audio = []
        
        # Timing
        start_wait = time.time()
        max_wait_frames = int(timeout_seconds * 1000 / frame_ms)
        wait_frame_count = 0
        
        # Phase 1: Wait for speech onset
        speech_started = False
        while not speech_started:
            # Timeout check
            current_time = time.time()
            wait_frame_count += 1
            if (current_time - start_wait >= timeout_seconds) or (wait_frame_count >= max_wait_frames):
                if not silent:
                    print(f"⏰ No speech detected within {timeout_seconds}s")
                return ("", "") if do_transcription else (b"", "")
            
            # Capture audio frame
            try:
                data, _ = self.stream.read(frame_samples)
            except Exception as e:
                if not silent:
                    print(f"⚠️ Audio capture error: {e}")
                time.sleep(0.01)
                continue
            
            frame_data = bytes(data)
            
            # VAD check with RMS filter
            try:
                if self.vad.is_speech(frame_data, rate) and not is_frame_silent(frame_data, threshold=0.005):
                    # Speech detected, include buffer
                    recorded_audio.extend(pre_speech_buffer)
                    recorded_audio.append(frame_data)
                    speech_started = True
                    if not silent:
                        print(f"✓ Speech detected at {current_time - start_wait:.1f}s")
                else:
                    pre_speech_buffer.append(frame_data)
            except Exception as e:
                if not silent:
                    print(f"⚠️ VAD error: {e}")
                continue
        
        # Phase 2: Record until silence
        silence_limit = 2.0
        last_speech = time.time()
        recording_start = time.time()
        max_recording = 180
        
        while True:
            # Max duration check
            if time.time() - recording_start > max_recording:
                if not silent:
                    print("⚠️ Recording limit reached")
                break
            
            # Capture frame
            try:
                data, _ = self.stream.read(frame_samples)
            except Exception as e:
                if not silent:
                    print(f"⚠️ Audio capture error: {e}")
                time.sleep(0.01)
                continue
            
            frame_data = bytes(data)
            recorded_audio.append(frame_data)
            
            # VAD check
            try:
                speech_detected = self.vad.is_speech(frame_data, rate) and not is_frame_silent(frame_data, threshold=0.005)
                if speech_detected:
                    last_speech = time.time()
                else:
                    if time.time() - last_speech > silence_limit:
                        if not silent:
                            print(f"🔇 Silence detected after {silence_limit}s")
                        break
            except Exception as e:
                if not silent:
                    print(f"⚠️ VAD error: {e}")
                continue
        
        # Phase 3: Transcribe if needed
        if not recorded_audio:
            return ("", "") if do_transcription else (b"", "")
        
        combined_audio = b"".join(recorded_audio)
        
        if not do_transcription:
            return combined_audio, ""
        
        # Prepare for Whisper
        audio_float = np.frombuffer(combined_audio, dtype=np.int16).astype(np.float32) / 32768.0
        
        try:
            result = self.whisper_model.transcribe(audio_float, language=None)
            text = " ".join(seg.text for seg in result[0]).strip()
            lang = result[1].language
            return text, lang
        except Exception as e:
            if not silent:
                print(f"⚠️ Transcription error: {e}")
            return "", ""

    def process_query(self, transcription: str, detected_language: str) -> Dict[str, Any]:
        """Process transcription through RAG."""
        if not transcription.strip():
            return {"response": "No speech detected.", "language": detected_language}

        cleaned_query = clean_transcription(transcription)
        self.conversation_manager.add_user_message(cleaned_query, {
            'raw_transcription': transcription, 'detected_language': detected_language
        })

        try:
            import time
            start_time = time.time()
            result = rag_query_pipeline(
                query_text=cleaned_query,
                conversation_manager=self.conversation_manager,
                model="gemini-2.5-flash"
            )
            query_time = time.time() - start_time
            response = result.get("answer", "No response generated.")
            self.conversation_manager.add_assistant_message(response)
            return {"response": response, "language": detected_language, "query_time": query_time}
        except Exception as e:
            error_msg = f"Processing failed: {e}"
            print(f"⚠️ {error_msg}")
            self.conversation_manager.add_assistant_message(error_msg)
            return {"response": error_msg, "language": detected_language}

    def speak_response(self, text: str, language: str):
        """Speak the response."""
        plain_text = strip_markdown(text)
        play_audio_response(plain_text, language)

    def handle_command(self, transcription: str) -> bool:
        """Handle voice commands."""
        cmd = transcription.lower().strip()
        if cmd in ['stop', 'exit', 'quit', 'goodbye']:
            print("🛑 Ending conversation.")
            return False
        elif cmd in ['clear history', 'reset']:
            self.conversation_manager.clear_history()
            self.speak_response("Conversation history cleared.", "en")
        elif cmd == 'status':
            status = f"Active conversation with {len(self.conversation_manager.messages)} messages."
            print(f"📊 {status}")
            self.speak_response(status, "en")
        return True

    def run(self):
        """Run the continuous voice conversation loop."""
        self.preload_models()
        if not self.whisper_model:
            print("❌ Cannot start voice mode without Whisper model.")
            return

        # Add console instance for styled output
        console = Console()

        self.conversation_manager.start_conversation()

        try:
            self.initialize_audio()
            
            # Display voice mode instructions once at start
            voice_panel = Panel(
                "Voice Query Mode Active. Ready to Listen.\n\n"
                "• Speak your question naturally\n"
                "• Languages Supported: English, Hindi (preview)\n"
                "• The system will wait for 5 seconds for you to speak.\n"
                "• Recording stops after a brief silence\n"
                "• Press Ctrl+C to cancel and return to text mode",
                title="Voice Conversation Started",
                border_style="green",
                box=box.ROUNDED
            )
            console.print(voice_panel)
            
            self.running = True
            last_activity = time.time()

            while self.running:
                # Call listening progress callback
                if 'listening' in self.progress_callbacks:
                    progress = self.progress_callbacks['listening']()
                    with progress:
                        task = progress.add_task("Listening for speech...", total=None)
                        audio_data, _ = self.listen_for_speech(timeout_seconds=5, silent=True, do_transcription=False)
                        progress.update(task, completed=True, visible=False)
                else:
                    audio_data, _ = self.listen_for_speech(timeout_seconds=5, silent=True, do_transcription=False)
                
                if audio_data:
                    # Transcribe the audio
                    if 'transcribing' in self.progress_callbacks:
                        progress = self.progress_callbacks['transcribing']()
                        with progress:
                            task = progress.add_task("Transcribing...", total=None)
                            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                            try:
                                segments, info = self.whisper_model.transcribe(audio_np, language=None)
                                transcription = " ".join(segment.text for segment in segments).strip()
                                detected_language = info.language
                                progress.update(task, completed=True, visible=False)
                            except Exception as e:
                                progress.update(task, completed=True, visible=False)
                                print(f"⚠️ Transcription failed: {e}")
                                transcription = ""
                                detected_language = ""
                    else:
                        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                        try:
                            segments, info = self.whisper_model.transcribe(audio_np, language=None)
                            transcription = " ".join(segment.text for segment in segments).strip()
                            detected_language = info.language
                        except Exception as e:
                            print(f"⚠️ Transcription failed: {e}")
                            transcription = ""
                            detected_language = ""
                    
                    if transcription:
                        # Styled output to match CLI prompt aesthetic
                        console.print(f"[cyan]❯[/cyan] {transcription}")
                        
                        if not self.handle_command(transcription):
                            break
                        
                        # Call processing progress callback
                        if 'processing' in self.progress_callbacks:
                            progress = self.progress_callbacks['processing']()
                            with progress:
                                task = progress.add_task("Processing query...", total=None)
                                result = self.process_query(transcription, detected_language)
                                progress.update(task, completed=True, visible=False)
                        else:
                            result = self.process_query(transcription, detected_language)
                        
                        response = result.get("response", "No response generated.")
                        
                        # Use response callback if available, otherwise print directly
                        if 'response' in self.progress_callbacks:
                            self.progress_callbacks['response'](response, result.get('query_time'))
                        else:
                            print(f"Response: {response}")
                            if 'query_time' in result:
                                print(f"⏱️  Response generated in {result['query_time']:.2f}s")
                        
                        # Call speaking progress callback
                        if 'speaking' in self.progress_callbacks:
                            progress = self.progress_callbacks['speaking']()
                            with progress:
                                task = progress.add_task("Generating speech...", total=None)
                                plain_text = strip_markdown(response)
                                result = play_audio_response(plain_text, detected_language, mode='generate')
                                if result:
                                    pcm, sample_rate, sample_width, channels, filename = result
                                    progress.update(task, description="Speaking..")
                                    play_audio_response(pcm=pcm, sample_rate=sample_rate, sample_width=sample_width, channels=channels, mode='play')
                                progress.update(task, completed=True, visible=False)
                        else:
                            self.speak_response(response, detected_language)
                        
                        last_activity = time.time()
                    else:
                        # No speech detected within the listen timeout - treat as inactivity and end
                        print("⏰ Inactivity timeout. Ending conversation.")
                        break

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user.")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.cleanup_audio()
            self.conversation_manager.end_conversation()
            

def voice_query_cli(model: str = "gemini-2.5-flash"):
    """
    CLI function for voice queries using continuous voice mode.
    This is a backward compatibility wrapper for single voice queries.
    """
    voice_mode = VoiceMode()
    voice_mode.run()


def main():
    """Main entry point for voice mode."""
    parser = argparse.ArgumentParser(description="Samvaad Voice Mode")
    parser.add_argument("--model", default="gemini-2.5-flash", help="LLM model")
    args = parser.parse_args()

    voice_mode = VoiceMode()
    voice_mode.run()

if __name__ == "__main__":
    main()
