"""
Samvaad API - FastAPI Backend
Security-hardened with proper middleware ordering and rate limiting.
"""

import asyncio
import json
import os
import threading
import time
import uuid

import httpx
from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from samvaad.api.deps import get_current_user
from samvaad.api.routers import conversations, files, users
from samvaad.db.models import User
from samvaad.interfaces.voice_agent import create_daily_room, start_voice_agent
from samvaad.pipeline.ingestion.ingestion import ingest_file_pipeline
from samvaad.utils.clean_markdown import strip_markdown
from samvaad.utils.logger import logger

# Load environment variables
load_dotenv()

logger.info("Samvaad API starting...")

# =============================================================================
# Configuration
# =============================================================================

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Trusted hosts for TrustedHostMiddleware
# Allow wildcard in non-production for easier local/staging development
DEFAULT_HOSTS = "localhost,127.0.0.1,samvaad.live,www.samvaad.live,samvaad.up.railway.app"
ALLOWED_HOSTS = [
    h.strip().strip('"').strip("'") for h in os.getenv("ALLOWED_HOSTS", DEFAULT_HOSTS).split(",") if h.strip()
]

# CORS origins
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if FRONTEND_URL:
    clean_url = FRONTEND_URL.strip().strip('"').strip("'").rstrip("/")
    if clean_url not in CORS_ORIGINS:
        CORS_ORIGINS.append(clean_url)

    if "www.samvaad.live" in clean_url:
        base_url = clean_url.replace("www.", "")
        if base_url not in CORS_ORIGINS:
            CORS_ORIGINS.append(base_url)
    elif "samvaad.live" in clean_url and "www." not in clean_url:
        www_url = clean_url.replace("://", "://www.")
        if www_url not in CORS_ORIGINS:
            CORS_ORIGINS.append(www_url)


# Request size limits
MAX_JSON_BODY = 1 * 1024 * 1024  # 1MB for JSON payloads
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB for file uploads

# Allowed MIME types for file uploads
ALLOWED_MIME_TYPES = frozenset(
    [
        "application/pdf",
        "text/plain",
        "text/csv",
        "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "audio/mpeg",
        "audio/wav",
        "image/png",
        "image/jpeg",
    ]
)

# =============================================================================
# Application Initialization
# =============================================================================

# Disable docs in production
docs_url = "/docs" if not IS_PRODUCTION else None
redoc_url = "/redoc" if not IS_PRODUCTION else None

app = FastAPI(title="Samvaad RAG Backend", docs_url=docs_url, redoc_url=redoc_url)
logger.info("FastAPI app initialized")

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# =============================================================================
# Middleware Configuration
# =============================================================================
# IMPORTANT: Middleware execution order is REVERSE of addition order.
# Last added = First to execute on request, Last to execute on response.
# Order added (bottom to top execution on request):
#   1. SlowAPI (rate limiting)
#   2. Security Headers
#   3. Request Size Limiter
#   4. GZip Compression
#   5. TrustedHost (with health endpoint bypass)
#   6. CORS (must run FIRST to handle preflight OPTIONS)
# =============================================================================

# 1. Rate limiting middleware
app.add_middleware(SlowAPIMiddleware)  # type: ignore


# 2. Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    # HSTS: Force HTTPS for 1 year, include subdomains
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Control referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# 3. Request body size limiter for specific endpoints
@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    """Limit request body size for JSON endpoints to prevent DoS."""
    if request.method == "POST" and request.url.path in ["/text-mode", "/voice-mode", "/auth/login"]:
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_JSON_BODY:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    return await call_next(request)


# 4. GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)  # type: ignore


# 5. Custom TrustedHost middleware that bypasses health endpoint
# Railway's internal healthchecks may not send expected Host headers
@app.middleware("http")
async def trusted_host_with_health_bypass(request: Request, call_next):
    if request.url.path == "/health" or request.method == "OPTIONS":
        return await call_next(request)

    host = request.headers.get("host", "").split(":")[0]
    if host and host not in ALLOWED_HOSTS and "*" not in ALLOWED_HOSTS:
        logger.warning(f"Rejected request with untrusted host: {host}")
        return JSONResponse(status_code=400, content={"detail": "Invalid host header"})
    return await call_next(request)


# 6. CORS - Must be added LAST so it runs FIRST (handles preflight OPTIONS)
app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Routers
# =============================================================================

app.include_router(files.router)
app.include_router(conversations.router)
app.include_router(users.router)

# =============================================================================
# Health Check (Public - No Auth Required)
# =============================================================================


@app.get("/health")
def health_check():
    """Health check endpoint for load balancers and orchestrators."""
    return JSONResponse(content={"status": "ok"})


# =============================================================================
# Request/Response Models
# =============================================================================


class TextMessageRequest(BaseModel):
    message: str
    conversation_id: str
    user_message_id: str | None = None
    assistant_message_id: str | None = None
    persona: str = "default"
    strict_mode: bool = False
    allowed_file_ids: list[str] | None = None


class VoiceModeRequest(BaseModel):
    conversation_id: str
    enable_tts: bool = True
    persona: str = "default"
    strict_mode: bool = False


class VoiceDisconnectRequest(BaseModel):
    room_url: str


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


class TTSTokenRequest(BaseModel):
    text: str


# =============================================================================
# File Ingestion Endpoint
# =============================================================================


@app.post("/ingest")
@limiter.limit("20/minute")
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Ingest a document file into the RAG system.

    Supported formats: PDF, DOCX, XLSX, PPTX, HTML, CSV, TXT, MD,
    PNG, JPEG, WAV, MP3, and more.
    """
    filename = file.filename
    content_type = file.content_type
    contents = await file.read()

    # Validate file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 25MB.")

    # Validate MIME type (permissive for text/* types)
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        is_text_fallback = content_type.startswith("text/") or (
            filename and filename.lower().endswith((".txt", ".md", ".csv"))
        )
        if not is_text_fallback:
            logger.warning(f"Potentially unsupported content-type: {content_type} for {filename}")

    logger.info(f"Processing file: {filename} for user {current_user.id}")

    # Use asyncio.to_thread to avoid event loop conflicts with LlamaParse
    result = await asyncio.to_thread(
        ingest_file_pipeline,
        filename,
        content_type,
        contents,
        user_id=current_user.id,  # type: ignore
    )

    logger.info(f"Processed {result['num_chunks']} chunks, embedded {result['new_chunks_embedded']} new chunks.")
    return result


# =============================================================================
# Text Mode Endpoint
# =============================================================================


@app.post("/text-mode")
async def text_mode(
    request: TextMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Handle text messages with persistent conversation storage.
    Uses sliding window + summary for efficient context management.
    """
    from uuid import UUID as UUIDType

    from samvaad.core.memory import detect_query_complexity
    from samvaad.core.unified_context import SLIDING_WINDOW_SIZE, UnifiedContextManager
    from samvaad.utils.text import build_sliding_window_context
    from samvaad.db.conversation_service import ConversationService

    conversation_service = ConversationService()

    try:
        # Parse conversation ID
        conversation_id = UUIDType(request.conversation_id)

        # Get or create conversation
        conversation = conversation_service.get_or_create_conversation(
            conversation_id=str(conversation_id),
            user_id=current_user.id,  # type: ignore
        )

        # Create context manager
        context_manager = UnifiedContextManager(
            str(conversation.id),
            str(current_user.id),
            conversation_service=conversation_service,
        )

        # Load and prepare messages
        db_messages = conversation_service.get_messages(conversation.id)
        messages = [{"role": m.role, "content": m.content} for m in db_messages]
        recent_messages, older_messages = build_sliding_window_context(messages, SLIDING_WINDOW_SIZE)

        # Log query complexity
        complexity = detect_query_complexity(request.message)
        if complexity["recommendation"] != "baseline":
            logger.info(f"[Memory] Complex query detected: {complexity['signals']}")

        # Generate response using text agent
        from samvaad.interfaces.text_agent import text_agent_respond

        result = await text_agent_respond(
            query=request.message,
            conversation_id=str(conversation.id),
            user_id=current_user.id,  # type: ignore
            messages=recent_messages,
            persona=request.persona,
            strict_mode=request.strict_mode,
            conversation_summary=conversation.summary,  # type: ignore
            conversation_facts=conversation.facts,  # type: ignore
            file_ids=request.allowed_file_ids,
        )

        response = result["response"]
        sources = result.get("sources", [])

        if result.get("used_tool"):
            logger.info("[TextAgent] Used fetch_context tool")

        # Trigger centralized background tasks
        background_tasks.add_task(
            context_manager.run_post_response_tasks,
            user_message=request.message,
            assistant_response=response,
            current_summary=conversation.summary,
            current_facts=conversation.facts,
            sources=sources,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )

        # Auto-generate title for new conversations
        if len(messages) == 0:
            title = request.message[:50] + ("..." if len(request.message) > 50 else "")
            conversation_service.update_conversation(
                conversation_id=conversation.id,
                user_id=current_user.id,
                title=title,
            )

        return {
            "conversation_id": str(conversation.id),
            "response": response,
            "success": True,
            "sources": sources,
        }

    except Exception as e:
        import traceback

        logger.error(f"Error in text mode: {e}")
        logger.error(traceback.format_exc())
        # Return generic error to client (don't expose internals)
        return {"error": "An internal server error occurred.", "success": False}


# =============================================================================
# Voice Mode Endpoints
# =============================================================================

# Track active voice tasks to prevent garbage collection
active_voice_tasks: set = set()


async def _run_voice_agent_wrapper(
    room_url: str,
    token: str | None,
    user_id: str,
    conversation_id: str,
    **kwargs,
):
    """Wrapper to run voice agent safely in background."""
    try:
        logger.info(f"[VoiceAgent] Starting agent for room {room_url} (user {user_id})")
        await start_voice_agent(
            room_url,
            token,
            user_id=user_id,
            conversation_id=conversation_id,
            **kwargs,
        )
        logger.info(f"[VoiceAgent] Agent finished successfully for room {room_url}")
    except asyncio.CancelledError:
        logger.info(f"[VoiceAgent] Agent task cancelled for room {room_url}")
    except Exception as e:
        import traceback

        logger.error(f"[VoiceAgent] ERROR: Agent failed for room {room_url}: {e}")
        logger.error(traceback.format_exc())


async def _create_voice_session(
    request: VoiceModeRequest,
    user_id: str,
) -> tuple[str, str | None, str]:
    """
    Create Daily room and start voice agent.
    Returns (room_url, token, conversation_id).
    """
    room_url, token = await create_daily_room()
    conversation_id = request.conversation_id

    # Create and track the background task
    task = asyncio.create_task(
        _run_voice_agent_wrapper(
            room_url,
            token,
            user_id=user_id,
            conversation_id=conversation_id,
            enable_tts=request.enable_tts,
            persona=request.persona,
            strict_mode=request.strict_mode,
        )
    )
    active_voice_tasks.add(task)
    task.add_done_callback(active_voice_tasks.discard)

    return room_url, token, conversation_id


@app.post("/voice-mode")
async def voice_mode(
    request: VoiceModeRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a Daily room and start the voice agent for real-time voice conversation.
    Returns room_url, token, session_id, conversation_id.
    """
    try:
        room_url, token, conversation_id = await _create_voice_session(
            request,
            user_id=current_user.id,
        )
        return {
            "room_url": room_url,
            "token": token,
            "conversation_id": conversation_id,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error starting voice mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start voice session: {str(e)}") from e


@app.post("/api/connect")
async def api_connect(
    request: VoiceModeRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create Daily room for PipecatClient.startBotAndConnect().
    Returns {url, token} format expected by the SDK.
    """
    try:
        room_url, token, _ = await _create_voice_session(request, user_id=current_user.id)
        return {"url": room_url, "token": token}
    except Exception as e:
        logger.error(f"Error in /api/connect: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}") from e


@app.post("/voice-mode/disconnect")
async def voice_disconnect(
    request: VoiceDisconnectRequest,
    current_user: User = Depends(get_current_user),
):
    """Delete the Daily room when user ends voice session."""
    from samvaad.interfaces.voice_agent import delete_daily_room

    try:
        success = await delete_daily_room(request.room_url)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error disconnecting voice mode: {e}")
        return {"success": False, "error": str(e)}


@app.post("/voice-mode/disconnect-beacon")
async def voice_disconnect_beacon(request: Request):
    """
    Delete Daily room via sendBeacon (browser close/tab close).

    Note: No auth required - room URL acts as capability token since
    browser sendBeacon cannot easily attach auth headers.
    """
    from samvaad.interfaces.voice_agent import delete_daily_room

    try:
        body = await request.body()
        data = json.loads(body.decode("utf-8"))
        room_url = data.get("room_url")

        if not room_url:
            return {"success": False, "error": "No room_url provided"}

        logger.info(f"[beacon] Cleaning up room: {room_url}")
        success = await delete_daily_room(room_url)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error in beacon disconnect: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# TTS Endpoints
# =============================================================================

# Thread-safe TTS token cache
tts_cache: dict[str, tuple[str, float]] = {}
tts_cache_lock = threading.Lock()


@app.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate audio from text using Deepgram TTS engine."""
    try:
        clean_text = strip_markdown(request.text)

        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            return {"error": "DEEPGRAM_API_KEY not set"}

        url = "https://api.deepgram.com/v1/speak?model=aura-2-asteria-en&encoding=mp3"
        headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

        async def stream_audio():
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=headers, json={"text": clean_text}) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(
            stream_audio(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )
    except Exception as exc:
        logger.error(f"TTS Error: {exc}")
        return {"error": f"Failed to generate speech: {exc}"}


@app.post("/tts/token")
async def get_tts_token(
    request: TTSTokenRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a temporary token for audio streaming."""
    token = str(uuid.uuid4())
    current_time = time.time()

    with tts_cache_lock:
        # Cleanup expired tokens (>5 min old)
        to_remove = [k for k, v in tts_cache.items() if current_time - v[1] > 300]
        for k in to_remove:
            del tts_cache[k]
        tts_cache[token] = (request.text, current_time)

    return {"token": token}


@app.get("/tts/stream/{token}")
async def stream_audio_by_token(token: str):
    """
    Stream audio to browser using a token.

    Note: No auth header required since browsers fetching <audio src>
    cannot easily attach headers. Token acts as short-lived capability.
    """
    if token not in tts_cache:
        raise HTTPException(status_code=404, detail="Token not found or expired")

    text, _ = tts_cache[token]
    clean_text = strip_markdown(text)

    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DEEPGRAM_API_KEY not set")

    url = "https://api.deepgram.com/v1/speak?model=aura-2-asteria-en&encoding=mp3"
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

    async def stream_generator():
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=headers, json={"text": clean_text}) as response:
                    if response.status_code != 200:
                        yield b""
                        return
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception as e:
            logger.error(f"Stream error: {e}")

    return StreamingResponse(
        stream_generator(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": "inline; filename=speech.mp3",
        },
    )


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
