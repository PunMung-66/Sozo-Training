#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"

JOB_REFERENCE="Server job"
if [[ -n "$JOB_ID" ]]; then
    JOB_REFERENCE="Slurm job $JOB_ID"
fi
JOB_MESSAGE="มาร์คเสียใจด้วยครับ งานนี้มีปัญหานิดหน่อยครับ มาร์คทำเท่าที่ทำได้แล้วครับ 😢"

send_embed "🚨 $JOB_REFERENCE needs attention: $JOB_STATE" "E74C3C" \
    "$JOB_MESSAGE
$(job_summary "EXIT CODE: $JOB_EXITCODE")"
