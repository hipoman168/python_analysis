# DAYONG AgentOS Node-02 watchdog v0.0.8
# Runs one approved worker attempt, without continuous polling.
$ErrorActionPreference = 'Stop'
$Root = 'C:\DAYONG_AI\agentos'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('watchdog-' + (Get-Date -Format 'yyyyMMdd') + '.log')
$Mutex = New-Object System.Threading.Mutex($false, 'Local\DAYONG-AgentOS-Node02-Worker')
$Acquired = $false
try {
    try { $Acquired = $Mutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $Acquired = $true }
    if (-not $Acquired) {
        Add-Content -Path $Log -Value "$(Get-Date -Format o) SKIP_ALREADY_RUNNING"
        exit 0
    }
    $Starter = Join-Path $Root 'start_worker.ps1'
    if (-not (Test-Path $Starter)) { throw 'STARTER_MISSING' }
    & $Starter *>> $Log
    if (-not $?) { throw 'WORKER_FAILED' }
    Add-Content -Path $Log -Value "$(Get-Date -Format o) RUN_FINISHED"
} catch {
    Add-Content -Path $Log -Value "$(Get-Date -Format o) ERROR $($_.Exception.Message)"
    exit 1
} finally {
    if ($Acquired) { $Mutex.ReleaseMutex() }
    $Mutex.Dispose()
}
