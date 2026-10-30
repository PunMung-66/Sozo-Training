

# this code is just a AI generated template for metrics, it is not used in the current implementation
# JJ will update and optimize it later, for now it is just a placeholder for future metrics implementation
# list of metrics to implement:
# - four input calling path and output path
# - consider about running on GPU or CPU
# - clean code and remove unnecessary imports
# - do i need to separate the metrics into different files? or just keep them in one file?


"""Comparison metrics for one (input, mask, output, prompt) case.

- SSIM / LPIPS on the unmasked region only (background preservation; SSIM higher, LPIPS lower is better)
- CLIP score of the prompt vs. the masked region's bounding-box crop (prompt-following)

Usage: python metrics.py --input in.png --mask mask.png --output out.png --prompt "..." [--sanity]
--sanity also scores the paste-back composite (should give SSIM ~1 / LPIPS ~0), the SDXL VAE
round-trip of the input (floor any non-paste-back model pays), and the original image's crop CLIP.
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(HERE / "hf_cache"))
os.environ.setdefault("TORCH_HOME", str(HERE / "hf_cache" / "torch"))

import argparse
import json

import numpy as np
import torch
from PIL import Image
from skimage.metrics import structural_similarity

CLIP_REPO = "openai/clip-vit-large-patch14"
_lpips = None
_clip = None


def load_rgb(path, size=None):
    im = Image.open(path).convert("RGB")
    return im.resize((size, size)) if size and im.size != (size, size) else im


def load_mask(path, size):
    m = Image.open(path).convert("L").resize((size, size), Image.NEAREST)
    return np.asarray(m) > 127  # True = inpaint region


def ssim_unmasked(ref, out, mask):
    _, smap = structural_similarity(
        np.asarray(ref), np.asarray(out), channel_axis=-1, data_range=255, full=True,
    )
    return float(smap.mean(axis=-1)[~mask].mean())


def lpips_unmasked(ref, out, mask):
    global _lpips
    import lpips

    if _lpips is None:
        _lpips = lpips.LPIPS(net="alex", spatial=True, verbose=False).cuda().eval()

    def t(im):
        return torch.from_numpy(np.array(im)).permute(2, 0, 1)[None].float().cuda() / 127.5 - 1

    with torch.no_grad():
        dmap = _lpips(t(ref), t(out))[0, 0].cpu().numpy()
    return float(dmap[~mask].mean())


def clip_score(im, prompt):
    """100 * max(cos, 0), the torchmetrics CLIPScore convention."""
    global _clip
    from transformers import CLIPModel, CLIPProcessor

    if _clip is None:
        _clip = (CLIPModel.from_pretrained(CLIP_REPO).cuda().eval(), CLIPProcessor.from_pretrained(CLIP_REPO))
    model, proc = _clip
    inputs = proc(text=[prompt], images=im, return_tensors="pt", padding=True, truncation=True, max_length=77).to("cuda")
    with torch.no_grad():
        o = model(**inputs)
    cos = torch.nn.functional.cosine_similarity(o.image_embeds, o.text_embeds).item()
    return 100 * max(cos, 0.0)


def mask_crop(im, mask):
    ys, xs = np.nonzero(mask)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def score(ref, out, mask, prompt):
    return {
        "ssim_unmasked": round(ssim_unmasked(ref, out, mask), 4),
        "lpips_unmasked": round(lpips_unmasked(ref, out, mask), 4),
        "clip_crop": round(clip_score(mask_crop(out, mask), prompt), 2),
        "clip_full": round(clip_score(out, prompt), 2),
    }


def vae_roundtrip(im, repo="diffusers/stable-diffusion-xl-1.0-inpainting-0.1"):
    from diffusers import AutoencoderKL

    # SDXL's VAE overflows in fp16, so run it in fp32 with tiling to fit 8 GB.
    vae = AutoencoderKL.from_pretrained(repo, subfolder="vae", torch_dtype=torch.float32).cuda()
    vae.enable_tiling()
    x = torch.from_numpy(np.array(im)).permute(2, 0, 1)[None].float().cuda() / 127.5 - 1
    with torch.no_grad():
        y = vae.decode(vae.encode(x).latent_dist.mode()).sample
    y = ((y[0].clamp(-1, 1) + 1) * 127.5).round().byte().permute(1, 2, 0).cpu().numpy()
    del vae
    torch.cuda.empty_cache()
    return Image.fromarray(y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--mask", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--sanity", action="store_true")
    ap.add_argument("--log", type=Path, help="append the record to this jsonl file")
    args = ap.parse_args()

    out = load_rgb(args.output)
    size = out.size[0]
    ref = load_rgb(args.input, size)
    mask = load_mask(args.mask, size)

    record = {"output": args.output.name, "prompt": args.prompt, "size": size,
              "mask_frac": round(float(mask.mean()), 4), **score(ref, out, mask, args.prompt)}

    if args.sanity:
        m3 = mask[..., None]
        composite = Image.fromarray(np.where(m3, np.asarray(out), np.asarray(ref)))
        record["sanity_composite"] = score(ref, composite, mask, args.prompt)
        record["sanity_vae_floor"] = {k: v for k, v in score(ref, vae_roundtrip(ref), mask, args.prompt).items()
                                      if k.endswith("unmasked")}
        record["sanity_original_clip_crop"] = round(clip_score(mask_crop(ref, mask), args.prompt), 2)

    print(json.dumps(record, indent=2))
    if args.log:
        with open(args.log, "a") as f:
            f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    main()
