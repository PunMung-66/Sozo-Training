WEBHOOK_FILE="$HOME/.secrets/discord_webhook"

send() {
    [[ -f "$WEBHOOK_FILE" ]] || return 0
    curl -s -m 15 -F "content=$1" "$(<"$WEBHOOK_FILE")" > /dev/null || true
}