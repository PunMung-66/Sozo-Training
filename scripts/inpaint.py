#!/usr/bin/env python3
"""Command-line entry point for Kandinsky 2.2, SDXL, and FLUX.1 Fill."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        choices=("kandinsky", "sdxl", "flux-fill"),
        default="kandinsky",
        help="Inpainting model to use (default: kandinsky)",
    )
    parser.add_argument("--image", type=Path, required=True, help="Source image path")
    parser.add_argument("--mask", type=Path, required=True, help="Mask image path")
    parser.add_argument("--prompt", required=True, help="Description of the image to generate")
    parser.add_argument("--negative", default="", help="Content to avoid in the generated image")
    parser.add_argument("--output", type=Path, required=True, help="Output image path")
    parser.add_argument("--steps", type=int, help="Number of inference steps")
    parser.add_argument("--guidance-scale", type=float, help="Prompt guidance scale")
    parser.add_argument(
        "--strength",
        type=float,
        help="SDXL only: how much of the masked area to regenerate, in (0, 1] (default: 0.99)",
    )
    parser.add_argument("--seed", type=int, help="Optional seed for reproducible generation")
    parser.add_argument(
        "--device",
        choices=("auto", "cuda", "cpu"),
        default="auto",
        help="Device to use; auto selects CUDA when PyTorch can access it",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from PIL import Image

    if args.strength is not None and args.model != "sdxl":
        raise SystemExit("--strength is only supported with --model sdxl.")
    extra_kwargs = {}
    if args.model == "sdxl":
        if args.strength is not None:
            extra_kwargs["strength"] = args.strength
        from sdxl_inpainting import generate_inpainting

        steps = args.steps if args.steps is not None else 30
        guidance_scale = (
            args.guidance_scale if args.guidance_scale is not None else 7.5
        )
    elif args.model == "flux-fill":
        from flux_inpainting import generate_inpainting

        steps = args.steps if args.steps is not None else 50
        guidance_scale = (
            args.guidance_scale if args.guidance_scale is not None else 30.0
        )
    else:
        from kandinsky_inpainting import generate_inpainting

        steps = args.steps if args.steps is not None else 50
        guidance_scale = (
            args.guidance_scale if args.guidance_scale is not None else 4.0
        )

    with Image.open(args.image) as source:
        image = source.convert("RGB")
    with Image.open(args.mask) as source:
        mask_image = source.convert("L")

    generated = generate_inpainting(
        image=image,
        mask_image=mask_image,
        prompt=args.prompt,
        negative_prompt=args.negative,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        seed=args.seed,
        device=args.device,
        **extra_kwargs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generated.save(args.output)
    print(f"Generated image saved to {args.output}")


if __name__ == "__main__":
    main()
