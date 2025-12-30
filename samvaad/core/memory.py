"""
In-Chat Memory Service

Provides:
1. Complexity detection (heuristics)
2. Fact extraction (background)
3. Summarization (background)

Note: Sliding window and message formatting moved to unified_context.py
"""

import os
import re

from groq import AsyncGroq

# Import from unified source of truth
from samvaad.core.unified_context import format_messages_for_prompt

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


def detect_query_complexity(query: str, recent_entities: list[str] = None) -> dict:
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

SUMMARIZATION_PROMPT = """Summarize this conversation by grouping turns into topic ranges.

Previous summary:
{existing_summary}

New messages (turns {start_turn}-{end_turn}):
{new_messages}

Format your summary as:
- Start with: "Started with: [first topic]"
- Group turns: "Turns X-Y: [topic summary]"
- End with: "Currently: [what user is working on]"

Example:
"Started with: VPC networking basics.
Turns 1-4: Explained CIDR blocks and subnet design.
Turns 5-8: Deep dive into NAT Gateway vs NAT Instance.
Currently: User implementing private subnet routing."

Keep under 150 words. Preserve any user preferences mentioned.

Updated summary:"""


async def update_conversation_summary(
    existing_summary: str,
    exiting_messages: list[dict],
    start_turn: int = 1,
    end_turn: int = 1,
    groq_api_key: str = None,
) -> str:
    """
    Update conversation summary when messages exit the sliding window.
    Uses llama-3.1-8b-instant for cost efficiency.

    Args:
        existing_summary: Previous summary text
        exiting_messages: Messages to incorporate
        start_turn: Starting turn number for this batch
        end_turn: Ending turn number for this batch
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
        start_turn=start_turn,
        end_turn=end_turn,
        new_messages=format_messages_for_prompt(exiting_messages),
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

FACT_EXTRACTION_PROMPT = """You manage a list of facts about the user and conversation.

Current facts:
{existing_facts}

New exchange:
User: {user_message}
Assistant: {assistant_message}

Instructions:
1. Extract ALL new facts from this exchange (preferences, progress, decisions, entities).
2. Merge with existing facts to create a COMPREHENSIVE list. Do not drop valid facts.
3. **Resolve Conflicts with Recency Bias**:
   - If a new fact conflicts with an old one (e.g. user preferred tables but now wants lists), overwrite the old fact.
   - For progress (e.g. "Step 2" -> "Step 3"), update to the latest state.
4. Keep the list concise (max 20 facts, ~300 words total). Discard least important facts if limit reached.
5. Strictly deduplicate: do not include the same fact twice.

Output the COMPLETE updated facts list as a JSON array.
If no changes needed, return existing facts as-is.

Example output: ["User prefers bullet points", "Currently on Step 4 of VPC setup", "Using AWS region ap-south-1"]

Updated facts:"""


async def extract_facts_from_exchange(
    user_message: str, assistant_message: str, existing_facts: str = "", groq_api_key: str = None
) -> list[dict]:
    """
    Extract and merge facts from a user-assistant exchange.
    Uses llama-3.1-8b-instant for cost efficiency.

    Args:
        user_message: The user's message
        assistant_message: The assistant's response
        existing_facts: Current facts string to merge with

    Returns:
        List of {"fact": str} dicts
    """
    api_key = groq_api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        return []

    client = AsyncGroq(api_key=api_key)

    prompt = FACT_EXTRACTION_PROMPT.format(
        existing_facts=existing_facts or "None yet.", user_message=user_message, assistant_message=assistant_message
    )

    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )

        content = response.choices[0].message.content
        if not content:
            return []

        content = content.strip()

        # Parse JSON array from response - robust extraction
        import json

        # Handle potential markdown code blocks
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

        # Extract first JSON array - non-greedy to avoid multi-array issues
        # Find first [ and then find its matching ]
        start_idx = content.find("[")
        if start_idx == -1:
            return []

        # Find matching closing bracket
        depth = 0
        end_idx = start_idx
        for i, char in enumerate(content[start_idx:], start_idx):
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break

        content = content[start_idx:end_idx]

        # Skip if empty or whitespace-only
        if not content or not content.strip():
            return []

        # Skip if empty array
        if content.strip() == "[]":
            return []

        # Try to parse
        facts_raw = json.loads(content)

        # Handle non-list responses
        if not isinstance(facts_raw, list):
            return []

        # Convert to structured format
        facts = []
        for fact in facts_raw:
            if isinstance(fact, str) and fact.strip():
                facts.append({"fact": fact.strip(), "entity_name": None})
            elif isinstance(fact, dict) and fact.get("fact"):
                facts.append(fact)

        return facts  # LLM is instructed to keep max 10

    except Exception as e:
        print(f"[Memory] Fact extraction error: {e}")
        return []
