"""
In-Chat Memory Service

Provides:
1. Complexity detection (heuristics)
2. Fact extraction (background)
3. Summarization (background)

Note: Sliding window and message formatting moved to unified_context.py
"""
from typing import List, Dict, Optional, Tuple
from uuid import UUID
import re

from groq import AsyncGroq
import os

# Import from unified source of truth
from samvaad.core.unified_context import (
    SLIDING_WINDOW_SIZE,
    build_sliding_window_context,
    format_messages_for_prompt
)


# ─────────────────────────────────────────────────────────────────────────────
# Complexity Detection (Heuristics)
# ─────────────────────────────────────────────────────────────────────────────

# Keywords that suggest user is referencing earlier conversation
HISTORY_REFERENCE_PATTERNS = [
    r"\b(earlier|before|previously|last time|remember when)\b",
    r"\b(we discussed|we talked about|you (said|mentioned|told me))\b",
    r"\b(as you (said|mentioned)|like you (said|mentioned))\b",
    r"\b(go back to|back to the|referring to)\b",
]

# Keywords that suggest synthesis/aggregation needs
SYNTHESIS_PATTERNS = [
    r"\b(compare|contrast|difference between|similarities)\b",
    r"\b(summarize|summary|recap|overview)\b",
    r"\b(all the|everything we|list all)\b",
    r"\b(how does .+ relate to)\b",
]

# Pronouns that might need resolution from history
AMBIGUOUS_REFERENCE_PATTERNS = [
    r"\b(tell me more about (it|that|this|him|her|them))\b",
    r"\b(what about (it|that|this))\b",
    r"\b(explain (it|that|this) further)\b",
]


def detect_query_complexity(query: str, recent_entities: List[str] = None) -> Dict:
    """
    Analyze query to determine if extended context (tools) might be needed.
    
    Returns:
        {
            "needs_history": bool,      # Likely needs search_conversation_history
            "needs_synthesis": bool,    # Likely needs aggregation
            "has_ambiguous_refs": bool, # Has pronouns that need resolution
            "signals": List[str],       # Which patterns matched
            "recommendation": str       # "baseline" | "may_need_tools" | "likely_needs_tools"
        }
    """
    query_lower = query.lower()
    signals = []
    
    # Check history references
    needs_history = False
    for pattern in HISTORY_REFERENCE_PATTERNS:
        if re.search(pattern, query_lower):
            needs_history = True
            signals.append(f"history_ref: {pattern}")
            break
    
    # Check synthesis needs
    needs_synthesis = False
    for pattern in SYNTHESIS_PATTERNS:
        if re.search(pattern, query_lower):
            needs_synthesis = True
            signals.append(f"synthesis: {pattern}")
            break
    
    # Check ambiguous references
    has_ambiguous_refs = False
    for pattern in AMBIGUOUS_REFERENCE_PATTERNS:
        if re.search(pattern, query_lower):
            has_ambiguous_refs = True
            signals.append(f"ambiguous_ref: {pattern}")
            break
    
    # Check if query mentions entities not in recent context
    mentions_old_entity = False
    if recent_entities:
        # Simple check: any word in query matches known entity?
        query_words = set(query_lower.split())
        for entity in recent_entities:
            if entity.lower() in query_words:
                # Entity mentioned - check if it's in recent messages
                # (This would need actual recent context to be accurate)
                pass
    
    # Determine recommendation
    score = sum([needs_history, needs_synthesis, has_ambiguous_refs])
    if score == 0:
        recommendation = "baseline"
    elif score == 1:
        recommendation = "may_need_tools"
    else:
        recommendation = "likely_needs_tools"
    
    return {
        "needs_history": needs_history,
        "needs_synthesis": needs_synthesis,
        "has_ambiguous_refs": has_ambiguous_refs,
        "signals": signals,
        "recommendation": recommendation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Summarization (Background Task)
# ─────────────────────────────────────────────────────────────────────────────

SUMMARIZATION_PROMPT = """You are a conversation summarizer. Create a concise summary.

Current summary:
{existing_summary}

New messages to incorporate:
{new_messages}

Write an updated summary (max 100 words) that:
1. Preserves key facts from previous summary
2. Adds important new information (topics, decisions, preferences)
3. Removes redundant details

Updated summary:"""


async def update_conversation_summary(
    existing_summary: str,
    exiting_messages: List[Dict],
    groq_api_key: str = None
) -> str:
    """
    Update conversation summary when messages exit the sliding window.
    Uses llama-3.1-8b-instant for cost efficiency.
    """
    if not exiting_messages:
        return existing_summary or ""
    
    api_key = groq_api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        # Fallback: simple concatenation
        new_content = format_messages_for_prompt(exiting_messages)
        return f"{existing_summary}\n{new_content}".strip()[:500]
    
    client = AsyncGroq(api_key=api_key)
    
    prompt = SUMMARIZATION_PROMPT.format(
        existing_summary=existing_summary or "No previous summary.",
        new_messages=format_messages_for_prompt(exiting_messages)
    )
    
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Memory] Summarization error: {e}")
        # Fallback
        return existing_summary or ""


# ─────────────────────────────────────────────────────────────────────────────
# Fact Extraction (Background Task)
# ─────────────────────────────────────────────────────────────────────────────

FACT_EXTRACTION_PROMPT = """Extract 0-3 key facts from this conversation exchange.
Only extract facts that would be useful to remember for future responses.
Focus on: user preferences, decisions made, important topics, named entities.

User: {user_message}
Assistant: {assistant_message}

Output as JSON array. If no important facts, output empty array [].
Example: ["User prefers Python over JavaScript", "Discussed AWS VPC networking"]

Facts:"""


async def extract_facts_from_exchange(
    user_message: str,
    assistant_message: str,
    groq_api_key: str = None
) -> List[Dict]:
    """
    Extract facts from a user-assistant exchange.
    Uses llama-3.1-8b-instant for cost efficiency.
    
    Returns:
        List of {"fact": str, "entity_name": str | None}
    """
    api_key = groq_api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        return []
    
    client = AsyncGroq(api_key=api_key)
    
    prompt = FACT_EXTRACTION_PROMPT.format(
        user_message=user_message,
        assistant_message=assistant_message
    )
    
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON array from response
        import json
        # Handle potential markdown code blocks
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        facts_raw = json.loads(content)
        
        # Convert to structured format
        facts = []
        for fact in facts_raw:
            if isinstance(fact, str):
                facts.append({"fact": fact, "entity_name": None})
            elif isinstance(fact, dict):
                facts.append(fact)
        
        return facts[:3]  # Max 3 facts per exchange
        
    except Exception as e:
        print(f"[Memory] Fact extraction error: {e}")
        return []
