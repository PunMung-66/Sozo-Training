#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"

JOB_COLOR="2ECC71"
if [[ "$JOB_STATE" != "COMPLETED" ]]; then
    JOB_COLOR="E74C3C"
fi

JOB_MESSAGE="มาร์คขอแจ้งให้ทราบครับ มาร์คทำงานเสร็จแล้วครับ มาร์คขอไปเล่นเกมต่อนะครับ 😎 🎮"

send_embed "⏹️ Job ended: $JOB_STATE" "$JOB_COLOR" \
    "$JOB_MESSAGE
$(job_summary "TIME: $(date '+%F %T')" "TIME USED: $JOB_ELAPSED" "EXIT CODE: $JOB_EXITCODE")" "everyone"
