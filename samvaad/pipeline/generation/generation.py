from groq import Groq
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()


def generate_answer_with_groq(
    query: str, 
    chunks: List[Dict], 
    model: str = "llama-3.3-70b-versatile", 
    conversation_context: str = "",
    persona: str = "default",
    strict_mode: bool = False,
    rag_context: str = ""  # Pre-formatted context from context_manager
) -> str:
    """Generate answer using Groq with retrieved chunks as context.
    
    Args:
        query: User's question
        chunks: Raw chunks (used if rag_context not provided)
        model: Groq model name
        conversation_context: Formatted conversation history
        persona: Persona name
        strict_mode: Whether to use strict mode
        rag_context: Pre-formatted RAG context (from context_manager)
                     If provided, chunks are ignored to avoid duplicate formatting
    """
    
    groq_key = os.getenv("GROQ_API_KEY")

    if not groq_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    from samvaad.prompts import get_system_prompt

    # Use pre-formatted context if provided, otherwise format chunks
    if rag_context:
        # Already formatted - pass directly without re-formatting
        prompt = get_system_prompt(
            persona=persona,
            strict_mode=strict_mode,
            context_chunks=[],  # Empty - we'll inject rag_context directly
            conversation_history=conversation_context,
            query=query,
            preformatted_context=rag_context  # New param
        )
    else:
        # Fallback: format chunks here (for backward compatibility)
        safe_chunks = []
        for chunk in chunks:
            safe_chunks.append({
                "content": chunk.get("content", ""),
                "filename": chunk.get("filename", "unknown_document")
            })

        prompt = get_system_prompt(
            persona=persona,
            strict_mode=strict_mode,
            context_chunks=safe_chunks,
            conversation_history=conversation_context,
            query=query
        )

    # Initialize Groq client
    client = Groq(api_key=groq_key)

    # Generate response
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query}
        ],
        temperature=0.3,
        max_tokens=1024,
    )

    return response.choices[0].message.content
