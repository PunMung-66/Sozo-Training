#!/usr/bin/env python3
"""Command-line entry point for Kandinsky 2.2 image inpainting."""

from __future__ import annotations

import argparse
from pathlib import Path

from kandinsky_inpainting import generate_inpainting


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("kandinsky",), default="kandinsky")
    parser.add_argument("--image", type=Path, required=True, help="Source image path")
    parser.add_argument("--mask", type=Path, required=True, help="Mask image path")
    parser.add_argument("--prompt", required=True, help="Description of the image to generate")
    parser.add_argument("--negative", default="", help="Content to avoid in the generated image")
    parser.add_argument("--output", type=Path, required=True, help="Output image path")
    parser.add_argument("--steps", type=int, default=50, help="Number of inference steps")
    parser.add_argument("--guidance-scale", type=float, default=4.0)
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

    with Image.open(args.image) as source:
        image = source.convert("RGB")
    with Image.open(args.mask) as source:
        mask_image = source.convert("L")

    generated = generate_inpainting(
        image=image,
        mask_image=mask_image,
        prompt=args.prompt,
        negative_prompt=args.negative,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance_scale,
        seed=args.seed,
        device=args.device,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generated.save(args.output)
    print(f"Generated image saved to {args.output}")


if __name__ == "__main__":
    main()
