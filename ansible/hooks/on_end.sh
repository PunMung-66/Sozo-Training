#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
send "⏹️ **Job ended: $JOB_STATE**
Time: $(date '+%F %T')
Job ID: $JOB_ID
Node: $JOB_NODE
Time used: $JOB_ELAPSED
Exit code: $JOB_EXITCODE"