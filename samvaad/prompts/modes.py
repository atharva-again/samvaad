"""
Mode Instructions for Samvaad

Provides mode-specific instructions (Strict vs Hybrid) for the LLM.
Used by unified_context.py to build system prompts.
"""


def get_mode_instruction(strict_mode: bool, is_voice: bool = False) -> str:
    """
    Returns the core instruction block based on mode.
    Now standardized to always assume tool capabilities (or framework-managed tools).
    Distinction is mainly between Voice (natural, concise) vs Text (formatted, cited).
    """
    if strict_mode:
        base_instruction = """### Strict Mode
1. **Persona**: Follow your persona instructions.
2. **Search First**: Always use `fetch_context` to find information.
3. **No Internal Knowledge**: Answer ONLY using the content found in the tool results. If the answer isn't there, state "I don't have information about that."
4. **Citations - CRITICAL**:
   - The tool returns content in `<document id="X">` tags where X is a number (1, 2, 3, etc.).
   - You MUST cite inline using `[1]`, `[2]`, `[3]` matching the document IDs.
   - Example: "According to the research [1], workers are using AI [2]."
   - **NEVER** use filenames like `[file.pdf]` - only use numeric IDs.
   - **NEVER** add a references section at the end.

### Conversational Rules
- Resolve pronouns (it, him, that) using the chat history before searching.
- If asking follow-up questions, remember the previous context."""

        return base_instruction

    else:
        # Hybrid Mode
        base_instruction = """### Hybrid Mode
1. **Persona**: Follow your persona instructions.
2. **Knowledge**: Use your own knowledge for general questions.
3. **Tools**: Use `fetch_context` when the user asks about documents, files, uploaded notes, or any factual question that may benefit from retrieved context.
4. **Citations - CRITICAL**:
   - When you use content from `fetch_context` results, you MUST cite using `[1]`, `[2]`, `[3]` inline.
   - Match citations to the `<document id="X">` tags in the tool response.
   - Example: "According to the research [1], workers are using AI tools [2]."
   - **NEVER** use filenames like `[file.pdf]`.
   - **NEVER** add a references section at the end.

### Conversational Rules
- Resolve pronouns using history.
- Maintain context across turns."""

        return base_instruction


def get_unified_system_prompt(
    persona_intro: str,
    context: str,
    mode_instruction: str,
    conversation_history: str | None = None,
) -> str:
    """
    Constructs the final system prompt with XML-structured input data.
    Used for text mode where context is pre-fetched.
    """
    return f"""{persona_intro}

{mode_instruction}

### Input Data

<history>
{conversation_history if conversation_history else "No history."}
</history>

<context>
{context if context else "No context provided."}
</context>

Provide your answer:"""
