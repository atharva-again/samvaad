import os
import sys    
import argparse
import warnings
import torch
import threading
import time
# Defer heavy imports until needed
# from RealtimeSTT import AudioToTextRecorder
from backend.pipeline.retrieval.query import rag_query_pipeline

# Suppress warnings before any imports
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message='.*pkg_resources.*')
warnings.filterwarnings("ignore", message='.*deprecated.*')

# Also suppress ctranslate2 logging warnings
import logging
logging.getLogger('ctranslate2').setLevel(logging.ERROR)
logging.getLogger('faster_whisper').setLevel(logging.ERROR)


def voice_query_cli(language: str = "en", model: str = "gemini-2.5-flash"):
    """
    CLI function for voice queries using RealTimeSTT.
    Transcribes speech in real-time, then processes the full query through RAG when speech stops.
    """
    print("🎤 Starting voice query mode...")
    print("Speak your query. Real-time transcription will appear below.")
    print("Stop speaking to process the query and get an answer.")
    print("=" * 60)

    final_transcription = ""

    # Detect GPU availability for better performance
    try:
        use_gpu = torch.cuda.is_available()
        if use_gpu:
            device = "cuda"
            model_size = "tiny"  # Use tiny model for faster loading
            print("🔧 GPU detected.")
        else:
            device = "cpu"
            model_size = "tiny"  # Use tiny model on CPU
            print("🔧 Using CPU (GPU not available).")
    except Exception as e:
        print("⚠️  GPU detection failed, falling back to CPU: {}".format(e))
        use_gpu = False
        device = "cpu"
        model_size = "tiny"
    
    print("🔧 Using device: {} (Model: {})".format(device.upper(), model_size))
    
    # Initialize the recorder with GPU acceleration if available
    recorder_kwargs = {
        "model": model_size,
        "language": language,
        "enable_realtime_transcription": True,
        "realtime_processing_pause": 0.05,
        "post_speech_silence_duration": 5,  # Increased from 1.0 to 1.5 seconds for more patience
        "min_length_of_recording": 0.5,
        "pre_recording_buffer_duration": 0.1,
        "spinner": False,
        "level": 30,  # Less verbose logging
        "device": device
    }
    
    if use_gpu:
        recorder_kwargs["gpu_device_index"] = 0

    try:
        print("\n🎙️  Listening...")
        print("🔄 Initializing AudioToTextRecorder...")
        try:
            from RealtimeSTT import AudioToTextRecorder
        except Exception as import_error:
            print("❌ Failed to import RealTimeSTT: {}".format(import_error))
            return
        
        # Track recording state
        speech_detected = False
        recording_started_time = None
        
        def recording_start_callback():
            """Callback when recording actually starts."""
            print("🎙️  Ready! Start speaking now... (you have 10 seconds)", flush=True)
            time.sleep(0.1)  # Small delay to ensure message is displayed
            nonlocal recording_started_time
            recording_started_time = time.time()
        
        def realtime_callback(text):
            """Callback for real-time transcription updates."""
            nonlocal speech_detected
            if text.strip():  # If we have actual transcribed text
                speech_detected = True
            print("\r🔊 Real-time: {}".format(text), end="", flush=True)
        
        # Initialize the recorder with callbacks
        recorder_kwargs["on_recording_start"] = recording_start_callback
        recorder_kwargs["on_realtime_transcription_update"] = realtime_callback
        
        recorder = AudioToTextRecorder(**recorder_kwargs)
        print("✅ Recorder initialized successfully.")
        
        # Function to run recording in a separate thread
        def record_audio():
            nonlocal final_transcription
            try:
                with recorder:
                    final_transcription = recorder.text()
            except Exception as e:
                print("❌ Recording error: {}".format(e))
        
        # Start recording in a separate thread
        recording_thread = threading.Thread(target=record_audio)
        recording_thread.start()
        
        # Wait for recording to start
        while recording_started_time is None and recording_thread.is_alive():
            time.sleep(0.1)
        
        # Monitor for 10 seconds after recording starts
        if recording_started_time:
            timeout_time = recording_started_time + 10
            while time.time() < timeout_time and recording_thread.is_alive():
                if speech_detected:
                    break  # Speech detected, continue normally
                time.sleep(0.1)
            
            if not speech_detected and recording_thread.is_alive():
                print("\n❌ No speech detected within 10 seconds. Stopping recording...")
                # Note: We can't forcibly stop the recorder thread, but we can proceed without transcription
                recording_thread.join(timeout=1)  # Give it 1 second to finish
                return
        
        # Wait for recording to complete
        recording_thread.join()
        
        print("\n🛑 Recording stopped.")
        
    except KeyboardInterrupt:
        print("\n🛑 Voice query interrupted by user.")
        # The 'with' statement's exit logic should handle shutdown.
        return
    except Exception as e:
        print("❌ Error during recording: {}".format(e))
        import traceback
        traceback.print_exc()
        return
    
    # --- Processing happens AFTER the recorder is fully shut down by the 'with' block ---

    print("📝 Final query: {}".format(final_transcription))

    if final_transcription.strip():
        try:
            # Process through RAG pipeline
            print("🔄 Processing query through RAG pipeline...")
            result = rag_query_pipeline(final_transcription, model=model, language=language)

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
