#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"

JOB_DETAILS="Host: $JOB_HOST
Working directory: $JOB_WORKDIR"
if [[ -n "$JOB_ID" ]]; then
    JOB_DETAILS="Slurm job ID: $JOB_ID
$JOB_DETAILS
Node: ${JOB_NODE:-unknown}
Partition: ${JOB_PARTITION:-unknown}"
fi

send "⏹️ **Job ended: $JOB_STATE**
Time: $(date '+%F %T')
$JOB_DETAILS
Time used: $JOB_ELAPSED
Exit code: $JOB_EXITCODE"
