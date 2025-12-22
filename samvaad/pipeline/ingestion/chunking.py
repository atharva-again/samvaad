"""
Document ingestion pipeline with Structural Chunking.
Uses LlamaParse JSON mode for rich metadata (breadcrumbs, content types).
"""

import os
import tempfile
import time
import json
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Any, Optional

# Lazy parser import
_parser = None

@dataclass
class Chunk:
    """A structural chunk of text with rich metadata."""
    content: str
    metadata: Dict[str, Any]
    # Metadata includes: page_number, breadcrumbs (List[str]), content_type (str)

def get_llama_parser():
    """Get LlamaParse in JSON mode."""
    global _parser
    if _parser is None:
        from llama_cloud_services import LlamaParse
        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not api_key:
            raise ValueError("LLAMA_CLOUD_API_KEY required")
            
        _parser = LlamaParse(
            api_key=api_key,
            result_type="json",  # JSON mode!
            num_workers=4,
            verbose=False,
            language="en"
        )
    return _parser

def parse_file(filename: str, content_type: str, contents: bytes) -> Tuple[List[Dict], str]:
    """
    Parse a file into JSON pages using LlamaParse.
    Returns (pages_json, error).
    """
    pages = []
    error = None
    ext = os.path.splitext(filename)[1].lower()
    
    # Text types: fallback to manual "page" creation
    # [FIX] Allow .txt and .md to go through LlamaParse to get headings/structure if possible
    # Only bypass strictly unstructured data or config files
    if ext in [".csv", ".json", ".xml", ".yaml", ".yml"]:
        try:
            text = contents.decode("utf-8")
            # Create a mock JSON page structure for consistency
            page = {
                "page": 1,
                "items": [
                    {"type": "text", "value": text, "md": text}
                ]
            }
            return [page], None
        except Exception as e:
            return [], str(e)

    # Docs/PDFs
    try:
        parser = get_llama_parser()
        
        # [SECURITY-FIX #96] Use TemporaryDirectory for safer cleanup
        # This ensures the directory and all contents are removed even if crashes occur
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, f"upload{ext}")
            
            with open(temp_file_path, "wb") as tf:
                tf.write(contents)
            
            # Try to use get_json_result (preferred for JSON mode)
            if hasattr(parser, "get_json_result"):
                 try:
                     json_objs = parser.get_json_result(temp_file_path)
                 except Exception:
                     # Fallback
                     json_objs = parser.load_data(temp_file_path)
            else:
                 json_objs = parser.load_data(temp_file_path)
            
            # Determine format
            if json_objs:
                first = json_objs[0]
                
                # Case A: It's a Document object with .text containing JSON string
                if hasattr(first, 'text'):
                    try:
                        data = json.loads(first.text)
                    except:
                        data = {}
                # Case B: It's already a dict (from get_json_result)
                elif isinstance(first, dict):
                    data = first
                else:
                    data = {}
                    
                if isinstance(data, dict) and "pages" in data:
                    pages = data["pages"]
                elif isinstance(data, list):
                    pages = data 
                else:
                    pages = []
                     
            if not pages:
                 error = "LlamaParse returned no structured data."

    except Exception as e:
        import traceback
        traceback.print_exc()
        error = f"LlamaParse extraction failed: {e}"
        # Fallback to text decode if possible? 
        try:
            text = contents.decode("utf-8", errors='ignore')
            pages = [{"page": 1, "items": [{"type": "text", "md": text}]}]
            error = None # Recovered
        except:
             pass

    return pages, error

def _cleanup_temp_file(path):
    try:
        if os.path.exists(path):
            os.unlink(path)
    except:
        pass

class StructuralChunker:
    """Chunks documents based on layout and headings."""
    
    def chunk(self, pages_json: List[Dict]) -> List[Chunk]:
        chunks = []
        
        # State
        heading_stack = [] # List of (level, text)
        current_chunk_text = []
        current_chunk_type = "text"
        current_page = 1
        current_size = 0
        limit = 1200 # Char limit approx
        overlap = 80 # ~20 tokens
        
        for page in pages_json:
            page_num = page.get("page", 1)
            items = page.get("items", [])
            
            for item in items:
                itype = item.get("type", "text")
                content = item.get("md") or item.get("value") or ""
                # Try to get heading level, default to 1 if missing but is heading
                level = item.get("lvl", item.get("level", None))
                
                if not content.strip():
                    continue

                # Update current page if starting new chunk
                if not current_chunk_text:
                    current_page = page_num
                    
                # HEADING: Updates breadcrumbs, starts new chunk
                if itype == "heading":
                    # 1. Flush previous text using OLD stack context
                    if current_chunk_text:
                        old_breadcrumbs = [h[1] for h in heading_stack]
                        self._finalize(chunks, current_chunk_text, current_chunk_type, current_page, old_breadcrumbs, limit, overlap)
                        current_chunk_text = []
                        current_size = 0

                    # 2. Update Stack with NEW heading
                    if level is not None:
                        # Pop anything deeper or same level
                        while heading_stack and heading_stack[-1][0] >= level:
                            heading_stack.pop()
                        heading_stack.append((level, content.strip()))
                    else:
                        # Fallback
                        heading_stack = [(1, content.strip())]
                    
                    # 3. Add heading to NEXT chunk metadata/context
                    # Note: We don't change breadcrumbs var here because we won't use it until next item or next flush
                    
                    # Add heading text itself to the content flow
                    current_chunk_text.append(f"# {content}")
                    current_size += len(content)
                    current_chunk_type = "text"
                    
                # TABLE: Distinct chunk but check size
                elif itype == "table":
                    # Flush pending text
                    if current_chunk_text:
                        breadcrumbs = [h[1] for h in heading_stack]
                        self._finalize(chunks, current_chunk_text, current_chunk_type, current_page, breadcrumbs, limit, overlap)
                        current_chunk_text = []
                        current_size = 0
                        
                    breadcrumbs = [h[1] for h in heading_stack]
                    if len(content) > limit:
                        # Treat large table as text to split it
                        self._recursive_split(chunks, content, limit, overlap, ["\n\n", "\n", "  "], "table", page_num, breadcrumbs)
                    else:
                        self._create_single(chunks, content, "table", page_num, breadcrumbs)
                    
                # TEXT / LIST / OTHER
                else:
                    # Append
                    current_chunk_text.append(content)
                    current_size += len(content)
                    current_chunk_type = "text"
                    
                    # Split if too big
                    if current_size > limit:
                        breadcrumbs = [h[1] for h in heading_stack]
                        self._finalize(chunks, current_chunk_text, current_chunk_type, page_num, breadcrumbs, limit, overlap)
                        # Overlap Logic: Keep last bit of text?
                        # _finalize clears text.
                        # Ideally _finalize handles splitting and we start fresh OR we keep tails?
                        # Simplified: _finalize splits correctly.
                        # But cross-chunk overlap (between items) is hard here.
                        # We'll rely on _finalize's internal splitting for overlap within the block.
                        # For cross-block, we'd need a rolling buffer. 
                        # Let's keep it simple: restart empty.
                        current_chunk_text = []
                        current_size = 0
                        
        # Final flush
        if current_chunk_text:
            breadcrumbs = [h[1] for h in heading_stack]
            self._finalize(chunks, current_chunk_text, current_chunk_type, current_page, breadcrumbs, limit, overlap)
            
        return chunks

    def _finalize(self, chunks, text_list, ctype, page, breadcrumbs, limit, overlap):
        full_text = "\n\n".join(text_list).strip()
        if not full_text:
            return
            
        if len(full_text) > limit:
             self._recursive_split(chunks, full_text, limit, overlap, ["\n\n", "\n", ". ", " ", ""], ctype, page, breadcrumbs)
        else:
             meta = {
                "page_number": page,
                "heading": breadcrumbs[-1] if breadcrumbs else None,
                "breadcrumbs": breadcrumbs,
                "content_type": ctype
             }
             chunks.append(Chunk(content=full_text, metadata=meta))

    def _recursive_split(self, chunks, text, limit, overlap, separators, ctype, page, breadcrumbs):
        """Splits text recursively with overlap."""
        if len(text) <= limit:
             meta = {
                "page_number": page, "heading": breadcrumbs[-1] if breadcrumbs else None,
                "breadcrumbs": breadcrumbs, "content_type": ctype
             }
             chunks.append(Chunk(content=text, metadata=meta))
             return
        else:
            # Find best separator
            best_sep = ""
            best_sep_idx = -1
            for i, sep in enumerate(separators):
                if sep in text:
                    best_sep = sep
                    best_sep_idx = i
                    break
            
            # If no separator found (Char split case)
            if best_sep == "":
                # Hard chunking
                # Use a simpler loop for char chunking
                for i in range(0, len(text), limit - overlap):
                    final_chunks.append(text[i:i + limit])
            else:
                # Split
                parts = text.split(best_sep)
                current_c = []
                current_len = 0
                
                for part in parts:
                    part_len = len(part) + len(best_sep)
                    if current_len + part_len > limit:
                         # Flush
                         if current_c:
                             chunk_txt = best_sep.join(current_c)
                             # RECURSION CHECK
                             if len(chunk_txt) > limit:
                                 # Try next separator
                                 next_seps = separators[best_sep_idx+1:]
                                 if next_seps:
                                     self._recursive_split(chunks, chunk_txt, limit, overlap, next_seps, ctype, page, breadcrumbs)
                                     # Don't append here, recursion handles it
                                 else:
                                     # No more separators, force char split (recurse with empty sep logic?)
                                     # Or just emit (should be protected by best_sep="" case above logic entry if passed recursively)
                                     # Wait, we need to manually call it.
                                     # Actually, let's just emit if we ran out of seps.
                                     # Valid fallback: char split logic manually on this piece
                                     for i in range(0, len(chunk_txt), limit - overlap):
                                        c_part = chunk_txt[i:i+limit]
                                        meta = {
                                            "page_number": page, "heading": breadcrumbs[-1] if breadcrumbs else None,
                                            "breadcrumbs": breadcrumbs, "content_type": ctype
                                        }
                                        chunks.append(Chunk(content=c_part, metadata=meta))
                             else:
                                 # Good chunk
                                 meta = {
                                    "page_number": page, "heading": breadcrumbs[-1] if breadcrumbs else None,
                                    "breadcrumbs": breadcrumbs, "content_type": ctype
                                 }
                                 chunks.append(Chunk(content=chunk_txt, metadata=meta))
                         
                         # Start new with OVERLAP?
                         # Text splitting overlap by token is hard with 'parts'.
                         # We'll overlap by keeping the last 'part'?
                         # Simple overlap: Keep last part if it exists
                         if overlap > 0 and len(current_c) > 0:
                             # Keep last item(s) that fit in overlap size?
                             # Rough heuristic: keep last part
                             current_c = [current_c[-1]]
                             current_len = len(current_c[-1]) + len(best_sep)
                         else:
                             current_c = []
                             current_len = 0
                             
                         current_c.append(part)
                         current_len += part_len
                    else:
                        current_c.append(part)
                        current_len += part_len
                
                # Final flush loop
                if current_c:
                    chunk_txt = best_sep.join(current_c)
                    if len(chunk_txt) > limit:
                         next_seps = separators[best_sep_idx+1:]
                         if next_seps:
                             self._recursive_split(chunks, chunk_txt, limit, overlap, next_seps, ctype, page, breadcrumbs)
                         else:
                             # Force char split
                             for i in range(0, len(chunk_txt), limit - overlap):
                                 c_part = chunk_txt[i:i+limit]
                                 meta = {
                                     "page_number": page, "heading": breadcrumbs[-1] if breadcrumbs else None,
                                     "breadcrumbs": breadcrumbs, "content_type": ctype
                                 }
                                 chunks.append(Chunk(content=c_part, metadata=meta))
                    else:
                        meta = {
                            "page_number": page, "heading": breadcrumbs[-1] if breadcrumbs else None,
                            "breadcrumbs": breadcrumbs, "content_type": ctype
                        }
                        chunks.append(Chunk(content=chunk_txt, metadata=meta))
            return 
        
        # If we hit base case len <= limit, append it (handled at top)
        for c in final_chunks:
            meta = {
                "page_number": page,
                "heading": breadcrumbs[-1] if breadcrumbs else None,
                "breadcrumbs": breadcrumbs,
                "content_type": ctype
            }
            chunks.append(Chunk(content=c, metadata=meta))

    def _create_single(self, chunks, text, ctype, page, breadcrumbs):
        meta = {
            "page_number": page,
            "heading": breadcrumbs[-1] if breadcrumbs else None,
            "breadcrumbs": breadcrumbs,
            "content_type": ctype
        }
        chunks.append(Chunk(content=text, metadata=meta))

def structural_chunk(pages_json: List[Dict]) -> List[Chunk]:
    return StructuralChunker().chunk(pages_json)
