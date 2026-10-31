"""Kandinsky 2.2 inpainting helpers."""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

PRIOR_MODEL_ID = "kandinsky-community/kandinsky-2-2-prior"
INPAINT_MODEL_ID = "kandinsky-community/kandinsky-2-2-inpainting"


def generate_inpainting(
    image: Image.Image,
    mask_image: Image.Image,
    prompt: str,
    negative_prompt: str = "",
    num_inference_steps: int = 50,
    guidance_scale: float = 4.0,
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
    if image.width % 64 or image.height % 64:
        raise ValueError(
            "Kandinsky 2.2 requires image width and height to be multiples of 64; "
            f"got {image.width}x{image.height}."
        )

    import torch
    from diffusers import KandinskyV22InpaintPipeline, KandinskyV22PriorPipeline
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
    if use_cuda:
        print("Using CUDA with CPU model offload.")
    else:
        print("Using CPU; image generation will be slow.")
    generator = torch.Generator(device=device)
    if seed is not None:
        generator.manual_seed(seed)

    prior = KandinskyV22PriorPipeline.from_pretrained(
        PRIOR_MODEL_ID,
        torch_dtype=dtype,
    )
    if use_cuda:
        prior.enable_model_cpu_offload()
    else:
        prior.to(device)

    prior_output = prior(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=generator,
    )
    image_embeds = prior_output.image_embeds
    negative_image_embeds = prior_output.negative_image_embeds
    del prior, prior_output
    gc.collect()
    if use_cuda:
        torch.cuda.empty_cache()

    pipeline = KandinskyV22InpaintPipeline.from_pretrained(
        INPAINT_MODEL_ID,
        torch_dtype=dtype,
    )
    if use_cuda:
        pipeline.enable_model_cpu_offload()
    else:
        pipeline.to(device)

    result = pipeline(
        image_embeds=image_embeds,
        negative_image_embeds=negative_image_embeds,
        image=image.convert("RGB"),
        mask_image=mask_image.convert("L"),
        height=image.height,
        width=image.width,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=generator,
    )
    return result.images[0]
