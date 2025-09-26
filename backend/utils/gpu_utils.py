"""
GPU utilities for device detection and management.
"""

import warnings

import torch


def get_device():
    """Detect and return the available device ('cuda' or 'cpu')."""
    try:
        if torch.cuda.is_available():
            return 'cuda'
    except Exception as exc:
        warnings.warn(
            f"GPU detection failed ({exc!s}); defaulting to CPU.",
            RuntimeWarning,
        )
    return 'cpu'