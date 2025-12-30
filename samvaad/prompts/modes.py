"""
Mode Instructions for Samvaad

Provides mode-specific instructions (Strict vs Hybrid) for the LLM.
Used by unified_context.py to build system prompts.
"""


def get_mode_instruction(
    persona_intro: str,
    strict_mode: bool,
    is_voice: bool = False
) -> str:
    """
    Returns the core instruction block based on mode.
    Now standardized to always assume tool capabilities (or framework-managed tools).
    Distinction is mainly between Voice (natural, concise) vs Text (formatted, cited).
    """
    if strict_mode:
        base_instruction = """### Strict Mode
1. **Search First**: Always use `fetch_context` to find information.
2. **No Internal Knowledge**: Answer ONLY using the content found in the tool results. If the answer isn't there, state "I don't have information about that."
3. **Citations**: 
   - The tool provides content in `<document id="X">` tags.
   - You must cite the ID number: `[1]`, `[2]`.
   - **NEVER** use filenames like `[file.pdf]`.

### Conversational Rules
- Resolve pronouns (it, him, that) using the chat history before searching.
- If asking follow-up questions, remember the previous context."""

        if is_voice:
            return base_instruction + "\n\n### Output Format\nSpeak naturally. Say citation numbers naturally, e.g. 'According to document one' or 'as shown in source two.' Always include `[1]`, `[2]` in your text when citing. Short answers. No markdown."
        else:
            return base_instruction + "\n\n### Output Format\nUse markdown. Cite sources using [1], [2] format. No references section."

    else:
        # Hybrid Mode
        base_instruction = """### Hybrid Mode
1. **Persona**: Follow your persona instructions.
2. **Knowledge**: Use your own knowledge for general questions.
3. **Tools**: Use `fetch_context` ONLY when the user asks about specific documents, files, or uploaded notes.
4. **Citations**:
   - If you use tool content, cite it using `[1]`, `[2]` matching the `<document id="X">` tags.
   - **NEVER** use filenames.

### Conversational Rules
- Resolve pronouns using history.
- Maintain context across turns."""

        if is_voice:
            return base_instruction + "\n\n### Output Format\nSpeak naturally. When citing tool results, include `[1]`, `[2]` markers. Complete sentences. No markdown."
        else:
            return base_instruction + "\n\n### Output Format\nUse markdown. Cite sources using [1], [2] format. No references section."


def get_unified_system_prompt(
    persona_intro: str,
    context: str,
    mode_instruction: str,
    conversation_history: str | None = None,
    query: str | None = None
) -> str:
    """
    Constructs the final system prompt with XML-structured input data.
    Used for text mode where context is pre-fetched.
    
    Note: query parameter kept for backward compatibility but not used in prompt.
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
