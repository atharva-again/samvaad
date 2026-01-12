def build_sliding_window_context(messages: list[dict], window_size: int = 6) -> tuple[list[dict], list[dict]]:
    """
    Split messages into sliding window (recent) and older messages.
    """
    if len(messages) <= window_size:
        return messages, []
    return messages[-window_size:], messages[:-window_size]


def format_messages_for_prompt(messages: list[dict]) -> str:
    """
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
