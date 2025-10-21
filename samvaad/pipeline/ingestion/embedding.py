from typing import List, Tuple, Union
from samvaad.pipeline.vectorstore.vectorstore import get_collection
from samvaad.utils.hashing import generate_chunk_id
from samvaad.utils.gpu_utils import get_device
from llama_cpp import Llama
import numpy as np
import contextlib
import os


"""
GGUF-based embedding model for EmbeddingGemma.
Uses llama-cpp-python for efficient quantized inference.
"""


class GGUFEmbeddingModel:
    """
    GGUF-based embedding model using llama-cpp-python.
    Optimized for EmbeddingGemma with proper prompt handling.
    """

    def __init__(
        self,
        model_repo: str = "unsloth/embeddinggemma-300m-GGUF",
        quantization: str = "Q8_0",
    ):
        """
        Initialize GGUF embedding model.

        Args:
            model_repo: HuggingFace repo containing GGUF files
            quantization: Quantization type (Q4_0, Q8_0, etc.)
        """
        # Map quantization to filename
        filename_map = {
            "Q4_0": "embeddinggemma-300M-Q4_0.gguf",
            "Q8_0": "embeddinggemma-300M-Q8_0.gguf",
            "f16": "embeddinggemma-300M-f16.gguf",
            "f32": "embeddinggemma-300M-f32.gguf",
        }

        filename = filename_map.get(quantization, "embeddinggemma-300M-Q8_0.gguf")

        # Detect GPU availability
        device = get_device()
        use_gpu = device == "cuda"

        # Initialize llama model for embeddings using from_pretrained
        model_kwargs = {
            "repo_id": model_repo,
            "filename": filename,
            "embedding": True,  # Enable embedding mode
            "n_ctx": 2048,  # Max context length for EmbeddingGemma
            "n_threads": -1,  # Use all available CPU threads
            "verbose": False,  # Reduce logging
            "local_files_only": True,  # Use only local cached files, no network access
        }

        # Add GPU acceleration if available
        if use_gpu:
            model_kwargs.update(
                {
                    "n_gpu_layers": -1,  # Offload all layers to GPU (may not help much for embeddings)
                    "main_gpu": 0,  # Use first GPU
                    "use_mmap": True,  # Memory mapping for faster loading
                    "use_mlock": False,  # Don't lock memory (let GPU manage)
                }
            )

        with contextlib.redirect_stderr(open(os.devnull, "w")):
            self.model = Llama.from_pretrained(**model_kwargs)

    def encode_document(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Encode documents with proper retrieval prompts.

        Args:
            texts: Single text or list of texts

        Returns:
            numpy array of embeddings (shape: [len(texts), 768])
        """
        if isinstance(texts, str):
            texts = [texts]

        all_embeddings = []
        for text in texts:
            # Apply document prompt
            prompted_text = f"title: none | text: {text}"

            try:
                with contextlib.redirect_stderr(open(os.devnull, "w")):
                    embedding = self.model.embed(prompted_text)
                all_embeddings.append(embedding)
            except Exception as e:
                print(f"Warning: Failed to embed text: {e}")
                # Return zero vector as fallback
                all_embeddings.append(np.zeros(768, dtype=np.float32))

        return np.array(all_embeddings)

    def encode_query(self, text: str) -> np.ndarray:
        """
        Encode query with proper retrieval prompt.

        Args:
            text: Query text

        Returns:
            numpy array of embedding (shape: [768])
        """
        # Apply query prompt
        prompted_text = f"task: search result | query: {text}"

        # Get embedding
        with contextlib.redirect_stderr(open(os.devnull, "w")):
            embedding = self.model.embed(prompted_text)

        return np.array(embedding)


# Use GGUF quantized EmbeddingGemma (Q8_0 for better accuracy)
_MODEL_REPO = "unsloth/embeddinggemma-300m-GGUF"
_QUANTIZATION = "Q8_0"

# Global model instance to avoid reloading
_model = None


def embed_chunks_with_dedup(
    chunks: List[str], filename: str = None
) -> Tuple[List[List[float]], List[int]]:
    """
    Embed chunks with deduplication - only compute embeddings for chunks that don't already exist in ChromaDB.
    Uses content-based IDs to avoid re-embedding identical chunks that may have shifted position.
    Returns: (embeddings_list, indices_embedded) where indices_embedded shows which chunks were actually embedded.
    """

    # Generate content-based IDs for all chunks (SHA256 hash only)
    chunk_ids = [generate_chunk_id(chunk) for chunk in chunks]

    # Deduplicate within the current batch first
    unique_chunks_map = {}  # chunk_id -> (original_index, chunk_content)
    for i, (chunk, chunk_id) in enumerate(zip(chunks, chunk_ids)):
        if chunk_id not in unique_chunks_map:
            unique_chunks_map[chunk_id] = (i, chunk)

    unique_chunk_ids = list(unique_chunks_map.keys())

    # Check which chunks already exist in ChromaDB
    existing = set()
    if len(unique_chunk_ids) > 0:
        try:
            collection = get_collection()
            get_res = collection.get(ids=unique_chunk_ids)
        except Exception as exc:
            print(
                f"Warning: unable to query existing chunk IDs from Chroma ({exc}). Treating all as new."
            )
            get_res = None
        if get_res and "ids" in get_res:
            existing = set(get_res["ids"])

    # Find chunks that need embedding
    to_embed = []
    for chunk_id, (original_idx, chunk_content) in unique_chunks_map.items():
        if chunk_id not in existing:
            to_embed.append((original_idx, chunk_content))

    if not to_embed:
        print(
            "All chunks for this file already exist in ChromaDB. No embeddings needed."
        )
        return [], []

    # Extract chunks that need embedding
    embed_indices, chunks_to_embed = zip(*to_embed)
    embed_indices = list(embed_indices)
    chunks_to_embed = list(chunks_to_embed)

    print(
        f"Embedding {len(chunks_to_embed)} new chunks out of {len(chunks)} total chunks."
    )

    # Compute embeddings only for new chunks
    global _model
    if _model is None:
        _model = GGUFEmbeddingModel(_MODEL_REPO, _QUANTIZATION)

    embeddings = _model.encode_document(chunks_to_embed)

    return embeddings.tolist(), embed_indices
