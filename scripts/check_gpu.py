#!/usr/bin/env python3
"""Report NVIDIA driver visibility and PyTorch CUDA availability."""

from __future__ import annotations

from gpu_status import check_cuda


def main() -> int:
    try:
        import torch
    except ImportError:
        print("PyTorch: not installed in this Python environment")
        print("Install dependencies with `python -m pip install -r scripts/requirement.txt`.")
        return 1

    if not check_cuda(torch):
        print("CUDA is unavailable; image generation will use CPU unless CUDA is required.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
