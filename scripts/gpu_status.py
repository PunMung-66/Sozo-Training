"""GPU availability checks shared by the diagnostic and image generator."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


def check_cuda(torch_module: Any) -> bool:
    """Report NVIDIA driver/PyTorch status and return CUDA usability."""
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        print("nvidia-smi: not found")
    else:
        result = subprocess.run(
            [
                nvidia_smi,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode == 0:
            print("GPUs visible to NVIDIA driver:")
            print(result.stdout.strip() or "  no GPUs found")
        else:
            print(f"nvidia-smi failed: {result.stderr.strip() or result.returncode}")

    cuda_available = torch_module.cuda.is_available()
    print(f"PyTorch: {torch_module.__version__}")
    print(f"PyTorch CUDA runtime: {torch_module.version.cuda or 'CPU-only build'}")
    if not cuda_available:
        print("PyTorch CUDA: unavailable")
        return False

    print(f"PyTorch CUDA: available ({torch_module.cuda.device_count()} device(s))")
    for index in range(torch_module.cuda.device_count()):
        name = torch_module.cuda.get_device_name(index)
        capability = torch_module.cuda.get_device_capability(index)
        print(f"  GPU {index}: {name}, compute capability {capability[0]}.{capability[1]}")
        if capability[0] >= 12 and torch_module.version.cuda:
            cuda_version = tuple(
                int(part) for part in torch_module.version.cuda.split(".")[:2]
            )
            if cuda_version < (12, 8):
                print(
                    "  WARNING: RTX 50-series GPUs need a PyTorch build with CUDA 12.8 "
                    "or newer for Blackwell support."
                )
    return True
