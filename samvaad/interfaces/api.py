from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
import asyncio
from samvaad.pipeline.ingestion.ingestion import ingest_file_pipeline
from samvaad.pipeline.retrieval.query import rag_query_pipeline
from samvaad.pipeline.generation.kokoro_tts import KokoroTTS
from pydantic import BaseModel
import base64
from samvaad.pipeline.retrieval.voice_mode import ConversationManager

from samvaad.utils.clean_markdown import strip_markdown

app = FastAPI(title="Samvaad RAG Backend")


_kokoro_tts: KokoroTTS | None = None

# Global conversation manager instances
_conversation_managers: Dict[str, ConversationManager] = {}


def get_tts() -> KokoroTTS:
    global _kokoro_tts
    if _kokoro_tts is None:
        try:
            _kokoro_tts = KokoroTTS()
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise Kokoro TTS: {exc}") from exc
    return _kokoro_tts


def get_conversation_manager(session_id: str) -> ConversationManager:
    """Get or create a conversation manager for the given session."""
    global _conversation_managers
    if session_id not in _conversation_managers:
        _conversation_managers[session_id] = ConversationManager()
    return _conversation_managers[session_id]


@app.get("/health")
def health_check():
    """Health check endpoint to verify the server is running."""
    return JSONResponse(content={"status": "ok"})


class VoiceQuery(BaseModel):
    query: str
    language: str


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


class TextQuery(BaseModel):
    query: str


class ConversationMessageRequest(BaseModel):
    message: str
    session_id: str = "default"


class ConversationSettingsRequest(BaseModel):
    session_id: str = "default"
    language: Optional[str] = None
    model: Optional[str] = None


# Ingest endpoint for uploading various document files
@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    """
    Accept various document file uploads and process them into the RAG system.

    Supported formats: PDF, DOCX, XLSX, PPTX, HTML, XHTML, CSV, TXT, MD,
    PNG, JPEG, TIFF, BMP, WEBP, WebVTT, WAV, MP3, and more.

    The system uses Docling for advanced document parsing and understanding.
    """
    filename = file.filename
    content_type = file.content_type
    contents = await file.read()

    print(f"Processing file: {filename}")
    result = ingest_file_pipeline(filename, content_type, contents)
    print(
        f"Processed {result['num_chunks']} chunks, embedded {result['new_chunks_embedded']} new chunks."
    )

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
    result = rag_query_pipeline(request.query, model="gemini-2.5-flash")
    return result


# TTS endpoint for voice responses
@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Generate audio from text using Kokoro TTS engine.
    """
    try:
        tts_engine = get_tts()
    except Exception as exc:
        return {"error": str(exc)}

    try:
        # Strip markdown formatting for better TTS pronunciation
        clean_text = strip_markdown(request.text)

        wav_bytes, sample_rate = tts_engine.synthesize_wav(
            clean_text,
            language=request.language,
            speed=1.0,
        )
    except Exception as exc:
        return {"error": f"Failed to generate speech: {exc}"}

    audio_base64 = base64.b64encode(wav_bytes).decode()
    return {"audio_base64": audio_base64, "sample_rate": sample_rate, "format": "wav"}


# Conversation endpoints
@app.post("/conversation/start")
async def start_conversation(session_id: str = "default"):
    """
    Start a new conversation session.
    """
    try:
        manager = get_conversation_manager(session_id)
        if not manager.is_active:
            manager.start_conversation()
        return {
            "status": "started",
            "session_id": session_id,
            "message": "Conversation started successfully"
        }
    except Exception as e:
        return {"error": str(e), "session_id": session_id}


@app.post("/conversation/message")
async def send_conversation_message(request: ConversationMessageRequest):
    """
    Send a message to a conversation and get a response.
    """
    try:
        manager = get_conversation_manager(request.session_id)

        # Add user message
        manager.add_user_message(request.message)

        # Process through RAG pipeline
        result = rag_query_pipeline(
            request.message,
            model=manager.settings['model'],
            conversation_manager=manager
        )

        # Add assistant response
        manager.add_assistant_message(result['answer'])

        return {
            "session_id": request.session_id,
            "response": result['answer'],
            "success": result['success'],
            "sources": result.get('sources', []),
            "conversation_context": manager.get_context()
        }
    except Exception as e:
        return {
            "error": str(e),
            "session_id": request.session_id,
            "response": f"Sorry, I encountered an error: {str(e)}"
        }


@app.post("/conversation/settings")
async def update_conversation_settings(request: ConversationSettingsRequest):
    """
    Update conversation settings.
    """
    try:
        manager = get_conversation_manager(request.session_id)

        updates = {}
        if request.language:
            updates['language'] = request.language
        if request.model:
            updates['model'] = request.model

        if updates:
            manager.update_settings(**updates)

        return {
            "status": "updated",
            "session_id": request.session_id,
            "settings": manager.settings
        }
    except Exception as e:
        return {"error": str(e), "session_id": request.session_id}


@app.get("/conversation/status/{session_id}")
async def get_conversation_status(session_id: str):
    """
    Get the status of a conversation session.
    """
    try:
        manager = get_conversation_manager(session_id)
        summary = manager.get_conversation_summary()
        return {
            "session_id": session_id,
            "status": summary
        }
    except Exception as e:
        return {"error": str(e), "session_id": session_id}


@app.post("/conversation/clear/{session_id}")
async def clear_conversation(session_id: str):
    """
    Clear the conversation history for a session.
    """
    try:
        manager = get_conversation_manager(session_id)
        manager.clear_history()
        return {
            "status": "cleared",
            "session_id": session_id,
            "message": "Conversation history cleared"
        }
    except Exception as e:
        return {"error": str(e), "session_id": session_id}


@app.post("/conversation/end/{session_id}")
async def end_conversation(session_id: str):
    """
    End a conversation session.
    """
    try:
        manager = get_conversation_manager(session_id)
        manager.end_conversation()
        return {
            "status": "ended",
            "session_id": session_id,
            "message": "Conversation ended"
        }
    except Exception as e:
        return {"error": str(e), "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
