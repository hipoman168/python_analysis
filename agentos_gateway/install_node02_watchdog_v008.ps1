# Install DAYONG Node-02 four-hour watchdog. Run as the same user who saved DPAPI token.
$ErrorActionPreference = 'Stop'
$Root = 'C:\DAYONG_AI\agentos'
$Source = 'https://raw.githubusercontent.com/hipoman168/python_analysis/feature/agentos-gateway-v006/agentos_gateway/node02_watchdog_v008.ps1'
$Watchdog = Join-Path $Root 'node02_watchdog_v008.ps1'
if (-not (Test-Path (Join-Path $Root 'node_token.dpapi'))) { throw 'TOKEN_FILE_MISSING' }
Invoke-WebRequest -Uri $Source -OutFile $Watchdog -UseBasicParsing
$ParseErrors = $null
[System.Management.Automation.PSParser]::Tokenize((Get-Content $Watchdog -Raw), [ref]$ParseErrors) | Out-Null
if ($ParseErrors.Count -gt 0) { throw 'WATCHDOG_SYNTAX_ERROR' }
$TaskName = 'DAYONG-AgentOS-Node02-Watchdog'
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $Watchdog + '"')
$Trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(5)) -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration (New-TimeSpan -Days 3650)
$Principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName,State
Write-Host 'NODE02_WATCHDOG_REGISTERED' -ForegroundColor Green
