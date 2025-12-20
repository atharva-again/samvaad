"""
Memory Tools for Agent

These functions are registered as tools that the LLM agent can call
to retrieve context from conversation history.
"""
from typing import List, Dict
from uuid import UUID

from samvaad.db.conversation_service import ConversationService
from samvaad.core.voyage import get_voyage_embeddings


# Tool definitions for LLM function calling
MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_conversation_history",
            "description": "Search earlier messages in this conversation by meaning. Use when user references something discussed before or when you need to find specific past context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in conversation history"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_facts",
            "description": "Get known facts about a topic or entity from this conversation. Use when user asks about something specific we've discussed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "The topic or entity to get facts about (e.g., 'AWS', 'VPC', 'the project')"
                    }
                },
                "required": ["entity_name"]
            }
        }
    }
]


async def execute_memory_tool(
    tool_name: str,
    tool_args: Dict,
    conversation_id: UUID
) -> str:
    """
    Execute a memory tool and return results as string for LLM context.
    """
    service = ConversationService()
    
    if tool_name == "search_conversation_history":
        return await _search_conversation_history(
            service,
            conversation_id,
            tool_args.get("query", ""),
            tool_args.get("limit", 5)
        )
    
    elif tool_name == "get_entity_facts":
        return _get_entity_facts(
            service,
            conversation_id,
            tool_args.get("entity_name", "")
        )
    
    return "Unknown tool"


async def _search_conversation_history(
    service: ConversationService,
    conversation_id: UUID,
    query: str,
    limit: int = 5
) -> str:
    """Search messages by semantic similarity."""
    if not query:
        return "No query provided."
    
    # Get embedding for query
    try:
        embeddings = await get_voyage_embeddings([query])
        if not embeddings:
            return "Could not generate embedding for search."
        query_embedding = embeddings[0]
    except Exception as e:
        return f"Embedding error: {e}"
    
    # Search messages
    messages = service.search_messages_by_embedding(
        conversation_id, query_embedding, limit
    )
    
    if not messages:
        return "No relevant messages found in conversation history."
    
    # Format results
    results = []
    for msg in messages:
        role = "User" if msg.role == "user" else "Assistant"
        results.append(f"{role}: {msg.content[:200]}...")
    
    return "Found in conversation history:\n" + "\n\n".join(results)


def _get_entity_facts(
    service: ConversationService,
    conversation_id: UUID,
    entity_name: str
) -> str:
    """Get facts about an entity."""
    if not entity_name:
        return "No entity name provided."
    
    facts = service.get_facts_by_entity(conversation_id, entity_name)
    
    if not facts:
        return f"No facts found about '{entity_name}' in this conversation."
    
    # Format results
    lines = [f"Known facts about '{entity_name}':"]
    for f in facts:
        lines.append(f"- {f['fact']}")
    
    return "\n".join(lines)
