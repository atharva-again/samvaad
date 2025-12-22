from .personas import get_persona_prompt
from .modes import get_mode_instruction, get_unified_system_prompt

def get_system_prompt(
    persona: str, 
    strict_mode: bool, 
    context_chunks: list[dict], 
    conversation_history: str = "",
    query: str = None,
    preformatted_context: str = ""  # Pre-formatted from context_manager
) -> str:
    """
    Build system prompt for text mode (pre-fetched context, no tools).
    
    For voice mode, use UnifiedContextManager.build_system_prompt() instead.
    
    Args:
        preformatted_context: If provided, used directly instead of formatting context_chunks.
    """
    # 1. Get Persona
    persona_intro = get_persona_prompt(persona)

    # 2. Build Context String
    if preformatted_context:
        full_context = preformatted_context
    else:
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            content = chunk.get("content", "")
            filename = chunk.get("filename", f"doc_{i}") 
            context_parts.append(f'<document id="{i}" source="{filename}">\n{content}\n</document>')
        full_context = "\n".join(context_parts)

    # 3. Get Mode Instruction (has_tools=False for text mode)
    mode_inst = get_mode_instruction(strict_mode, has_tools=False)

    # 4. Combine
    return get_unified_system_prompt(
        persona_intro=persona_intro,
        context=full_context,
        mode_instruction=mode_inst,
        conversation_history=conversation_history,
        query=query
    )

