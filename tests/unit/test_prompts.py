"""Test prompt generation functions."""

import pytest
from samvaad.prompts import get_system_prompt
from samvaad.prompts.personas import get_persona_prompt, PERSONAS
from samvaad.prompts.modes import get_mode_instruction


def test_get_persona_prompt_defaults():
    """Test default persona fallback."""
    assert get_persona_prompt("nonexistent") == PERSONAS["default"]
    assert get_persona_prompt("default") == PERSONAS["default"]


def test_get_persona_prompt_new_personas():
    """Test new persona types."""
    assert get_persona_prompt("friend") == PERSONAS["friend"]
    assert get_persona_prompt("expert") == PERSONAS["expert"]
    assert get_persona_prompt("quizzer") == PERSONAS["quizzer"]
    assert "human friend" in PERSONAS["friend"] or "friend" in PERSONAS["friend"].lower()
    assert "domain expert" in PERSONAS["expert"] or "expert" in PERSONAS["expert"].lower()
    assert "quiz" in PERSONAS["quizzer"].lower()


def test_get_mode_instruction_strict():
    """Test strict mode instruction content."""
    inst = get_mode_instruction(strict_mode=True)
    # Check for strict mode markers in current implementation
    assert "Strict Mode" in inst
    assert "don't know" in inst.lower() or "do not" in inst.lower()


def test_get_mode_instruction_hybrid():
    """Test hybrid mode instruction content."""
    inst = get_mode_instruction(strict_mode=False)
    # Hybrid mode should have different content than strict mode
    assert "Hybrid Mode" in inst
    # Strict mode marker should not be present
    assert "Strict Mode" not in inst


def test_get_system_prompt_structure():
    """Test that system prompt contains all key components."""
    chunks = [{"content": "Doc content", "filename": "doc1.txt"}]
    prompt = get_system_prompt(
        persona="friend",
        strict_mode=True,
        context_chunks=chunks,
        conversation_history="User said hi"
    )
    
    # Check for components - using markers from current implementation
    assert PERSONAS["friend"] in prompt
    assert "Doc content" in prompt
    assert "User said hi" in prompt
    assert "Strict Mode" in prompt
    # Current implementation uses "<context>" tags instead of "Instructions:"
    assert "<context>" in prompt or "context" in prompt.lower()
