# DAYONG AgentOS Dual Channel: single attempt; never used as a keepalive.
# This is separate from the legacy v007/v008 worker. Do not register a
# recurring task until durable inbox backend and end-to-end Evidence pass.
$ErrorActionPreference = 'Stop'
$Root = 'C:\DAYONG_AI\agentos'
$TokenFile = Join-Path $Root 'node_token.dpapi'
$WorkerFile = Join-Path $Root 'node_inbox_worker.py'
$Python = Join-Path $Root 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $TokenFile -PathType Leaf)) { throw 'NODE_TOKEN_FILE_MISSING' }
if (-not (Test-Path -LiteralPath $WorkerFile -PathType Leaf)) { throw 'INBOX_WORKER_MISSING' }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'PYTHON_MISSING' }

$env:CLOUD_GATEWAY_URL = 'https://dayong-agentos-gateway.onrender.com'
$env:NODE_ID = 'node-02'

$SecureToken = Get-Content -LiteralPath $TokenFile | ConvertTo-SecureString
$TokenPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
try {
    $env:NODE_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($TokenPtr)
    & $Python $WorkerFile
    if ($LASTEXITCODE -ne 0) { throw ('INBOX_WORKER_EXIT_' + $LASTEXITCODE) }
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($TokenPtr)
    Remove-Item Env:NODE_TOKEN -ErrorAction SilentlyContinue
}
