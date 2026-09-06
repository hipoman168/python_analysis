#!/usr/bin/env bash
set -euo pipefail
CODE="${1:-}"
NODE_ID="DY-CN-SHANGHAI-001"
BASE_URL="https://cdn.jsdelivr.net/gh/hipoman168/python_analysis@8adf928d0f85054f43c228c25e1b8e111e974eb1/blacklight_factory/bootstrap/shanghai_linux_safe_executor_v2.sh"
ENROLL_URL="https://slsxzbevdoctwnncywwh.supabase.co/functions/v1/worker-enroll-once"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
[[ "$(id -u)" -eq 0 ]] || { echo 'REENROLL_BLOCKED root_required' >&2; exit 20; }
[[ ${#CODE} -ge 20 ]] || { echo 'REENROLL_BLOCKED enrollment_code_required' >&2; exit 21; }
curl -fsSL --connect-timeout 15 --max-time 90 "$BASE_URL" -o "$TMP"
set +e
bash "$TMP"
RC=$?
set -e
if [[ "$RC" -eq 0 ]]; then exit 0; fi
[[ "$RC" -eq 21 ]] || exit "$RC"
RESP="$(curl -fsS --connect-timeout 15 --max-time 60 -H 'content-type: application/json' -d "{\"code\":\"$CODE\",\"node_id\":\"$NODE_ID\"}" "$ENROLL_URL")"
export RESP
TOKEN="$(python3 - <<'PY'
import json,os
x=json.loads(os.environ['RESP'])
t=x.get('worker_token','')
if not x.get('ok') or len(t)<32: raise SystemExit(1)
print(t)
PY
)"
unset RESP
install -d -m 0755 /opt/dayong-command-seat/linux-runner
umask 077
printf 'DAYONG_NODE_ID=%s\nDAYONG_WORKER_TOKEN=%s\n' "$NODE_ID" "$TOKEN" > /opt/dayong-command-seat/linux-runner/runtime.env
unset TOKEN CODE
echo WORKER_REENROLLMENT_CREDENTIAL_MOUNTED
bash "$TMP"
