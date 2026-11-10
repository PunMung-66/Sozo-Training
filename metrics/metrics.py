"""Inpainting comparison metrics: SSIM / LPIPS (unmasked area), CLIP score (mask crop / full image).

How to run (from Sozo-Training/):
    pip install torch transformers lpips scikit-image numpy pillow
    python metrics/metrics.py                                   # all slurm/inputs/manifest_*.json, all models
    python metrics/metrics.py --manifests slurm/inputs/manifest_1024p.json --models flux

Files:
    slurm/inputs/manifest_<res>.json   [{"id", "level", "prompt", "image", "mask"}, ...]
                                       image/mask paths relative to --base (default: current dir); mask white = inpaint
    outputs/images/<model>_<res>/<id>_<level>.png
                                       generated image, written by slurm/run_<model>_<res>.sh
                                       (change with --gen-root / --gen-pattern; placeholders {model} {res} {id} {level})
    -> metrics/results/metrics.jsonl (per test case), metrics/results/summary.csv (mean/std per model x res, overall and per level)
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

CLIP_REPO = "openai/clip-vit-large-patch14"
METRICS = ["ssim_unmasked", "lpips_unmasked", "clip_crop", "clip_full"]


def load_manifest(path):
    """(res, cases) from manifest_<res>.json; res comes from the file name (manifest_1024p.json -> 1024p)."""
    res = path.stem.removeprefix("manifest").lstrip("_") or "default"
    cases = json.loads(path.read_text(encoding="utf-8"))
    for c in cases:
        missing = {"id", "prompt", "image", "mask"} - c.keys()
        if missing:
            raise ValueError(f"{path}: entry {c.get('id')} is missing {sorted(missing)}")
    return res, cases


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
        groups[(r["model"], r["res"], "ALL")].append(r)
        groups[(r["model"], r["res"], r["level"])].append(r)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "res", "level", "n"] + [f"{m}_{s}" for m in METRICS for s in ("mean", "std")])
        for (model, res, level), rs in sorted(groups.items()):
            stats = []
            for m in METRICS:
                v = np.array([r[m] for r in rs])
                stats += [round(v.mean(), 4), round(v.std(), 4)]
            w.writerow([model, res, level, len(rs)] + stats)
            if level == "ALL":
                print(f"{model:<10} {res:<6} n={len(rs):<3} "
                      + "  ".join(f"{m}={stats[2 * i]}" for i, m in enumerate(METRICS)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifests", type=Path, nargs="+",
                    default=sorted(Path("slurm/inputs").glob("manifest_*.json")))
    ap.add_argument("--base", type=Path, default=Path("."), help="directory the manifest image/mask paths are relative to")
    ap.add_argument("--gen-root", type=Path, default=Path("slurm/outputs/images"))
    ap.add_argument("--gen-pattern", default="{model}_{res}/{id}_{level}.png",
                    help="generated image path under --gen-root")
    ap.add_argument("--models", nargs="+", default=["sdxl", "kandinsky", "flux"])
    ap.add_argument("--results", type=Path, default=Path("metrics/results"))
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    if not args.manifests:
        ap.error("no manifest found (looked for slurm/inputs/manifest_*.json); pass --manifests")
    manifests = [load_manifest(p) for p in args.manifests]
    scorer = Scorer(args.device)
    args.results.mkdir(parents=True, exist_ok=True)

    rows = []
    for model in args.models:
        for res, cases in manifests:
            for c in cases:
                level = c.get("level", "-")
                out = args.gen_root / args.gen_pattern.format(model=model, res=res, id=c["id"], level=level)
                img, mask = args.base / c["image"], args.base / c["mask"]
                missing = [str(p) for p in (out, img, mask) if not p.exists()]
                if missing:
                    print(f"SKIP {model}/{res}/{c['id']}: missing {', '.join(missing)}")
                    continue
                row = {"model": model, "res": res, "id": c["id"], "level": level, "image": c["image"],
                       **scorer.score(img, mask, out, c["prompt"])}
                rows.append(row)
                print(f"{model}/{res}/{c['id']} ({level}): " + "  ".join(f"{m}={row[m]}" for m in METRICS))

    with open(args.results / "metrics.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    if rows:
        print()
        write_summary(rows, args.results / "summary.csv")


if __name__ == "__main__":
    main()
