#!/usr/bin/env bash
set -euo pipefail
CODE="${1:-}"
NODE_ID="DY-CN-SHANGHAI-001"
ENROLL_URL="https://slsxzbevdoctwnncywwh.supabase.co/functions/v1/bridge-credential-enroll-once"
ENV_FILE="/opt/dayong-voice/dayong-voice.env"
[[ "$(id -u)" -eq 0 ]] || { echo 'BRIDGE_ROTATE_BLOCKED root_required' >&2; exit 20; }
[[ ${#CODE} -ge 20 ]] || { echo 'BRIDGE_ROTATE_BLOCKED enrollment_code_required' >&2; exit 21; }
PY=""
for p in /opt/python311/bin/python3.11 /opt/dayong-cabinet/venv/bin/python /usr/bin/python3; do
  if [[ -x "$p" ]]; then PY="$p"; break; fi
done
[[ -n "$PY" ]] || { echo 'BRIDGE_ROTATE_BLOCKED python_not_found' >&2; exit 22; }
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
curl -fsS --connect-timeout 15 --max-time 60 -H 'content-type: application/json' \
  -d "{\"code\":\"$CODE\",\"node_id\":\"$NODE_ID\"}" "$ENROLL_URL" > "$TMP"
TOKEN="$($PY - "$TMP" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]))
t=j.get('bridge_token','')
if not j.get('ok') or len(t)<32:
    raise SystemExit(2)
print(t)
PY
)"
[[ -n "$TOKEN" ]] || { echo 'BRIDGE_ROTATE_BLOCKED token_empty' >&2; exit 23; }
install -d -m 0755 "$(dirname "$ENV_FILE")"
if [[ -f "$ENV_FILE" ]]; then cp -a "$ENV_FILE" "$ENV_FILE.lkg"; fi
"$PY" - "$ENV_FILE" "$TOKEN" <<'PY'
import sys
p,t=sys.argv[1:]
try: lines=open(p).read().splitlines()
except FileNotFoundError: lines=[]
out=[]; done=False
for line in lines:
    if line.startswith('DAYONG_BRIDGE_TOKEN='):
        if not done:
            out.append('DAYONG_BRIDGE_TOKEN='+t); done=True
    else:
        out.append(line)
if not done: out.append('DAYONG_BRIDGE_TOKEN='+t)
open(p,'w').write('\n'.join(out)+'\n')
PY
GROUP="$(stat -c '%G' "$ENV_FILE" 2>/dev/null || true)"
[[ -n "$GROUP" && "$GROUP" != UNKNOWN ]] || GROUP=admin
chown root:"$GROUP" "$ENV_FILE"
chmod 640 "$ENV_FILE"
unset TOKEN CODE
systemctl daemon-reload
systemctl restart dayong-voice
sleep 2
[[ "$(systemctl is-active dayong-voice)" == active ]] || { echo 'BRIDGE_ROTATE_BLOCKED service_inactive' >&2; exit 24; }
PID="$(systemctl show -p MainPID --value dayong-voice)"
[[ "$PID" =~ ^[0-9]+$ && "$PID" -gt 0 ]] || { echo 'BRIDGE_ROTATE_BLOCKED pid_missing' >&2; exit 25; }
tr '\0' '\n' < "/proc/$PID/environ" | grep -q '^DAYONG_BRIDGE_TOKEN=.' || { echo 'BRIDGE_ROTATE_BLOCKED process_token_missing' >&2; exit 26; }
echo "DAYONG_BRIDGE_CREDENTIAL_ROTATE_PASS service=active process_token=present registry=hash-backed python=$PY mode=$(stat -c '%a' "$ENV_FILE") owner=$(stat -c '%U:%G' "$ENV_FILE")"
