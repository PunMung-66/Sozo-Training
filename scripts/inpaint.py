import argparse
import torch
from diffusers import AutoPipelineForInpainting, FluxFillPipeline
from diffusers.utils import load_image

p = argparse.ArgumentParser()
p.add_argument("--model", required=True, choices=["flux", "sdxl", "kandinsky"])
p.add_argument("--image", required=True)
p.add_argument("--mask", required=True)
p.add_argument("--prompt", required=True)
p.add_argument("--negative", default="")
p.add_argument("--output", default="outputs/result.png")
p.add_argument("--seed", type=int, default=92)
args = p.parse_args()

init_image = load_image(args.image).convert("RGB")
mask_image = load_image(args.mask).convert("L")   # white = repaint, black = keep
generator = torch.Generator("cuda").manual_seed(args.seed)

if args.model == "flux":
    pipe = FluxFillPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-Fill-dev", dtype=torch.bfloat16
    )
    pipe.enable_model_cpu_offload()
    result = pipe(
        prompt=args.prompt,
        image=init_image,
        mask_image=mask_image,
        height=init_image.height,
        width=init_image.width,
        guidance_scale=30,
        num_inference_steps=50,
        max_sequence_length=512,
        generator=generator,
    ).images[0]

elif args.model == "sdxl":
    pipe = AutoPipelineForInpainting.from_pretrained(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        dtype=torch.float16, variant="fp16",
    )
    pipe.enable_model_cpu_offload()
    init_image = init_image.resize((1024, 1024))
    mask_image = mask_image.resize((1024, 1024))
    result = pipe(
        prompt=args.prompt,
        negative_prompt=args.negative,
        image=init_image,
        mask_image=mask_image,
        strength=0.99,
        generator=generator,
    ).images[0]

else:  # kandinsky (loads the prior automatically)
    pipe = AutoPipelineForInpainting.from_pretrained(
        "kandinsky-community/kandinsky-2-2-decoder-inpaint", dtype=torch.float16
    )
    pipe.enable_model_cpu_offload()
    result = pipe(
        prompt=args.prompt,
        negative_prompt=args.negative,
        image=init_image,
        mask_image=mask_image,
        generator=generator,
    ).images[0]

result.save(args.output)
print("Saved to", args.output)