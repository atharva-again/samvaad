import asyncio
import base64
import os
import shutil
import tempfile
import uuid
import time
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pipecat.services.deepgram.tts import DeepgramTTSService
from pydantic import BaseModel
import httpx

from samvaad.interfaces.voice_agent import create_daily_room, start_voice_agent
from samvaad.pipeline.ingestion.ingestion import ingest_file_pipeline
from samvaad.pipeline.retrieval.query import rag_query_pipeline
from samvaad.utils.clean_markdown import strip_markdown
from samvaad.api.deps import get_current_user
from samvaad.db.models import User

load_dotenv()

from samvaad.api.routers import files

app = FastAPI(title="Samvaad RAG Backend")

app.include_router(files.router)

# CORS configuration - support both local and production frontend URLs
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# Add production frontend URL if configured
if frontend_url and frontend_url not in cors_origins:
    cors_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory session storage (use database for production)
sessions: Dict[str, Dict] = {}

def synthesize_audio(text: str, model="aura-2-asteria-en"):
    """
    Synthesize text to audio using Deepgram API via HTTP request.
    Returns: (audio_bytes, sample_rate)
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY environment variable not set")

    url = f"https://api.deepgram.com/v1/speak?model={model}&encoding=mp3"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    payload = {"text": text}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.content, 24000  # MP3 default sample rate
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Deepgram API error: {e.response.text}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to synthesize audio: {e}") from e


@app.get("/health")
def health_check():
    """Health check endpoint to verify the server is running."""
    return JSONResponse(content={"status": "ok"})


class TextMessageRequest(BaseModel):
    message: str
    session_id: str = "default"
    persona: str = "default"
    strict_mode: bool = False


class VoiceModeRequest(BaseModel):
    session_id: str = "default"
    enable_tts: bool = True
    persona: str = "default"
    strict_mode: bool = False


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


# Ingest endpoint for uploading various document files
@app.post("/ingest")
def ingest_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Accept various document file uploads and process them into the RAG system.
    Supported formats: PDF, DOCX, XLSX, PPTX, HTML, XHTML, CSV, TXT, MD,
    PNG, JPEG, TIFF, BMP, WEBP, WebVTT, WAV, MP3, and more.
    """
    filename = file.filename
    content_type = file.content_type
    contents = file.file.read()

    print(f"Processing file: {filename} for user {current_user.id}")
    # Pass user_id to ingestion pipeline
    result = ingest_file_pipeline(filename, content_type, contents, user_id=current_user.id)
    print(
        f"Processed {result['num_chunks']} chunks, embedded {result['new_chunks_embedded']} new chunks."
    )

    return result


# Text mode endpoint for handling text conversations
@app.post("/text-mode")
async def text_mode(
    request: TextMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Handle text messages in conversation mode with session management.
    """
    session_id = request.session_id
    # Use user-specific session keys if needed, for now simplistic
    if session_id not in sessions:
        sessions[session_id] = {"messages": []}

    # Add user message to session
    sessions[session_id]["messages"].append(
        {"role": "user", "content": request.message}
    )

    # Build history string from previous messages (excluding current user msg)
    history_msgs = sessions[session_id]["messages"][:-1]
    history_str = ""
    for msg in history_msgs:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_str += f"{role}: {msg['content']}\n"

    try:
        # Process through RAG pipeline, passing user_id for filtering
        result = rag_query_pipeline(
            request.message, 
            model="llama-3.3-70b-versatile",
            user_id=current_user.id,
            persona=request.persona,
            strict_mode=request.strict_mode,
            history_str=history_str
        )
        response = result.get("answer", "No response generated.")

        # Add assistant response to session
        sessions[session_id]["messages"].append(
            {"role": "assistant", "content": response}
        )

        return {
            "session_id": session_id,
            "response": response,
            "success": True,
            "sources": result.get("sources", []),
        }
    except Exception as e:
        print(f"Error in text mode: {e}")
        return {"error": str(e), "success": False}


# Voice mode endpoint for initiating real-time voice conversations
@app.post("/voice-mode")
async def voice_mode(
    request: VoiceModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a Daily room and start the voice agent for real-time voice conversation.
    """
    try:
        room_url, token = await create_daily_room()

        # Start the voice agent in the background
        asyncio.create_task(
            start_voice_agent(
                room_url, 
                token, 
                enable_tts=request.enable_tts, 
                persona=request.persona,
                strict_mode=request.strict_mode,
                user_id=current_user.id
            )
        )

        return {
            "room_url": room_url,
            "token": token,
            "session_id": request.session_id,
            "success": True,
        }
    except Exception as e:
        print(f"Error starting voice mode: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start voice session: {str(e)}"
        )


# Connect endpoint for Pipecat SDK's startBotAndConnect() method
# This returns the simpler {url, token} format expected by the SDK
@app.post("/api/connect")
async def api_connect(
    request: VoiceModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a Daily room and start the voice agent.
    Returns {url, token} format for PipecatClient.startBotAndConnect().
    """
    try:
        room_url, token = await create_daily_room()

        # Start the voice agent in the background
        asyncio.create_task(
            start_voice_agent(
                room_url, 
                token, 
                enable_tts=request.enable_tts, 
                persona=request.persona,
                strict_mode=request.strict_mode,
                user_id=current_user.id
            )
        )

        # Return format expected by startBotAndConnect
        return {
            "url": room_url,
            "token": token,
        }
    except Exception as e:
        print(f"Error in /api/connect: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to connect: {str(e)}"
        )


class VoiceDisconnectRequest(BaseModel):
    room_url: str


# Voice disconnect endpoint to clean up Daily room
@app.post("/voice-mode/disconnect")
async def voice_disconnect(
    request: VoiceDisconnectRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Delete the Daily room when user ends voice session.
    This saves minutes by not waiting for auto-expiry.
    """
    from samvaad.interfaces.voice_agent import delete_daily_room
    
    try:
        success = await delete_daily_room(request.room_url)
        return {"success": success}
    except Exception as e:
        print(f"Error disconnecting voice mode: {e}")
        return {"success": False, "error": str(e)}


# Beacon-compatible disconnect endpoint (for browser close/tab close)
# This endpoint accepts raw body from sendBeacon and doesn't require auth
# The room URL itself acts as a short-lived capability (rooms auto-expire)
from fastapi import Request
import json as json_module

@app.post("/voice-mode/disconnect-beacon")
async def voice_disconnect_beacon(request: Request):
    """
    Delete the Daily room via sendBeacon (browser close/tab close).
    Accepts text/plain body from navigator.sendBeacon.
    No auth required - room URL acts as capability token.
    """
    from samvaad.interfaces.voice_agent import delete_daily_room
    
    try:
        body = await request.body()
        data = json_module.loads(body.decode("utf-8"))
        room_url = data.get("room_url")
        
        if not room_url:
            return {"success": False, "error": "No room_url provided"}
        
        print(f"[beacon] Cleaning up room: {room_url}")
        success = await delete_daily_room(room_url)
        return {"success": success}
    except Exception as e:
        print(f"Error in beacon disconnect: {e}")
        return {"success": False, "error": str(e)}


# TTS endpoint for voice responses (Protected? Maybe optional, keep protected for safety)
@app.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate audio from text using Deepgram TTS engine.
    """
    import io
    
    try:
        # Strip markdown formatting for better TTS pronunciation
        clean_text = strip_markdown(request.text)
        
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            return {"error": "DEEPGRAM_API_KEY not set"}
        
        url = f"https://api.deepgram.com/v1/speak?model=aura-2-asteria-en&encoding=mp3"
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }
        
        # Stream the response from Deepgram directly to client
        async def stream_audio():
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=headers, json={"text": clean_text}) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk
        
        return StreamingResponse(
            stream_audio(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )
        
    except Exception as exc:
        print(f"TTS Error: {exc}")
        return {"error": f"Failed to generate speech: {exc}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# Token-based TTS Streaming for Native Browser Support (<5s Latency)
# Simple cache: {token: (text, timestamp)}
tts_cache: Dict[str, tuple[str, float]] = {}

class TTSTokenRequest(BaseModel):
    text: str

@app.post("/tts/token")
async def get_tts_token(
    request: TTSTokenRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a temporary token for audio streaming.
    """
    token = str(uuid.uuid4())
    # Clean up old tokens (simple expiration)
    current_time = time.time()
    to_remove = [k for k, v in tts_cache.items() if current_time - v[1] > 300]
    for k in to_remove:
        del tts_cache[k]
        
    tts_cache[token] = (request.text, current_time)
    return {"token": token}

@app.get("/tts/stream/{token}")
async def stream_audio_by_token(token: str):
    """
    Stream audio directly to browser using a token.
    Browser <audio src="..."> will hit this endpoint.
    Note: verify_supabase_token is NOT called here because browsers fetching <audio> tags 
    can't easily attach headers. The 'token' itself acts as a short-lived capability URL.
    """
    if token not in tts_cache:
        raise HTTPException(status_code=404, detail="Token not found or expired")
    
    text, _ = tts_cache[token]
    clean_text = strip_markdown(text)
    
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DEEPGRAM_API_KEY not set")
    
    url = "https://api.deepgram.com/v1/speak?model=aura-2-asteria-en&encoding=mp3"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    
    # Create a generator that yields chunks
    async def stream_generator():
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=headers, json={"text": clean_text}) as response:
                    if response.status_code != 200:
                        yield b"" # Handle error?
                        return
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception as e:
            print(f"Stream error: {e}")
            
    return StreamingResponse(
        stream_generator(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": "inline; filename=speech.mp3"
        }
    )
