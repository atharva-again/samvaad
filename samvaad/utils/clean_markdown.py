import re


def strip_markdown(text: str) -> str:
    """
    Strip markdown formatting from text for clean display or TTS.
    Removes headers, bold, italic, code blocks, links, lists, etc.
    while preserving the readable content.

    Args:
        text (str): Text with markdown formatting

    Returns:
        str: Plain text without markdown formatting
    """
    if not text:
        return text

    # Remove code blocks (```code```)
    text = re.sub(r"```[\s\S]*?```", "", text)

    # Remove inline code (`code`)
    text = re.sub(r"`([^`]*)`", r"\1", text)

    # Remove headers (# ## ###)
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

    # Remove bold (**text** or __text__)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)

    # Remove italic (*text* or _text_)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)

    # Remove strikethrough (~~text~~)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)

    # Remove links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)

    # Remove images ![alt](url) -> alt
    text = re.sub(r"!\[([^\]]+)\]\(([^)]+)\)", r"\1", text)

    # Remove blockquotes (> text)
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

    # Convert unordered lists (- item, * item, + item) to plain text
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)

    # Remove horizontal rules (--- or ***)
    text = re.sub(r"^[-*_]{3,}$", "", text, flags=re.MULTILINE)

    # Clean up extra whitespace while preserving newlines
    text = re.sub(r"[ \t]+", " ", text)  # Normalize spaces and tabs to single space
    text = re.sub(r"\n\s*\n", "\n\n", text)  # Multiple newlines
    text = (
        text.strip()
    )  # Strip only leading/trailing whitespace, preserving internal newlines

    return text
