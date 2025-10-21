from google import genai
from google.genai import types
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()


def generate_answer_with_gemini(
    query: str, chunks: List[Dict], model: str = "gemini-2.5-flash", conversation_context: str = ""
) -> str:
    """Generate answer using Google Gemini with retrieved chunks as context."""
    
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not gemini_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")

    # Build context from chunks (use full content)
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        content = chunk.get("content", "")
        context_parts.append(f"Document {i} ({chunk['filename']}):\n{content}\n")

    context = "\n".join(context_parts)

    # Create the prompt
    if conversation_context:
        prompt = f"""You are a helpful assistant engaged in a conversation. Use the conversation history and provided context to give relevant, contextual answers.

                Conversation History:
                {conversation_context}

                Document Context:
                {context}

                Current Question: {query}

                Instructions:
                - If the conversation history is empty, answer based only on the document context.
                - If the conversation history is not empty, only then consider the conversation history when answering
                - Answer based on the document context when relevant, but use conversation context for coherence (if available)
                - If the documents don't contain relevant information, answer based on the conversation flow
                - Be concise but comprehensive
                - Respond in the same language and style as the user
                - Use lists if and only if necessary. Even then, use numbered lists instead of bullet points.
                - Don't use nested lists. If answers are in nested format, use headings like 'Section 1', 'Section 2', etc.
                - Include a conclusion if appropriate.
                Answer:"""
    else:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
        prompt = f"""You are a helpful assistant that answers questions based on the provided context.

                    Document Context:
                    {context}

                    Question: {query}

                    Instructions:
                    - Answer the question based only on the information provided in the context above.
                    - If the context doesn't contain enough information to answer the question, say so.
                    - Be concise but comprehensive.
                    - Respond in the same language and style as the question.
                    - Use lists if and only if necessary. Even then, use numbered lists instead of bullet points.
                    - Don't use nested lists. If answers are in nested format, use headings like 'Section 1', 'Section 2', etc.
                    - Include a conclusion if appropriate.
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
            thinking_config=types.ThinkingConfig(
                thinking_budget=0
            ),  # Disable thinking for speed
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="NONE")
            ),
        ),
    )

    return response.text
