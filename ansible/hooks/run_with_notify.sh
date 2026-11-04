#!/usr/bin/env bash
# Usage: run_with_notify.sh <job_file>
set -uo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
    echo "Usage: $0 <existing job_file>" >&2
    exit 2
fi

JOB_FILE="$(realpath "$1")"
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

export JOB_FILE
export JOB_HOST="$(hostname)"
export JOB_WORKDIR="$(pwd)"
export JOB_ID="" JOB_NODE="" JOB_PARTITION="" JOB_STATE="" JOB_ELAPSED="" JOB_EXITCODE=""

# Run hooks through Bash so executable bits are not required.
hook() {
    local f="$HOOK_DIR/$1"
    [[ -f "$f" ]] && bash "$f" || true
}

if grep -Eq '^[[:space:]]*#SBATCH([[:space:]]|$)' "$JOB_FILE"; then
    JOB_ID="$(sbatch --parsable "$JOB_FILE")" || { JOB_STATE="SUBMIT_FAILED"; hook on_fail.sh; exit 1; }
    JOB_ID="${JOB_ID%%;*}"; export JOB_ID
    printf 'Submitted Slurm job %s\n' "$JOB_ID"
    hook on_submit.sh

    # wait until it starts (or leaves the queue)
    while true; do
        ST="$(squeue -j "$JOB_ID" -h -o %T 2>/dev/null)"
        [[ -z "$ST" || "$ST" == "RUNNING" ]] && break
        sleep 20
    done

    if [[ "$ST" == "RUNNING" ]]; then
        export JOB_NODE="$(squeue -j "$JOB_ID" -h -o %N)"
        export JOB_PARTITION="$(squeue -j "$JOB_ID" -h -o %P)"
        export JOB_STATE="RUNNING"
        hook on_start.sh
    fi

    # wait until it ends
    while [[ -n "$(squeue -j "$JOB_ID" -h 2>/dev/null)" ]]; do sleep 30; done
    sleep 5

    ACCOUNTING="$(sacct -j "$JOB_ID" -X -n -P -o State,Elapsed,ExitCode,NodeList)"
    IFS='|' read -r JOB_STATE JOB_ELAPSED JOB_EXITCODE JOB_NODE <<< "$ACCOUNTING"
    if [[ -z "$JOB_STATE" ]]; then
        JOB_STATE="UNKNOWN"
        JOB_EXITCODE="UNKNOWN"
    fi
    export JOB_STATE JOB_ELAPSED JOB_EXITCODE JOB_NODE

    RC=0
    [[ "$JOB_STATE" == "COMPLETED" && "$JOB_EXITCODE" == "0:0" ]] || RC=1
else
    # plain bash script
    SECONDS=0
    export JOB_STATE="RUNNING"; hook on_start.sh
    bash "$JOB_FILE"; RC=$?
    export JOB_EXITCODE="$RC:0" JOB_ELAPSED="$((SECONDS/60)) min $((SECONDS%60)) s"
    export JOB_STATE="COMPLETED"; [[ $RC -ne 0 ]] && export JOB_STATE="FAILED"
fi

# end hooks
hook on_end.sh
if [[ "$JOB_STATE" == "COMPLETED" ]]; then hook on_success.sh; else hook on_fail.sh; fi
exit "$RC"