#!/usr/bin/env bash
# Run from the project root with: bash slurm/job.sbatch

set -Eeuo pipefail
cd "$(dirname "$0")/.."

# Edit these values
INPUT_IMAGE="https://us.aws.cdn.hf.co/xet-bridge-us/621ffdd236468d709f1835cf/ad764ab41665ebf583add562e08aa2002b112489cd60dfa17554e141afada78e?response-content-disposition=inline%3B+filename*%3DUTF-8%27%27inpaint.png%3B+filename%3D%22inpaint.png%22%3B&X-Xet-Cas-Uid=65767e47177b3b46638f185f&response-content-type=image%2Fpng&user_id=65767e47177b3b46638f185f&xip=XGs2YXmthqc&Expires=1793462516&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly91cy5hd3MuY2RuLmhmLmNvL3hldC1icmlkZ2UtdXMvNjIxZmZkZDIzNjQ2OGQ3MDlmMTgzNWNmL2FkNzY0YWI0MTY2NWViZjU4M2FkZDU2MmUwOGFhMjAwMmIxMTI0ODljZDYwZGZhMTc1NTRlMTQxYWZhZGE3OGVcXD9yZXNwb25zZS1jb250ZW50LWRpc3Bvc2l0aW9uPWlubGluZSUzQitmaWxlbmFtZSUyQSUzRFVURi04JTI3JTI3aW5wYWludC5wbmclM0IrZmlsZW5hbWUlM0QlMjJpbnBhaW50LnBuZyUyMiUzQiZYLVhldC1DYXMtVWlkPTY1NzY3ZTQ3MTc3YjNiNDY2MzhmMTg1ZiZyZXNwb25zZS1jb250ZW50LXR5cGU9aW1hZ2UlMkZwbmcmdXNlcl9pZD02NTc2N2U0NzE3N2IzYjQ2NjM4ZjE4NWYmeGlwPVhHczJZWG10aHFjIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJFcG9jaFRpbWUiOjE3OTM0NjI1MTZ9fX1dfQ__&Signature=MEYCIQDKAFozToKUxpkjLlHwNQ7g%7E2liTdh-5Zn5CYBAg-4wkAIhAMx-mCW5uGemXJ53AwqC4lZyWGaltqf8GPvaUzBSc3Gj&Key-Pair-Id=01KXEF4KZ1B6FV465MAWR4M21F&Hash-Algorithm=SHA256"
MASK_IMAGE="https://us.aws.cdn.hf.co/xet-bridge-us/621ffdd236468d709f1835cf/d728f5c84973079beb1bc7f96f31245ab81c73c2be7d9fa2b629e49f171a92e9?user_id=65767e47177b3b46638f185f&response-content-disposition=inline%3B+filename*%3DUTF-8%27%27inpaint_mask.png%3B+filename%3D%22inpaint_mask.png%22%3B&X-Xet-Cas-Uid=65767e47177b3b46638f185f&response-content-type=image%2Fpng&xip=XGs2YXmthqc&Expires=1793462531&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly91cy5hd3MuY2RuLmhmLmNvL3hldC1icmlkZ2UtdXMvNjIxZmZkZDIzNjQ2OGQ3MDlmMTgzNWNmL2Q3MjhmNWM4NDk3MzA3OWJlYjFiYzdmOTZmMzEyNDVhYjgxYzczYzJiZTdkOWZhMmI2MjllNDlmMTcxYTkyZTlcXD91c2VyX2lkPTY1NzY3ZTQ3MTc3YjNiNDY2MzhmMTg1ZiZyZXNwb25zZS1jb250ZW50LWRpc3Bvc2l0aW9uPWlubGluZSUzQitmaWxlbmFtZSUyQSUzRFVURi04JTI3JTI3aW5wYWludF9tYXNrLnBuZyUzQitmaWxlbmFtZSUzRCUyMmlucGFpbnRfbWFzay5wbmclMjIlM0ImWC1YZXQtQ2FzLVVpZD02NTc2N2U0NzE3N2IzYjQ2NjM4ZjE4NWYmcmVzcG9uc2UtY29udGVudC10eXBlPWltYWdlJTJGcG5nJnhpcD1YR3MyWVhtdGhxYyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiRXBvY2hUaW1lIjoxNzkzNDYyNTMxfX19XX0_&Signature=MEUCIAlRwT-vj7Qi96ei3I3Vg%7EjL886%7EHPiecHo7BQ8qB0FyAiEAyUtbAkxzxMnyPRqBjIigNvd5rAcp0ZukhmSi27RY1Q4_&Key-Pair-Id=01KXEF4KZ1B6FV465MAWR4M21F&Hash-Algorithm=SHA256"
OUTPUT_IMAGE="outputs/inpainted_$(date +%Y%m%d_%H%M%S).png"
PROMPT="a black cat with glowing eyes, highly detailed"
NEGATIVE_PROMPT="bad anatomy, deformed, ugly, blurry"
DEVICE="auto"
STEPS=50

# Use the virtual environment if it exists
[ -f .venv/bin/activate ] && source .venv/bin/activate

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