#!/usr/bin/env bash
# Usage: run_with_notify.sh <job_file> [sbatch options...]
set -uo pipefail

if [[ $# -lt 1 || ! -f "$1" ]]; then
    echo "Usage: $0 <existing job_file> [sbatch options...]" >&2
    exit 2
fi

JOB_FILE_ARG="$1"
shift
JOB_FILE="$(realpath "$JOB_FILE_ARG")"
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

export JOB_FILE
export JOB_HOST="$(hostname)"
export JOB_WORKDIR="$(pwd)"
JOB_TRACKING_ID="$(printf '%s' "$(date -u +%s%N)-$$" | sha256sum | cut -c1-16)"
export JOB_TRACKING_ID
export JOB_ID="" JOB_NODE="" JOB_PARTITION="" JOB_STATE="" JOB_ELAPSED="" JOB_EXITCODE=""

# Run hooks through Bash so executable bits are not required.
hook() {
    local f="$HOOK_DIR/$1"
    [[ -f "$f" ]] && bash "$f" || true
}

if grep -Eq '^[[:space:]]*#SBATCH([[:space:]]|$)' "$JOB_FILE"; then
    WRAPPER_DIR="${HOME}/.cache/sozo-training/slurm-notify"
    mkdir -p "$WRAPPER_DIR"
    chmod 700 "$WRAPPER_DIR"
    SBATCH_WRAPPER="$(mktemp "$WRAPPER_DIR/job.XXXXXX.sbatch")"

    {
        printf '#!/usr/bin/env bash\n'
        awk '
            /^[[:space:]]*#SBATCH([[:space:]]|$)/ { print; next }
            /^[[:space:]]*$/ || /^[[:space:]]*#/ { next }
            { exit }
        ' "$JOB_FILE"
        printf 'JOB_FILE=%q\nHOOK_DIR=%q\nexport JOB_TRACKING_ID=%q\n' \
            "$JOB_FILE" "$HOOK_DIR" "$JOB_TRACKING_ID"
        cat <<'SBATCH_BODY'
export JOB_ID="${SLURM_JOB_ID:-unknown}"
export JOB_HOST="$(hostname)"
export JOB_WORKDIR="$(pwd)"
export JOB_NODE="${SLURM_JOB_NODELIST:-$JOB_HOST}"
export JOB_PARTITION="${SLURM_JOB_PARTITION:-unknown}"
SECONDS=0

finish_job() {
    local rc=$?
    export JOB_EXITCODE="${rc}:0"
    export JOB_ELAPSED="$((SECONDS / 60)) min $((SECONDS % 60)) s"
    if [[ "$rc" -eq 0 ]]; then
        export JOB_STATE="COMPLETED"
    else
        export JOB_STATE="FAILED"
    fi

    bash "$HOOK_DIR/on_end.sh" || true
    if [[ "$JOB_STATE" == "COMPLETED" ]]; then
        [[ ! -f "$HOOK_DIR/on_success.sh" ]] || bash "$HOOK_DIR/on_success.sh" || true
    else
        bash "$HOOK_DIR/on_fail.sh" || true
    fi
}

trap finish_job EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
bash "$JOB_FILE"
SBATCH_BODY
    } > "$SBATCH_WRAPPER"
    chmod 600 "$SBATCH_WRAPPER"

    if ! SUBMIT_OUTPUT="$(sbatch --parsable "$@" "$SBATCH_WRAPPER")"; then
        JOB_STATE="SUBMIT_FAILED"
        hook on_fail.sh
        rm -f "$SBATCH_WRAPPER"
        exit 1
    fi
    JOB_ID="${SUBMIT_OUTPUT%%;*}"
    rm -f "$SBATCH_WRAPPER"
    [[ -n "$JOB_ID" ]] || { JOB_STATE="SUBMIT_FAILED"; hook on_fail.sh; exit 1; }
    JOB_ID="${JOB_ID%%;*}"; export JOB_ID
    JOB_STATE="SUBMITTED"; export JOB_STATE
    printf 'Submitted Slurm job %s\n' "$JOB_ID"
    hook on_submit.sh
    exit 0
else
    # plain bash script
    SECONDS=0
    export JOB_STATE="RUNNING"
    hook on_submit.sh
    bash "$JOB_FILE"; RC=$?
    export JOB_EXITCODE="$RC:0" JOB_ELAPSED="$((SECONDS/60)) min $((SECONDS%60)) s"
    export JOB_STATE="COMPLETED"; [[ $RC -ne 0 ]] && export JOB_STATE="FAILED"
fi

# end hooks
hook on_end.sh
if [[ "$JOB_STATE" == "COMPLETED" ]]; then hook on_success.sh; else hook on_fail.sh; fi
exit "$RC"