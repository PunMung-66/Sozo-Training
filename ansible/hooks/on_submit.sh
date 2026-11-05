#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"

if [[ -n "$JOB_ID" ]]; then
    JOB_TITLE="Slurm job submitted"
else
    JOB_TITLE="Server job started"
fi

send_embed "🚀 $JOB_TITLE" "3498DB" "$(job_summary)"
