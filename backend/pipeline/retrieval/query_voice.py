import os
import sys    
import argparse
import warnings
import torch
import threading
import time
import json
# Defer heavy imports until needed
# from vosk import Model, KaldiRecognizer
# import pyaudio
from backend.pipeline.retrieval.query import rag_query_pipeline

# Suppress warnings before any imports
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message='.*pkg_resources.*')
warnings.filterwarnings("ignore", message='.*deprecated.*')

# Also suppress vosk logging warnings
import logging
logging.getLogger('vosk').setLevel(logging.ERROR)


def clean_transcription(text):
    """
    Clean up speech recognition transcription using a lightweight language model.
    Removes repetitions, filler words, noise, and improves readability.
    
    Args:
        text (str): Raw transcription text
        
    Returns:
        str: Cleaned transcription
    """
    if not text or not text.strip():
        return text
    
    # Use a global cache for the model to avoid reloading
    if not hasattr(clean_transcription, '_model'):
        try:
            from transformers import pipeline
            # Detect GPU availability
            device = 0 if torch.cuda.is_available() else -1
            print(f"🔄 Loading lightweight text cleaning model on {'GPU' if device == 0 else 'CPU'}...")
            clean_transcription._model = pipeline(
                "text2text-generation",
                model="google/flan-t5-small",
                device=device,
                max_length=512
            )
            print("✅ Text cleaning model loaded.")
        except Exception as e:
            print(f"⚠️ Failed to load text cleaning model: {e}")
            print("🔄 Returning original text...")
            return text
    
    try:
        # Prepare prompt for the model
        prompt = f"Clean this speech transcription by removing repetitions, filler words, noise, and fixing errors. Keep the meaning intact: {text}"
        
        # Generate cleaned text
        result = clean_transcription._model(prompt, max_length=256, num_beams=2, early_stopping=True)
        cleaned = result[0]['generated_text'].strip()
        
        # Post-process: remove any model artifacts
        cleaned = cleaned.replace("Cleaned transcription: ", "").replace("Clean transcription: ", "")
        
        return cleaned if cleaned else text
    
    except Exception as e:
        print(f"⚠️ Error during model-based cleaning: {e}")
        print("🔄 Returning original text...")
        return text





def download_vosk_model(model_name="vosk-model-small-en-in-0.4"):
    """Download Vosk model if not already present."""
    import urllib.request
    import zipfile
    
    model_path = os.path.join(os.path.dirname(__file__), model_name)
    if os.path.exists(model_path):
        print("✅ Vosk model already downloaded.")
        return model_path
    
    print("🔄 Downloading Vosk model (this may take a moment on first run)...")
    
    # Create models directory if it doesn't exist
    models_dir = os.path.dirname(__file__)
    os.makedirs(models_dir, exist_ok=True)
    
    # Download the model
    url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
    zip_path = os.path.join(models_dir, f"{model_name}.zip")
    
    try:
        urllib.request.urlretrieve(url, zip_path)
        
        # Extract the model
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(models_dir)
        
        # Clean up zip file
        os.remove(zip_path)
        
        print("✅ Vosk model downloaded successfully.")
        return model_path
    except Exception as e:
        print(f"❌ Failed to download Vosk model: {e}")
        # Fallback to older model if latest fails
        print("🔄 Falling back to vosk-model-en-us-0.22...")
        return download_vosk_model("vosk-model-en-us-0.22")


def voice_query_cli(language: str = "en", model: str = "gemini-2.5-flash"):
    """
    CLI function for voice queries using Vosk.
    Records audio, transcribes speech, then processes the query through RAG.
    """
    print("🎤 Starting voice query mode with Indian English support...")
    print("You have 10 seconds to start speaking after recording begins.")
    print("Recording will stop automatically after 3 seconds of silence.")
    print("=" * 60)

    final_transcription = ""
    try:
        use_gpu = torch.cuda.is_available()
        if use_gpu:
            print("🔧 GPU detected (not used for Vosk).")
        else:
            print("🔧 Using CPU.")
    except Exception as e:
        print("⚠️  GPU detection failed: {}".format(e))
    
    # Preload the text cleaning model to avoid delay later
    print("🔄 Preloading text cleaning model...")
    _ = clean_transcription("test")  # This loads the model
    print("✅ Text cleaning model ready.")
    
    # Initialize audio variables
    audio = None
    stream = None
    
    try:
        print("\n🎙️  Setting up voice recognition...")
        
        # Import Vosk dependencies
        try:
            from vosk import Model, KaldiRecognizer
            import pyaudio
        except Exception as import_error:
            print("❌ Failed to import Vosk/PyAudio: {}".format(import_error))
            print("Please install vosk and pyaudio: pip install vosk pyaudio")
            return
        
        # Download and load Vosk model
        model_path = download_vosk_model()
        if not model_path:
            return
            
        try:
            vosk_model = Model(model_path)
            recognizer = KaldiRecognizer(vosk_model, 16000)
        except Exception as model_error:
            print("❌ Failed to load Vosk model: {}".format(model_error))
            return
        
        # Setup PyAudio
        try:
            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16,
                              channels=1,
                              rate=16000,
                              input=True,
                              frames_per_buffer=8192)
        except Exception as audio_error:
            print("❌ Failed to initialize audio stream: {}".format(audio_error))
            print("Make sure you have a microphone connected and permissions are granted.")
            return
        
        print("✅ Voice recognition ready.")
        print("🎙️  Start speaking now... (you have 10 seconds to begin speaking)")
        print("Recording will stop automatically after 3 seconds of silence.")

        # Track recording state
        speech_detected = False
        transcription_parts = []
        headway_expired = False
        silence_start_time = None

        # Start the timer only after the user is prompted to speak
        recording_start_time = time.time()

        while True:
            data = stream.read(4096, exception_on_overflow=False)
            
            # Check if headway period has expired (10 seconds)
            if not headway_expired and time.time() - recording_start_time > 10.0:
                headway_expired = True
                if not speech_detected:
                    print("\n🛑 No speech detected within 10 seconds. Recording stopped.")
                    break
            
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                
                if text:
                    speech_detected = True
                    silence_start_time = None  # Reset silence timer when speech is detected
                    transcription_parts.append(text)
                    final_transcription = " ".join(transcription_parts).strip()
                    print("\r🔊 {}".format(final_transcription), end="", flush=True)
                else:
                    # No speech in this chunk
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif speech_detected and time.time() - silence_start_time > 3.0:
                        # 3 seconds of silence after speech was detected
                        print("\n🛑 Recording stopped (3 seconds of silence detected).")
                        break
            else:
                # Partial results for real-time feedback
                partial = json.loads(recognizer.PartialResult())
                partial_text = partial.get("partial", "").strip()
                if partial_text:
                    # Combine previous transcription with current partial
                    current_display = final_transcription + (" " + partial_text if final_transcription else partial_text)
                    print("\r🔊 {}...".format(current_display), end="", flush=True)
                    silence_start_time = None  # Reset silence timer during partial speech
            
            # Safety timeout: stop after 60 seconds total
            if time.time() - recording_start_time > 60.0:
                print("\n🛑 Recording stopped (60 second safety timeout).")
                break
        
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
            result = rag_query_pipeline(cleaned_transcription, model=model, language=language)

            # Display results
            print("\n🤖 ANSWER: {}".format(result['answer']))

            if result['success'] and result['sources']:
                print("\n📚 SOURCES ({} chunks retrieved):".format(result['retrieval_count']))
                for i, source in enumerate(result['sources'], 1):
                    distance = source.get('distance')
                    similarity = " (Similarity: {:.3f})".format(1 - distance) if distance is not None else ""
                    print("\n{}. {}{}".format(i, source['filename'], similarity))
                    preview = source.get('content_preview', '')[:200]
                    print("   Preview: {}...".format(preview))
        except Exception as e:
            print("❌ Error during RAG processing: {}".format(e))
    else:
        print("❌ No speech detected. Please try again.")
    
    print("🎤 Voice query session ended.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice Query CLI")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model (default: gemini-2.5-flash)")
    args = parser.parse_args()

    voice_query_cli(language=args.language, model=args.model)
