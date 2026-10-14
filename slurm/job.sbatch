#!/bin/bash
#SBATCH --job-name=example-job
#SBATCH --partition=cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=job_%j.out
#SBATCH --error=job_%j.err

echo "Job started on $(hostname)"
echo "Running as user: $(whoami)"