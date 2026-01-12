"""
Text Agent for Samvaad

Handles text-mode conversations with tool-based RAG.
Mirrors voice_agent.py architecture for consistency.

Flow:
1. User query arrives
2. LLM sees system prompt + conversation history
3. LLM DECIDES whether to call fetch_context tool
4. If tool called: RAG runs, results fed back to LLM
5. LLM generates final response
"""

import asyncio
import os

from groq import AsyncGroq

from samvaad.core.types import ConversationMode
from samvaad.utils.text import format_messages_for_prompt
from samvaad.pipeline.retrieval.query import rag_query_pipeline
from samvaad.prompts import PromptBuilder
from samvaad.utils.citations import format_rag_context
from samvaad.utils.logger import logger

# Tool definition (same as voice_agent.py)
FETCH_CONTEXT_TOOL = {
    "type": "function",
    "function": {
        "name": "fetch_context",
        "description": "Search the knowledge base for information. Use when you need specific information from the user's documents. Call ONLY ONCE per question.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The search query - use key terms or topic"}},
            "required": ["query"],
        },
    },
}

RAG_TIMEOUT_SECONDS = 10.0


async def _execute_rag(query: str, user_id: str, file_ids: list[str] = None, strict_mode: bool = False) -> dict:
    """Execute RAG pipeline with timeout.

    Args:
        query: Search query
        user_id: User ID for access control
        file_ids: Optional list of file IDs to filter by (RAG source whitelist)
        strict_mode: Whether using strict mode (for logging purposes)

    Returns:
        dict: {
            "context": str,  # Formatted text for LLM
            "sources": list  # Full source objects for citations
        }
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                rag_query_pipeline,
                query,
                user_id=user_id,
                file_ids=file_ids,
            ),
            timeout=RAG_TIMEOUT_SECONDS,
        )

        # Format chunks as context using unified utility
        chunks = result.get("chunks", [])
        context = format_rag_context(chunks)

        # Build full source objects for citations panel
        sources = []
        for chunk in chunks[:3]:
            sources.append(
                {
                    "filename": chunk.get("filename", "document"),
                    "content_preview": chunk.get("content", "")[:1000],
                    "rerank_score": chunk.get("rerank_score"),
                    "chunk_id": chunk.get("chunk_id"),
                    "metadata": chunk.get("metadata", {}),
                }
            )

        return {"context": context, "sources": sources}

    except TimeoutError:
        return {"context": "Search timed out. Please try again.", "sources": []}
    except Exception as e:
        logger.error(f"[text_agent] RAG error: {e}")
        return {"context": "An error occurred while searching.", "sources": []}


async def text_agent_respond(
    query: str,
    conversation_id: str,
    user_id: str,
    messages: list[dict],
    persona: str = "default",
    strict_mode: bool = False,
    conversation_summary: str | None = None,
    conversation_facts: str | None = None,
    file_ids: list[str] | None = None,
) -> dict:
    """
    Text mode agent with tool-based RAG.

    Args:
        query: User's question
        conversation_id: Conversation UUID string
        user_id: User ID string
        messages: Recent conversation messages [{"role": str, "content": str}]
        persona: Persona name
        strict_mode: Whether to use strict mode
        conversation_summary: Optional summary of older messages
        conversation_facts: Optional facts string
        file_ids: Optional list of file IDs to filter RAG by (source whitelist)

    Returns:
        {"response": str, "sources": list, "used_tool": bool}
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not set")

    client = AsyncGroq(api_key=groq_key)

    # Build system prompt using unified builder
    builder = (
        PromptBuilder()
        .with_persona(persona)
        .with_strict_mode(strict_mode)
        .with_mode(ConversationMode.TEXT)
        .with_tools()
        .with_history(format_messages_for_prompt(messages))
    )

    if conversation_facts:
        builder.add_section(f"### User Facts\n{conversation_facts}")
    if conversation_summary:
        builder.add_section(f"### Conversation Summary\n{conversation_summary}")

    system_prompt = builder.build()

    # Build message history for LLM
    llm_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages[-6:]:  # Last 6 messages as context
        llm_messages.append({"role": msg["role"], "content": msg["content"]})
    llm_messages.append({"role": "user", "content": query})

    # First LLM call - may request tool use
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=llm_messages,
        tools=[FETCH_CONTEXT_TOOL],
        tool_choice="auto",
        temperature=0.3,
        max_tokens=1024,
    )

    message = response.choices[0].message
    sources = []
    used_tool = False

    # Check if LLM wants to use tool
    if message.tool_calls:
        used_tool = True
        tool_call = message.tool_calls[0]

        if tool_call.function.name == "fetch_context":
            import json

            args = json.loads(tool_call.function.arguments)
            search_query = args.get("query", query)

            logger.info(f"[text_agent] Tool called: fetch_context('{search_query}')")

            # Execute RAG
            rag_result = await _execute_rag(search_query, user_id, file_ids=file_ids, strict_mode=strict_mode)
            rag_context = rag_result["context"]
            sources = rag_result["sources"]

            # Add assistant message with tool call (Groq-compatible format)
            # Cannot use model_dump() as it includes unsupported fields like 'executed_tools'
            llm_messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                        }
                    ],
                }
            )

            # Add tool result
            llm_messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": rag_context})

            # Second LLM call with tool results
            final_response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=llm_messages,
                temperature=0.3,
                max_tokens=1024,
            )

            final_content = final_response.choices[0].message.content

            return {"response": final_content, "sources": sources, "used_tool": True}

    # No tool call - return direct response
    return {"response": message.content, "sources": [], "used_tool": False}
