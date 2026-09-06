#!/usr/bin/env bash
set -euo pipefail
SERVICE="dayong-voice"
ENV_FILE="/opt/dayong-voice/dayong-voice.env"
DROPIN="/etc/systemd/system/dayong-voice.service.d/runtime-env.conf"
PYTHON="/opt/dayong-cabinet/venv/bin/python"
SERVER="/opt/dayong-voice/server.py"
[[ "$(id -u)" -eq 0 ]] || { echo 'PATCH_BLOCKED root_required' >&2; exit 20; }
[[ -f "$ENV_FILE" ]] || { echo 'PATCH_BLOCKED env_missing' >&2; exit 21; }
USER_NAME="$(systemctl show -p User --value "$SERVICE" || true)"
GROUP_NAME="$(systemctl show -p Group --value "$SERVICE" || true)"
[[ -n "$USER_NAME" ]] || USER_NAME=root
if [[ -z "$GROUP_NAME" ]]; then GROUP_NAME="$(id -gn "$USER_NAME" 2>/dev/null || echo root)"; fi
chown root:"$GROUP_NAME" "$ENV_FILE"
chmod 0640 "$ENV_FILE"
if command -v restorecon >/dev/null 2>&1; then restorecon -F "$ENV_FILE" >/dev/null 2>&1 || true; fi
install -d -m 0755 "$(dirname "$DROPIN")"
cat > "$DROPIN" <<EOF
[Service]
ExecStart=
ExecStart=/bin/bash -lc 'set -a; . $ENV_FILE; set +a; exec $PYTHON $SERVER'
EOF
systemctl daemon-reload
systemctl restart "$SERVICE"
sleep 2
systemctl is-active --quiet "$SERVICE"
PID="$(systemctl show -p MainPID --value "$SERVICE")"
[[ "$PID" =~ ^[0-9]+$ && "$PID" -gt 0 ]]
if ! tr '\0' '\n' < "/proc/$PID/environ" | grep -q '^DAYONG_BRIDGE_TOKEN=.'; then echo 'PATCH_BLOCKED process_token_missing' >&2; exit 22; fi
MODE="$(stat -c '%a' "$ENV_FILE")"
OWNER="$(stat -c '%U:%G' "$ENV_FILE")"
printf 'DAYONG_VOICE_ENV_PERMISSION_PATCH_PASS service=active process_token=present mode=%s owner=%s\n' "$MODE" "$OWNER"
