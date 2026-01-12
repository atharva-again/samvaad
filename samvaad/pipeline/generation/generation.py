import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def generate_answer_with_groq(
    query: str,
    chunks: list[dict],
    model: str = "llama-3.3-70b-versatile",
    conversation_context: str = "",
    persona: str = "default",
    strict_mode: bool = False,
    rag_context: str = "",  # Pre-formatted context from context_manager
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

    from samvaad.prompts import PromptBuilder

    if rag_context:
        context = rag_context
    else:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("content", "")
            filename = chunk.get("filename", f"doc_{i}")
            context_parts.append(f'<document id="{i}" source="{filename}">\n{content}\n</document>')
        context = "\n".join(context_parts)

    prompt = (
        PromptBuilder()
        .with_persona(persona)
        .with_strict_mode(strict_mode)
        .with_context(context)
        .with_history(conversation_context)
        .with_query(query)
        .build()
    )

    # Initialize Groq client
    client = Groq(api_key=groq_key)

    # Generate response
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": query}],
        temperature=0.3,
        max_tokens=1024,
    )

    return response.choices[0].message.content
