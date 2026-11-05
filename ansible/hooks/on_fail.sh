#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"

JOB_REFERENCE="Server job"
if [[ -n "$JOB_ID" ]]; then
    JOB_REFERENCE="Slurm job $JOB_ID"
fi

send_embed "🚨 $JOB_REFERENCE needs attention: $JOB_STATE" "E74C3C" \
    "$(job_box "Exit code: $JOB_EXITCODE")"
