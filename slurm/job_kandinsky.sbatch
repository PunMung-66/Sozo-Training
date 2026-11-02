#!/usr/bin/env bash
#SBATCH --job-name=inpaint
#SBATCH --partition=gpu4090 
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=slurm/outputs/logs/%x_%j.out
#SBATCH --error=slurm/outputs/logs/%x_%j.err

set -Eeuo pipefail

PROJECT_ROOT="$HOME/Sozo-Training"
cd "$PROJECT_ROOT"

INPUT_IMAGE="${INPUT_IMAGE:-slurm/inputs/image.png}"
MASK_IMAGE="${MASK_IMAGE:-slurm/inputs/mask.png}"
OUTPUT_IMAGE="${OUTPUT_IMAGE:-slurm/outputs/images/inpainted_kandinsky_${SLURM_JOB_ID:-$(date +%Y%m%d_%H%M%S)}.png}"
PROMPT="${PROMPT:-a black cat with glowing eyes, highly detailed}"
NEGATIVE_PROMPT="${NEGATIVE_PROMPT:-bad anatomy, deformed, ugly, blurry}"
DEVICE="${DEVICE:-auto}"
STEPS="${STEPS:-50}"

if [[ -f venv/bin/activate ]]; then
    source venv/bin/activate
else
    echo "Virtual environment not found at $PROJECT_ROOT/venv; run setup first." >&2
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT_IMAGE")"

python scripts/inpaint.py \
    --model kandinsky \
    --image "$INPUT_IMAGE" \
    --mask "$MASK_IMAGE" \
    --prompt "$PROMPT" \
    --negative "$NEGATIVE_PROMPT" \
    --output "$OUTPUT_IMAGE" \
    --device "$DEVICE" \
    --steps "$STEPS"
