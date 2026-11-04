"""Inpainting comparison metrics: SSIM / LPIPS (unmasked area), CLIP score (mask crop / full image).

How to run (from Sozo-Training/):
    pip install torch transformers lpips scikit-image numpy pillow
    python metrics/metrics.py --root datasets --gen-root outputs --models sdxl kandinsky flux --prompts prompts.json

Files:
    datasets/<style>/<stem>.jpg + <stem>_mask.png   room + mask (white = inpaint area)
    outputs/<model>/<style>/<stem>.png              generated image (same stem)
    prompts.json  {"<style>/<stem>": "prompt"}       or {"<style>": "prompt"} for a whole folder
    -> results/metrics.jsonl (per image), results/summary.csv (mean/std per model and model x style)
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import lpips
import numpy as np
import torch
from PIL import Image, ImageOps
from skimage.metrics import structural_similarity
from transformers import CLIPModel, CLIPProcessor

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
CLIP_REPO = "openai/clip-vit-large-patch14"
METRICS = ["ssim_unmasked", "lpips_unmasked", "clip_crop", "clip_full"]


def find_pairs(root):
    """(style, image, mask) for every <style>/<stem>.* that has a <stem>_mask.* next to it."""
    pairs = []
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        for f in sorted(d.iterdir()):
            if f.suffix.lower() in IMG_EXT and not f.stem.endswith("_mask"):
                mask = next((m for m in d.iterdir() if m.stem == f.stem + "_mask"), None)
                if mask:
                    pairs.append((d.name, f, mask))
    return pairs


def load_reference(img_path, mask_path, size):
    """Original image + bool mask (True = inpaint) resized to the output size, like the generator saw them."""
    img = ImageOps.exif_transpose(Image.open(img_path)).convert("RGB").resize(size, Image.LANCZOS)
    mask = Image.open(mask_path).convert("L").resize(size, Image.NEAREST)
    return img, np.asarray(mask) > 127


def mask_crop(im, mask):
    """Mask bounding box, padded to a square so CLIP's center crop keeps all of it."""
    ys, xs = np.nonzero(mask)
    crop = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    side = max(crop.size)
    square = Image.new("RGB", (side, side))
    square.paste(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    return square


class Scorer:
    def __init__(self, device):
        self.device = device
        self.lpips = lpips.LPIPS(net="alex", spatial=True, verbose=False).to(device).eval()
        self.clip = CLIPModel.from_pretrained(CLIP_REPO).to(device).eval()
        self.proc = CLIPProcessor.from_pretrained(CLIP_REPO)

    @torch.no_grad()
    def clip_score(self, im, prompt):
        x = self.proc(text=[prompt], images=im, return_tensors="pt", padding=True, truncation=True).to(self.device)
        o = self.clip(**x)
        return 100 * max(torch.cosine_similarity(o.image_embeds, o.text_embeds).item(), 0.0)

    @torch.no_grad()
    def score(self, img_path, mask_path, out_path, prompt):
        out = Image.open(out_path).convert("RGB")
        ref, mask = load_reference(img_path, mask_path, out.size)
        keep = ~mask
        # Put the original back inside the mask so the new furniture can't leak into the background score.
        bg = np.where(mask[..., None], np.asarray(ref), np.asarray(out))

        _, smap = structural_similarity(np.asarray(ref), bg, channel_axis=-1, data_range=255, full=True)
        to_t = lambda a: torch.from_numpy(np.array(a)).permute(2, 0, 1)[None].float().to(self.device) / 127.5 - 1
        dmap = self.lpips(to_t(ref), to_t(bg))[0, 0].cpu().numpy()

        return {
            "prompt": prompt,
            "mask_frac": round(float(mask.mean()), 4),
            "ssim_unmasked": round(float(smap.mean(-1)[keep].mean()), 4),
            "lpips_unmasked": round(float(dmap[keep].mean()), 4),
            "clip_crop": round(self.clip_score(mask_crop(out, mask), prompt), 2),
            "clip_full": round(self.clip_score(out, prompt), 2),
        }


def write_summary(rows, path):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["model"], "ALL")].append(r)
        groups[(r["model"], r["style"])].append(r)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "style", "n"] + [f"{m}_{s}" for m in METRICS for s in ("mean", "std")])
        for (model, style), rs in sorted(groups.items()):
            stats = []
            for m in METRICS:
                v = np.array([r[m] for r in rs])
                stats += [round(v.mean(), 4), round(v.std(), 4)]
            w.writerow([model, style, len(rs)] + stats)
            if style == "ALL":
                print(f"{model:<10} n={len(rs):<3} " + "  ".join(f"{m}={stats[2 * i]}" for i, m in enumerate(METRICS)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path("datasets"))
    ap.add_argument("--gen-root", type=Path, default=Path("outputs"))
    ap.add_argument("--models", nargs="+", default=["sdxl", "kandinsky", "flux"])
    ap.add_argument("--prompts", type=Path, required=True)
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    prompts = json.loads(args.prompts.read_text(encoding="utf-8"))
    scorer = Scorer(args.device)
    args.results.mkdir(parents=True, exist_ok=True)

    rows = []
    for model in args.models:
        for style, img, mask in find_pairs(args.root):
            out = args.gen_root / model / style / f"{img.stem}.png"
            if not out.exists():
                print(f"MISSING {out}")
                continue
            prompt = prompts.get(f"{style}/{img.stem}", prompts.get(style, style))
            row = {"model": model, "style": style, "stem": img.stem, **scorer.score(img, mask, out, prompt)}
            rows.append(row)
            print(f"{model}/{style}/{img.stem}: " + "  ".join(f"{m}={row[m]}" for m in METRICS))

    with open(args.results / "metrics.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    if rows:
        print()
        write_summary(rows, args.results / "summary.csv")


if __name__ == "__main__":
    main()
