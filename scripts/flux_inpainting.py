"""FLUX.1 Fill [dev] inpainting helpers."""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

INPAINT_MODEL_ID = "black-forest-labs/FLUX.1-Fill-dev"


def generate_inpainting(
    image: Image.Image,
    mask_image: Image.Image,
    prompt: str,
    negative_prompt: str = "",
    num_inference_steps: int = 50,
    guidance_scale: float = 30.0,
    seed: int | None = None,
    device: str = "auto",
) -> Image.Image:
    """Generate an inpainted image; white mask pixels are regenerated."""
    if device not in {"auto", "cuda", "cpu"}:
        raise ValueError(f"Unsupported device {device!r}; choose 'auto', 'cuda', or 'cpu'.")
    if image.size != mask_image.size:
        raise ValueError(
            f"Image and mask dimensions must match; got {image.size} and {mask_image.size}."
        )
    if image.width % 16 or image.height % 16:
        raise ValueError(
            "FLUX.1 Fill requires image width and height to be multiples of 16; "
            f"got {image.width}x{image.height}."
        )
    if negative_prompt:
        raise ValueError(
            "FLUX.1 Fill does not support negative prompts; omit --negative "
            "when using --model flux-fill."
        )

    import torch
    from diffusers import FluxFillPipeline
    from gpu_status import check_cuda

    cuda_available = check_cuda(torch) if device != "cpu" else False
    if device == "cuda" and not cuda_available:
        raise RuntimeError(
            "CUDA was requested, but PyTorch cannot access a CUDA GPU. "
            "Run `python scripts/check_gpu.py` to diagnose the environment."
        )
    use_cuda = cuda_available and device != "cpu"
    device = "cuda" if use_cuda else "cpu"
    dtype = torch.bfloat16 if use_cuda else torch.float32
    if use_cuda:
        print("Using CUDA with CPU model offload.")
    else:
        print("Using CPU; FLUX.1 Fill is a large model and generation will be very slow.")
    generator = torch.Generator(device=device)
    if seed is not None:
        generator.manual_seed(seed)

    pipeline = FluxFillPipeline.from_pretrained(
        INPAINT_MODEL_ID,
        torch_dtype=dtype,
    )
    if use_cuda:
        pipeline.enable_model_cpu_offload()
    else:
        pipeline.to(device)

    try:
        result = pipeline(
            prompt=prompt,
            image=image.convert("RGB"),
            mask_image=mask_image.convert("L"),
            height=image.height,
            width=image.width,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            max_sequence_length=512,
            generator=generator,
        )
        output = result.images[0]
    finally:
        del pipeline
        gc.collect()
        if use_cuda:
            torch.cuda.empty_cache()
    return output
