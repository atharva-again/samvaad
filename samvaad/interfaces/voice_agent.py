import asyncio
import os
import time

import aiohttp
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.base_task import PipelineTaskParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import LLMUserAggregatorParams
from pipecat.processors.frameworks.rtvi import (
    RTVIObserver,
    RTVIProcessor,
    RTVIServerMessageFrame,
)
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter

# Import unified context manager
from samvaad.core.unified_context import SamvaadLLMContext

# Import shared RAG logic
from samvaad.pipeline.retrieval.query import rag_query_pipeline
from samvaad.utils.logger import logger
from samvaad.utils.text_filters import CitationTextFilter


async def create_daily_room() -> tuple[str, str | None]:
    """
    Creates a new temporary room via the Daily REST API.
    NOT the Daily Python SDK.
    """
    api_key = os.getenv("DAILY_API_KEY")
    if not api_key:
        raise ValueError("DAILY_API_KEY is not set in environment variables")
    assert isinstance(api_key, str)

    api_url = "https://api.daily.co/v1/rooms"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    expiration_time = int(time.time()) + 3600

    # Create a room that expires in 1 hour to keep your account clean
    # [SECURITY-FIX #84] Force private room to prevent eavesdropping
    payload = {
        "privacy": "private",
        "properties": {
            "exp": expiration_time,
            "enable_chat": False,
            "start_video_off": True,
            "permissions": {"canSend": ["audio"]},
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, headers=headers, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Failed to create room: {text}")

            data = await response.json()

            # [SECURITY-FIX #84] Now that room is private, we MUST generate a token for the owner
            # The 'token' field in room creation response might be None if not requested or different API.
            # Best practice: Explicitly create a meeting token for the user.

            # Actually, Daily's room creation response usually doesn't include a token unless requested?
            # Wait, the previous code expected `data.get("token")`.
            # If the room is private, we need a token to join.
            # Let's create a meeting token explicitly.

            owner_token_url = "https://api.daily.co/v1/meeting-tokens"
            token_payload = {
                "properties": {
                    "room_name": data["name"],
                    "is_owner": True,
                    "exp": expiration_time,
                }
            }

            async with session.post(owner_token_url, headers=headers, json=token_payload) as token_res:
                if token_res.status != 200:
                    # Fallback? If token fails, user can't join private room.
                    token_text = await token_res.text()
                    raise Exception(f"Room created but token generation failed: {token_text}")

                token_data = await token_res.json()
                return data["url"], token_data["token"]


async def delete_daily_room(room_url: str) -> bool:
    """
    Delete a Daily room to save minutes.
    Extracts room name from URL and calls DELETE on Daily API.
    """
    api_key = os.getenv("DAILY_API_KEY")
    if not api_key:
        logger.warning("DAILY_API_KEY not set, cannot delete room")
        return False

    # Extract room name from URL (e.g., https://samvaad.daily.co/abc123 -> abc123)
    room_name = room_url.rstrip("/").split("/")[-1]
    if not room_name:
        logger.warning(f"Could not extract room name from URL: {room_url}")
        return False

    api_url = f"https://api.daily.co/v1/rooms/{room_name}"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(api_url, headers=headers) as response:
                if response.status in (200, 204, 404):
                    # 200/204 = deleted, 404 = already gone
                    logger.info(f"Daily room {room_name} deleted successfully")
                    return True
                else:
                    text = await response.text()
                    logger.warning(f"Failed to delete Daily room: {text}")
                    return False
    except Exception as e:
        logger.error(f"Error deleting Daily room: {e}")
        return False


async def start_voice_agent(
    room_url: str,
    token: str | None,
    enable_tts: bool = True,
    persona: str = "default",
    strict_mode: bool = False,
    user_id: str = None,
    conversation_id: str = None,  # NEW: For unified context
):
    """Entry point to start the bot in a specific Daily room"""

    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    if not deepgram_api_key:
        raise ValueError("DEEPGRAM_API_KEY is not set in environment variables")
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set in environment variables")

    # 1. Define Transport
    # VAD parameters tuned for better interruption handling:
    # - confidence=0.8: Higher threshold to avoid false positives from noise
    # - start_secs=0.5: User must speak for 0.5s before triggering (prevents accidental interrupts)
    # - stop_secs=1.0: Allow 1 second of silence before considering speech complete
    #                  (higher value = fewer splits but slower response time)
    # - min_volume=0.7: Filter out quiet background noise
    vad_analyzer = SileroVADAnalyzer(params=VADParams(confidence=0.8, start_secs=0.5, stop_secs=1.0, min_volume=0.7))
    transport = DailyTransport(
        room_url=room_url,
        token=token,
        bot_name="Samvaad",
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            camera_out_enabled=False,
            vad_analyzer=vad_analyzer,
            # Increase join timeout for slow networks (default is ~10s)
            meeting_join_timeout_s=30,
        ),
    )

    # 2. Create RTVI processor early (needed by fetch_context for citations)
    rtvi = RTVIProcessor()

    # 3. Define Tools (The RAG Integration)
    RAG_TIMEOUT_SECONDS = 10.0

    async def fetch_context(function_call_params):
        try:
            # [SECURITY-FIX #74] Strict validation of tool arguments
            args = function_call_params.arguments
            if not isinstance(args, dict):
                raise ValueError("Invalid arguments format")

            query = args.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError("Query must be a non-empty string")

            # Sanitize length to prevent excessive processing
            if len(query) > 500:
                query = query[:500]

            logger.info(f"RAG Tool Triggered: {query} (user_id: {user_id})")

            sources = []
            # Run blocking RAG code with timeout to avoid hanging
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    rag_query_pipeline, query, generate_answer=False, user_id=user_id, strict_mode=strict_mode
                ),
                timeout=RAG_TIMEOUT_SECONDS,
            )
            rag_text = result.get("answer", "No information found.")

            # Extract sources for citations panel
            chunks = result.get("chunks", [])
            for chunk in chunks[:3]:
                # Pass full metadata - already includes extra.page_number, etc from DB
                sources.append(
                    {
                        "filename": chunk.get("filename", "document"),
                        "content_preview": chunk.get("content", "")[:1000],
                        "rerank_score": chunk.get("rerank_score"),
                        "chunk_id": chunk.get("chunk_id"),
                        "metadata": chunk.get("metadata", {}),
                    }
                )

        except TimeoutError:
            logger.warning(f"[voice_agent] RAG timeout after {RAG_TIMEOUT_SECONDS}s for query: {query}")
            rag_text = "Search timed out. Please try your question again."
        except ValueError as e:
            logger.warning(f"[voice_agent] Tool validation error: {e}")
            rag_text = f"Invalid search request: {e}"
        except Exception as e:
            logger.error(f"[voice_agent] RAG error: {e}")
            rag_text = "An error occurred while searching. Please try again."

        # Send citations to frontend via RTVI custom message
        if sources:
            try:
                frame = RTVIServerMessageFrame(data={"type": "citations", "sources": sources})

                await rtvi.push_frame(frame)
                logger.debug(f"[voice_agent] Sent {len(sources)} citations to frontend")
            except Exception as e:
                logger.error(f"[voice_agent] Failed to send citations: {e}")

        await function_call_params.result_callback(rag_text)

    # OpenAI-compatible tool format for Groq
    tools = [
        {
            "type": "function",
            "function": {
                "name": "fetch_context",
                "description": "Search the knowledge base for information. IMPORTANT: Call this tool ONLY ONCE per user question. If the search does not return relevant information, answer based on your own knowledge instead of searching again. Do NOT retry with a modified query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query - use the user's key terms or topic",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    # 3. Define Services (using EU endpoint for better connectivity from India)
    stt = DeepgramSTTService(api_key=deepgram_api_key, base_url="wss://api.eu.deepgram.com/v1/listen")
    md_filter = MarkdownTextFilter()
    citation_filter = CitationTextFilter()

    # 4. Context & Persona - Use unified context manager for consistent prompts
    from samvaad.core.unified_context import UnifiedContextManager

    # Build system prompt using unified manager (same structure as text mode)
    if conversation_id and user_id:
        unified_ctx = UnifiedContextManager(conversation_id, user_id)
        system_instruction = unified_ctx.build_system_prompt(
            persona=persona,
            strict_mode=strict_mode,
            rag_context="",  # RAG is fetched via tool call, not pre-loaded
            conversation_history="",  # History managed by Pipecat context
            query="",  # Query comes from speech
            is_voice=True,  # Adds ~50 word limit instruction
            has_tools=True,  # Tool-based RAG - LLM will call fetch_context
        )
        print(
            f"[VoiceAgent] DEBUG: strict_mode={strict_mode}, prompt contains 'Strict Mode': {'### Strict Mode' in system_instruction}"
        )
    else:
        # Fallback for sessions without conversation_id
        from samvaad.core.unified_context import VOICE_STYLE_INSTRUCTION
        from samvaad.prompts.personas import get_persona_prompt

        system_instruction = get_persona_prompt(persona) + VOICE_STYLE_INSTRUCTION
        if strict_mode:
            system_instruction += " CRITICAL: You are in Strict Mode. Answer ONLY based on information retrieved from tools. If no information is found via tools, state that you do not know. Do not use outside knowledge."

    # Use Groq with OpenAI gpt-oss-120b
    llm = GroqLLMService(api_key=groq_api_key, model="openai/gpt-oss-120b")
    llm.register_function("fetch_context", fetch_context)

    # Context Manager (Keeps track of conversation history)
    # Use SamvaadLLMContext for database persistence
    if conversation_id:
        context = SamvaadLLMContext(conversation_id=conversation_id, user_id=user_id, tools=tools, tool_choice="auto")
        context.load_history()  # Load existing messages from DB
    else:
        # Fallback to in-memory only (no persistence)
        from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

        context = OpenAILLMContext(tools=tools, tool_choice="auto")

    context.add_message(
        {
            "role": "system",
            "content": system_instruction,
        }
    )
    # Disable emulated VAD interruptions to prevent user speech from being
    # split into multiple messages when there are pauses in speaking
    context_aggregator = llm.create_context_aggregator(
        context,
        user_params=LLMUserAggregatorParams(enable_emulated_vad_interruptions=False),
    )

    # 6. The Pipeline (Data Flow)
    # RTVIProcessor handles RTVI protocol messages (BotReady, user/bot speaking, etc.)
    # (rtvi already created earlier for fetch_context access)

    # Conditional pipeline construction based on enable_tts
    processors = [
        transport.input(),  # Microphone Audio in
        rtvi,  # RTVI protocol handler
        stt,  # Speech to Text
        context_aggregator.user(),  # Add user text to history
        llm,  # Groq thinks
    ]

    if enable_tts:
        tts = DeepgramTTSService(
            api_key=deepgram_api_key,
            base_url="wss://api.eu.deepgram.com",  # EU endpoint for better connectivity
            voice="aura-2-asteria-en",
            encoding="linear16",
            text_filters=[md_filter, citation_filter],  # Strip markdown and citations from TTS
        )
        processors.append(tts)

    processors.append(transport.output())  # Audio out (or text frames if TTS missing)
    processors.append(context_aggregator.assistant())  # Add bot answer to history

    pipeline = Pipeline(processors)

    # 6. RTVI Event Handler - Send bot-ready when client is ready
    # Track if transport has joined to avoid timing race
    transport_joined = False

    @transport.event_handler("on_joined")
    async def on_joined(transport_obj, participant):
        nonlocal transport_joined
        transport_joined = True
        # Safe access - participant may be dict without 'id' or a different type
        if isinstance(participant, dict):
            participant_id = participant.get("id", participant.get("session_id", "unknown"))
        else:
            participant_id = str(participant)
        logger.info(f"[voice_agent] Successfully joined room as: {participant_id}")

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi_processor):
        nonlocal transport_joined
        # Wait for transport to join before sending bot-ready
        if not transport_joined:
            logger.info("[voice_agent] Client ready but transport not joined yet, waiting...")
            # Wait up to 5 seconds for transport to join
            for _ in range(50):
                await asyncio.sleep(0.1)
                if transport_joined:
                    break
        logger.info("[voice_agent] Client ready - sending bot-ready")
        await rtvi_processor.set_bot_ready()

    # Cleanup flag to prevent duplicate cleanup (both events can fire)
    cleanup_done = False

    async def do_cleanup(reason: str):
        nonlocal cleanup_done
        if cleanup_done:
            logger.info(f"[voice_agent] Cleanup already done, skipping ({reason})")
            return
        cleanup_done = True
        logger.info(f"[voice_agent] Cleaning up - {reason}")
        await delete_daily_room(room_url)
        await task.cancel()

    # 7. Handle participant leaving - cleanup room
    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport_obj, participant, reason):
        logger.info(f"[voice_agent] Participant left: {participant['id']}, reason: {reason}")
        await do_cleanup("participant_left")

    # 8. Handle client disconnection (browser close, etc.)
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport_obj, client):
        logger.info("[voice_agent] Client disconnected")
        await do_cleanup("client_disconnected")

    # 9. Handle transport errors explicitly - trigger cleanup on failure
    # Note: rtvi.send_error() can't work before transport joins, so we
    # rely on the frontend's 30-second timeout to detect connection failure
    @transport.event_handler("on_error")
    async def on_transport_error(transport_obj, error):
        logger.error(f"[voice_agent] Transport error: {error}")
        # Trigger cleanup to allow frontend timeout to detect failure
        await do_cleanup("transport_error")

    # 9. Run the pipeline with 60-second idle timeout
    pipeline_params = PipelineParams(
        allow_interruptions=True,
        enable_metrics=True,
    )
    task = PipelineTask(
        pipeline,
        params=pipeline_params,
        observers=[RTVIObserver(rtvi)],
        idle_timeout_secs=60,  # 1 minute idle timeout
        cancel_on_idle_timeout=True,  # Cancel task when idle
    )
    task_params = PipelineTaskParams(loop=asyncio.get_event_loop())
    await task.run(task_params)
