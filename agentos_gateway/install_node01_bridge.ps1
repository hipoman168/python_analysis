# DAYONG AgentOS Node-01 outbound bootstrap (safe; not a remote shell).
# Expected prerequisite: node01_token.dpapi protected with ConvertFrom-SecureString
# under the SAME Windows account running this task. Do not put bearer values in code/logs.
# The script installs only allowlisted system_info reporting through HTTPS Render.
$ErrorActionPreference = 'Stop'
$root = 'C:\DAYONG_AI\agentos'
New-Item -ItemType Directory -Path $root -Force | Out-Null
$tokenFile = Join-Path $root 'node01_token.dpapi'
$worker = Join-Path $root 'node01_outbound_worker.py'
$start = Join-Path $root 'start_node01_bridge.ps1'
if (-not (Test-Path $tokenFile -PathType Leaf)) {
    throw 'NODE01_TOKEN_DPAPI_NOT_ENROLLED - provision securely with an authorized same-user channel; do not paste into chat.'
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'PYTHON_LAUNCHER_MISSING'
}
$immutableSource='https://raw.githubusercontent.com/hipoman168/python_analysis/863febe8b360a984e4db9f0d0725cbb9a01e0e98/agentos_gateway/node01_outbound_worker.py'
$tmp = Join-Path $root ('node01_worker_'+[guid]::NewGuid().ToString('N')+'.partial')
try {
    Invoke-WebRequest -Uri $immutableSource -OutFile $tmp -UseBasicParsing
    $raw = Get-Content -LiteralPath $tmp -Raw -Encoding UTF8
    if (($raw -notmatch 'NODE_ID = "node-01"') -or ($raw -notmatch 'SKILL_NOT_ALLOWED_NODE01')) {
        throw 'WORKER_SOURCE_IDENTITY_MISMATCH'
    }
    & py -3 -c "import ast,sys;ast.parse(open(sys.argv[1], encoding='utf-8').read())" $tmp
    if ($LASTEXITCODE -ne 0) {throw 'WORKER_PYTHON_SYNTAX_INVALID'}
    Move-Item -LiteralPath $tmp -Destination $worker -Force
}
finally {Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue}
$launcher = @'
$ErrorActionPreference = 'Stop'
$root = 'C:\DAYONG_AI\agentos'
$tokenPath = Join-Path $root 'node01_token.dpapi'
if (-not (Test-Path $tokenPath -PathType Leaf)) { throw 'NODE01_TOKEN_MISSING' }
$sec = Get-Content -LiteralPath $tokenPath | ConvertTo-SecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try {
    $env:NODE_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    $env:NODE_ID = 'node-01'
    & py -3 (Join-Path $root 'node01_outbound_worker.py')
    if ($LASTEXITCODE -ne 0) {throw ('NODE01_WORKER_EXIT_'+$LASTEXITCODE)}
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    Remove-Item Env:NODE_TOKEN -ErrorAction SilentlyContinue
}
'@
[IO.File]::WriteAllText($start,$launcher,[Text.UTF8Encoding]::new($false))
$taskName='DAYONG-AgentOS-Node01-4H'
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$start+'"')
$trigger=New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(5)) -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration (New-TimeSpan -Days 3650)
$principal=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Output 'NODE01_OUTBOUND_BRIDGE_REGISTERED_WITH_DPAPI'
Write-Output ('TASK_NAME='+$taskName)
