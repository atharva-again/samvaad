from .modes import get_mode_instruction
from .personas import get_persona_prompt
from .styles import VOICE_STYLE_INSTRUCTION


class PromptBuilder:
    """
    Unified prompt builder for all modes (text, voice, tool-based, pre-fetched context).

    Single source of truth for prompt assembly logic.
    Replaces scattered prompt building code across text_agent, voice_agent, generation, etc.

    Usage:
        # Voice mode with tools
        prompt = (PromptBuilder()
            .with_persona("tutor")
            .with_strict_mode(True)
            .for_voice_mode()
            .with_tools()
            .build())

        # Text mode with pre-fetched context
        prompt = (PromptBuilder()
            .with_persona("default")
            .with_strict_mode(False)
            .with_context(formatted_chunks)
            .with_history(conversation_history)
            .build())
    """

    def __init__(self):
        self.persona = "default"
        self.strict_mode = False
        self.is_voice = False
        self.has_tools = False
        self.context = ""
        self.history = ""
        self.additional_sections = []

    def with_persona(self, persona: str) -> "PromptBuilder":
        self.persona = persona
        return self

    def with_strict_mode(self, enabled: bool) -> "PromptBuilder":
        self.strict_mode = enabled
        return self

    def for_voice_mode(self) -> "PromptBuilder":
        self.is_voice = True
        return self

    def with_tools(self) -> "PromptBuilder":
        self.has_tools = True
        return self

    def with_context(self, context: str) -> "PromptBuilder":
        self.context = context
        return self

    def with_history(self, history: str) -> "PromptBuilder":
        self.history = history
        return self

    def add_section(self, section: str) -> "PromptBuilder":
        """Add custom sections like '### User Facts' or '### Conversation Summary'"""
        self.additional_sections.append(section)
        return self

    def build(self) -> str:
        """
        Assemble the final system prompt based on configuration.

        Logic:
        1. Voice mode: Persona + Mode (with voice style baked in)
        2. Text mode with tools: Persona + Mode + History
        3. Text mode with pre-fetched context: Persona + Mode + XML structure (history, context)
        """
        persona_intro = get_persona_prompt(self.persona)
        mode_instruction = get_mode_instruction(self.strict_mode, is_voice=self.is_voice)

        if self.is_voice:
            base = f"{persona_intro}\n\n{mode_instruction}\n\n{VOICE_STYLE_INSTRUCTION}"
            if self.additional_sections:
                base += "\n\n" + "\n\n".join(self.additional_sections)
            return base

        if self.has_tools and not self.context:
            base = f"{persona_intro}\n\n{mode_instruction}"
            if self.history:
                base += f"\n\n### Conversation History\n{self.history}"
            else:
                base += "\n\n### Conversation History\nNo history yet."

            if self.additional_sections:
                base += "\n\n" + "\n\n".join(self.additional_sections)

            base += "\n\nProvide your answer:"
            return base

        history_section = self.history if self.history else "No history."
        context_section = self.context if self.context else "No context provided."

        prompt = f"""{persona_intro}

{mode_instruction}

### Input Data

<history>
{history_section}
</history>

<context>
{context_section}
</context>"""

        if self.additional_sections:
            prompt += "\n\n" + "\n\n".join(self.additional_sections)

        prompt += "\n\nProvide your answer:"
        return prompt
