from google import genai
from google.genai import types
from typing import List, Dict, Any
import os

def generate_answer_with_gemini(query: str, chunks: List[Dict], model: str = "gemini-2.5-flash") -> str:
    """Generate answer using Google Gemini with retrieved chunks as context."""
    # DEBUG: Print GEMINI_API_KEY (masked)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print(f"[DEBUG] GEMINI_API_KEY loaded")
    else:
        print("[DEBUG] GEMINI_API_KEY is NOT loaded (None or empty)")

    # Build context from chunks (use full content)
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        content = chunk.get('content', '')
        context_parts.append(f"Document {i} ({chunk['filename']}):\n{content}\n")

    context = "\n".join(context_parts)

    # Create the prompt
    prompt = f"""You are a helpful assistant that answers questions based on the provided context.

                Context:
                {context}

                Question: {query}

                Instructions:
                - Answer the question based only on the information provided in the context above.
                - If the context doesn't contain enough information to answer the question, say so.
                - Be concise but comprehensive.
                - Cite the specific documents you used in your answer.
                - If multiple documents are relevant, mention them all.
                - Respond in the same language and style as the question.

                Answer:"""

    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    # Generate response
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,  # Slightly higher to encourage concise responses
            max_output_tokens=1024,  # Limit response length to reduce token usage
            thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disable thinking for speed
        )
    )

    return response.text

