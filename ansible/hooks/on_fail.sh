#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"

JOB_REFERENCE="Shell job"
if [[ -n "$JOB_ID" ]]; then
    JOB_REFERENCE="Slurm job $JOB_ID"
fi

send "🚨 **$JOB_REFERENCE needs attention: $JOB_STATE**
Host: $JOB_HOST
Working directory: $JOB_WORKDIR
Exit code: $JOB_EXITCODE"
