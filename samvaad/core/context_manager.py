"""
Context Manager - Manages conversation context within token budget.
Implements hybrid sliding window + summary buffer approach.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import tiktoken


@dataclass
class ContextBudget:
    """Token budget allocation for context window."""
    total_budget: int = 8000  # Conservative limit for Groq's 8k context
    system_prompt: int = 500
    summary_buffer: int = 1000
    recent_messages: int = 4000
    rag_context: int = 2500


class ConversationContextManager:
    """
    Manages context window for conversations using hybrid approach:
    - Recent messages: kept verbatim (sliding window)
    - Older messages: summarized (summary buffer)
    - RAG chunks: truncated to fit budget
    """
    
    def __init__(self, budget: Optional[ContextBudget] = None):
        self.budget = budget or ContextBudget()
        # cl100k_base is compatible with GPT-4 and Groq's Llama models
        self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        if not text:
            return 0
        return len(self.encoder.encode(text))
    
    def count_message_tokens(self, messages: List[Dict]) -> int:
        """Count total tokens in a list of messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.count_tokens(content)
            # Add overhead for role/structure (~4 tokens per message)
            total += 4
        return total
    
    def build_context(
        self,
        messages: List[Dict],
        rag_chunks: List[Dict],
        conversation_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build optimized context within token budget.
        
        Args:
            messages: List of {role, content} dicts
            rag_chunks: List of {content, filename} dicts from RAG
            conversation_summary: Pre-computed summary of older messages
            
        Returns:
            Dict with summary, recent_history, rag_context, and token counts
        """
        # 1. Get recent messages within budget (sliding window)
        recent_messages, older_messages = self._split_messages_by_budget(
            messages, self.budget.recent_messages
        )
        
        # 2. Use provided summary or generate placeholder for older messages
        summary = conversation_summary or ""
        if older_messages and not summary:
            # If we have older messages but no summary, create a simple one
            # (Full LLM summarization would be done async via trigger)
            summary = self._create_simple_summary(older_messages)
        
        # Truncate summary if too long
        summary = self._truncate_to_budget(summary, self.budget.summary_buffer)
        
        # 3. Truncate RAG context to budget
        rag_context = self._format_rag_chunks(rag_chunks, self.budget.rag_context)
        
        # 4. Format recent messages as history string
        recent_history = self._format_messages(recent_messages)
        
        return {
            "summary": summary,
            "recent_history": recent_history,
            "rag_context": rag_context,
            "recent_messages": recent_messages,
            "older_messages_count": len(older_messages),
            "token_counts": {
                "summary": self.count_tokens(summary),
                "recent_history": self.count_tokens(recent_history),
                "rag_context": self.count_tokens(rag_context),
            }
        }
    
    def _split_messages_by_budget(
        self, 
        messages: List[Dict], 
        token_limit: int
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Split messages into recent (within budget) and older.
        Works backwards from most recent to fill the budget.
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
        older = messages[:-len(recent)] if recent else messages
        return recent, older
    
    def _create_simple_summary(self, messages: List[Dict]) -> str:
        """
        Create a simple summary without LLM call.
        For proper summarization, use summarize_with_llm() method.
        """
        if not messages:
            return ""
        
        # Simple approach: take first user message and last exchange
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
        summary_parts.append(
            f"[{user_count} user messages and {assistant_count} assistant replies summarized]"
        )
        
        return " ".join(summary_parts)
    
    def _truncate_to_budget(self, text: str, token_limit: int) -> str:
        """Truncate text to fit within token limit."""
        if not text:
            return ""
        
        tokens = self.encoder.encode(text)
        if len(tokens) <= token_limit:
            return text
        
        truncated_tokens = tokens[:token_limit]
        return self.encoder.decode(truncated_tokens) + "..."
    
    def _format_messages(self, messages: List[Dict]) -> str:
        """Format messages as a conversation history string."""
        if not messages:
            return ""
        
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_label = "User" if role == "user" else "Assistant"
            lines.append(f"{role_label}: {content}")
        
        return "\n".join(lines)
    
    def _format_rag_chunks(self, chunks: List[Dict], token_limit: int) -> str:
        """Format and truncate RAG chunks to fit token budget."""
        if not chunks:
            return ""
        
        result = []
        total_tokens = 0
        
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("content", "")
            filename = chunk.get("filename", f"doc_{i}")
            
            formatted = f'<document id="{i}" source="{filename}">\n{content}\n</document>'
            chunk_tokens = self.count_tokens(formatted)
            
            if total_tokens + chunk_tokens > token_limit:
                break
            
            result.append(formatted)
            total_tokens += chunk_tokens
        
        return "\n\n".join(result)
    
    def should_trigger_summarization(
        self,
        messages: List[Dict],
        trigger_threshold: int = 10
    ) -> bool:
        """
        Check if conversation should trigger summarization.
        Returns True if number of unsummarized messages exceeds threshold.
        """
        _, older_messages = self._split_messages_by_budget(
            messages, self.budget.recent_messages
        )
        return len(older_messages) >= trigger_threshold
    
    async def summarize_with_llm(
        self,
        messages: List[Dict],
        existing_summary: Optional[str] = None
    ) -> str:
        """
        Generate summary using LLM for older messages.
        Uses progressive summarization: incorporates existing summary.
        """
        from groq import Groq
        import os
        
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return self._create_simple_summary(messages)
        
        client = Groq(api_key=groq_key)
        
        # Build prompt for summarization
        context = ""
        if existing_summary:
            context = f"Previous summary:\n{existing_summary}\n\nNew messages to incorporate:\n"
        
        messages_text = self._format_messages(messages)
        
        prompt = f"""{context}{messages_text}

Create a concise summary (max 200 words) that captures:
1. Main topics discussed
2. Key questions asked by the user
3. Important information provided by the assistant
4. Any decisions or conclusions reached

Summary:"""
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a conversation summarizer. Be concise and focus on key information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Summarization error: {e}")
            return self._create_simple_summary(messages)
