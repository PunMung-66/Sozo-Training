#!/usr/bin/env bash
# Run from the project root with: bash slurm/job.sbatch

set -Eeuo pipefail
cd "$(dirname "$0")/.."

# Edit these values
INPUT_IMAGE="scripts/inputs/image.png"
MASK_IMAGE="scripts/inputs/mask.png"
OUTPUT_IMAGE="outputs/inpainted_$(date +%Y%m%d_%H%M%S).png"
PROMPT="a black cat with glowing eyes, highly detailed"
NEGATIVE_PROMPT="bad anatomy, deformed, ugly, blurry"
DEVICE="auto"
STEPS=50

# Use the virtual environment if it exists
[ -f venv/bin/activate ] && source venv/bin/activate

mkdir -p outputs

python scripts/inpaint.py \
    --model kandinsky \
    --image "$INPUT_IMAGE" \
    --mask "$MASK_IMAGE" \
    --prompt "$PROMPT" \
    --negative "$NEGATIVE_PROMPT" \
    --output "$OUTPUT_IMAGE" \
    --device "$DEVICE" \
    --steps "$STEPS"