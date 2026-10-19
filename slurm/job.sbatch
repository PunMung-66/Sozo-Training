#!/bin/bash
#SBATCH --job-name=inpaint
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

source ~/project/Sozo-Training/venv/bin/activate
cd ~/project/Sozo-Training/script || exit 1
mkdir -p logs

export HF_HUB_OFFLINE=1
MODEL=${MODEL:-sdxl}

nvidia-smi
python inpaint_batch.py \
    --model "$MODEL" \
    --root  ~/project/Sozo-Training/script/inputs \
    --out   ~/project/Sozo-Training/script/outputs/$MODEL