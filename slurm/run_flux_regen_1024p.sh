#!/usr/bin/env bash
# Regeneration test: edit the Partial outputs from round 1 (Criteria2, Table 3).
# Run with: bash slurm/run_flux_regen_1024p.sh
set -Eeuo pipefail

PROJECT_ROOT="$HOME/Sozo-Training"
cd "$PROJECT_ROOT"

MODEL="flux"
MANIFEST="slurm/inputs/manifest_regen_1024p.json"
SBATCH_FILE="slurm/job_flux.sbatch"
OUTPUT_DIR="outputs/images/regen/flux_1024p"

[[ -f "$MANIFEST" ]]    || { echo "Manifest not found: $MANIFEST" >&2; exit 1; }
[[ -f "$SBATCH_FILE" ]] || { echo "Sbatch file not found: $SBATCH_FILE" >&2; exit 1; }

mkdir -p "$OUTPUT_DIR" outputs/logs

# One tab-separated line per entry: id, level, seed, image, mask, prompt
ENTRIES="$(python3 - "$MANIFEST" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    for job in json.load(f):
        print("\t".join([
            str(job["id"]), job["level"], str(job["seed"]),
            job["image"], job["mask"], job["prompt"],
        ]))
PY
)"

while IFS=$'\t' read -r ID LEVEL SEED IMAGE MASK PROMPT; do
    OUTPUT_IMAGE="$OUTPUT_DIR/${ID}_${LEVEL}.png"
    echo "Submitting $MODEL regen job $ID ($LEVEL, seed $SEED) -> $OUTPUT_IMAGE"

    INPUT_IMAGE="$IMAGE" MASK_IMAGE="$MASK" OUTPUT_IMAGE="$OUTPUT_IMAGE" PROMPT="$PROMPT" SEED="$SEED" \
        bash ansible/hooks/run_with_notify.sh "$SBATCH_FILE" \
            --chdir="$HOME" --job-name="${MODEL}-regen-$ID" --export=ALL
done <<< "$ENTRIES"
