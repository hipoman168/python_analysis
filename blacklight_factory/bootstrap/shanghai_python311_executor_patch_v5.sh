#!/usr/bin/env bash
set -euo pipefail
SERVICE="dayong-linux-safe-executor"
UNIT="/etc/systemd/system/${SERVICE}.service"
PY311="/opt/dayong-cabinet/venv/bin/python"
RUNNER="/opt/dayong-command-seat/linux-runner/runner.py"
[[ "$(id -u)" -eq 0 ]] || { echo 'PATCH_BLOCKED root_required' >&2; exit 20; }
[[ -x "$PY311" ]] || { echo 'PATCH_BLOCKED python311_missing' >&2; exit 21; }
[[ -f "$RUNNER" ]] || { echo 'PATCH_BLOCKED runner_missing' >&2; exit 22; }
cp -a "$UNIT" "${UNIT}.bak.$(date -u +%Y%m%dT%H%M%SZ)" 2>/dev/null || true
python_ver="$($PY311 -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])')"
sed -i "s#^ExecStart=.*runner.py#ExecStart=${PY311} ${RUNNER}#" "$UNIT"
systemctl daemon-reload
systemctl restart "$SERVICE"
sleep 3
systemctl is-active --quiet "$SERVICE"
PID="$(systemctl show -p MainPID --value "$SERVICE")"
[[ "$PID" =~ ^[0-9]+$ && "$PID" -gt 0 ]]
exe="$(readlink -f "/proc/$PID/exe")"
[[ "$exe" == "$PY311" || "$exe" == "${PY311%/bin/python}/bin/python3.11" || "$exe" == *"python3.11" ]]
printf 'DAYONG_EXECUTOR_PY311_PATCH_PASS python=%s pid=%s exe=%s\n' "$python_ver" "$PID" "$exe"
