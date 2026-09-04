#requires -Version 5.1
[CmdletBinding()]
param(
  [int]$WorkerPort = 8790,
  [switch]$WriteEvidence
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = Join-Path $env:ProgramData 'DEUSNode'
$ConfigPath = Join-Path $Root 'config\node-config.json'
$EvidenceDir = Join-Path $Root 'evidence'
$checks = New-Object System.Collections.Generic.List[object]

function Add-Check([string]$Name, [bool]$Pass, [string]$Detail, [string]$Severity = 'P0') {
  $checks.Add([ordered]@{ name = $Name; pass = $Pass; detail = $Detail; severity = $Severity })
}

function Test-UnauthenticatedExecute([int]$Port) {
  try {
    $body = '{"task":{"id":"audit-unauthenticated","capability":"compute.echo","payload":"deny-me"}}'
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/v1/execute" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 3 | Out-Null
    return @{ pass = $false; status = 'unexpected-success' }
  }
  catch {
    $response = $_.Exception.Response
    if ($response -and [int]$response.StatusCode -eq 401) { return @{ pass = $true; status = '401' } }
    return @{ pass = $false; status = $_.Exception.Message }
  }
}

$firewall = @(Get-NetFirewallProfile)
foreach ($profile in $firewall) {
  Add-Check "Firewall-$($profile.Name)-Enabled" ([bool]$profile.Enabled) "Enabled=$($profile.Enabled)"
  Add-Check "Firewall-$($profile.Name)-InboundBlock" ([string]$profile.DefaultInboundAction -eq 'Block') "DefaultInboundAction=$($profile.DefaultInboundAction)"
}

if (Get-Command Get-MpComputerStatus -ErrorAction SilentlyContinue) {
  try {
    $mp = Get-MpComputerStatus
    Add-Check 'Defender-Antivirus' ([bool]$mp.AntivirusEnabled) "AntivirusEnabled=$($mp.AntivirusEnabled)" 'P1'
    Add-Check 'Defender-Realtime' ([bool]$mp.RealTimeProtectionEnabled) "RealTimeProtectionEnabled=$($mp.RealTimeProtectionEnabled)" 'P0'
    Add-Check 'Defender-BehaviorMonitor' ([bool]$mp.BehaviorMonitorEnabled) "BehaviorMonitorEnabled=$($mp.BehaviorMonitorEnabled)" 'P1'
  }
  catch { Add-Check 'Defender-Readable' $false $_.Exception.Message 'P1' }
}
else { Add-Check 'Defender-Available' $false 'Defender cmdlets unavailable' 'P1' }

$remoteRegistry = Get-CimInstance Win32_Service -Filter "Name='RemoteRegistry'" -ErrorAction SilentlyContinue
if ($remoteRegistry) {
  Add-Check 'RemoteRegistry-Disabled' ($remoteRegistry.StartMode -eq 'Disabled' -and $remoteRegistry.State -ne 'Running') "StartMode=$($remoteRegistry.StartMode); State=$($remoteRegistry.State)" 'P1'
}

$controlMachine = [Environment]::GetEnvironmentVariable('BL_CONTROL_TOKEN', 'Machine')
$controlUser = [Environment]::GetEnvironmentVariable('BL_CONTROL_TOKEN', 'User')
$controlProcess = [Environment]::GetEnvironmentVariable('BL_CONTROL_TOKEN', 'Process')
Add-Check 'No-Control-Token-On-Worker' (-not ($controlMachine -or $controlUser -or $controlProcess)) 'BL_CONTROL_TOKEN must not exist in machine/user/process environment' 'P0'

if (Test-Path $ConfigPath) {
  $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
  Add-Check 'Node-Config-State' ($config.state -eq 'STAGED_LOCAL_ONLY') "state=$($config.state)" 'P0'
  Add-Check 'Node-Remote-Routable-False' (-not [bool]$config.remoteRoutable) "remoteRoutable=$($config.remoteRoutable)" 'P0'
  Add-Check 'Node-Host-Loopback' ($config.workerHost -eq '127.0.0.1') "workerHost=$($config.workerHost)" 'P0'
  $WorkerPort = [int]$config.workerPort
}
else {
  Add-Check 'Node-Config-Present' $false "$ConfigPath missing" 'P0'
}

$executionSecretPath = Join-Path $Root 'secrets\execution.dpapi'
$heartbeatSecretPath = Join-Path $Root 'secrets\heartbeat.dpapi'
Add-Check 'Execution-Secret-DPAPI-Present' (Test-Path $executionSecretPath) 'DPAPI ciphertext file only; secret value not inspected' 'P0'
Add-Check 'Heartbeat-Secret-DPAPI-Present' (Test-Path $heartbeatSecretPath) 'DPAPI ciphertext file only; secret value not inspected' 'P0'

$task = Get-ScheduledTask -TaskName 'DEUS-PhysicalNode' -ErrorAction SilentlyContinue
$taskDetail = 'missing'
if ($task) { $taskDetail = "State=$($task.State)" }
Add-Check 'Startup-Task-Present' ([bool]$task) $taskDetail 'P1'

$listeners = @()
try { $listeners = @(Get-NetTCPConnection -LocalPort $WorkerPort -State Listen -ErrorAction Stop) } catch { $listeners = @() }
$unsafe = @($listeners | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') })
Add-Check 'Worker-No-NonLoopback-Listener' ($unsafe.Count -eq 0) "listeners=$(@($listeners | ForEach-Object { "$($_.LocalAddress):$($_.LocalPort)" }) -join ',')" 'P0'

$healthOk = $false
try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:$WorkerPort/health" -Method Get -TimeoutSec 3
  $healthOk = [bool]$health.ok
  Add-Check 'Worker-Local-Health' $healthOk "service=$($health.service); inFlight=$($health.inFlight); maxConcurrency=$($health.maxConcurrency)" 'P0'
  $caps = Invoke-RestMethod -Uri "http://127.0.0.1:$WorkerPort/v1/capabilities" -Method Get -TimeoutSec 3
  $allowed = @('compute.echo', 'compute.sha256', 'json.project', 'text.stats')
  $actual = @($caps.capabilities | Sort-Object)
  $capSafe = (@(Compare-Object ($allowed | Sort-Object) $actual).Count -eq 0)
  Add-Check 'Worker-Capability-Allowlist' $capSafe "capabilities=$($actual -join ',')" 'P0'
  $unauth = Test-UnauthenticatedExecute $WorkerPort
  Add-Check 'Worker-Execution-Requires-Auth' ([bool]$unauth.pass) "unauthenticatedStatus=$($unauth.status)" 'P0'
}
catch {
  Add-Check 'Worker-Local-Health' $false $_.Exception.Message 'P0'
}

$p0Failures = @($checks | Where-Object { $_.severity -eq 'P0' -and -not $_.pass })
$p1Failures = @($checks | Where-Object { $_.severity -eq 'P1' -and -not $_.pass })
$verdict = if ($p0Failures.Count -eq 0 -and $healthOk) { 'READY_LOCAL_ONLY' } elseif ($p0Failures.Count -eq 0) { 'HARDENED_RUNTIME_NOT_READY' } else { 'FAIL_CLOSED' }

$result = [ordered]@{
  schema = 'DEUS_PHYSICAL_NODE_AUDIT_V1'
  observedAt = (Get-Date).ToUniversalTime().ToString('o')
  verdict = $verdict
  remoteRoutable = $false
  remoteAuthorityProven = $false
  authenticatedHeartbeatProven = $false
  checks = @($checks)
  summary = @{ p0Failures = $p0Failures.Count; p1Failures = $p1Failures.Count; total = $checks.Count }
  secretsRead = $false
}

$result | ConvertTo-Json -Depth 10
if ($WriteEvidence) {
  if (-not (Test-Path $EvidenceDir)) { New-Item -ItemType Directory -Path $EvidenceDir -Force | Out-Null }
  $path = Join-Path $EvidenceDir ("audit-{0}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
  $result | ConvertTo-Json -Depth 10 | Set-Content -Path $path -Encoding UTF8
  Write-Host "Audit evidence: $path" -ForegroundColor Green
}

if ($verdict -eq 'FAIL_CLOSED') { exit 2 }
if ($verdict -eq 'HARDENED_RUNTIME_NOT_READY') { exit 1 }
exit 0