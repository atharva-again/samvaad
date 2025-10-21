"""
Document ingestion pipeline with Docling integration.

Supports GPU acceleration when available for faster processing.
"""

from samvaad.utils.filehash_db import chunk_exists, add_chunk
from samvaad.utils.hashing import generate_file_id, generate_chunk_id
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer
from typing import Tuple, List
import tempfile
import os
import time
import warnings

# Suppress pin_memory warning for CPU-only usage
warnings.filterwarnings(
    "ignore", message="'pin_memory' argument is set as true but no accelerator is found"
)
warnings.filterwarnings("ignore", message=".*pin_memory.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*accelerator.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*CUDA.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*GPU.*", category=UserWarning)
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Suppress tokenizer warnings
os.environ["OMP_NUM_THREADS"] = "1"  # Limit OpenMP threads for CPU usage

# Initialize Docling components for GPU/CPU usage (uses GPU if available)
_converter = None
_chunker = None

# Initialize Docling components for GPU/CPU usage (uses GPU if available)
_converter = None
_chunker = None


def get_docling_converter():
    """Get a singleton Docling DocumentConverter instance."""
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter


def get_docling_chunker():
    """Get a singleton Docling HierarchicalChunker instance configured for 200 tokens, no overlap."""
    global _chunker
    if _chunker is None:
        # Use the same tokenizer as before for consistency
        tokenizer = HuggingFaceTokenizer(
            tokenizer=AutoTokenizer.from_pretrained("BAAI/bge-m3"),
            max_tokens=200,  # Set to 200 tokens as requested
        )

        # For pure hierarchical chunking without overlap, use HierarchicalChunker
        # HybridChunker applies token-aware refinements which might cause overlap
        _chunker = HierarchicalChunker(
            tokenizer=tokenizer,
            merge_list_items=False,  # Disable merging to avoid overlap
        )
    return _chunker


def find_new_chunks(chunks, file_id):
    """
    For each chunk, check deduplication.
    Returns a list of (chunk, chunk_id) that are new for this file.
    """
    new_chunks = []
    seen_in_batch = set()  # Track IDs already seen in this batch

    for chunk in chunks:
        chunk_id = generate_chunk_id(chunk)

        # Skip if we've already seen this chunk_id in this batch
        if chunk_id in seen_in_batch:
            continue

        # Check if chunk exists globally (not per file)
        if not chunk_exists(chunk_id):
            new_chunks.append((chunk, chunk_id))
            seen_in_batch.add(chunk_id)
    return new_chunks


def update_chunk_file_db(new_chunks, file_id):
    """
    Add new (chunk_id, file_id) pairs to the DB.
    Returns a list of (chunk, chunk_id) that were newly added.
    """

    for chunk in new_chunks:
        # chunk may be a string or a tuple (chunk, chunk_id)
        if isinstance(chunk, tuple):
            chunk_id = chunk[1]
        else:
            chunk_id = generate_chunk_id(chunk)
        # Only add the (chunk_id, file_id) mapping if it doesn't exist
        if not chunk_exists(chunk_id, file_id):
            add_chunk(chunk_id, file_id)
    return new_chunks


def parse_file(filename: str, content_type: str, contents: bytes) -> Tuple[str, str]:
    """
    Always use Docling for all supported file types, fallback to UTF-8 decode only if Docling fails.
    Returns (text, error) for compatibility, but now also stores the DoclingDocument globally for chunking.
    """
    text = ""
    error = None
    temp_file_path = None
    format_hint = None
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".txt":
        format_hint = "md"  # Use markdown for plain text

    try:
        converter = get_docling_converter()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(contents)
            temp_file.flush()
            temp_file_path = temp_file.name

        # Convert document using Docling, force format for .txt files
        if format_hint:
            result = converter.convert(temp_file_path, format=format_hint)
        else:
            result = converter.convert(temp_file_path)
        # Store the DoclingDocument for advanced chunking
        parse_file._last_document = result.document
        parse_file._last_was_text = False
        # Export to markdown for text preview/compatibility
        text = result.document.export_to_markdown()
        error = None
    except Exception as e:
        # If Docling fails, fallback to UTF-8 decode for text-like files
        try:
            text = contents.decode("utf-8")
            parse_file._last_document = None
            parse_file._last_was_text = True
            error = None
        except Exception as decode_error:
            text = ""
            error = f"Docling and UTF-8 decoding both failed: {e}; {decode_error}"
    finally:
        # Clean up temporary file with retry logic
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
    Use Docling's hierarchical chunker with 200 tokens, no overlap.
    If we have a DoclingDocument from parsing, use it directly.
    For simple text, use fallback chunking directly.
    """
    try:
        # Check if we have a DoclingDocument from the previous parse_file call
        docling_doc = getattr(parse_file, "_last_document", None)
        was_text = getattr(parse_file, "_last_was_text", True)

        if docling_doc is not None and not was_text:
            # Use the existing DoclingDocument from Docling parsing
            chunker = get_docling_chunker()
            chunks = list(chunker.chunk(dl_doc=docling_doc))

            # Extract the contextualized text from chunks
            chunk_texts = []
            for chunk in chunks:
                chunk_text = chunker.contextualize(chunk=chunk)
                if chunk_text.strip():
                    chunk_texts.append(chunk_text.strip())

            return chunk_texts
        else:
            # For simple text files, use fallback chunking directly
            print("Using fallback chunking for text file")
            return _fallback_chunk_text(text, chunk_size)

    except Exception as e:
        # Fallback to simple splitting if Docling chunking fails
        print(
            f"Warning: Docling chunking failed ({e}), falling back to simple chunking"
        )
        return _fallback_chunk_text(text, chunk_size)


def _fallback_chunk_text(text: str, chunk_size: int = 200) -> List[str]:
    """
    Fallback chunking method using the original token-based approach.
    """
    from transformers import AutoTokenizer
    import threading

    # Use a singleton tokenizer to avoid repeated loading
    _tokenizer = getattr(_fallback_chunk_text, "_tokenizer", None)
    _tokenizer_lock = getattr(_fallback_chunk_text, "_tokenizer_lock", None)
    if _tokenizer is None:
        if _tokenizer_lock is None:
            _tokenizer_lock = threading.Lock()
            setattr(_fallback_chunk_text, "_tokenizer_lock", _tokenizer_lock)
        with _tokenizer_lock:
            _tokenizer = getattr(_fallback_chunk_text, "_tokenizer", None)
            if _tokenizer is None:
                _tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
                setattr(_fallback_chunk_text, "_tokenizer", _tokenizer)

    separators = ["\n\n", "\n", ".", "?", "!", " ", ""]

    def num_tokens(text):
        return len(_tokenizer.encode(text, add_special_tokens=False))

    def split_text_recursive(text: str, separators: List[str]) -> List[str]:
        if not text.strip():
            return []
        if num_tokens(text) <= chunk_size:
            return [text.strip()] if text.strip() else []

        for idx, separator in enumerate(separators):
            if separator == "":
                break
            if separator in text:
                splits = text.split(separator)
                result = []
                current_chunk = ""
                for split in splits:
                    split_with_sep = split + (separator if separator != "" else "")
                    # If adding this split would exceed chunk_size tokens
                    if num_tokens(current_chunk + split_with_sep) > chunk_size:
                        if current_chunk.strip():
                            result.append(current_chunk.strip())
                        if num_tokens(split_with_sep) > chunk_size:
                            split_for_recursion = (
                                split if separator != "" else split_with_sep
                            )
                            recursive_splits = split_text_recursive(
                                split_for_recursion, separators[idx + 1 :]
                            )
                            result.extend(recursive_splits)
                            current_chunk = ""
                        else:
                            current_chunk = split_with_sep
                    else:
                        current_chunk += split_with_sep
                if current_chunk.strip():
                    result.append(current_chunk.strip())
                return result
        # If no separators worked, force split at chunk_size tokens
        tokens = _tokenizer.encode(text, add_special_tokens=False)
        chunks = []
        for i in range(0, len(tokens), chunk_size):
            chunk_tokens = tokens[i : i + chunk_size]
            chunk = _tokenizer.decode(chunk_tokens)
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

    return split_text_recursive(text, separators)
