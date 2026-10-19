import argparse, gc
from pathlib import Path
import torch
from PIL import Image, ImageOps
from diffusers import AutoPipelineForInpainting, FluxFillPipeline

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}

# EDIT THESE: one prompt per style folder (these are only placeholders)
PROMPTS = {
    "japandi":     "japandi style interior, natural wood, minimal, warm neutral tones, highly detailed, photorealistic",
    "modern":      "modern style interior, clean lines, neutral palette, highly detailed, photorealistic",
    "traditional": "traditional style interior, classic furniture, warm tones, highly detailed, photorealistic",
}
NEGATIVE = "bad anatomy, deformed, ugly, blurry, low quality"

p = argparse.ArgumentParser()
p.add_argument("--model", required=True, choices=["flux", "sdxl", "kandinsky"])
p.add_argument("--root", required=True)      # folder containing japandi/ modern/ traditional/
p.add_argument("--out", required=True)
p.add_argument("--seed", type=int, default=92)
args = p.parse_args()

def find_pairs(root):
    pairs = []
    for d in sorted(x for x in Path(root).iterdir() if x.is_dir()):
        for f in sorted(d.iterdir()):
            if f.suffix.lower() in IMG_EXT and not f.stem.endswith("_mask"):
                masks = [m for m in d.iterdir() if m.stem == f.stem + "_mask"]
                if masks:
                    pairs.append((d.name, f, masks[0]))
                else:
                    print(f"WARNING: no mask for {f}")
    return pairs

def fit(img, mask, long_side, multiple=16):
    """Scale so the long side = long_side, keep aspect ratio, round to a multiple."""
    w, h = img.size
    s = long_side / max(w, h)
    w = max(multiple, int(w * s) // multiple * multiple)
    h = max(multiple, int(h * s) // multiple * multiple)
    img = img.resize((w, h), Image.LANCZOS)
    mask = mask.resize((w, h), Image.NEAREST).point(lambda v: 255 if v > 127 else 0)
    return img, mask

def load_pipe(model):
    if model == "flux":
        pipe = FluxFillPipeline.from_pretrained("black-forest-labs/FLUX.1-Fill-dev", dtype=torch.bfloat16)
    elif model == "sdxl":
        pipe = AutoPipelineForInpainting.from_pretrained(
            "diffusers/stable-diffusion-xl-1.0-inpainting-0.1", dtype=torch.float16, variant="fp16")
    else:
        pipe = AutoPipelineForInpainting.from_pretrained(
            "kandinsky-community/kandinsky-2-2-decoder-inpaint", dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    return pipe

LONG_SIDE = {"flux": 1024, "sdxl": 1024, "kandinsky": 768}
MULTIPLE  = {"flux": 16, "sdxl": 8, "kandinsky": 64}

pairs = find_pairs(args.root)
print(f"Found {len(pairs)} image/mask pairs")
pipe = load_pipe(args.model)

for style, img_path, mask_path in pairs:
    out_path = Path(args.out) / style / f"{img_path.stem}.png"
    if out_path.exists():
        print("skip (exists):", out_path); continue
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        img = ImageOps.exif_transpose(Image.open(img_path)).convert("RGB")
        mask = Image.open(mask_path).convert("L").resize(img.size, Image.NEAREST)  # white = repaint
        img, mask = fit(img, mask, LONG_SIDE[args.model], MULTIPLE[args.model])
        w, h = img.size
        prompt = PROMPTS.get(style, style)
        gen = torch.Generator("cuda").manual_seed(args.seed)

        if args.model == "flux":
            res = pipe(prompt=prompt, image=img, mask_image=mask, height=h, width=w,
                       guidance_scale=30, num_inference_steps=50,
                       max_sequence_length=512, generator=gen).images[0]
        elif args.model == "sdxl":
            res = pipe(prompt=prompt, negative_prompt=NEGATIVE, image=img, mask_image=mask,
                       height=h, width=w, strength=0.99, generator=gen).images[0]
        else:
            res = pipe(prompt=prompt, negative_prompt=NEGATIVE, image=img, mask_image=mask,
                       height=h, width=w, generator=gen).images[0]

        res.save(out_path)
        print("saved:", out_path, flush=True)
    except Exception as e:                      # one bad image won't kill the whole job
        print(f"FAILED {img_path}: {e}", flush=True)
    gc.collect(); torch.cuda.empty_cache()