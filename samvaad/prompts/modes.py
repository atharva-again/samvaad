from typing import Optional

def get_mode_instruction(strict_mode: bool) -> str:
    """Returns the instruction set for Strict or Hybrid mode."""
    if strict_mode:
        return """
        ### Strict Mode Instructions
        
        1. **Goal**: Answer **ONLY** using the information provided in the `<context>` tags.
        2. **Constraint**: Do **NOT** use your own internal knowledge.
        3. **Refusal**: If the answer is NOT in `<context>`, you **MUST** say: "I don't know.".
        """
    else:
        return """
        ### Hybrid Mode Instructions
        
        **Follow your assigned persona.**
        
        1. **Goal**: Answer the user's question directly and helpfully.
        2. **Subject Resolution (CRITICAL)**: 
           - If the user says "him", "it", "that", or "tell me more", CHECK THE `<history>` TAGS FIRST.
           - Identify who we are talking about (e.g., "Lionel Messi"). 
           - **Stick to this subject**. Do not switch subjects just because the retrieval text talks about someone else.
        3. **Context Check**: Now look at `<context>`.
           - **Think**: "Does this context have information about [Identified Subject]?"
           - **Action**: 
             - If **YES**, use it.
             - If **NO**, or if it's irrelevant, **IGNORE IT COMPLETELY**.
        4. **Knowledge**: Use your own internal knowledge about [Identified Subject] if the context is irrelevant.
        
        ### Constraints
        - Answer naturally.
        - Do not mention "context" or "RAG" in your final answer.
        """

def get_unified_system_prompt(persona_intro: str, context: str, mode_instruction: str, conversation_history: Optional[str] = None, query: Optional[str] = None) -> str:
    """
    Constructs the final system prompt. 
    Unified to handle both history-present and history-absent cases seamlessly.
    """
    history_section = ""
    if conversation_history:
        history_section = f"""
        Conversation History:
        {conversation_history}
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
    
    <query>
    {query if query else "N/A"}
    </query>
    
    ### Output
    Based on the above instructions and data, provide your Answer, but don't include your thinking process:"""
