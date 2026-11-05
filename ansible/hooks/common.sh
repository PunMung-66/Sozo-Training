WEBHOOK_FILE="$HOME/.secrets/discord_webhook"

job_summary() {
    printf '```text\n'
    printf 'TRACKING ID: %s\n' "${JOB_TRACKING_ID:-unknown}"
    if [[ -n "${JOB_ID:-}" ]]; then
        printf 'JOB ID: %s\n' "$JOB_ID"
    fi
    printf '\nJOB FILE: %s\n\n' "${JOB_FILE:-unknown}"
    printf 'WORKING DIRECTORY: %s\n\n' "${JOB_WORKDIR:-unknown}"
    printf 'STATE: %s\n' "${JOB_STATE:-unknown}"
    printf 'HOST: %s\n' "${JOB_HOST:-unknown}"
    if [[ -n "${JOB_ID:-}" ]]; then
        printf 'NODE: %s\n' "${JOB_NODE:-unknown}"
        printf 'PARTITION: %s\n' "${JOB_PARTITION:-unknown}"
    fi
    for detail in "$@"; do
        printf '%s\n' "$detail"
    done
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