#!/usr/bin/env bash
# Submit from the project root with: sbatch slurm/job_flux.sbatch
# Accept the FLUX.1 Fill model license and run `hf auth login` on Slurm first.
# The 50G RAM request supports loading this large model with CPU offload.
#SBATCH --job-name=flux-fill
#SBATCH --partition=gpu4090
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=58G
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=Sozo-Training/outputs/flux_fill_%j.out
#SBATCH --error=Sozo-Training/outputs/flux_fill_%j.err

set -Eeuo pipefail

PROJECT_ROOT="$HOME/Sozo-Training"
cd "$PROJECT_ROOT"

INPUT_IMAGE="${INPUT_IMAGE:-slurm/inputs/image.png}"
MASK_IMAGE="${MASK_IMAGE:-slurm/inputs/mask.png}"
OUTPUT_IMAGE="${OUTPUT_IMAGE:-outputs/images/flux_fill_${SLURM_JOB_ID:-$(date +%Y%m%d_%H%M%S)}.png}"
PROMPT="${PROMPT:-a black cat with glowing eyes, highly detailed}"
DEVICE="${DEVICE:-auto}"
STEPS="${STEPS:-50}"
GUIDANCE_SCALE="${GUIDANCE_SCALE:-30.0}"

if [[ -f venv/bin/activate ]]; then
    source venv/bin/activate
else
    echo "Virtual environment not found at $PROJECT_ROOT/venv; run setup first." >&2
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT_IMAGE")"

python scripts/inpaint.py \
    --model flux-fill \
    --image "$INPUT_IMAGE" \
    --mask "$MASK_IMAGE" \
    --prompt "$PROMPT" \
    --output "$OUTPUT_IMAGE" \
    --device "$DEVICE" \
    --steps "$STEPS" \
    --guidance-scale "$GUIDANCE_SCALE"
