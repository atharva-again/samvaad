import asyncio
import base64
import os
import shutil
import tempfile
import threading
import uuid
import time
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends, BackgroundTasks
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

from samvaad.api.routers import files, conversations

app = FastAPI(title="Samvaad RAG Backend")

app.include_router(files.router)
app.include_router(conversations.router)

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

# Legacy in-memory session storage (kept for backward compatibility)
# New conversations use database via ConversationService
sessions: Dict[str, Dict] = {}




@app.get("/health")
def health_check():
    """Health check endpoint to verify the server is running."""
    return JSONResponse(content={"status": "ok"})


class TextMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # UUID string, if None creates new conversation
    user_message_id: Optional[str] = None  # Client-generated UUID7 for user message
    assistant_message_id: Optional[str] = None  # Client-generated UUID7 for assistant message
    session_id: str = "default"  # Legacy, kept for backward compatibility
    persona: str = "default"
    strict_mode: bool = False


class VoiceModeRequest(BaseModel):
    conversation_id: Optional[str] = None  # Existing conversation to continue
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


# Background task for LLM summarization (#1, #2, #9)
async def summarize_and_save(
    conversation_id,
    user_id: str,
    messages: List[Dict],
    existing_summary: Optional[str]
):
    """Background task: LLM summarization → save to DB."""
    from samvaad.core.unified_context import UnifiedContextManager
    from samvaad.db.conversation_service import ConversationService
    
    try:
        # Create a minimal context manager for summarization
        ctx = UnifiedContextManager(str(conversation_id), user_id)
        svc = ConversationService()
        
        new_summary = await ctx.summarize_with_llm(messages, existing_summary)
        svc.update_conversation(conversation_id, user_id, summary=new_summary)
        print(f"[Summarization] Saved summary for conversation {conversation_id}")
    except Exception as e:
        print(f"[Summarization] Error: {e}")


# Text mode endpoint for handling text conversations
@app.post("/text-mode")
async def text_mode(
    request: TextMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Handle text messages with persistent conversation storage.
    Uses sliding window + summary for efficient context management.
    """
    from uuid import UUID as UUIDType
    from samvaad.db.conversation_service import ConversationService
    from samvaad.core.unified_context import (
        UnifiedContextManager,
        build_sliding_window_context,
        format_messages_for_prompt,
        SLIDING_WINDOW_SIZE
    )
    from samvaad.core.memory import (
        detect_query_complexity,
        update_conversation_summary,
        extract_facts_from_exchange
    )
    from samvaad.core.voyage import embed_texts
    
    conversation_service = ConversationService()
    
    try:
        # 1. Get or create conversation
        conversation_id = None
        if request.conversation_id:
            try:
                conversation_id = UUIDType(request.conversation_id)
            except ValueError:
                pass
        
        conversation = conversation_service.get_or_create_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
        
        # Create context manager for this conversation
        context_manager = UnifiedContextManager(
            str(conversation.id),
            str(current_user.id),
            conversation_service=conversation_service
        )
        
        # 2. Load existing messages
        db_messages = conversation_service.get_messages(conversation.id)
        messages = [{"role": m.role, "content": m.content} for m in db_messages]
        
        # 3. Build sliding window context
        recent_messages, older_messages = build_sliding_window_context(
            messages, SLIDING_WINDOW_SIZE
        )
        recent_history = format_messages_for_prompt(recent_messages)
        
        # 4. Detect query complexity (for logging/future tool hints)
        complexity = detect_query_complexity(request.message)
        if complexity["recommendation"] != "baseline":
            print(f"[Memory] Complex query detected: {complexity['signals']}")
        
        # 5. Process through RAG pipeline
        result = rag_query_pipeline(
            request.message, 
            model="openai/gpt-oss-120b",  # Updated model
            user_id=current_user.id,
            persona=request.persona,
            strict_mode=request.strict_mode,
            generate_answer=False  # Just get chunks first
        )
        
        # 6. Build context with sliding window + summary + RAG
        context = context_manager.build_context(
            messages=recent_messages,  # Only recent messages
            rag_chunks=result.get("chunks", []),
            conversation_summary=conversation.summary
        )
        
        # Debug: Log token counts
        print(f"[Context] RAG chunks: {len(result.get('chunks', []))}, "
              f"RAG context tokens: {context['token_counts'].get('rag_context', 0)}, "
              f"History tokens: {context['token_counts'].get('recent_history', 0)}")
        
        # 7. Generate answer
        from samvaad.pipeline.generation.generation import generate_answer_with_groq
        response = generate_answer_with_groq(
            query=request.message,
            chunks=[],  # Empty - using pre-formatted context
            model="openai/gpt-oss-120b",  # Use GPT OSS 120B for tool calling capability
            conversation_context=context["recent_history"],
            persona=request.persona,
            strict_mode=request.strict_mode,
            rag_context=context["rag_context"]
        )
        
        # 8. Save messages to database
        user_tokens = context_manager.count_tokens(request.message)
        assistant_tokens = context_manager.count_tokens(response)
        
        user_message_id = None
        if request.user_message_id:
            try:
                user_message_id = UUIDType(request.user_message_id)
            except ValueError:
                pass
        
        assistant_message_id = None
        if request.assistant_message_id:
            try:
                assistant_message_id = UUIDType(request.assistant_message_id)
            except ValueError:
                pass
        
        user_msg = conversation_service.add_message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
            token_count=user_tokens,
            message_id=user_message_id
        )
        asst_msg = conversation_service.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=response,
            sources=result.get("sources", []),
            token_count=assistant_tokens,
            message_id=assistant_message_id
        )
        
        # 9. Background tasks for memory
        # 9a. Update summary if messages exited window
        if len(older_messages) > 0 and len(messages) >= SLIDING_WINDOW_SIZE:
            # Messages that just exited the window
            exiting = messages[-SLIDING_WINDOW_SIZE-2:-SLIDING_WINDOW_SIZE] if len(messages) > SLIDING_WINDOW_SIZE else []
            if exiting:
                background_tasks.add_task(
                    _update_summary_task,
                    conversation.id,
                    current_user.id,
                    conversation.summary,
                    exiting
                )
        
        # 9b. Extract facts from this exchange
        background_tasks.add_task(
            _extract_facts_task,
            conversation.id,
            request.message,
            response,
            asst_msg.id
        )
        
        # 9c. Embed the assistant message for semantic search
        background_tasks.add_task(
            _embed_message_task,
            asst_msg.id,
            response
        )
        
        # 10. Auto-generate title for new conversations
        if len(messages) == 0:
            title = request.message[:50] + ("..." if len(request.message) > 50 else "")
            conversation_service.update_conversation(
                conversation_id=conversation.id,
                user_id=current_user.id,
                title=title
            )
        
        return {
            "conversation_id": str(conversation.id),
            "response": response,
            "success": True,
            "sources": result.get("sources", []),
        }
    except Exception as e:
        print(f"Error in text mode: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "success": False}


# Background task helpers for memory
async def _update_summary_task(
    conversation_id,
    user_id: str,
    existing_summary: str,
    exiting_messages: list
):
    """Background: Update conversation summary."""
    from samvaad.core.memory import update_conversation_summary
    from samvaad.db.conversation_service import ConversationService
    
    try:
        new_summary = await update_conversation_summary(existing_summary, exiting_messages)
        ConversationService().update_conversation(
            conversation_id, user_id, summary=new_summary
        )
        print(f"[Memory] Updated summary for {conversation_id}")
    except Exception as e:
        print(f"[Memory] Summary update error: {e}")


async def _extract_facts_task(
    conversation_id,
    user_message: str,
    assistant_message: str,
    source_message_id
):
    """Background: Extract and save facts from exchange."""
    from samvaad.core.memory import extract_facts_from_exchange
    from samvaad.db.conversation_service import ConversationService
    
    try:
        facts = await extract_facts_from_exchange(user_message, assistant_message)
        service = ConversationService()
        for fact_data in facts:
            service.add_fact(
                conversation_id=conversation_id,
                fact=fact_data.get("fact", ""),
                entity_name=fact_data.get("entity_name"),
                source_message_id=source_message_id
            )
        if facts:
            print(f"[Memory] Extracted {len(facts)} facts for {conversation_id}")
    except Exception as e:
        print(f"[Memory] Fact extraction error: {e}")


def _embed_message_task(message_id, content: str):
    """Background: Embed message for semantic search."""
    from samvaad.core.voyage import embed_texts
    from samvaad.db.conversation_service import ConversationService
    
    try:
        embeddings = embed_texts([content], input_type="document")
        if embeddings:
            ConversationService().add_message_embedding(message_id, embeddings[0])
            print(f"[Memory] Embedded message {message_id}")
    except Exception as e:
        print(f"[Memory] Embedding error: {e}")


# Voice mode endpoint for initiating real-time voice conversations
@app.post("/voice-mode")
async def voice_mode(
    request: VoiceModeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a Daily room and start the voice agent for real-time voice conversation.
    If conversation_id is provided, continues that conversation. Otherwise creates new.
    """
    try:
        from samvaad.db.conversation_service import ConversationService
        conversation_service = ConversationService()
        
        room_url, token = await create_daily_room()
        
        # Get or create conversation for this voice session
        conversation_id = request.conversation_id
        if not conversation_id:
            # Create new conversation for voice mode
            conversation = conversation_service.create_conversation(
                user_id=current_user.id,
                title="Voice Conversation"
            )
            conversation_id = str(conversation.id)

        # Start the voice agent in the background
        asyncio.create_task(
            start_voice_agent(
                room_url, 
                token, 
                enable_tts=request.enable_tts, 
                persona=request.persona,
                strict_mode=request.strict_mode,
                user_id=current_user.id,
                conversation_id=conversation_id
            )
        )

        return {
            "room_url": room_url,
            "token": token,
            "session_id": request.session_id,
            "conversation_id": conversation_id,  # Return for frontend sync
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
    If conversation_id is provided, continues that conversation. Otherwise creates new.
    """
    try:
        from samvaad.db.conversation_service import ConversationService
        conversation_service = ConversationService()
        
        room_url, token = await create_daily_room()
        
        # Get or create conversation for this voice session
        conversation_id = request.conversation_id
        if not conversation_id:
            # Create new conversation for voice mode
            conversation = conversation_service.create_conversation(
                user_id=current_user.id,
                title="Voice Conversation"
            )
            conversation_id = str(conversation.id)

        # Start the voice agent in the background
        asyncio.create_task(
            start_voice_agent(
                room_url, 
                token, 
                enable_tts=request.enable_tts, 
                persona=request.persona,
                strict_mode=request.strict_mode,
                user_id=current_user.id,
                conversation_id=conversation_id
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
# Thread-safe cache with lock (#10)
tts_cache: Dict[str, tuple[str, float]] = {}
tts_cache_lock = threading.Lock()

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
    current_time = time.time()
    
    # Thread-safe cleanup and add (#10)
    with tts_cache_lock:
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
