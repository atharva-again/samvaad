import os
import argparse
import warnings
import torch
import time
import numpy as np
from dotenv import load_dotenv
import re 

load_dotenv()

# Defer heavy imports until needed
# from faster_whisper import WhisperModel
# import webrtcvad
# import pyaudio
from backend.pipeline.retrieval.query import rag_query_pipeline
from backend.pipeline.generation.piper_tts import PiperTTS
from backend.pipeline.generation.kokoro_tts import KokoroTTS

# Suppress warnings before any imports
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*deprecated.*")

# Also suppress Whisper logging warnings
import logging

logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("whisper").setLevel(logging.ERROR)


_piper_tts: PiperTTS | None = None
_kokoro_tts: KokoroTTS | None = None


def get_piper_tts() -> PiperTTS:
    global _piper_tts
    if _piper_tts is None:
        try:
            _piper_tts = PiperTTS()
            print("🔊 Piper TTS engine initialised.")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise Piper TTS: {exc}") from exc
    return _piper_tts


def get_kokoro_tts() -> KokoroTTS:
    global _kokoro_tts
    if _kokoro_tts is None:
        try:
            _kokoro_tts = KokoroTTS()
            print("🔊 Kokoro TTS engine initialised.")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise Kokoro TTS: {exc}") from exc
    return _kokoro_tts


def play_audio_response(text: str, language: str | None, engine: str = "piper") -> None:
    """Generate and play an audio response for the provided text."""

    if not text or not text.strip():
        return

    # Skip audio playback in CI environments (GitHub Actions, etc.)
    if os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CONTINUOUS_INTEGRATION') == 'true':
        print("🔇 Skipping audio playback in CI environment")
        return

    try:
        import pygame
    except ImportError:
        print("⚠️ pygame is not installed; skipping audio playback.")
        return

    try:
        if engine.lower() == "kokoro":
            tts_engine = get_kokoro_tts()
        else:
            tts_engine = get_piper_tts()
    except Exception as exc:
        print(f"⚠️ TTS engine '{engine}' unavailable: {exc}")
        return

    mixer_initialised = False

    try:
        print("🔈 Generating spoken response...")
        if engine.lower() == "kokoro":
            pcm, sample_rate, sample_width, channels = tts_engine.synthesize(
                text,
                language=language,
                speed=1.0,
            )
        else:
            pcm, sample_rate, sample_width, channels = tts_engine.synthesize(
                text,
                language=language,
            )

        # Save audio to file
        import wave
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"data/audio_responses/response_{engine}_{timestamp}.wav"
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm)
        print(f"💾 Audio response saved to: {filename}")

        pygame.mixer.init(
            frequency=sample_rate,
            size=-(sample_width * 8),
            channels=channels,
        )
        mixer_initialised = True

        sound = pygame.mixer.Sound(buffer=pcm)
        channel = sound.play()
        while channel.get_busy():
            pygame.time.wait(100)

    except Exception as exc:
        print(f"⚠️ Failed to play audio response: {exc}")
    finally:
        if mixer_initialised:
            try:
                pygame.mixer.quit()
            except Exception:
                pass


def clean_transcription(text):
    """
    Clean up speech recognition transcription using Gemini-2.5-flash-lite.
    Removes repetitions, filler words, noise, and improves readability.

    Args:
        text (str): Raw transcription text

    Returns:
        str: Cleaned transcription
    """
    if not text or not text.strip():
        return text

    # Use a global cache for the client to avoid reinitializing
    if not hasattr(clean_transcription, "_client"):
        try:
            from google import genai
            from google.genai import types

            # Get API key from environment
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                print("⚠️ GEMINI_API_KEY environment variable not set")
                print("🔄 Returning original text...")
                return text

            print("🔄 Initializing Gemini client for text cleaning...")
            clean_transcription._client = genai.Client(api_key=api_key)
            clean_transcription._types = types  # Store types module globally
            print("✅ Gemini client ready for text cleaning.")
        except Exception as e:
            print(f"⚠️ Failed to initialize Gemini client: {e}")
            print("🔄 Returning original text...")
            return text

    try:
        # Prepare prompt for Gemini
        prompt = f"""This text is a user query transcribed from speech recognition. 
        I need to use it to retrieve relevant documents from my RAG system. 
        Please clean and summarize it, while preserving original intent and keywords. 
        Only add additional context and words if necessary. 
        In no case should you use your knowledge to answer any question in the text. 
        Return in the same language and style, preserve transliteration, and only a single sentence: \n\n{text}"""

        # Generate cleaned text using Gemini
        response = clean_transcription._client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=clean_transcription._types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent cleaning
                max_output_tokens=256,  # Limit response length
                thinking_config=clean_transcription._types.ThinkingConfig(
                    thinking_budget=0
                ),  # Disable thinking for speed
            ),
        )

        cleaned = response.text.strip()

        # Post-process: remove any model artifacts or extra formatting
        cleaned = cleaned.strip('"').strip("'")

        return cleaned if cleaned else text

    except Exception as e:
        print(f"⚠️ Error during Gemini-based cleaning: {e}")
        print("🔄 Returning original text...")
        return text


def strip_markdown(text: str) -> str:
    """
    Strip markdown formatting from text for TTS compatibility.
    Removes headers, bold, italic, code blocks, links, lists, etc.
    while preserving the readable content.

    Args:
        text (str): Text with markdown formatting

    Returns:
        str: Plain text without markdown formatting
    """
    if not text:
        return text

    # Remove code blocks (```code```)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Remove inline code (`code`)
    text = re.sub(r'`([^`]*)`', r'\1', text)

    # Remove headers (# ## ###)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

    # Remove bold (**text** or __text__)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)

    # Remove italic (*text* or _text_)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # Remove strikethrough (~~text~~)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)

    # Remove links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove images ![alt](url) -> alt
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)

    # Remove blockquotes (> text)
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # Convert unordered lists (- item, * item, + item) to plain text
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)

    # Convert ordered lists (1. item, 2. item) to plain text
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove horizontal rules (--- or ***)
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)

    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines
    text = text.strip()

    return text


def initialize_whisper_model(model_size="base", device="auto", compute_type="default"):
    """Initialize Faster Whisper model for speech recognition."""
    try:
        from faster_whisper import WhisperModel

        # Auto-detect device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"

        print(f"🔄 Loading Whisper model ({model_size}) on {device}...")
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print("✅ Whisper model loaded successfully.")
        return model
    except Exception as e:
        print(f"❌ Failed to load Whisper model: {e}")
        return None


def voice_query_cli(model: str = "gemini-2.5-flash", tts_engine: str = "piper"):
    """
    CLI function for voice queries using Whisper ASR.
    Records audio until silence is detected, then transcribes the complete audio.
    """

    final_transcription = ""
    detected_language = None

    # Initialize audio variables
    audio = None
    stream = None
    vad = None

    try:
        print("\n🎙️  Setting up voice recognition...")

        # Import Whisper and VAD dependencies
        try:
            from faster_whisper import WhisperModel
            import webrtcvad
            import pyaudio
        except Exception as import_error:
            print("❌ Failed to import required packages: {}".format(import_error))
            print("Please install: pip install faster-whisper webrtcvad pyaudio")
            return

        # Initialize Whisper model
        whisper_model = initialize_whisper_model(
            model_size="small",  # Good balance of speed and accuracy
            device="auto",
        )
        if not whisper_model:
            return

        # Initialize VAD for speech detection
        vad = webrtcvad.Vad(3)  # Aggressiveness level 2 (0-3, higher = more aggressive)

        # Setup PyAudio
        try:
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=320,
            )  # 20ms frames for VAD
        except Exception as audio_error:
            print("❌ Failed to initialize audio stream: {}".format(audio_error))
            print(
                "Make sure you have a microphone connected and permissions are granted."
            )
            return

        print("✅ Voice recognition ready.")
        print("🎙️  Start speaking now... (you have 10 seconds to begin speaking)")
        print("Recording will stop automatically after 2 seconds of silence.")
        print("*" * 60)

        # Audio processing variables
        audio_frames = []  # Store all audio frames
        speech_detected = False
        silence_frames = 0
        headway_expired = False

        # Timing variables
        recording_start_time = time.time()

        while True:
            # Read 20ms of audio (320 bytes at 16kHz, 16-bit)
            data = stream.read(320, exception_on_overflow=False)
            audio_frames.append(data)

            # Check if headway period has expired (10 seconds)
            if not headway_expired and time.time() - recording_start_time > 10.0:
                headway_expired = True
                if not speech_detected:
                    print(
                        "\n🛑 No speech detected within 10 seconds. Recording stopped."
                    )
                    break

            # Convert to bytes for VAD (expects 16-bit PCM)
            is_speech = vad.is_speech(data, 16000)

            if is_speech:
                speech_detected = True
                silence_frames = 0
            else:
                if speech_detected:
                    silence_frames += 1
                    # If we've had 2 seconds of silence (100 frames * 20ms = 2 seconds)
                    if silence_frames > 100:
                        print("\n� Recording stopped (2 seconds of silence detected).")
                        break

            # Safety timeout: stop after 60 seconds total
            if time.time() - recording_start_time > 60.0:
                print("\n🛑 Recording stopped (60 second safety timeout).")
                break

        # Transcribe the complete recorded audio
        if speech_detected and audio_frames:
            print("🔄 Transcribing audio...")

            # Convert audio frames to numpy array
            audio_data = b"".join(audio_frames)
            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            )

            try:
                segments, info = whisper_model.transcribe(
                    audio_np,
                    task="transcribe",
                    vad_filter=True,
                    vad_parameters=dict(threshold=0.5, min_speech_duration_ms=250),
                    initial_prompt=None,
                )

                # Print detected language for debugging
                print(
                    f"🔍 Detected language: {info.language} (confidence: {info.language_probability:.2f})"
                )
                detected_language = info.language

                # Collect all transcribed text
                for segment in segments:
                    final_transcription += segment.text

                final_transcription = final_transcription.strip()

                if final_transcription:
                    print("✅ Transcription complete.")
                else:
                    print("⚠️ No speech detected in transcription.")

            except Exception as transcribe_error:
                print(f"❌ Transcription error: {transcribe_error}")
                return

        # Cleanup audio resources
        try:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        except:
            pass  # Ignore cleanup errors

    except KeyboardInterrupt:
        print("\n🛑 Voice query interrupted by user.")
        # Cleanup audio resources
        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except:
                pass
        if audio:
            try:
                audio.terminate()
            except:
                pass
        return
    except Exception as e:
        print("❌ Error during recording: {}".format(e))
        import traceback

        traceback.print_exc()
        # Cleanup audio resources
        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except:
                pass
        if audio:
            try:
                audio.terminate()
            except:
                pass
        return

    # --- Processing happens AFTER recording is complete ---

    # Clean up the transcription
    cleaned_transcription = clean_transcription(final_transcription)

    print("\n📝 Raw transcription: {}".format(final_transcription))
    if cleaned_transcription != final_transcription:
        print("📝 Cleaned query: {}".format(cleaned_transcription))

    if cleaned_transcription.strip():
        try:
            # Process through RAG pipeline
            print("🔄 Processing query through RAG pipeline...")
            result = rag_query_pipeline(cleaned_transcription, model=model)

            # Display results (strip markdown for clean terminal display)
            clean_answer = strip_markdown(result["answer"])
            print("\n🤖 ANSWER: {}".format(clean_answer))

            # Play audio response using detected language or fallback to English
            # Strip markdown formatting for better TTS pronunciation
            tts_text = strip_markdown(result.get("answer", ""))
            response_language = result.get("language") or detected_language or "en"
            play_audio_response(tts_text, response_language, engine=tts_engine)

            if result["success"] and result["sources"]:
                print(
                    "\n📚 SOURCES ({} chunks retrieved):".format(
                        result["retrieval_count"]
                    )
                )
                for i, source in enumerate(result["sources"], 1):
                    distance = source.get("distance")
                    similarity = (
                        " (Similarity: {:.3f})".format(1 - distance)
                        if distance is not None
                        else ""
                    )
                    print("\n{}. {}{}".format(i, source["filename"], similarity))
                    preview = source.get("content_preview", "")[:200]
                    print("   Preview: {}...".format(preview))
        except Exception as e:
            print("❌ Error during RAG processing: {}".format(e))
    else:
        print("❌ No speech detected. Please try again.")

    print("🎤 Voice query session ended.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice Query CLI")
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Gemini model (default: gemini-2.5-flash)",
    )
    parser.add_argument(
        "--tts-engine",
        choices=["piper", "kokoro"],
        help="TTS engine to use",
    )
    parser.add_argument(
        "-k", "--kokoro",
        action="store_true",
        help="Use Kokoro TTS engine",
    )
    parser.add_argument(
        "-p", "--piper",
        action="store_true",
        help="Use Piper TTS engine",
    )
    args = parser.parse_args()

    if args.kokoro:
        tts_engine = "kokoro"
    elif args.piper:
        tts_engine = "piper"
    else:
        tts_engine = args.tts_engine or "piper"

    voice_query_cli(model=args.model, tts_engine=tts_engine)

    # print(clean_transcription("Um, can you tell me, like, the summary of the anthropic threat report and what it says about AI risks?"))
