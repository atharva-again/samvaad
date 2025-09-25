"""
GPU utilities for device detection and management.
"""

import torch

def get_device():
    """
    Detect and return the available device ('cuda' or 'cpu').
    """
    if torch.cuda.is_available():
        return 'cuda'
    else:
        return 'cpu'