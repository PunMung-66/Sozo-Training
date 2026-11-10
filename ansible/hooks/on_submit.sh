#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"

if [[ -n "$JOB_ID" ]]; then
    JOB_TITLE="Slurm job submitted"
else
    JOB_TITLE="Server job started"
fi

JOB_MESSAGE="ตอนนี้มาร์คส่งงานให้ทุกคนแล้วนะครับ เดียวมาร์คดูเองครับ 🚀"
JOB_DESCRIPTION=$'\n'"$JOB_MESSAGE"$'\n\n'"$(job_summary)"

send_embed "🚀 $JOB_TITLE" "3498DB" "$JOB_DESCRIPTION"
