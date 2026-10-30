#!/bin/bash
#SBATCH --job-name=inpaint
#SBATCH --partition=gpul40        # 48GB VRAM, good for FLUX. Use gpu4090 for sdxl/kandinsky
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G                 # FLUX needs a lot of CPU RAM for offloading
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

source ~/project/Sozo-Training/venv/bin/activate
cd ~/project/Sozo-Training/script || exit 1
mkdir -p logs outputs

export HF_HUB_OFFLINE=1           # use only the cached models
nvidia-smi

MODEL=${MODEL:-flux}              # flux | sdxl | kandinsky

python inpaint.py \
    --model "$MODEL" \
    --image  inputs/image.png \
    --mask   inputs/mask.png \
    --prompt "a black cat with glowing eyes, highly detailed" \
    --negative "bad anatomy, deformed, ugly, blurry" \
    --output outputs/${MODEL}_${SLURM_JOB_ID}.png