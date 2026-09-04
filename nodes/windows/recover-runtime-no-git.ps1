#requires -Version 5.1
#requires -RunAsAdministrator
[CmdletBinding()]
param(
  [string]$RuntimeRef = '15ba4e771167bff2ddda1631c3f7bb9047cbf1d9'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Join-Path $env:ProgramData 'DEUSNode'
$ConfigPath = Join-Path $Root 'config\node-config.json'
$SecretsDir = Join-Path $Root 'secrets'
$LogsDir = Join-Path $Root 'logs'
$EvidenceDir = Join-Path $Root 'evidence'
$SourceDir = Join-Path $Root 'source'
$LauncherPath = Join-Path $Root 'Start-DeusPhysicalNode.ps1'
$ManifestPath = Join-Path $EvidenceDir 'provider-manifest-candidate.json'
$ReportPath = Join-Path $EvidenceDir 'physical-node-readiness.json'
$ExecutionSecretPath = Join-Path $SecretsDir 'execution.dpapi'
$HeartbeatSecretPath = Join-Path $SecretsDir 'heartbeat.dpapi'
$TaskName = 'DEUS-PhysicalNode'

function Write-Step([string]$Message) { Write-Host "[DEUS-RECOVERY] $Message" -ForegroundColor Cyan }
function Resolve-Executable([string]$CommandName, [string[]]$Fallbacks) {
  $cmd = Get-Command $CommandName -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  foreach ($path in $Fallbacks) { if (Test-Path $path) { return $path } }
  return $null
}

if (-not (Test-Path $ConfigPath)) { throw "Node config missing: $ConfigPath. Run bootstrap.ps1 first." }
if (-not (Test-Path $ExecutionSecretPath)) { throw 'DPAPI execution credential missing; refusing to regenerate authority during recovery.' }
if (-not (Test-Path $HeartbeatSecretPath)) { throw 'DPAPI heartbeat credential missing; refusing to regenerate authority during recovery.' }

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
if ([string]$config.state -ne 'STAGED_LOCAL_ONLY') { throw "Unexpected node state: $($config.state)" }
if ([string]$config.workerHost -ne '127.0.0.1') { throw 'Recovery refuses any non-loopback worker host.' }
if ([bool]$config.remoteRoutable) { throw 'Recovery refuses a node already marked remote-routable.' }
if ($config.runtimeRef -and [string]$config.runtimeRef -ne $RuntimeRef) { throw "Pinned runtime mismatch: config=$($config.runtimeRef), requested=$RuntimeRef" }

$nodeExe = Resolve-Executable 'node.exe' @("$env:ProgramFiles\nodejs\node.exe")
$npmExe = Resolve-Executable 'npm.cmd' @("$env:ProgramFiles\nodejs\npm.cmd")
if (-not $nodeExe -or -not $npmExe) { throw 'Node.js/npm are required and were not found. This recovery intentionally does not install system packages.' }

foreach ($dir in @($LogsDir, $EvidenceDir, $SecretsDir)) {
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

Write-Step "Downloading pinned BL-CF snapshot $RuntimeRef without Git/winget"
$work = Join-Path $env:TEMP ("DEUSNodeRecovery-{0}" -f ([Guid]::NewGuid().ToString('N')))
$archive = Join-Path $work 'runtime.zip'
$expanded = Join-Path $work 'expanded'
New-Item -ItemType Directory -Path $expanded -Force | Out-Null

try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $urls = @(
    "https://codeload.github.com/kimbach91-prog/bl-infinity/zip/$RuntimeRef",
    "https://github.com/kimbach91-prog/bl-infinity/archive/$RuntimeRef.zip"
  )
  $downloaded = $false
  $lastError = $null
  foreach ($url in $urls) {
    try {
      Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $archive -TimeoutSec 90
      if ((Test-Path $archive) -and (Get-Item $archive).Length -gt 1024) { $downloaded = $true; break }
    }
    catch { $lastError = $_.Exception.Message }
  }
  if (-not $downloaded) { throw "Unable to download pinned runtime archive. Last error: $lastError" }

  Expand-Archive -Path $archive -DestinationPath $expanded -Force
  $rootCandidate = Get-ChildItem -Path $expanded -Directory | Where-Object {
    Test-Path (Join-Path $_.FullName 'runtime\federation\worker\server.mjs')
  } | Select-Object -First 1
  if (-not $rootCandidate) { throw 'Downloaded archive does not contain the expected BL-CF runtime layout.' }

  if (Test-Path $SourceDir) { Remove-Item $SourceDir -Recurse -Force }
  New-Item -ItemType Directory -Path $SourceDir -Force | Out-Null
  Copy-Item -Path (Join-Path $rootCandidate.FullName '*') -Destination $SourceDir -Recurse -Force
}
finally {
  if (Test-Path $work) { Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue }
}

$runtimeDir = Join-Path $SourceDir 'runtime\federation'
if (-not (Test-Path (Join-Path $runtimeDir 'worker\server.mjs'))) { throw 'Runtime copy verification failed.' }

Write-Step 'Installing pinned runtime npm dependencies'
Push-Location $runtimeDir
try {
  & $npmExe install --omit=dev --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw "npm install failed with exit code $LASTEXITCODE" }
}
finally { Pop-Location }

$launcher = @'
#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = Join-Path $env:ProgramData 'DEUSNode'
$Config = Get-Content (Join-Path $Root 'config\node-config.json') -Raw | ConvertFrom-Json
$LogDir = Join-Path $Root 'logs'
$RuntimeDir = Join-Path $Root 'source\runtime\federation'
$NodeExe = if (Test-Path "$env:ProgramFiles\nodejs\node.exe") { "$env:ProgramFiles\nodejs\node.exe" } else { (Get-Command node.exe -ErrorAction Stop).Source }
function Unprotect([string]$Path) {
  Add-Type -AssemblyName System.Security
  $cipher = [IO.File]::ReadAllBytes($Path)
  $plain = [Security.Cryptography.ProtectedData]::Unprotect($cipher, $null, [Security.Cryptography.DataProtectionScope]::LocalMachine)
  try { return [Text.Encoding]::UTF8.GetString($plain) } finally { [Array]::Clear($plain, 0, $plain.Length) }
}
$env:HOST = '127.0.0.1'
$env:PORT = [string]$Config.workerPort
$env:BL_WORKER_MAX_CONCURRENCY = [string]$Config.maxConcurrency
$env:BL_WORKER_MAX_BODY_BYTES = '262144'
$env:BL_FEDERATION_SHARED_SECRET = Unprotect (Join-Path $Root 'secrets\execution.dpapi')
if ($Config.heartbeatUrl) {
  $env:BL_PROVIDER_ID = [string]$Config.nodeId
  $env:BL_HEARTBEAT_URL = [string]$Config.heartbeatUrl
  $env:BL_HEARTBEAT_SECRET_ENV = 'DEUS_NODE_HEARTBEAT_SECRET'
  $env:DEUS_NODE_HEARTBEAT_SECRET = Unprotect (Join-Path $Root 'secrets\heartbeat.dpapi')
  $env:BL_HEARTBEAT_INTERVAL_MS = '20000'
  $env:BL_HEARTBEAT_TIMEOUT_MS = '5000'
}
$log = Join-Path $LogDir ("worker-{0}.log" -f (Get-Date -Format 'yyyyMMdd'))
Push-Location $RuntimeDir
try {
  & $NodeExe (Join-Path $RuntimeDir 'worker\server.mjs') *>> $log
}
finally {
  $env:BL_FEDERATION_SHARED_SECRET = $null
  $env:DEUS_NODE_HEARTBEAT_SECRET = $null
  Pop-Location
}
'@
$launcher | Set-Content -Path $LauncherPath -Encoding UTF8

Write-Step 'Registering localhost-only worker startup task'
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
$action = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$LauncherPath`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'DEUS BL-CF physical worker; localhost-only; node-scoped credentials; no control token.' | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 4

$port = [int]$config.workerPort
$health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health" -Method Get -TimeoutSec 5
$caps = Invoke-RestMethod -Uri "http://127.0.0.1:$port/v1/capabilities" -Method Get -TimeoutSec 5
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction Stop | Select-Object LocalAddress, LocalPort, OwningProcess)
$unsafe = @($listeners | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') })
if ($unsafe.Count -gt 0) {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  throw 'Worker exposed a non-loopback listener; task stopped and readiness denied.'
}

$allowed = @('compute.echo', 'compute.sha256', 'json.project', 'text.stats') | Sort-Object
$actual = @($caps.capabilities | Sort-Object)
if (@(Compare-Object $allowed $actual).Count -ne 0) {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  throw "Unexpected capability set: $($actual -join ',')"
}

$manifest = [ordered]@{
  schema = 'BL_CF_PHYSICAL_NODE_CANDIDATE_V1'
  status = 'STAGED_LOCAL_ONLY'
  id = [string]$config.nodeId
  kind = 'owner-device-windows'
  endpoint = @{ transport = 'http-worker'; url = "http://127.0.0.1:$port"; exposure = 'localhost-only'; remoteRoutable = $false }
  capabilities = $actual
  authorization = @{ state = 'OWNER_DIRECTIVE_OBSERVED_LOCAL_CANDIDATE'; consentRef = 'REQUIRES_BOUND_SIGNED_PROVIDER_GRANT_BEFORE_REMOTE_ROUTING'; selfGrant = $false }
  dataPolicy = @{ allowedDataClasses = @('public', 'internal'); privateDataEgress = $false; restrictedData = 'DENY_UNTIL_EXPLICIT_POLICY' }
  limits = @{ maxConcurrency = [int]$config.maxConcurrency; maxTaskBytes = 262144 }
  liveness = @{ heartbeatRequiredBeforeRemoteRouting = $true; heartbeatTtlMs = 60000; heartbeatAuth = @{ mode = 'hmac-env'; secretEnv = 'DEUS_NODE_HEARTBEAT_SECRET' } }
  runtimeRef = $RuntimeRef
  secretsIncluded = $false
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $ManifestPath -Encoding UTF8

$report = [ordered]@{
  schema = 'DEUS_PHYSICAL_NODE_READINESS_V1'
  observedAt = (Get-Date).ToUniversalTime().ToString('o')
  nodeId = [string]$config.nodeId
  runtime = @{
    pinnedRef = $RuntimeRef
    installed = $true
    scheduledTask = [bool](Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)
    localHealth = $health
    capabilities = $actual
    listeners = $listeners
    localhostOnly = $true
    remoteRoutable = $false
    remoteAuthorityGranted = $false
    firstAuthenticatedHeartbeatObserved = $false
    installTransport = 'pinned-github-archive-no-git'
  }
  secretsEmitted = $false
  controlTokenInstalled = $false
}
$report | ConvertTo-Json -Depth 10 | Set-Content -Path $ReportPath -Encoding UTF8

Write-Host "[DEUS-RECOVERY] READY_LOCAL_ONLY: $($config.nodeId) on 127.0.0.1:$port" -ForegroundColor Green
Write-Host "Evidence: $ReportPath" -ForegroundColor Green
Write-Host 'Remote routing remains DENIED until secure transport + signed/revocable provider grant + authenticated heartbeat are separately proven.' -ForegroundColor Yellow
