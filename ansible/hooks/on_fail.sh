#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
send "🚨 Job $JOB_ID needs attention: $JOB_STATE. Check the .err file in $JOB_WORKDIR"