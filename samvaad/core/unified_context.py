"""
Unified Context Manager for Samvaad.

Single source of truth for context management across both text and voice modes.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

import tiktoken
from pipecat.processors.aggregators.llm_context import LLMContext, NOT_GIVEN

from samvaad.db.conversation_service import ConversationService
from samvaad.utils.logger import logger
from samvaad.utils.text import build_sliding_window_context, format_messages_for_prompt

SLIDING_WINDOW_SIZE = int(os.getenv("HISTORY_WINDOW_SIZE", "6"))


# ─────────────────────────────────────────────────────────────────────────────
# Pipecat Integration: SamvaadLLMContext
# ─────────────────────────────────────────────────────────────────────────────


class SamvaadLLMContext(LLMContext):
    """
    Database-backed LLM context manager for Pipecat voice pipelines.

    Extends LLMContext with:
    - Sliding window context management (via UnifiedContextManager)
    - Database persistence for messages
    - Automatic fact extraction & summarization orchestration

    Uses the same context logic as text mode for consistency.

    Migration Notes (2025-01):
    - Migrated from deprecated OpenAILLMContext to LLMContext
    - Updated to use LLMContextAggregatorPair instead of llm.create_context_aggregator
    - Tools wrapped in ToolsSchema for compatibility
    - conversation_id now optional (generates UUID if None)
    """

    def __init__(
        self,
        conversation_id: str | None,
        user_id: str,
        conversation_service: ConversationService | None = None,
        tools=None,
        tool_choice=None,
    ):
        """
        Initialize context with database backing and unified context management.

        Args:
            conversation_id: UUID string of the conversation (None to generate new)
            user_id: UUID of the user
            conversation_service: Optional injected service (for testing)
            tools: Tools for the LLM
            tool_choice: Tool choice setting
        """
        if conversation_id is None:
            import uuid

            conversation_id = str(uuid.uuid4())

        super().__init__(
            messages=[],
            tools=tools if tools is not None else NOT_GIVEN,
            tool_choice=tool_choice if tool_choice is not None else NOT_GIVEN,
        )
        self.conversation_id = conversation_id
        self.user_id = user_id
        self._db = conversation_service or ConversationService()
        self._context_manager = UnifiedContextManager(conversation_id, user_id, conversation_service)
        self._initialized = False

    def load_history(self):
        """
        Load recent messages from database with sliding window.
        Only loads messages within the window to prevent token explosion.
        """
        if self._initialized:
            return

        all_messages = self._db.get_messages(UUID(self.conversation_id))
        messages = [{"role": msg.role, "content": msg.content} for msg in all_messages]

        recent_messages, older_messages = self._context_manager.get_sliding_window(messages, SLIDING_WINDOW_SIZE)

        for msg in recent_messages:
            # Cast dict to expected type
            from typing import cast
            from openai.types.chat import ChatCompletionMessageParam

            super().add_message(cast(ChatCompletionMessageParam, msg))

        self._initialized = True

        if older_messages:
            logger.info(
                f"[VoiceContext] Loaded {len(recent_messages)} recent messages "
                f"({len(older_messages)} older messages summarized)"
            )

    def add_message(self, message):
        """
        Override: Add message to in-memory context AND trigger background persistence/tasks.
        """
        role = ""
        content = ""
        sources = None

        # Type guard for message access
        if isinstance(message, dict):
            role = message.get("role", "")
            content = message.get("content", "")
            sources = message.get("sources")
        else:
            # Fallback for non-dict messages (though we expect dict)
            content = str(getattr(message, "content", ""))

        # Add to in-memory context (super().add_message handles system messages correctly)
        from typing import cast
        from openai.types.chat import ChatCompletionMessageParam

        super().add_message(cast(ChatCompletionMessageParam, message))

        if role == "assistant" and self.user_id and self.conversation_id:
            # Find the last user message to pair with this assistant response
            messages = self.get_messages()
            user_msg = ""
            for m in messages[:-1]:
                if isinstance(m, dict) and m.get("role") == "user":
                    user_msg = str(m.get("content", ""))
                    break

            # Trigger centralized orchestration for background tasks
            if user_msg:
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        self._context_manager.run_post_response_tasks(
                            user_message=user_msg,
                            assistant_response=str(content),
                            sources=sources,
                        )
                    )
                except RuntimeError:
                    # Fallback for sync environments
                    self._context_manager.save_message("user", user_msg)
                    self._context_manager.save_message("assistant", str(content))


# ─────────────────────────────────────────────────────────────────────────────
# Token Budget Configuration
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ContextBudget:
    """Token budget allocation for context window."""

    total_budget: int = 8000
    system_prompt: int = 500
    facts_state: int = 500
    summary: int = 700
    recent_messages: int = 1500
    rag_context: int = 1000


class UnifiedContextManager:
    """
    Single source of truth for context management in text and voice modes.

    Provides:
    - Token counting with tiktoken (cl100k_base encoding) + LRU caching
    - Sliding window for recent messages
    - Database persistence with proper UUID handling
    - Summarization & fact extraction orchestration
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
    # Sliding Window
    # ─────────────────────────────────────────────────────────────────────────

    def get_sliding_window(
        self, messages: list[dict], window_size: int = SLIDING_WINDOW_SIZE
    ) -> tuple[list[dict], list[dict]]:
        """
        Split messages into recent (within window) and older messages.
        Simple count-based sliding window.
        """
        if len(messages) <= window_size:
            return messages, []
        return messages[-window_size:], messages[:-window_size]

    # ─────────────────────────────────────────────────────────────────────────
    # Database Operations
    # ─────────────────────────────────────────────────────────────────────────

    def save_message(self, role: str, content: str) -> None:
        """
        Persist message to database with proper UUID handling.
        """
        try:
            # Ensure conversation exists before saving message
            self._db.get_or_create_conversation(self.conversation_id, self.user_id)
            self._db.add_message(conversation_id=self.conversation_id, role=role, content=content)
        except Exception as e:
            logger.error(f"[Context] Failed to persist message: {e}")

    def load_messages(self) -> list[dict]:
        """
        Load messages from database.
        """
        try:
            messages = self._db.get_messages(self.conversation_id)
            return [{"role": msg.role, "content": msg.content} for msg in messages]
        except Exception as e:
            logger.error(f"[Context] Failed to load messages: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Orchestration & Background Tasks
    # ─────────────────────────────────────────────────────────────────────────

    async def run_post_response_tasks(
        self,
        user_message: str,
        assistant_response: str,
        current_summary: str | None = None,
        current_facts: str | None = None,
        sources: list[dict] | None = None,
    ) -> None:
        """
        Orchestrates background tasks after an assistant response.
        Handles:
        1. Persisting messages to DB
        2. Triggering summarization if needed
        3. Triggering fact extraction
        """
        # 1. Save messages to database
        self.save_message("user", user_message)
        self.save_message("assistant", assistant_response)

        # 2. Extract facts from this exchange
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._extract_facts_async(user_message, assistant_response, current_facts))
        except RuntimeError:
            pass

        # 3. Handle sliding window and summarization
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._trigger_summarization_if_needed(current_summary))
        except RuntimeError:
            pass

    async def _extract_facts_async(self, user_message: str, assistant_message: str, existing_facts: str | None = None):
        """Background: Extract and merge facts, save to Conversation.facts."""
        from samvaad.core.memory import extract_facts_from_exchange

        try:
            # Get latest facts from DB if not provided
            if existing_facts is None:
                conversation = self._db.get_conversation(self.conversation_id, self.user_id)
                existing_facts_str: str = str(conversation.facts or "") if conversation else ""
                existing_facts = existing_facts_str

            # LLM merges existing + new facts
            merged_facts = await extract_facts_from_exchange(
                user_message, assistant_message, existing_facts=existing_facts
            )

            if merged_facts:
                updated_facts = ". ".join([f.get("fact", "") for f in merged_facts if f.get("fact")])
                self._db.update_conversation(self.conversation_id, self.user_id, facts=updated_facts)
                logger.info(f"[Context] Updated facts for {self.conversation_id}")
        except Exception as e:
            logger.error(f"[Context] Fact extraction error: {e}")

    async def _trigger_summarization_if_needed(self, existing_summary: str | None = None):
        """
        Check and trigger summarization (batched every 4 messages outside window).
        """
        from samvaad.core.memory import update_conversation_summary

        try:
            all_messages = self.load_messages()
            total_messages = len(all_messages)

            SUMMARIZATION_BATCH_SIZE = 4

            if total_messages > SLIDING_WINDOW_SIZE:
                messages_in_window = SLIDING_WINDOW_SIZE
                exited_count = total_messages - messages_in_window

                if exited_count >= SUMMARIZATION_BATCH_SIZE and exited_count % SUMMARIZATION_BATCH_SIZE < 2:
                    batch_start = max(0, exited_count - SUMMARIZATION_BATCH_SIZE)
                    exiting_batch = all_messages[batch_start:exited_count] if batch_start < len(all_messages) else []

                    if exiting_batch:
                        if existing_summary is None:
                            conversation = self._db.get_conversation(self.conversation_id, self.user_id)
                            existing_summary_str: str = str(conversation.summary or "") if conversation else ""
                            existing_summary = existing_summary_str

                        start_turn = batch_start + 1
                        end_turn = exited_count

                        new_summary = await update_conversation_summary(
                            existing_summary,
                            exiting_batch,
                            start_turn=start_turn,
                            end_turn=end_turn,
                        )

                        self._db.update_conversation(self.conversation_id, self.user_id, summary=new_summary)
                        logger.info(
                            f"[Context] Updated summary for {self.conversation_id} (turns {start_turn}-{end_turn})"
                        )
        except Exception as e:
            logger.error(f"[Context] Summarization error: {e}")
