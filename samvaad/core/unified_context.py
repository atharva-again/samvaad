"""
Unified Context Manager for Samvaad.

Single source of truth for context management across both text and voice modes.
Consolidates features from the deprecated ConversationContextManager.

Features:
- Token counting (tiktoken) with LRU caching
- Sliding window context building
- RAG context formatting with XML tags
- Unified system prompt generation
- Database persistence with proper UUID handling
- Summarization support
- Pipecat integration (SamvaadLLMContext)
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

import tiktoken
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

from samvaad.db.conversation_service import ConversationService
from samvaad.prompts.modes import get_mode_instruction, get_unified_system_prompt
from samvaad.prompts.personas import get_persona_prompt

# Voice-specific style instructions for ~50 word responses
VOICE_STYLE_INSTRUCTION = """

VOICE CONVERSATION STYLE:
1. Keep responses brief (2-3 sentences, ~50 words max).
2. Speak naturally and conversationally. Use contractions.
3. After answering, invite follow-up questions.
4. Avoid bullet points, lists, or robotic phrasing.
"""

# Default sliding window size
# Default sliding window size
# [PHASE-3 #81] Configurable History Window
SLIDING_WINDOW_SIZE = int(os.getenv("HISTORY_WINDOW_SIZE", "6"))


# ─────────────────────────────────────────────────────────────────────────────
# Pipecat Integration: SamvaadLLMContext
# ─────────────────────────────────────────────────────────────────────────────


class SamvaadLLMContext(OpenAILLMContext):
    """
    Database-backed LLM context manager for Pipecat voice pipelines.

    Extends OpenAILLMContext to automatically:
    - Load existing conversation history from DB on init
    - Persist new messages to DB when added

    This enables seamless switching between voice and text modes
    within the same conversation.
    """

    def __init__(
        self, conversation_id: str, user_id: str, conversation_service: ConversationService | None = None, **kwargs
    ):
        """
        Initialize context with database backing.

        Args:
            conversation_id: UUID of the conversation
            user_id: UUID of the user
            conversation_service: Optional injected service (for testing)
            **kwargs: Passed to OpenAILLMContext (tools, tool_choice, etc.)
        """
        super().__init__(**kwargs)
        self.conversation_id = conversation_id
        self.user_id = user_id
        self._db = conversation_service or ConversationService()
        self._initialized = False

    def load_history(self):
        """
        Load existing messages from database into context.
        Call this after initialization to populate history.
        """
        if self._initialized:
            return

        messages = self._db.get_messages(UUID(self.conversation_id))
        for msg in messages:
            # Use parent's add_message to avoid re-persisting
            super().add_message({"role": msg.role, "content": msg.content})
        self._initialized = True

    def add_message(self, message):
        """
        Override: Add message to in-memory context AND persist to database.

        Voice mode messages are saved server-side since the frontend cache
        (IndexedDB) is local-only and doesn't sync to backend.

        Background fact extraction is triggered after assistant responses.

        Args:
            message: Dict with 'role' and 'content' keys
        """
        # Skip system messages - they don't need to be persisted
        role = message.get("role", "")
        if role == "system":
            super().add_message(message)
            return

        # Add to in-memory context
        super().add_message(message)

        # Persist to database
        if self.conversation_id and self.user_id and role in ("user", "assistant"):
            try:
                content = message.get("content", "")
                sources = message.get("sources", [])

                # Fire-and-forget in background to avoid blocking pipeline
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._save_message_async(role, content, sources))
                except RuntimeError:
                    # No running loop - save synchronously as fallback
                    self._db.add_message(
                        conversation_id=UUID(self.conversation_id),
                        role=role,
                        content=content,
                        sources=sources if sources else None,
                    )
            except Exception as e:
                # Log but don't fail the pipeline
                import logging

                logging.getLogger(__name__).warning(f"[SamvaadLLMContext] Failed to persist message: {e}")

        # Trigger background fact extraction after assistant response
        if role == "assistant" and self.user_id and self.conversation_id:
            # Get the previous user message for fact extraction
            messages = self.get_messages()
            if len(messages) >= 2:
                # Find the last user message before this assistant response
                user_msg = None
                for m in reversed(messages[:-1]):  # Exclude the just-added assistant msg
                    if m.get("role") == "user":
                        user_msg = m.get("content", "")
                        break

                if user_msg:
                    # Fire-and-forget background task
                    import asyncio

                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._extract_facts_async(user_msg, message.get("content", "")))
                    except RuntimeError:
                        # No running loop - skip fact extraction
                        pass

    async def _save_message_async(self, role: str, content: str, sources: list = None):
        """Background task to save message to database."""
        try:
            # Ensure conversation exists before saving message
            self._db.get_or_create_conversation(UUID(self.conversation_id), self.user_id)

            self._db.add_message(
                conversation_id=UUID(self.conversation_id),
                role=role,
                content=content,
                sources=sources if sources else None,
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"[SamvaadLLMContext] Background save failed: {e}")

    async def _extract_facts_async(self, user_message: str, assistant_message: str):
        """Background: Extract and merge facts, save to Conversation.facts."""
        from samvaad.core.memory import extract_facts_from_exchange

        try:
            # Get current facts
            conversation = self._db.get_conversation(UUID(self.conversation_id), self.user_id)
            existing_facts = conversation.facts if conversation else ""

            # LLM merges existing + new facts, handles deduplication
            merged_facts = await extract_facts_from_exchange(
                user_message, assistant_message, existing_facts=existing_facts
            )

            if merged_facts:
                # Format merged facts as simple text
                updated_facts = ". ".join([f.get("fact", "") for f in merged_facts if f.get("fact")])

                self._db.update_conversation(UUID(self.conversation_id), self.user_id, facts=updated_facts)
                print(f"[Voice Memory] Updated facts for {self.conversation_id}")
        except Exception as e:
            print(f"[Voice Memory] Fact extraction error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Token Budget Configuration
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ContextBudget:
    """Token budget allocation for context window."""

    total_budget: int = 8000  # Efficient allocation
    system_prompt: int = 500  # Persona + instructions
    facts_state: int = 500  # Inline facts/preferences (increased for 20 facts)
    summary: int = 700  # Turn-range summary
    recent_messages: int = 1500  # JIT sliding window
    rag_context: int = 1000


class UnifiedContextManager:
    """
    Single source of truth for context management in text and voice modes.

    Provides:
    - Token counting with tiktoken (cl100k_base encoding) + LRU caching
    - Sliding window for recent messages
    - Structured RAG context formatting
    - Unified system prompt generation
    - Database persistence with proper UUID handling
    - Summarization support
    """

    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        conversation_service: ConversationService | None = None,
        budget: ContextBudget | None = None,
    ):
        """
        Initialize unified context manager.

        Args:
            conversation_id: UUID string of the conversation
            user_id: UUID string of the user
            conversation_service: Optional injected service (for testing)
            budget: Optional token budget configuration
        """
        self.conversation_id = UUID(conversation_id)
        self.user_id = user_id
        self._db = conversation_service or ConversationService()
        self.budget = budget or ContextBudget()
        # cl100k_base is compatible with GPT-4 and Groq's Llama models
        self.encoder = tiktoken.get_encoding("cl100k_base")

    # ─────────────────────────────────────────────────────────────────────────
    # Token Counting (with LRU cache)
    # ─────────────────────────────────────────────────────────────────────────

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken with caching."""
        if not text:
            return 0
        return self._count_tokens_cached(text)

    @lru_cache(maxsize=256)
    def _count_tokens_cached(self, text: str) -> int:
        """Cached token counting to avoid duplicate encoding."""
        return len(self.encoder.encode(text))

    def count_message_tokens(self, messages: list[dict]) -> int:
        """Count total tokens in a list of messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.count_tokens(content)
            # Add overhead for role/structure (~4 tokens per message)
            total += 4
        return total

    # ─────────────────────────────────────────────────────────────────────────
    # Sliding Window & Context Building
    # ─────────────────────────────────────────────────────────────────────────

    def get_sliding_window(
        self, messages: list[dict], window_size: int = SLIDING_WINDOW_SIZE
    ) -> tuple[list[dict], list[dict]]:
        """
        Split messages into recent (within window) and older messages.
        Simple count-based sliding window.

        Args:
            messages: List of message dicts with 'role' and 'content'
            window_size: Number of recent messages to keep

        Returns:
            (recent_messages, older_messages)
        """
        if len(messages) <= window_size:
            return messages, []
        return messages[-window_size:], messages[:-window_size]

    def get_sliding_window_by_tokens(self, messages: list[dict], token_limit: int) -> tuple[list[dict], list[dict]]:
        """
        Split messages into recent (within token budget) and older.
        Works backwards from most recent to fill the budget.

        Args:
            messages: List of message dicts
            token_limit: Maximum tokens for recent messages

        Returns:
            (recent_messages, older_messages)
        """
        recent = []
        total_tokens = 0

        for msg in reversed(messages):
            msg_tokens = self.count_tokens(msg.get("content", "")) + 4
            if total_tokens + msg_tokens > token_limit:
                break
            recent.insert(0, msg)
            total_tokens += msg_tokens

        # Older messages are everything not in recent
        older = messages[: -len(recent)] if recent else messages
        return recent, older

    def build_context(
        self, messages: list[dict], rag_chunks: list[dict], conversation_summary: str | None = None
    ) -> dict[str, Any]:
        """
        Build optimized context within token budget.

        Args:
            messages: List of {role, content} dicts
            rag_chunks: List of {content, filename} dicts from RAG
            conversation_summary: Pre-computed summary of older messages

        Returns:
            Dict with summary, recent_history, rag_context, and token counts
        """
        # 1. Get recent messages within budget (sliding window by tokens)
        recent_messages, older_messages = self.get_sliding_window_by_tokens(messages, self.budget.recent_messages)

        # 2. Use provided summary or generate placeholder for older messages
        summary = conversation_summary or ""
        if older_messages and not summary:
            summary = self._create_simple_summary(older_messages)

        # Truncate summary if too long
        summary = self._truncate_to_budget(summary, self.budget.summary_buffer)

        # 3. Truncate RAG context to budget
        rag_context = self.format_rag_context(rag_chunks, self.budget.rag_context)

        # 4. Format recent messages as history string
        recent_history = self.format_messages_for_prompt(recent_messages)

        # 5. Validate total doesn't exceed available budget
        available_budget = self.budget.total_budget - self.budget.system_prompt
        summary_tokens = self.count_tokens(summary)
        history_tokens = self.count_tokens(recent_history)
        rag_tokens = self.count_tokens(rag_context)
        total_tokens = summary_tokens + history_tokens + rag_tokens

        if total_tokens > available_budget:
            # Shrink RAG context to fit within budget
            overflow = total_tokens - available_budget
            new_rag_limit = max(500, self.budget.rag_context - overflow)
            rag_context = self.format_rag_context(rag_chunks, new_rag_limit)
            rag_tokens = self.count_tokens(rag_context)

        return {
            "summary": summary,
            "recent_history": recent_history,
            "rag_context": rag_context,
            "recent_messages": recent_messages,
            "older_messages_count": len(older_messages),
            "token_counts": {
                "summary": summary_tokens,
                "recent_history": history_tokens,
                "rag_context": rag_tokens,
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Formatting
    # ─────────────────────────────────────────────────────────────────────────

    def format_rag_context(self, chunks: list[dict], max_tokens: int = 2500) -> str:
        """
        Format RAG chunks with structured XML tags.

        Args:
            chunks: List of dicts with 'content' and 'filename' keys
            max_tokens: Maximum tokens for RAG context

        Returns:
            Formatted context string with <document> tags
        """
        if not chunks:
            return ""

        import html

        parts = []
        total_tokens = 0

        for i, chunk in enumerate(chunks, 1):
            # [SECURITY-FIX #75] Sanitize content to prevent injection via XML tags
            raw_content = chunk.get("content", "")
            # Escape XML special chars (<, >, &, ", ')
            content = html.escape(raw_content)

            # Sanitize filename too
            raw_filename = chunk.get("filename", f"doc_{i}")

            # Use strict XML format - NO source attribute to force numeric IDs
            formatted = f'<document id="{i}">\n{content}\n</document>'
            chunk_tokens = self.count_tokens(formatted)

            if total_tokens + chunk_tokens > max_tokens:
                break

            parts.append(formatted)
            total_tokens += chunk_tokens

        return "\n\n".join(parts)

    def format_messages_for_prompt(self, messages: list[dict]) -> str:
        """
        Format messages as conversation history string.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted history string
        """
        if not messages:
            return ""

        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_label = "User" if role == "user" else "Assistant"
            lines.append(f"{role_label}: {content}")

        return "\n".join(lines)

    def _truncate_to_budget(self, text: str, token_limit: int) -> str:
        """Truncate text to fit within token limit."""
        if not text:
            return ""

        tokens = self.encoder.encode(text)
        if len(tokens) <= token_limit:
            return text

        truncated_tokens = tokens[:token_limit]
        return self.encoder.decode(truncated_tokens) + "..."

    # ─────────────────────────────────────────────────────────────────────────
    # System Prompt Building
    # ─────────────────────────────────────────────────────────────────────────

    def build_system_prompt(
        self,
        persona: str,
        strict_mode: bool,
        rag_context: str,
        conversation_history: str,
        query: str,
        is_voice: bool = False,
        has_tools: bool = False,
    ) -> str:
        """
        Build unified system prompt for either text or voice mode.

        Args:
            persona: Persona name (default, tutor, coder, etc.)
            strict_mode: Whether strict mode is enabled
            rag_context: Pre-formatted RAG context (if pre-fetched)
            conversation_history: Pre-formatted conversation history
            query: Current user query
            is_voice: If True, uses lean format (no XML placeholders) + voice constraints
            has_tools: Whether LLM has access to fetch_context tool
                       (True for tool-based RAG, False for pre-fetched context)

        Returns:
            Complete system prompt
        """
        persona_intro = get_persona_prompt(persona)

        # Get mode instruction based on whether tools are available and if it's voice mode
        mode_instruction = get_mode_instruction(strict_mode=strict_mode, is_voice=is_voice)
        print(
            f"[UnifiedContext] DEBUG: strict_mode={strict_mode}, is_voice={is_voice}, mode_instruction starts with: {mode_instruction[:100]}..."
        )

        # Voice mode: Use lean format without XML placeholders
        # Pipecat manages conversation context as separate messages
        if is_voice:
            return f"""{persona_intro}

{mode_instruction}"""

        # Text mode with tools: Use lean format similar to voice (no empty XML tags)
        if has_tools and not rag_context:
            # [SECURITY-FIX #72] Do NOT interpolate query into system prompt.
            # The query is passed as the last user message in the message list.
            return f"""{persona_intro}

{mode_instruction}

### Conversation History
{conversation_history if conversation_history else "No history yet."}

Provide your answer:"""

        # Text mode with pre-fetched context: Use full unified prompt with XML structure
        return get_unified_system_prompt(
            persona_intro=persona_intro,
            context=rag_context,
            mode_instruction=mode_instruction,
            conversation_history=conversation_history,
            query=query,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Database Operations
    # ─────────────────────────────────────────────────────────────────────────

    def save_message(self, role: str, content: str) -> None:
        """
        Persist message to database with proper UUID handling.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content
        """
        try:
            # Ensure conversation exists before saving message
            self._db.get_or_create_conversation(self.conversation_id, self.user_id)
            self._db.add_message(conversation_id=self.conversation_id, role=role, content=content)
        except Exception as e:
            print(f"[UnifiedContextManager] Failed to persist message: {e}")

    def load_messages(self) -> list[dict]:
        """
        Load messages from database.

        Returns:
            List of message dicts with 'role' and 'content'
        """
        try:
            messages = self._db.get_messages(self.conversation_id)
            return [{"role": msg.role, "content": msg.content} for msg in messages]
        except Exception as e:
            print(f"[UnifiedContextManager] Failed to load messages: {e}")
            return []

    def get_conversation_summary(self) -> str | None:
        """
        Get conversation summary from database.

        Returns:
            Summary string or None
        """
        try:
            conversation = self._db.get_conversation(self.conversation_id, self.user_id)
            return conversation.summary if conversation else None
        except Exception as e:
            print(f"[UnifiedContextManager] Failed to get summary: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Summarization
    # ─────────────────────────────────────────────────────────────────────────

    def _create_simple_summary(self, messages: list[dict]) -> str:
        """
        Create a simple summary without LLM call.
        For proper LLM-based summarization, use memory.update_conversation_summary().
        """
        if not messages:
            return ""

        summary_parts = []

        # First user message (context)
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")[:200]
                summary_parts.append(f"Started with: {content}...")
                break

        # Count of messages summarized
        user_count = sum(1 for m in messages if m.get("role") == "user")
        assistant_count = sum(1 for m in messages if m.get("role") == "assistant")
        summary_parts.append(f"[{user_count} user messages and {assistant_count} assistant replies summarized]")

        return " ".join(summary_parts)

    def should_trigger_summarization(self, messages: list[dict], trigger_threshold: int = 10) -> bool:
        """
        Check if conversation should trigger summarization.
        Returns True if number of older messages exceeds threshold.
        """
        _, older_messages = self.get_sliding_window_by_tokens(messages, self.budget.recent_messages)
        return len(older_messages) >= trigger_threshold


# ─────────────────────────────────────────────────────────────────────────────
# NOTE: LLM-based summarization is in memory.py (update_conversation_summary)
# Use that function for proper summarization. _create_simple_summary above is
# a fallback for when LLM is unavailable.
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Standalone functions for backward compatibility (used by memory.py)
# ─────────────────────────────────────────────────────────────────────────────


def build_sliding_window_context(
    messages: list[dict], window_size: int = SLIDING_WINDOW_SIZE
) -> tuple[list[dict], list[dict]]:
    """
    Standalone function for backward compatibility.
    Split messages into sliding window (recent) and older messages.
    """
    if len(messages) <= window_size:
        return messages, []
    return messages[-window_size:], messages[:-window_size]


def format_messages_for_prompt(messages: list[dict]) -> str:
    """
    Standalone function for backward compatibility.
    Format messages as conversation history string for prompt.
    """
    if not messages:
        return ""

    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        role_label = "User" if role == "user" else "Assistant"
        lines.append(f"{role_label}: {content}")

    return "\n".join(lines)
