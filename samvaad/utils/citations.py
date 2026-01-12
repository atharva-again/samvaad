import html
from typing import Any


def format_rag_context(chunks: list[dict[str, Any]], max_content_length: int = 500) -> str:
    """
    Standardizes RAG chunk formatting into XML tags for LLM consumption.

    Args:
        chunks: List of document chunks from retrieval
        max_content_length: Maximum length of content per chunk to prevent token explosion

    Returns:
        XML-formatted string like <document id="1">...</document>
    """
    if not chunks:
        return "No relevant information found in the knowledge base."

    context_parts = []
    for i, chunk in enumerate(chunks[:3], 1):
        content = chunk.get("content", "")
        # Apply truncation to prevent context window saturation
        truncated_content = content[:max_content_length]

        # [SECURITY-FIX #75] Escape content to prevent XML injection
        escaped_content = html.escape(truncated_content)

        # Use clean XML structure for reliable LLM parsing
        context_parts.append(f'<document id="{i}">\n{escaped_content}\n</document>')

    return "\n\n".join(context_parts)
