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
$RuntimeDir = Join-Path $SourceDir 'runtime\federation'
$WorkerDir = Join-Path $RuntimeDir 'worker'
$LibDir = Join-Path $RuntimeDir 'lib'
$LauncherPath = Join-Path $Root 'Start-DeusPhysicalNode.ps1'
$ManifestPath = Join-Path $EvidenceDir 'provider-manifest-candidate.json'
$ReportPath = Join-Path $EvidenceDir 'physical-node-readiness.json'
$ExecutionSecretPath = Join-Path $SecretsDir 'execution.dpapi'
$HeartbeatSecretPath = Join-Path $SecretsDir 'heartbeat.dpapi'
$TaskName = 'DEUS-PhysicalNode'

function Write-Step([string]$Message) { Write-Host "[DEUS-RAW-RECOVERY] $Message" -ForegroundColor Cyan }

function Resolve-Executable([string]$CommandName, [string[]]$Fallbacks) {
  $cmd = Get-Command $CommandName -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  foreach ($path in $Fallbacks) { if (Test-Path $path) { return $path } }
  return $null
}

function Get-GitBlobSha1([string]$Path) {
  $bytes = [IO.File]::ReadAllBytes($Path)
  $prefix = [Text.Encoding]::UTF8.GetBytes("blob $($bytes.Length)`0")
  $all = New-Object byte[] ($prefix.Length + $bytes.Length)
  [Array]::Copy($prefix, 0, $all, 0, $prefix.Length)
  [Array]::Copy($bytes, 0, $all, $prefix.Length, $bytes.Length)
  $sha1 = [Security.Cryptography.SHA1]::Create()
  try {
    $hash = $sha1.ComputeHash($all)
    return ([BitConverter]::ToString($hash)).Replace('-', '').ToLowerInvariant()
  }
  finally {
    $sha1.Dispose()
    [Array]::Clear($all, 0, $all.Length)
  }
}

function Get-VerifiedRawFile([string]$RelativePath, [string]$ExpectedBlobSha, [string]$Destination) {
  $url = "https://raw.githubusercontent.com/kimbach91-prog/bl-infinity/$RuntimeRef/$RelativePath"
  Write-Step "Downloading $RelativePath"
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $Destination -TimeoutSec 30
  $actual = Get-GitBlobSha1 $Destination
  if ($actual -ne $ExpectedBlobSha.ToLowerInvariant()) {
    Remove-Item $Destination -Force -ErrorAction SilentlyContinue
    throw "Git blob verification failed for $RelativePath. expected=$ExpectedBlobSha actual=$actual"
  }
  Write-Host "[DEUS-RAW-RECOVERY] verified $RelativePath blob=$actual" -ForegroundColor Green
}

if (-not (Test-Path $ConfigPath)) { throw "Node config missing: $ConfigPath. Run bootstrap.ps1 first." }
if (-not (Test-Path $ExecutionSecretPath)) { throw 'DPAPI execution credential missing; refusing recovery.' }
if (-not (Test-Path $HeartbeatSecretPath)) { throw 'DPAPI heartbeat credential missing; refusing recovery.' }

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
if ([string]$config.state -ne 'STAGED_LOCAL_ONLY') { throw "Unexpected node state: $($config.state)" }
if ([string]$config.workerHost -ne '127.0.0.1') { throw 'Recovery refuses any non-loopback worker host.' }
if ([bool]$config.remoteRoutable) { throw 'Recovery refuses a node marked remote-routable.' }
if ($config.runtimeRef -and [string]$config.runtimeRef -ne $RuntimeRef) { throw "Pinned runtime mismatch: config=$($config.runtimeRef), requested=$RuntimeRef" }

$nodeExe = Resolve-Executable 'node.exe' @("$env:ProgramFiles\nodejs\node.exe")
if (-not $nodeExe) { throw 'Node.js is missing. This recovery intentionally does not install dependencies.' }
$nodeVersionText = & $nodeExe --version
if ($LASTEXITCODE -ne 0) { throw 'Unable to read Node.js version.' }
$major = 0
if ($nodeVersionText -match '^v([0-9]+)\.') { $major = [int]$Matches[1] }
if ($major -lt 18) { throw "Node.js 18+ required; observed $nodeVersionText" }
Write-Step "Using Node.js $nodeVersionText"

foreach ($dir in @($SourceDir, $RuntimeDir, $WorkerDir, $LibDir, $LogsDir, $EvidenceDir)) {
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

$files = @(
  [pscustomobject]@{ rel = 'runtime/federation/worker/server.mjs'; sha = '0735dca9d5db02d1a05e12937967bf77198a9c45'; dst = (Join-Path $WorkerDir 'server.mjs') },
  [pscustomobject]@{ rel = 'runtime/federation/worker/handlers.mjs'; sha = 'cd3446a36056e1079f828b158b295581e99e54d3'; dst = (Join-Path $WorkerDir 'handlers.mjs') },
  [pscustomobject]@{ rel = 'runtime/federation/worker/heartbeat.mjs'; sha = 'aa73cf91e5ea5d890c08ebf580b47a49b0da4dcf'; dst = (Join-Path $WorkerDir 'heartbeat.mjs') },
  [pscustomobject]@{ rel = 'runtime/federation/lib/protocol.mjs'; sha = '331a198fb29ae5c8fa4c09b1db00f7a8a9300edd'; dst = (Join-Path $LibDir 'protocol.mjs') },
  [pscustomobject]@{ rel = 'runtime/federation/lib/provider-heartbeat.mjs'; sha = 'fc06fcbe5b61d6232d049c30ee087764964af490'; dst = (Join-Path $LibDir 'provider-heartbeat.mjs') }
)

foreach ($file in $files) { Get-VerifiedRawFile $file.rel $file.sha $file.dst }

$launcher = @'
#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = Join-Path $env:ProgramData 'DEUSNode'
$Config = Get-Content (Join-Path $Root 'config\node-config.json') -Raw | ConvertFrom-Json
$RuntimeDir = Join-Path $Root 'source\runtime\federation'
$LogDir = Join-Path $Root 'logs'
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
try { & $NodeExe (Join-Path $RuntimeDir 'worker\server.mjs') *>> $log }
finally {
  $env:BL_FEDERATION_SHARED_SECRET = $null
  $env:DEUS_NODE_HEARTBEAT_SECRET = $null
  Pop-Location
}
'@
$launcher | Set-Content -Path $LauncherPath -Encoding UTF8

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
$action = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$LauncherPath`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'DEUS BL-CF physical worker; localhost-only; verified raw runtime; no control token.' | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$port = [int]$config.workerPort
$listeners = @()
try { $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction Stop) } catch { $listeners = @() }
$unsafe = @($listeners | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') })
if ($unsafe.Count -gt 0) {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  throw 'Worker exposed a non-loopback listener; task stopped fail-closed.'
}

$health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health" -Method Get -TimeoutSec 5
if (-not [bool]$health.ok) { throw 'Worker health endpoint did not return ok=true.' }
$caps = Invoke-RestMethod -Uri "http://127.0.0.1:$port/v1/capabilities" -Method Get -TimeoutSec 5
$expectedCaps = @('compute.echo', 'compute.sha256', 'json.project', 'text.stats') | Sort-Object
$actualCaps = @($caps.capabilities | Sort-Object)
if (@(Compare-Object $expectedCaps $actualCaps).Count -ne 0) {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  throw "Capability set mismatch: $($actualCaps -join ',')"
}

$manifest = [pscustomobject]@{
  schema = 'BL_CF_PHYSICAL_NODE_CANDIDATE_V1'
  status = 'STAGED_LOCAL_ONLY'
  id = [string]$config.nodeId
  kind = 'owner-device-windows'
  endpoint = [pscustomobject]@{ transport = 'http-worker'; url = "http://127.0.0.1:$port"; exposure = 'localhost-only'; remoteRoutable = $false }
  capabilities = $actualCaps
  authorization = [pscustomobject]@{ state = 'OWNER_DIRECTIVE_OBSERVED_LOCAL_CANDIDATE'; consentRef = 'REQUIRES_BOUND_SIGNED_PROVIDER_GRANT_BEFORE_REMOTE_ROUTING'; selfGrant = $false }
  runtimeRef = $RuntimeRef
  runtimeDelivery = 'VERIFIED_RAW_MODULE_SET'
  secretsIncluded = $false
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $ManifestPath -Encoding UTF8

$report = [pscustomobject]@{
  schema = 'DEUS_PHYSICAL_NODE_READINESS_V1'
  observedAt = (Get-Date).ToUniversalTime().ToString('o')
  nodeId = [string]$config.nodeId
  verdict = 'READY_LOCAL_ONLY'
  runtimeRef = $RuntimeRef
  delivery = 'VERIFIED_RAW_MODULE_SET'
  nodeVersion = $nodeVersionText
  localHealth = $health
  capabilities = $actualCaps
  listeners = @($listeners | Select-Object LocalAddress, LocalPort, OwningProcess)
  localhostOnly = $true
  remoteRoutable = $false
  remoteAuthorityGranted = $false
  authenticatedHeartbeatObserved = $false
  secretsEmitted = $false
  verifiedBlobShas = @($files | ForEach-Object { [pscustomobject]@{ path = $_.rel; blobSha1 = $_.sha } })
}
$report | ConvertTo-Json -Depth 10 | Set-Content -Path $ReportPath -Encoding UTF8

Write-Host "DEUS physical-node verdict: READY_LOCAL_ONLY" -ForegroundColor Green
Write-Host "Node: $($config.nodeId)" -ForegroundColor Green
Write-Host "Worker: http://127.0.0.1:$port" -ForegroundColor Green
Write-Host "Evidence: $ReportPath" -ForegroundColor Green
Write-Host 'Remote routing remains DENIED until secure transport + signed provider grant + authenticated heartbeat are separately proven.' -ForegroundColor Yellow
