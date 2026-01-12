"""Test prompt generation functions."""

from samvaad.prompts import PromptBuilder
from samvaad.prompts.modes import get_mode_instruction
from samvaad.prompts.personas import PERSONAS, get_persona_prompt


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
    # Check for key phrase variations
    assert "don't have information" in inst.lower()


def test_get_mode_instruction_hybrid():
    """Test hybrid mode instruction content."""
    inst = get_mode_instruction(strict_mode=False)
    # Hybrid mode should have different content than strict mode
    assert "Hybrid Mode" in inst
    # Strict mode marker should not be present
    assert "Strict Mode" not in inst


def test_prompt_builder_structure():
    """Test that system prompt contains all key components."""
    prompt = (
        PromptBuilder()
        .with_persona("friend")
        .with_strict_mode(True)
        .with_context("Doc content")
        .with_history("User said hi")
        .build()
    )

    # Check for components
    assert PERSONAS["friend"] in prompt
    assert "Doc content" in prompt
    assert "User said hi" in prompt
    assert "Strict Mode" in prompt
    assert "<context>" in prompt
    assert "</context>" in prompt
    assert "Provide your answer:" in prompt
