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
    strict_mode: bool = False
) -> str:
    """Generate answer using Groq with retrieved chunks as context."""
    
    groq_key = os.getenv("GROQ_API_KEY")

    if not groq_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    
    from samvaad.prompts import get_system_prompt

    # Build context chunks with filename fallback if needed
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
