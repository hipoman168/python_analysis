# Run once on Node-02 with elevated PowerShell; no secrets stored in repository.
$ErrorActionPreference = 'Stop'
$Root = 'C:\DAYONG_AI\agentos'
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Python = (Get-Command py -ErrorAction SilentlyContinue)
if (-not $Python) { throw 'Python launcher py not found' }
if (-not (Test-Path "$Root\venv\Scripts\python.exe")) { & py -3 -m venv "$Root\venv" }
& "$Root\venv\Scripts\python.exe" -m pip install --upgrade httpx
$Worker = Join-Path $Root 'node_worker_v007.py'
if (-not (Test-Path $Worker)) { throw "Missing worker file: $Worker. Copy verified GitHub worker before install." }
$EnvFile = Join-Path $Root 'node_worker.env.ps1'
if (-not (Test-Path $EnvFile)) { throw "Missing local credential file: $EnvFile (CLOUD_GATEWAY_URL, NODE_TOKEN, NODE_ID)." }
$Script = Join-Path $Root 'start_node_worker.ps1'
@'
$ErrorActionPreference = "Stop"
. "C:\DAYONG_AI\agentos\node_worker.env.ps1"
& "C:\DAYONG_AI\agentos\venv\Scripts\python.exe" "C:\DAYONG_AI\agentos\node_worker_v007.py"
'@ | Set-Content -Path $Script -Encoding UTF8
# Run once on startup; for new jobs trigger this task on demand or via approved event-based mechanism.
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "C:\DAYONG_AI\agentos\start_node_worker.ps1"'
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName 'DAYONG-AgentOS-Node02-OneShot' -Action $Action -Trigger $Trigger -Principal $Principal -Force | Out-Null
Write-Host 'Installed startup task. No 10-second polling. Node worker is one-shot.'
