from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.responses import JSONResponse
from typing import List
import asyncio
from RealtimeSTT import AudioToTextRecorder
from backend.pipeline.ingestion.ingestion import ingest_file_pipeline
from backend.pipeline.retrieval.query import rag_query_pipeline
from pydantic import BaseModel
import base64

app = FastAPI(title="Samvaad RAG Backend")

@app.get("/health")
def health_check():
	"""Health check endpoint to verify the server is running."""
	return JSONResponse(content={"status": "ok"})

class VoiceQuery(BaseModel):
    query: str
    language: str

class TTSRequest(BaseModel):
    text: str
    language: str = "en-us"

class TextQuery(BaseModel):
    query: str

# Ingest endpoint for uploading PDF or text files
@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
	"""
	Accept a PDF or text file upload, parse, chunk, embed, and store in the database.
	"""
	filename = file.filename
	content_type = file.content_type
	contents = await file.read()
	
	print(f"Processing file: {filename}")
	result = ingest_file_pipeline(filename, content_type, contents)
	print(f"Processed {result['num_chunks']} chunks, embedded {result['new_chunks_embedded']} new chunks.")
	
	return result

# Text query endpoint
@app.post("/query")
async def text_query(request: TextQuery):
    """
    Accept a text query and process through RAG pipeline.
    """
    print(f"Received query: {request.query}")
    try:
        result = rag_query_pipeline(request.query, model="gemini-2.5-flash")
        print("Query processed successfully")
        return result
    except Exception as e:
        print(f"Error in query endpoint: {e}")
        return {"error": str(e), "query": request.query}

# Voice query endpoint for RAG with language-aware generation
@app.post("/voice-query")
async def voice_query(request: VoiceQuery):
    """
    Accept a voice-transcribed query with detected language, process through RAG pipeline.
    """
    result = rag_query_pipeline(request.query, model="gemini-2.5-flash", language=request.language)
    return result

# TTS endpoint for voice responses
@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Generate audio from text using Kokoro TTS.
    """
    from kokoro_onnx import Kokoro
    import io
    import base64
    
    # Initialize Kokoro (cache it in future)
    kokoro = Kokoro("kokoro-v0_19.onnx", "voices.json")
    
    # Map language to voice
    voice = "en-us" if request.language.lower() == "english" else "hi-in"  # Basic mapping
    
    # Generate audio
    samples, sample_rate = kokoro.create(request.text, voice=voice, speed=1.0)
    
    # Convert to bytes (WAV)
    import wave
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes((samples * 32767).astype('int16').tobytes())
    
    buffer.seek(0)
    audio_base64 = base64.b64encode(buffer.getvalue()).decode()
    return {"audio_base64": audio_base64, "sample_rate": sample_rate}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# WebSocket endpoint for streaming ASR
@app.websocket("/ws/asr")
async def asr_websocket(websocket: WebSocket):
    await websocket.accept()
    
    # Queue for sending messages from callbacks (since callbacks are sync)
    message_queue = asyncio.Queue()
    
    def realtime_callback(text):
        asyncio.create_task(message_queue.put({"type": "realtime", "text": text, "language": recorder.language}))
    
    def final_callback(text):
        asyncio.create_task(message_queue.put({"type": "final", "text": text, "language": recorder.language}))
    
    # Initialize recorder with CPU-friendly settings
    recorder = AudioToTextRecorder(
        use_microphone=False,
        model="tiny",  # Small model for CPU
        language="",  # Auto-detect language
        enable_realtime_transcription=True,
        on_realtime_transcription_update=realtime_callback,
        on_transcription_finished=final_callback,
        realtime_model_type="tiny",
        realtime_processing_pause=0.1,  # Faster updates
        early_transcription_on_silence=0.5,  # Transcribe faster on silence
        allowed_latency_limit=50  # Prevent buffer overflow
    )
    
    try:
        while True:
            # Receive audio chunk from client
            data = await websocket.receive_bytes()
            recorder.feed_audio(data)
            
            # Send any pending messages
            while not message_queue.empty():
                msg = await message_queue.get()
                await websocket.send_json(msg)
                
    except Exception as e:
        print(f"ASR WebSocket error: {e}")
    finally:
        recorder.shutdown()
        await websocket.close()
