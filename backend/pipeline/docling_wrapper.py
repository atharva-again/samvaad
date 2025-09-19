"""
Docling wrapper for PDF parsing and hierarchical chunking.
This module provides a simplified interface compatible with the existing codebase.
"""

from typing import List, Tuple
import io
import os


class DoclingConverter:
    """
    Simplified Docling converter for CPU-only PDF processing.
    Falls back to a basic implementation when full Docling dependencies are not available.
    """
    
    def __init__(self):
        self._docling_available = False
        self._converter = None
        self._init_docling()
        
    def _init_docling(self):
        """Initialize Docling if available."""
        try:
            # Try to import and initialize Docling
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption
            
            # Configure for CPU-only processing
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False  # Disable OCR for CPU-only mode
            pipeline_options.do_table_structure = True
            pipeline_options.table_structure_options.do_cell_matching = True
            
            doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            
            self._converter = doc_converter
            self._docling_available = True
            
        except ImportError as e:
            print(f"Docling not fully available: {e}")
            self._docling_available = False
        except Exception as e:
            print(f"Error initializing Docling: {e}")
            self._docling_available = False
    
    def convert_pdf(self, content: bytes) -> Tuple[str, str]:
        """
        Convert PDF content to text using Docling.
        
        Args:
            content: PDF file content as bytes
            
        Returns:
            Tuple of (extracted_text, error_message)
        """
        if self._docling_available and self._converter:
            try:
                # Use actual Docling conversion
                from docling.datamodel.base_models import ConversionInput
                
                source = ConversionInput.from_streams(
                    file=io.BytesIO(content),
                    filename="document.pdf"
                )
                
                conv_result = self._converter.convert(source)
                text = conv_result.document.export_to_markdown()
                return text, None
                
            except Exception as e:
                return "", f"Docling PDF parsing error: {e}"
        else:
            # Fallback message
            return "", "Docling dependencies not fully available. Please install: pip install docling docling-core docling-parse"


class SimpleTokenCounter:
    """Simple token counter that doesn't require network access."""
    
    def __init__(self):
        # Simple approximation: ~4 characters per token on average
        self.chars_per_token = 4
    
    def count_tokens(self, text: str) -> int:
        """Approximate token count based on character length."""
        if not text:
            return 0
        # Simple heuristic: count words and punctuation
        import re
        tokens = re.findall(r'\b\w+\b|[^\w\s]', text)
        return len(tokens)


class DoclingHierarchicalChunker:
    """
    Hierarchical text chunker based on Docling's chunking approach.
    Implements token-based chunking with 200 tokens and no overlap.
    """
    
    def __init__(self, chunk_size: int = 200, overlap: int = 0):
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        # Try to initialize HuggingFace tokenizer, fall back to simple counter
        self._tokenizer = None
        self._token_counter = None
        self._init_tokenizer()
        
    def _init_tokenizer(self):
        """Initialize the tokenizer if possible, otherwise use simple counter."""
        try:
            # Try to use offline mode first
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            from transformers import AutoTokenizer
            import threading
            
            # Check if model is cached locally
            self._tokenizer = AutoTokenizer.from_pretrained(
                "BAAI/bge-m3", 
                local_files_only=True
            )
            print("Using cached HuggingFace tokenizer for token counting")
            
        except Exception:
            # Fall back to simple token counter
            print("Using simple token counter (HuggingFace tokenizer not available)")
            self._token_counter = SimpleTokenCounter()
            self._tokenizer = None
        finally:
            # Reset offline mode
            if "TRANSFORMERS_OFFLINE" in os.environ:
                del os.environ["TRANSFORMERS_OFFLINE"]
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._tokenizer:
            return len(self._tokenizer.encode(text, add_special_tokens=False))
        elif self._token_counter:
            return self._token_counter.count_tokens(text)
        else:
            # Ultimate fallback: character-based approximation
            return max(1, len(text) // 4)
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text using hierarchical approach with 200 tokens and no overlap.
        
        This implements a hierarchical chunking strategy similar to Docling:
        1. Try to split at natural document boundaries (paragraphs, sentences)
        2. Respect token limits
        3. No overlap between chunks
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        if not text.strip():
            return []
            
        # Hierarchical separators: paragraphs -> sentences -> clauses -> words
        separators = [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentence endings
            "? ",    # Question endings
            "! ",    # Exclamation endings
            "; ",    # Semicolon breaks
            ", ",    # Comma breaks
            " ",     # Word breaks
            ""       # Character level (fallback)
        ]
        
        return self._split_hierarchical(text, separators)
    
    def _split_hierarchical(self, text: str, separators: List[str]) -> List[str]:
        """
        Recursively split text using hierarchical separators.
        """
        if not text.strip():
            return []
            
        # If text fits within chunk size, return as single chunk
        if self._count_tokens(text) <= self.chunk_size:
            return [text.strip()] if text.strip() else []
        
        # Try each separator in hierarchical order
        for i, separator in enumerate(separators):
            if separator in text:
                splits = text.split(separator)
                result = []
                current_chunk = ""
                
                for split in splits:
                    # Add separator back except for empty separator (character level)
                    split_with_sep = split + (separator if separator != "" else "")
                    
                    # Check if adding this split would exceed chunk size
                    potential_chunk = current_chunk + split_with_sep
                    if self._count_tokens(potential_chunk) > self.chunk_size:
                        # Add current chunk if it has content
                        if current_chunk.strip():
                            result.append(current_chunk.strip())
                        
                        # If split itself is too large, recursively split it
                        if self._count_tokens(split_with_sep) > self.chunk_size:
                            remaining_separators = separators[i + 1:]
                            if remaining_separators:
                                split_to_process = split if separator != "" else split_with_sep
                                recursive_chunks = self._split_hierarchical(split_to_process, remaining_separators)
                                result.extend(recursive_chunks)
                            else:
                                # Force split at token level
                                result.extend(self._force_split_tokens(split_with_sep))
                            current_chunk = ""
                        else:
                            current_chunk = split_with_sep
                    else:
                        current_chunk = potential_chunk
                
                # Add remaining chunk
                if current_chunk.strip():
                    result.append(current_chunk.strip())
                
                return result
        
        # If no separators worked, force split at token level
        return self._force_split_tokens(text)
    
    def _force_split_tokens(self, text: str) -> List[str]:
        """
        Force split text at token boundaries when no natural separators work.
        """
        if self._tokenizer:
            # Use actual tokenizer if available
            tokens = self._tokenizer.encode(text, add_special_tokens=False)
            chunks = []
            
            for i in range(0, len(tokens), self.chunk_size):
                chunk_tokens = tokens[i:i + self.chunk_size]
                chunk_text = self._tokenizer.decode(chunk_tokens, skip_special_tokens=True)
                if chunk_text.strip():
                    chunks.append(chunk_text.strip())
            
            return chunks
        else:
            # Fallback: split by character approximation
            # Approximate tokens as words + punctuation
            import re
            words = re.findall(r'\b\w+\b|[^\w\s]', text)
            chunks = []
            
            current_chunk_tokens = []
            for word in words:
                current_chunk_tokens.append(word)
                if len(current_chunk_tokens) >= self.chunk_size:
                    chunk_text = ' '.join(current_chunk_tokens)
                    # Clean up extra spaces around punctuation
                    chunk_text = re.sub(r'\s+([^\w\s])', r'\1', chunk_text)
                    chunk_text = re.sub(r'([^\w\s])\s+', r'\1 ', chunk_text)
                    chunks.append(chunk_text.strip())
                    current_chunk_tokens = []
            
            # Add remaining tokens
            if current_chunk_tokens:
                chunk_text = ' '.join(current_chunk_tokens)
                chunk_text = re.sub(r'\s+([^\w\s])', r'\1', chunk_text)
                chunk_text = re.sub(r'([^\w\s])\s+', r'\1 ', chunk_text)
                chunks.append(chunk_text.strip())
            
            return chunks


# Global instances for reuse
_converter = None
_chunker = None

def get_docling_converter():
    """Get or create the global Docling converter instance."""
    global _converter
    if _converter is None:
        _converter = DoclingConverter()
    return _converter

def get_docling_chunker(chunk_size: int = 200):
    """Get or create the global Docling chunker instance."""
    global _chunker
    if _chunker is None or _chunker.chunk_size != chunk_size:
        _chunker = DoclingHierarchicalChunker(chunk_size=chunk_size, overlap=0)
    return _chunker