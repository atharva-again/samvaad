"""
GPU utilities for device detection and management.
"""

import warnings

import onnxruntime as ort


def get_device():
    """Detect and return the available device ('cuda' or 'cpu')."""
    try:
        providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in providers:
            return 'cuda'
    except Exception as exc:
        warnings.warn(
            f"GPU detection failed ({exc!s}); defaulting to CPU.",
            RuntimeWarning,
        )
    return 'cpu'


def get_ort_provider():
    """Return the preferred ONNX Runtime execution provider."""
    device = get_device()
    if device == 'cuda':
        return 'CUDAExecutionProvider'
    return 'CPUExecutionProvider'

if __name__ == "__main__":
    print(f"Detected device: {get_device()}")
    print(f"Using ONNX Runtime provider: {get_ort_provider()}")