# DAYONG AgentOS outbound worker installer — run on each authorized Windows node.
# Uses existing machine environment credentials. Does not print or store tokens.
param(
    [ValidateSet('node-01','node-02')][string]$NodeId = 'node-02',
    [string]$Root = 'C:\DAYONG_AI\agentos',
    [int]$IntervalHours = 4
)
$ErrorActionPreference = 'Stop'
if ($IntervalHours -lt 4) { throw 'Minimum interval is four hours' }
$worker = Join-Path $Root 'outbound_worker_entry_v013.py'
if (-not (Test-Path $worker)) { throw "Worker not deployed: $worker" }
$python = (Get-Command python -ErrorAction Stop).Source
foreach ($key in @('NODE_TOKEN','CLOUD_GATEWAY_URL')) {
    if (-not [Environment]::GetEnvironmentVariable($key,'Machine') -and -not [Environment]::GetEnvironmentVariable($key,'User')) {
        throw "$key not configured for scheduled task"
    }
}
$taskName = "DAYONG-AgentOS-Outbound-$NodeId"
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $worker + '"') -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'DAYONG outbound task worker' -Force | Out-Null
Write-Output "REGISTERED $taskName; interval hours=$IntervalHours; worker=$worker"
