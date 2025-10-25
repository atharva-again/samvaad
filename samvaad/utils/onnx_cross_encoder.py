import os
import numpy as np
import contextlib
from typing import List, Union
from transformers import AutoTokenizer
from huggingface_hub import hf_hub_download
from samvaad.utils.gpu_utils import get_ort_provider
import onnxruntime as ort


class ONNXCrossEncoder:
    """ONNX-based cross-encoder for efficient passage reranking."""

    def __init__(self, model_repo: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: str = None, model_file: str = "onnx/model.onnx"):
        """
        Initialize ONNX cross-encoder.

        Args:
            model_repo: HuggingFace repository containing the model
            device: Device to run inference on ('cpu', 'cuda', etc.)
            model_file: Specific ONNX model file to use (e.g., 'onnx/model_qint8_avx512.onnx')
        """
        self.model_repo = model_repo

        self.model_file = model_file

        # Download the specific ONNX model file
        self.model_path = hf_hub_download(model_repo, filename=model_file)

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_repo)

        # Set up ONNX Runtime session
        provider = get_ort_provider()
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        with contextlib.redirect_stderr(open(os.devnull, "w")):
            self.session = ort.InferenceSession(self.model_path, session_options, providers=[provider])

    def predict(self, pairs: List[List[str]]) -> np.ndarray:
        """
        Predict relevance scores for query-passage pairs.

        Args:
            pairs: List of [query, passage] pairs

        Returns:
            numpy array of scores
        """
        scores = []

        for query, passage in pairs:
            # Tokenize the pair
            inputs = self.tokenizer(
                query,
                passage,
                truncation=True,
                max_length=512,  # Standard max length for this model
                padding=True,
                return_tensors="np"
            )

            # Run inference directly with ONNX Runtime
            with contextlib.redirect_stderr(open(os.devnull, "w")):
                outputs = self.session.run(None, dict(inputs))

            # Extract logits from the model output
            logits = outputs[0]  # First output is typically the logits

            # For cross-encoders, we typically use the score from the positive class
            # This is usually the second column (index 1) for binary classification
            if logits.shape[1] == 2:
                score = logits[0, 1]  # Positive class score
            else:
                # If not binary classification, use the first logit
                score = logits[0, 0]

            scores.append(score)

        return np.array(scores)


# Global instance for reuse
_cross_encoder_instance = None


def get_onnx_cross_encoder(model_repo: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", model_file: str = "onnx/model_qint8_avx512.onnx") -> ONNXCrossEncoder:
    """Get or create ONNX cross-encoder instance."""
    global _cross_encoder_instance
    if _cross_encoder_instance is None:
        _cross_encoder_instance = ONNXCrossEncoder(model_repo, model_file=model_file)
    return _cross_encoder_instance