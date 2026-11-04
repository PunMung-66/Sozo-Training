#!/usr/bin/env bash
#SBATCH --job-name=test-notify
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:02:00
#SBATCH --output=Sozo-Training/outputs/test_notify_%j.out
#SBATCH --error=Sozo-Training/outputs/test_notify_%j.err

echo "Job $SLURM_JOB_ID started on $(hostname) at $(date)"
sleep "${TEST_SLEEP:-10}"

if [[ "${TEST_MODE:-success}" == "fail" ]]; then
    echo "Simulating a failure" >&2
    exit 3
fi

echo "Done at $(date)"
EOF