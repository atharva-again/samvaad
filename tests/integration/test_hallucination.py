import pytest
from unittest.mock import MagicMock, patch
from samvaad.pipeline.generation.generation import generate_answer_with_groq

@patch('samvaad.pipeline.generation.generation.Groq')
@patch('os.getenv')
def test_hallucination_prevention(mock_getenv, mock_groq_class):
    # Setup
    mock_getenv.return_value = "fake_key"
    
    # Mock LLM to simulate behaving correctly (since we can't really call LLM in unit test)
    # Ideally this would be a real integration test, but for now we verify the PROMPT contains the right instructions
    # and we can simulate the LLM's "decision" by checking what prompt was sent.
    
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    
    # Context is irrelevant (Ballism)
    chunks = [{"content": "Ballism is the theory that everything becomes spherical.", "filename": "ballism.txt"}]
    query = "Who is Lionel Messi?"
    
    # Run generation
    generate_answer_with_groq(query, chunks, strict_mode=False, persona="friend")
    
    # Get the actual call arguments
    call_args = mock_client.chat.completions.create.call_args
    sent_messages = call_args.kwargs['messages']
    system_prompt = sent_messages[0]['content']
    
    # 1. Verify Instruction Presence
    # 1. Verify Structure and Tags
    assert "<context>" in system_prompt
    assert "</context>" in system_prompt
    assert "<query>" in system_prompt
    assert "Who is Lionel Messi?" in system_prompt 

    # 2. Verify Logic Instructions (Soft RAG + Subject Resolution)
    assert "Follow your assigned persona" in system_prompt
    assert "Subject Resolution (CRITICAL)" in system_prompt
    assert "CHECK THE `<history>` TAGS FIRST" in system_prompt
    assert "Identify who we are talking about" in system_prompt
    assert "Stick to this subject" in system_prompt
    assert "IGNORE IT COMPLETELY" in system_prompt
    
    # 3. Verify Constraints
    assert "Answer naturally" in system_prompt
    
    print("\n[PASS] Prompt contains Permissive Soft-RAG instructions.")
