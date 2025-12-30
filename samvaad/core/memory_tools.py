"""
Memory Tools for Agent

These functions are registered as tools that the LLM agent can call
to retrieve context from conversation history.

Tools:
- search_history: Text search on archived messages
- (RAG tool defined separately in voice_agent.py)
"""

# Tool definitions for LLM function calling
MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_history",
            "description": "Search earlier messages in this conversation. Use when user references something discussed before, e.g., 'remember when we talked about...'",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in conversation history"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def search_history(query: str, archived_messages: list[dict], limit: int = 5) -> str:
    """
    Simple text search on archived messages.
    
    Args:
        query: Search term
        archived_messages: Messages outside the sliding window
        limit: Max results to return
    
    Returns:
        Formatted string of matching messages
    """
    if not query or not archived_messages:
        return "No matching messages found in history."

    query_lower = query.lower()
    matches = []

    for msg in archived_messages:
        content = msg.get("content", "")
        if query_lower in content.lower():
            role = "User" if msg.get("role") == "user" else "Assistant"
            # Truncate long messages
            snippet = content[:200] + "..." if len(content) > 200 else content
            matches.append(f"{role}: {snippet}")

    if not matches:
        return f"No messages found containing '{query}' in history."

    # Limit results
    matches = matches[:limit]

    return "Found in history:\n\n" + "\n\n".join(matches)


async def execute_memory_tool(
    tool_name: str,
    tool_args: dict,
    archived_messages: list[dict]
) -> str:
    """
    Execute a memory tool and return results as string for LLM context.
    
    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments passed from LLM
        archived_messages: Messages outside the sliding window
    """
    if tool_name == "search_history":
        return search_history(
            tool_args.get("query", ""),
            archived_messages,
            tool_args.get("limit", 5)
        )

    return "Unknown tool"
