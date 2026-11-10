"""Stable Diffusion XL inpainting helpers."""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

INPAINT_MODEL_ID = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
MIN_FREE_VRAM_BYTES = 12 * 1024**3


def generate_inpainting(
    image: Image.Image,
    mask_image: Image.Image,
    prompt: str,
    negative_prompt: str = "",
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
    strength: float = 0.99,
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
    if image.width % 8 or image.height % 8:
        raise ValueError(
            "SDXL requires image width and height to be multiples of 8; "
            f"got {image.width}x{image.height}."
        )
    if not 0.0 < strength <= 1.0:
        raise ValueError(f"strength must be in (0, 1]; got {strength}.")

    import torch
    from diffusers import StableDiffusionXLInpaintPipeline
    from gpu_status import check_cuda

    cuda_available = check_cuda(torch) if device != "cpu" else False
    if device == "cuda" and not cuda_available:
        raise RuntimeError(
            "CUDA was requested, but PyTorch cannot access a CUDA GPU. "
            "Run `python scripts/check_gpu.py` to diagnose the environment."
        )
    use_cuda = cuda_available and device != "cpu"
    device = "cuda" if use_cuda else "cpu"
    dtype = torch.float16 if use_cuda else torch.float32
    use_model_cpu_offload = False
    if use_cuda:
        free_vram, _ = torch.cuda.mem_get_info()
        use_model_cpu_offload = free_vram < MIN_FREE_VRAM_BYTES
        if use_model_cpu_offload:
            print(
                f"Only {free_vram / 1024**3:.1f} GiB of VRAM is free; "
                "using CUDA with CPU model offload."
            )
        else:
            print(
                f"Using CUDA without CPU model offload "
                f"({free_vram / 1024**3:.1f} GiB VRAM free)."
            )
    else:
        print("Using CPU; image generation will be very slow.")
    generator = torch.Generator(device=device)
    if seed is not None:
        generator.manual_seed(seed)

    pipeline = StableDiffusionXLInpaintPipeline.from_pretrained(
        INPAINT_MODEL_ID,
        torch_dtype=dtype,
        variant="fp16" if use_cuda else None,
        use_safetensors=True,
    )
    if use_cuda and use_model_cpu_offload:
        pipeline.enable_model_cpu_offload()
    else:
        pipeline.to(device)

    try:
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt or None,
            image=image.convert("RGB"),
            mask_image=mask_image.convert("L"),
            height=image.height,
            width=image.width,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
        )
        output = result.images[0]
    finally:
        del pipeline
        gc.collect()
        if use_cuda:
            torch.cuda.empty_cache()
    return output