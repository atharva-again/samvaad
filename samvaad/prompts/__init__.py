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
    Main entry point to generate the full system prompt.
    
    Args:
        preformatted_context: If provided, used directly instead of formatting context_chunks.
                             This avoids duplicate formatting when context_manager already formatted chunks.
    """
    # 1. Get Persona
    persona_intro = get_persona_prompt(persona)

    # 2. Build Context String
    if preformatted_context:
        # Use pre-formatted context directly (from context_manager)
        full_context = preformatted_context
    else:
        # Format chunks here (fallback for backward compatibility)
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            content = chunk.get("content", "")
            # Assuming chunk['filename'] exists, otherwise use a safe get or index
            filename = chunk.get("filename", f"doc_{i}") 
            context_parts.append(f'<document id="{i}" source="{filename}">\n{content}\n</document>')
        
        full_context = "\n".join(context_parts)

    # 3. Get Mode Instruction
    mode_inst = get_mode_instruction(strict_mode)

    # 4. Combine
    return get_unified_system_prompt(
        persona_intro=persona_intro,
        context=full_context,
        mode_instruction=mode_inst,
        conversation_history=conversation_history,
        query=query
    )
