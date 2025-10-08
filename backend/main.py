from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List
import asyncio
from backend.pipeline.ingestion.ingestion import ingest_file_pipeline
from backend.pipeline.retrieval.query import rag_query_pipeline
from backend.pipeline.generation.piper_tts import PiperTTS
from backend.pipeline.generation.kokoro_tts import KokoroTTS
from pydantic import BaseModel
import base64

from backend.utils.clean_markdown import strip_markdown

app = FastAPI(title="Samvaad RAG Backend")


_piper_tts: PiperTTS | None = None
_kokoro_tts: KokoroTTS | None = None


def get_piper_tts() -> PiperTTS:
    global _piper_tts
    if _piper_tts is None:
        try:
            _piper_tts = PiperTTS()
            print("🔊 Piper TTS engine initialised (API).")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise Piper TTS: {exc}") from exc
    return _piper_tts


def get_kokoro_tts() -> KokoroTTS:
    global _kokoro_tts
    if _kokoro_tts is None:
        try:
            _kokoro_tts = KokoroTTS()
            print("🔊 Kokoro TTS engine initialised (API).")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise Kokoro TTS: {exc}") from exc
    return _kokoro_tts


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
    engine: str = "piper"


class TextQuery(BaseModel):
    query: str


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
    Generate audio from text using specified TTS engine.
    """
    try:
        if request.engine.lower() == "kokoro":
            tts_engine = get_kokoro_tts()
        else:
            tts_engine = get_piper_tts()
    except Exception as exc:
        return {"error": str(exc)}

    try:
        # Strip markdown formatting for better TTS pronunciation
        clean_text = strip_markdown(request.text)

        if request.engine.lower() == "kokoro":
            wav_bytes, sample_rate = tts_engine.synthesize_wav(
                clean_text,
                language=request.language,
                speed=1.0,
            )
        else:
            wav_bytes, sample_rate = tts_engine.synthesize_wav(
                clean_text,
                language=request.language,
            )
    except Exception as exc:
        return {"error": f"Failed to generate speech: {exc}"}

    audio_base64 = base64.b64encode(wav_bytes).decode()
    return {"audio_base64": audio_base64, "sample_rate": sample_rate, "format": "wav"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
