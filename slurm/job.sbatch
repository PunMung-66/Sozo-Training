#!/usr/bin/env bash
# Local Linux launcher. Run with: bash slurm/job.sbatch
# Edit the defaults below or override them with environment variables.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Generation inputs: edit these defaults or set the matching environment variable.
INPUT_IMAGE="${INPUT_IMAGE:-scripts/inputs/image.png}"
MASK_IMAGE="${MASK_IMAGE:-scripts/inputs/mask.png}"
OUTPUT_IMAGE="${OUTPUT_IMAGE:-outputs/inpainted_$(date +%Y%m%d_%H%M%S).png}"
PROMPT="${PROMPT:-a black cat with glowing eyes, highly detailed}"
NEGATIVE_PROMPT="${NEGATIVE_PROMPT:-bad anatomy, deformed, ugly, blurry}"
DEVICE="${DEVICE:-auto}"
STEPS="${STEPS:-50}"
SEED="${SEED:-}"

VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
else
    echo "No virtual environment at $VENV_DIR; using the current Python environment."
fi

PYTHON="${PYTHON:-python}"

mkdir -p "$(dirname "$OUTPUT_IMAGE")"

args=(
    "$PROJECT_ROOT/scripts/inpaint.py"
    --model kandinsky
    --image "$INPUT_IMAGE"
    --mask "$MASK_IMAGE"
    --prompt "$PROMPT"
    --output "$OUTPUT_IMAGE"
    --device "$DEVICE"
    --steps "$STEPS"
)
if [[ -n "$NEGATIVE_PROMPT" ]]; then
    args+=(--negative "$NEGATIVE_PROMPT")
fi
if [[ -n "${SEED:-}" ]]; then
    args+=(--seed "$SEED")
fi

echo "Starting Kandinsky inpainting on device: $DEVICE"
exec "$PYTHON" "${args[@]}"
