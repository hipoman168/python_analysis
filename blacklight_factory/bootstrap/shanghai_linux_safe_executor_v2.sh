#!/usr/bin/env bash
set -euo pipefail

NODE_ID="DY-CN-SHANGHAI-001"
DST="/opt/dayong-command-seat/linux-runner"
SERVICE="dayong-linux-safe-executor"
BACKUP_ROOT="/opt/dayong-command-seat/backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$BACKUP_ROOT/linux-runner-$STAMP"

[[ "$(id -u)" -eq 0 ]] || { echo 'BOOTSTRAP_BLOCKED root_required' >&2; exit 20; }
install -d -m 0755 "$DST" "$BACKUP_ROOT"

if [[ -f "$DST/runner.py" || -f "$DST/runtime.env" ]]; then
  install -d -m 0700 "$BACKUP_DIR"
  cp -a "$DST/." "$BACKUP_DIR/" 2>/dev/null || true
fi

cat > "$DST/runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib
import json
import os
import time
import urllib.request
from voice_gateway import execute_voice_gateway_action
AGENT_ID=os.getenv('DAYONG_AGENT_ID','CEO-002')
NODE_ID=os.getenv('DAYONG_NODE_ID','DY-CN-SHANGHAI-001')
GATEWAY=os.getenv('DAYONG_TOOL_GATEWAY_URL','https://slsxzbevdoctwnncywwh.supabase.co/functions/v1/command-seat-tool-gateway')
KEY=os.getenv('DAYONG_MCP_API_KEY','')
POLL_SECONDS=max(2,int(os.getenv('DAYONG_TOOL_POLL_SECONDS','5')))
EXECUTOR_VERSION='DAYONG_LINUX_SAFE_EXECUTOR_V2'
def post(body):
    req=urllib.request.Request(GATEWAY,data=json.dumps(body,ensure_ascii=False).encode(),headers={'content-type':'application/json','x-dayong-mcp-key':KEY},method='POST')
    return json.loads(urllib.request.urlopen(req,timeout=90).read().decode())
def api(action,**kwargs): return post({'action':action,'agent_id':AGENT_ID,**kwargs})
def execute(request):
    tool=str(request.get('tool_name','')).upper(); action=str(request.get('action_name','')).upper(); args=request.get('arguments') or {}
    if tool!='LOCAL_LINUX_SAFE': raise ValueError('TOOL_NOT_IMPLEMENTED_BY_LINUX_EXECUTOR')
    return execute_voice_gateway_action(action,args)
def once():
    q=api('claim_tool_execution',node_id=NODE_ID)
    if not q.get('claimed'): return False
    request_id=q['request_id']; api('start_tool_execution',request_id=request_id)
    evidence={'agent_id':AGENT_ID,'node_id':NODE_ID,'executor':EXECUTOR_VERSION,'tool_name':q.get('tool_name'),'action_name':q.get('action_name')}
    try:
        ok,detail=execute(q); evidence['detail']=detail
        digest=hashlib.sha256(json.dumps(evidence,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        api('complete_tool_execution',request_id=request_id,ok=bool(ok),result_ref=f'inline://sha256/{digest}',evidence=evidence,error=None if ok else 'HANDLER_RETURNED_NONZERO')
    except Exception as exc:
        evidence['error_type']=type(exc).__name__
        api('complete_tool_execution',request_id=request_id,ok=False,result_ref=None,evidence=evidence,error=str(exc)[:1000])
    return True
def main():
    if not KEY: raise RuntimeError('DAYONG_MCP_API_KEY is required')
    while True:
        try: once()
        except Exception as exc: print(f'linux-safe-executor error: {exc}',flush=True)
        time.sleep(POLL_SECONDS)
if __name__=='__main__': main()
PY
chmod 0755 "$DST/runner.py"

cat > "$DST/voice_gateway.py" <<'PY'
#!/usr/bin/env python3
import json, pathlib, subprocess, urllib.request, ssl
SERVICE='dayong-voice'
ENV_FILE=pathlib.Path('/opt/dayong-voice/dayong-voice.env')
DROPIN_DIR=pathlib.Path('/etc/systemd/system/dayong-voice.service.d')
RUNTIME_DROPIN=DROPIN_DIR/'runtime-env.conf'
PYTHON='/opt/dayong-cabinet/venv/bin/python'
SERVER='/opt/dayong-voice/server.py'
HEALTH_URL='https://139.196.108.23/voice-test/api/health'
INWORLD_URL='https://139.196.108.23/voice-test/api/inworld'
def run(argv,timeout=60):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout,shell=False)
    return p.returncode==0,{'argv':argv,'returncode':p.returncode,'stdout':(p.stdout or '')[-8000:],'stderr':(p.stderr or '')[-8000:]}
def env_token_present_in_file():
    if not ENV_FILE.is_file(): return False
    return any(line.startswith('DAYONG_BRIDGE_TOKEN=') and len(line.split('=',1)[1])>0 for line in ENV_FILE.read_text(errors='replace').splitlines())
def repair_env():
    if not env_token_present_in_file(): return False,{'reason':'BRIDGE_TOKEN_NOT_PRESENT_IN_ENV_FILE'}
    DROPIN_DIR.mkdir(parents=True,exist_ok=True)
    content='[Service]\nExecStart=\n'+f"ExecStart=/bin/bash -lc 'set -a; . {ENV_FILE}; set +a; exec {PYTHON} {SERVER}'\n"
    if not RUNTIME_DROPIN.exists() or RUNTIME_DROPIN.read_text()!=content: RUNTIME_DROPIN.write_text(content)
    ok1,e1=run(['systemctl','daemon-reload']); ok2,e2=run(['systemctl','restart',SERVICE]) if ok1 else (False,{}); ok3,e3=run(['systemctl','is-active',SERVICE]) if ok2 else (False,{})
    return ok1 and ok2 and ok3 and e3.get('stdout','').strip()=='active',{'daemon_reload':e1,'restart':e2,'active':e3,'token_file_present':True,'secret_redacted':True}
def status():
    ok,d=run(['systemctl','is-active',SERVICE]); return ok and d.get('stdout','').strip()=='active',d
def logs():
    ok,d=run(['journalctl','-u',SERVICE,'-n','80','--no-pager'],60)
    for key in ('stdout','stderr'):
        s=d.get(key,'')
        for marker in ('DAYONG_BRIDGE_TOKEN=','x-dayong-bridge-token'): s=s.replace(marker,'[REDACTED_MARKER]=')
        d[key]=s
    return ok,d
def http_json(url,method='GET',body=None,timeout=60):
    data=None if body is None else json.dumps(body,ensure_ascii=False).encode()
    req=urllib.request.Request(url,data=data,headers={'content-type':'application/json','user-agent':'DAYONG-Linux-Safe-Executor/2'},method=method)
    with urllib.request.urlopen(req,timeout=timeout,context=ssl._create_unverified_context()) as r: return r.status,json.loads(r.read().decode())
def acceptance(mode):
    hs,h=http_json(HEALTH_URL)
    if hs!=200 or not h.get('ok') or not h.get('inworld_queue'): return False,{'health':h,'stage':'HEALTH'}
    body={'text':f'你好，這是大用科技上海伺服器 {mode.capitalize()} 語音自動驗收測試。','agent':'D1','mode':mode,'session_id':f'linux-runner-{mode}-acceptance'}
    try: sc,res=http_json(INWORLD_URL,'POST',body,60)
    except Exception as exc: return False,{'health':h,'stage':mode.upper(),'error':str(exc)[:1000]}
    return sc==200 and bool(res),{'health':h,'stage':mode.upper(),'response':res,'http_status':sc}
def execute_voice_gateway_action(action,args):
    del args
    if action=='VOICE_GATEWAY_ENV_REPAIR': return repair_env()
    if action=='VOICE_GATEWAY_RESTART':
        ok,d=run(['systemctl','restart',SERVICE]); return (False,d) if not ok else status()
    if action=='VOICE_GATEWAY_STATUS': return status()
    if action=='VOICE_GATEWAY_LOG_READ': return logs()
    if action=='VOICE_GATEWAY_STANDARD_ACCEPTANCE': return acceptance('standard')
    if action=='VOICE_GATEWAY_REALTIME_ACCEPTANCE': return acceptance('realtime')
    raise ValueError('LINUX_ACTION_NOT_ALLOWLISTED')
PY
chmod 0644 "$DST/voice_gateway.py"

cat > "/etc/systemd/system/${SERVICE}.service" <<'UNIT'
[Unit]
Description=DAYONG Linux Safe Executor v2
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/opt/dayong-command-seat/linux-runner
EnvironmentFile=-/opt/dayong-command-seat/linux-runner/runtime.env
ExecStart=/usr/bin/python3 /opt/dayong-command-seat/linux-runner/runner.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=/etc/systemd/system/dayong-voice.service.d /opt/dayong-voice
[Install]
WantedBy=multi-user.target
UNIT

RUNTIME_ENV="$DST/runtime.env"
TMP_ENV="$(mktemp)"
chmod 0600 "$TMP_ENV"
printf 'DAYONG_NODE_ID=%s\n' "$NODE_ID" > "$TMP_ENV"
extract_key_from_file(){
  local f="$1" line value
  [[ -r "$f" ]] || return 1
  line="$(grep -m1 -E '^[[:space:]]*(export[[:space:]]+)?DAYONG_MCP_API_KEY=' "$f" 2>/dev/null || true)"
  [[ -n "$line" ]] || return 1
  value="${line#*=}"; value="${value%$'\r'}"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then value="${value:1:${#value}-2}"; fi
  if [[ "$value" == \'*\' && "$value" == *\' ]]; then value="${value:1:${#value}-2}"; fi
  [[ -n "$value" ]] || return 1
  printf 'DAYONG_MCP_API_KEY=%s\n' "$value" >> "$TMP_ENV"
  return 0
}
KEY_FOUND=0
if [[ -r "$RUNTIME_ENV" ]] && extract_key_from_file "$RUNTIME_ENV"; then KEY_FOUND=1; else
  for candidate in /opt/dayong-cabinet/.env /opt/dayong-cabinet/runtime.env /opt/dayong-cabinet/dayong.env /opt/dayong-command-seat/runtime.env /etc/dayong/runtime.env /etc/dayong/command-seat.env /etc/default/dayong-command-seat /etc/sysconfig/dayong-command-seat; do
    if extract_key_from_file "$candidate"; then KEY_FOUND=1; break; fi
  done
fi
if [[ "$KEY_FOUND" -ne 1 ]]; then rm -f "$TMP_ENV"; echo 'BOOTSTRAP_BLOCKED credential_mount_missing' >&2; exit 21; fi
install -m 0600 "$TMP_ENV" "$RUNTIME_ENV"; rm -f "$TMP_ENV"

python3 -m py_compile "$DST/runner.py" "$DST/voice_gateway.py"
rollback(){
  systemctl stop "$SERVICE" >/dev/null 2>&1 || true
  if [[ -d "$BACKUP_DIR" ]]; then rm -rf "$DST"; install -d -m 0755 "$DST"; cp -a "$BACKUP_DIR/." "$DST/"; fi
  systemctl daemon-reload >/dev/null 2>&1 || true
}
trap 'rollback' ERR
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null
systemctl restart "$SERVICE"
sleep 3
systemctl is-active --quiet "$SERVICE"
PID="$(systemctl show -p MainPID --value "$SERVICE")"
[[ "$PID" =~ ^[0-9]+$ && "$PID" -gt 0 ]]
tr '\0' '\n' < "/proc/$PID/environ" | grep -q '^DAYONG_MCP_API_KEY=.'
RUNNER_SHA="$(sha256sum "$DST/runner.py" | awk '{print $1}')"
VOICE_SHA="$(sha256sum "$DST/voice_gateway.py" | awk '{print $1}')"
trap - ERR
printf 'DAYONG_SHANGHAI_BOOTSTRAP_PASS node=%s runner_sha=%s voice_sha=%s credential=present service=active\n' "$NODE_ID" "$RUNNER_SHA" "$VOICE_SHA"
