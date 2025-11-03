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

        # Tokenize all prompts at once
        inputs = self.tokenizer(prompts, truncation=True, padding=True, max_length=2048, return_tensors="np")
        input_ids_all = inputs['input_ids']
        attention_mask_all = inputs['attention_mask']

        # Manual batching based on token count
        batches: List[dict] = []
        current_input_ids: List[np.ndarray] = []
        current_attention_masks: List[np.ndarray] = []
        tokens_in_batch = 0

        for i, (input_id, attention_mask) in enumerate(zip(input_ids_all, attention_mask_all)):
            token_count = np.sum(attention_mask)  # Number of non-padding tokens
            if current_input_ids and (
                len(current_input_ids) >= self.MAX_BATCH_SIZE
                or tokens_in_batch + token_count > self.TARGET_TOKENS_PER_BATCH
            ):
                # Stack current batch
                batch_input_ids = np.stack(current_input_ids)
                batch_attention_mask = np.stack(current_attention_masks)
                batches.append({"input_ids": batch_input_ids, "attention_mask": batch_attention_mask})
                current_input_ids = []
                current_attention_masks = []
                tokens_in_batch = 0

            current_input_ids.append(input_id)
            current_attention_masks.append(attention_mask)
            tokens_in_batch += token_count

        if current_input_ids:
            batch_input_ids = np.stack(current_input_ids)
            batch_attention_mask = np.stack(current_attention_masks)
            batches.append({"input_ids": batch_input_ids, "attention_mask": batch_attention_mask})

        all_embeddings = []
        for batch in batches:
            try:
                with contextlib.redirect_stderr(open(os.devnull, "w")):
                    outputs = self.session.run(None, batch)

                batch_embeddings = outputs[-1]
                all_embeddings.extend(batch_embeddings)
            except Exception as exc:
                print(f"Warning: Failed to embed batch: {exc}")
                all_embeddings.extend(
                    [np.zeros(768, dtype=np.float32)] * len(batch["input_ids"])
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

        # Tokenize
        inputs = self.tokenizer(
            prompted_text, 
            truncation=True,
            max_length=2048,
            add_special_tokens=True,
            return_tensors="np"
        )
        
        input_ids = inputs['input_ids'][0]  # Since single
        attention_mask = inputs['attention_mask'][0]
        
        session_inputs = {
            "input_ids": input_ids.reshape(1, -1),  # Add batch dim
            "attention_mask": attention_mask.reshape(1, -1)
        }

        with contextlib.redirect_stderr(open(os.devnull, "w")):
            outputs = self.session.run(None, session_inputs)

        # Extract sentence embedding
        embedding = outputs[-1][0]  # Shape: (768,)
        return np.array(embedding)