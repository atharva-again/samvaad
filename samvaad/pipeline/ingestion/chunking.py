"""
Document ingestion pipeline with LlamaParse integration.

Uses LlamaParse hosted API for document parsing (PDF, DOCX, etc.).
"""

import os
import tempfile
import time
from typing import Tuple, List


# Singleton parser instance
_parser = None


def get_llama_parser():
    """Get a singleton LlamaParse instance."""
    global _parser
    if _parser is None:
        from llama_cloud_services import LlamaParse
        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not api_key:
            raise ValueError(
                "LLAMA_CLOUD_API_KEY environment variable is required. "
                "Get a free key at https://cloud.llamaindex.ai/api-key"
            )
        _parser = LlamaParse(
            api_key=api_key,
            verbose=False,
        )
    return _parser


def parse_file(filename: str, content_type: str, contents: bytes) -> Tuple[str, str]:
    """
    Parse a file using LlamaParse API. Falls back to UTF-8 decode for plain text.
    Returns (text, error).
    """
    text = ""
    error = None
    ext = os.path.splitext(filename)[1].lower()
    
    # For plain text files, just decode directly (no need for API call)
    if ext in [".txt", ".md", ".csv"]:
        try:
            text = contents.decode("utf-8")
            return text, None
        except UnicodeDecodeError as e:
            return "", f"Failed to decode text file: {e}"
    
    # For other files (PDF, DOCX, XLSX, etc.), use LlamaParse
    temp_file_path = None
    try:
        parser = get_llama_parser()
        
        # Write to temp file (LlamaParse needs file path or bytes with filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(contents)
            temp_file.flush()
            temp_file_path = temp_file.name
        
        # Parse with LlamaParse (new API: .parse() returns JobResult)
        result = parser.parse(temp_file_path)
        
        # Get markdown text from result
        if result and hasattr(result, 'pages') and result.pages:
            # Combine markdown from all pages
            text = "\n\n".join(
                page.md for page in result.pages if hasattr(page, 'md') and page.md
            )
        elif result:
            # Try to get markdown documents
            try:
                md_docs = result.get_markdown_documents(split_by_page=False)
                if md_docs:
                    text = "\n\n".join(doc.text for doc in md_docs if hasattr(doc, 'text') and doc.text)
            except Exception:
                # Fallback: try to get text documents
                try:
                    text_docs = result.get_text_documents(split_by_page=False)
                    if text_docs:
                        text = "\n\n".join(doc.text for doc in text_docs if hasattr(doc, 'text') and doc.text)
                except Exception:
                    pass
        
        if not text:
            error = "LlamaParse returned no content"
            
    except Exception as e:
        # Fallback to UTF-8 decode if LlamaParse fails
        try:
            text = contents.decode("utf-8")
            error = None
        except UnicodeDecodeError:
            text = ""
            error = f"LlamaParse failed and content is not valid UTF-8: {e}"
    finally:
        # Clean up temporary file
        if temp_file_path:
            _cleanup_temp_file(temp_file_path)
    
    return text, error


def _cleanup_temp_file(file_path: str, max_retries: int = 5):
    """
    Safely clean up temporary file with retry logic to handle file access issues.
    """
    for attempt in range(max_retries):
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                return  # Success
        except OSError as e:
            if attempt < max_retries - 1:
                # Wait progressively longer before retrying
                time.sleep(0.2 * (attempt + 1))
            else:
                # If all retries failed, just warn and continue
                print(
                    f"Warning: Could not delete temporary file {file_path} after {max_retries} attempts: {e}"
                )
                break


def chunk_text(text: str, chunk_size: int = 200) -> List[str]:
    """
    Split text into chunks using simple recursive text splitting.
    Uses separator hierarchy for natural chunk boundaries.
    """
    if not text or not text.strip():
        return []
    
    return _recursive_chunk_text(text, chunk_size)


def _recursive_chunk_text(text: str, chunk_size: int = 200) -> List[str]:
    """
    Recursive text chunking with separator hierarchy.
    Approximates token count as words * 1.3 (rough estimate).
    """
    def approx_tokens(t: str) -> int:
        """Approximate token count from word count."""
        return int(len(t.split()) * 1.3)
    
    separators = ["\n\n", "\n", ". ", "? ", "! ", " "]
    
    def split_recursive(text: str, separators: List[str]) -> List[str]:
        if not text.strip():
            return []
        if approx_tokens(text) <= chunk_size:
            return [text.strip()] if text.strip() else []

        for idx, separator in enumerate(separators):
            if separator in text:
                splits = text.split(separator)
                result = []
                current_chunk = ""
                
                for split in splits:
                    split_with_sep = split + separator if separator != " " else split + " "
                    
                    # If adding this split would exceed chunk_size
                    if approx_tokens(current_chunk + split_with_sep) > chunk_size:
                        if current_chunk.strip():
                            result.append(current_chunk.strip())
                        
                        # If single split is too large, recurse with finer separators
                        if approx_tokens(split_with_sep) > chunk_size:
                            remaining_seps = separators[idx + 1:] if idx + 1 < len(separators) else []
                            if remaining_seps:
                                recursive_splits = split_recursive(split, remaining_seps)
                                result.extend(recursive_splits)
                            else:
                                # Force split by characters as last resort
                                result.append(split_with_sep.strip())
                            current_chunk = ""
                        else:
                            current_chunk = split_with_sep
                    else:
                        current_chunk += split_with_sep
                
                if current_chunk.strip():
                    result.append(current_chunk.strip())
                return result
        
        # If no separators work, just return the text
        return [text.strip()] if text.strip() else []
    
    return split_recursive(text, separators)
