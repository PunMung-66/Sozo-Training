WEBHOOK_FILE="$HOME/.secrets/discord_webhook"

job_box() {
    printf '```text\n'
    printf '┌──────────────────────────────────────────────────┐\n'
    printf '│ Tracking ID: %s │\n' "${JOB_TRACKING_ID:-unknown}"
    if [[ -n "${JOB_ID:-}" ]]; then
        printf '│ Job ID: %s │\n' "$JOB_ID"
    fi
    printf '│ Job File: %s │\n' "${JOB_FILE:-unknown}"
    printf '│ Job Working Directory: %s │\n' "${JOB_WORKDIR:-unknown}"
    printf '│ State: %s │\n' "${JOB_STATE:-unknown}"
    printf '│ Host: %s │\n' "${JOB_HOST:-unknown}"
    if [[ -n "${JOB_ID:-}" ]]; then
        printf '│ Node: %s │\n' "${JOB_NODE:-unknown}"
        printf '│ Partition: %s │\n' "${JOB_PARTITION:-unknown}"
    fi
    for detail in "$@"; do
        printf '│ %s │\n' "$detail"
    done
    printf '└──────────────────────────────────────────────────┘\n'
    printf '```'
}

send() {
    [[ -f "$WEBHOOK_FILE" ]] || return 0
    curl -s -m 15 -F "content=$1" "$(<"$WEBHOOK_FILE")" > /dev/null || true
}

send_embed() {
    local title="$1"
    local color="$2"
    local description="$3"
    local payload

    [[ -f "$WEBHOOK_FILE" ]] || return 0
    payload="$(python3 -c '
import json
import sys

print(json.dumps({
    "embeds": [{
        "title": sys.argv[1],
        "description": sys.argv[3],
        "color": int(sys.argv[2], 16),
    }]
}))
' "$title" "$color" "$description")" || {
        echo "Failed to encode Discord notification payload" >&2
        return 1
    }

    curl -s -m 15 -H "Content-Type: application/json" \
        --data-binary "$payload" "$(<"$WEBHOOK_FILE")" > /dev/null || true
}