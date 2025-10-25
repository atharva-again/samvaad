from typing import List, Union
from samvaad.utils.gpu_utils import get_ort_provider
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from huggingface_hub import hf_hub_download
import contextlib
import os


class ONNXEmbeddingModel:
    """
    ONNX-based embedding model using onnxruntime.
    Optimized for EmbeddingGemma300m with proper prompt handling.
    """

    def __init__(
        self,
        model_repo: str = "onnx-community/embeddinggemma-300m-ONNX",
    ):
        """
        Initialize ONNX embedding model.

        Args:
            model_repo: HuggingFace repo containing ONNX model
        """
        # Download model files
        model_path = hf_hub_download(model_repo, subfolder="onnx", filename="model_q4.onnx")
        data_path = hf_hub_download(model_repo, subfolder="onnx", filename="model_q4.onnx_data")

        # Get provider and set adaptive parameters
        provider = get_ort_provider()
        is_gpu = provider == 'CUDAExecutionProvider'
        
        # Adaptive batch sizing based on device
        self.MAX_BATCH_SIZE = 64 if is_gpu else 32  # GPU can handle larger batches
        self.TARGET_TOKENS_PER_BATCH = 8_192 if is_gpu else 4_096  # GPU has more memory

        # Provider-specific session options
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        if not is_gpu:
            # CPU-specific optimizations
            session_options.intra_op_num_threads = 0  # Auto-detect physical cores
            session_options.inter_op_num_threads = 0  # Auto-detect
            session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL  

        with contextlib.redirect_stderr(open(os.devnull, "w")):
            self.session = ort.InferenceSession(model_path, session_options, providers=[provider])

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_repo)

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

        if not texts:
            return np.empty((0, 768), dtype=np.float32)

        prompts = [f"title: none | text: {text}" for text in texts]

        try:
            preview_encoding = self.tokenizer(
                prompts,
                padding=False,
                truncation=True,
                max_length=2048,
            )
            token_lengths = [len(ids) for ids in preview_encoding["input_ids"]]
        except Exception:
            token_lengths = [0] * len(prompts)

        batches: List[List[str]] = []
        current_batch: List[str] = []
        tokens_in_batch = 0

        for prompt, length in zip(prompts, token_lengths):
            token_count = max(1, length)
            if current_batch and (
                len(current_batch) >= self.MAX_BATCH_SIZE
                or tokens_in_batch + token_count > self.TARGET_TOKENS_PER_BATCH
            ):
                batches.append(current_batch)
                current_batch = []
                tokens_in_batch = 0

            current_batch.append(prompt)
            tokens_in_batch += token_count

        if current_batch:
            batches.append(current_batch)

        all_embeddings = []
        for batch_prompts in batches:
            try:
                inputs = self.tokenizer(
                    batch_prompts,
                    return_tensors="np",
                    padding=True,
                    truncation=True,
                    max_length=2048,
                )

                with contextlib.redirect_stderr(open(os.devnull, "w")):
                    outputs = self.session.run(None, inputs.data)

                batch_embeddings = outputs[-1]
                all_embeddings.extend(batch_embeddings)
            except Exception as exc:
                print(f"Warning: Failed to embed batch: {exc}")
                all_embeddings.extend(
                    [np.zeros(768, dtype=np.float32)] * len(batch_prompts)
                )

        return np.asarray(all_embeddings, dtype=np.float32)

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

        # Tokenize and run inference
        inputs = self.tokenizer(prompted_text, return_tensors="np", padding=True, truncation=True, max_length=2048)

        with contextlib.redirect_stderr(open(os.devnull, "w")):
            outputs = self.session.run(None, inputs.data)

        # Extract sentence embedding
        embedding = outputs[-1][0]  # Shape: (768,)
        return np.array(embedding)