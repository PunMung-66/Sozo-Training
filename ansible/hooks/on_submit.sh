#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"

send "🚀 **Slurm job submitted**
Job ID: $JOB_ID
Script: $JOB_FILE
Host: $JOB_HOST
Working directory: $JOB_WORKDIR
State: $JOB_STATE"
