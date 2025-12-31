from unittest.mock import MagicMock, patch

from samvaad.pipeline.generation.generation import generate_answer_with_groq


@patch("samvaad.pipeline.generation.generation.Groq")
@patch("os.getenv")
def test_hallucination_prevention(mock_getenv, mock_groq_class):
    # Setup
    mock_getenv.return_value = "fake_key"

    # Mock LLM to simulate behaving correctly (since we can't really call LLM in unit test)
    # Ideally this would be a real integration test, but for now we verify the PROMPT contains the right instructions
    # and we can simulate the LLM's "decision" by checking what prompt was sent.

    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    # Context is irrelevant (Ballism)
    chunks = [
        {
            "content": "Ballism is the theory that everything becomes spherical.",
            "filename": "ballism.txt",
        }
    ]
    query = "Who is Lionel Messi?"

    # Run generation
    generate_answer_with_groq(query, chunks, strict_mode=False, persona="friend")

    # Get the actual call arguments
    call_args = mock_client.chat.completions.create.call_args
    sent_messages = call_args.kwargs["messages"]
    system_prompt = sent_messages[0]["content"]

    # 1. Verify Core Concepts
    assert "hybrid mode" in system_prompt.lower()
    assert "persona" in system_prompt.lower()
    assert "context" in system_prompt.lower()

    # 2. Verify Hallucination Prevention Elements
    assert "follow your persona" in system_prompt.lower()
    assert "resolve pronouns" in system_prompt.lower()

    # 3. Verify Input Data Structure
    assert "<history>" in system_prompt
    assert "</history>" in system_prompt
    assert "<context>" in system_prompt
    assert "</context>" in system_prompt
    assert "provide your answer" in system_prompt.lower()

    print("\n[PASS] Prompt contains Permissive Soft-RAG instructions.")
