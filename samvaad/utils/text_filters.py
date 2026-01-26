"""
Custom text filters for Pipecat TTS pipeline.

These filters process text before it's sent to TTS services,
allowing content to appear in transcripts but not be spoken.
"""

import re
from typing import Any, Mapping

from pipecat.utils.text.base_text_filter import BaseTextFilter


class CitationTextFilter(BaseTextFilter):
    """
    Strips citation markers [1], [2], etc. from text before TTS.

    Citations remain in the original LLM output for transcript persistence,
    but are removed before the text is spoken.

    Matches patterns like: [1], [2], [10], [123]
    Note: Only handles individual citations like [1], not ranges [1-3] or lists [1,2]
    """

    # Regex to match citation patterns: [1], [2], [10], etc.
    CITATION_PATTERN = re.compile(r"\[\d+\]")

    async def filter(self, text: str) -> str:
        """Remove citation markers from text."""
        # Remove citations and clean up any double spaces left behind
        result = self.CITATION_PATTERN.sub("", text)
        result = re.sub(r"\s{2,}", " ", result)  # Collapse multiple spaces
        return result.strip()

    async def update_settings(self, settings: Mapping[str, Any]) -> None:
        """No configurable settings for this filter."""
        pass

    async def handle_interruption(self) -> None:
        """Stateless filter - nothing to reset on interruption."""
        pass

    async def reset_interruption(self) -> None:
        """Stateless filter - nothing to reset."""
        pass
