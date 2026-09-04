#requires -Version 5.1
#requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [switch]$InstallDependencies,
  [switch]$DisableLegacySMB1,
  [switch]$DisableRdp,
  [switch]$DisableWinRM,
  [int]$WorkerPort = 8790,
  [int]$WorkerMaxConcurrency = 1,
  [string]$RuntimeRef = '15ba4e771167bff2ddda1631c3f7bb9047cbf1d9'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Join-Path $env:ProgramData 'DEUSNode'
$ConfigDir = Join-Path $Root 'config'
$SecretsDir = Join-Path $Root 'secrets'
$LogsDir = Join-Path $Root 'logs'
$EvidenceDir = Join-Path $Root 'evidence'
$SourceDir = Join-Path $Root 'source'
$SnapshotPath = Join-Path $EvidenceDir 'pre-change-snapshot.json'
$ConfigPath = Join-Path $ConfigDir 'node-config.json'
$ManifestPath = Join-Path $EvidenceDir 'provider-manifest-candidate.json'
$ReportPath = Join-Path $EvidenceDir 'physical-node-readiness.json'
$LauncherPath = Join-Path $Root 'Start-DeusPhysicalNode.ps1'
$ExecutionSecretPath = Join-Path $SecretsDir 'execution.dpapi'
$HeartbeatSecretPath = Join-Path $SecretsDir 'heartbeat.dpapi'
$TaskName = 'DEUS-PhysicalNode'
$RepoUrl = 'https://github.com/kimbach91-prog/bl-infinity.git'

function Write-Step([string]$Message) {
  Write-Host "[DEUS-NODE] $Message" -ForegroundColor Cyan
}

function Write-Warn([string]$Message) {
  Write-Warning "[DEUS-NODE] $Message"
}

function Get-RegistryValueState([string]$Path, [string]$Name) {
  if (-not (Test-Path $Path)) {
    return [ordered]@{ path = $Path; name = $Name; existed = $false; valueExisted = $false; value = $null }
  }
  $item = Get-ItemProperty -Path $Path -ErrorAction SilentlyContinue
  $property = $item.PSObject.Properties[$Name]
  return [ordered]@{
    path = $Path
    name = $Name
    existed = $true
    valueExisted = [bool]$property
    value = if ($property) { $property.Value } else { $null }
  }
}

function Set-RegistryDword([string]$Path, [string]$Name, [int]$Value) {
  if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
  New-ItemProperty -Path $Path -Name $Name -PropertyType DWord -Value $Value -Force | Out-Null
}

function New-RandomSecret {
  $bytes = New-Object byte[] 32
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  return [Convert]::ToBase64String($bytes)
}

function New-NodeId {
  $bytes = New-Object byte[] 8
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  $suffix = ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
  return "deus-win-$suffix"
}

function Protect-MachineSecret([string]$Secret, [string]$Path) {
  Add-Type -AssemblyName System.Security
  $plain = [Text.Encoding]::UTF8.GetBytes($Secret)
  try {
    $cipher = [Security.Cryptography.ProtectedData]::Protect(
      $plain,
      $null,
      [Security.Cryptography.DataProtectionScope]::LocalMachine
    )
    [IO.File]::WriteAllBytes($Path, $cipher)
  }
  finally {
    [Array]::Clear($plain, 0, $plain.Length)
  }
}

function Invoke-BestEffort([string]$Label, [scriptblock]$Action, [ref]$Warnings) {
  try {
    & $Action
  }
  catch {
    $Warnings.Value += "$Label: $($_.Exception.Message)"
    Write-Warn "$Label could not be enforced: $($_.Exception.Message)"
  }
}

function Resolve-Executable([string]$CommandName, [string[]]$Fallbacks) {
  $cmd = Get-Command $CommandName -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  foreach ($path in $Fallbacks) { if (Test-Path $path) { return $path } }
  return $null
}

function Install-WingetPackage([string]$Id) {
  $winget = Resolve-Executable 'winget.exe' @()
  if (-not $winget) { throw "winget is unavailable; install dependency '$Id' manually" }
  & $winget install --id $Id -e --accept-package-agreements --accept-source-agreements --silent
  if ($LASTEXITCODE -ne 0) { throw "winget install failed for $Id with exit code $LASTEXITCODE" }
}

function Get-DefenderSnapshot {
  $result = [ordered]@{ available = $false; preference = $null; status = $null }
  if (Get-Command Get-MpPreference -ErrorAction SilentlyContinue) {
    try {
      $pref = Get-MpPreference
      $status = Get-MpComputerStatus
      $result.available = $true
      $result.preference = [ordered]@{
        DisableRealtimeMonitoring = $pref.DisableRealtimeMonitoring
        DisableBehaviorMonitoring = $pref.DisableBehaviorMonitoring
        DisableScriptScanning = $pref.DisableScriptScanning
        DisableIOAVProtection = $pref.DisableIOAVProtection
        DisableBlockAtFirstSeen = $pref.DisableBlockAtFirstSeen
        PUAProtection = $pref.PUAProtection
        EnableNetworkProtection = $pref.EnableNetworkProtection
        EnableControlledFolderAccess = $pref.EnableControlledFolderAccess
        MAPSReporting = $pref.MAPSReporting
        SubmitSamplesConsent = $pref.SubmitSamplesConsent
      }
      $result.status = [ordered]@{
        AntivirusEnabled = $status.AntivirusEnabled
        RealTimeProtectionEnabled = $status.RealTimeProtectionEnabled
        BehaviorMonitorEnabled = $status.BehaviorMonitorEnabled
        IoavProtectionEnabled = $status.IoavProtectionEnabled
        NISEnabled = $status.NISEnabled
        AntivirusSignatureLastUpdated = $status.AntivirusSignatureLastUpdated
      }
    } catch { $result.error = $_.Exception.Message }
  }
  return $result
}

function Get-BitLockerSummary {
  if (-not (Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue)) { return @{ available = $false } }
  try {
    $volume = Get-BitLockerVolume -MountPoint $env:SystemDrive
    return [ordered]@{
      available = $true
      VolumeStatus = [string]$volume.VolumeStatus
      ProtectionStatus = [string]$volume.ProtectionStatus
      EncryptionMethod = [string]$volume.EncryptionMethod
    }
  } catch { return @{ available = $true; error = $_.Exception.Message } }
}

function Get-TpmSummary {
  if (-not (Get-Command Get-Tpm -ErrorAction SilentlyContinue)) { return @{ available = $false } }
  try {
    $tpm = Get-Tpm
    return [ordered]@{
      available = $true
      TpmPresent = $tpm.TpmPresent
      TpmReady = $tpm.TpmReady
      TpmEnabled = $tpm.TpmEnabled
      TpmActivated = $tpm.TpmActivated
    }
  } catch { return @{ available = $true; error = $_.Exception.Message } }
}

function Get-SecureBootSummary {
  if (-not (Get-Command Confirm-SecureBootUEFI -ErrorAction SilentlyContinue)) { return @{ available = $false } }
  try { return @{ available = $true; enabled = [bool](Confirm-SecureBootUEFI) } }
  catch { return @{ available = $true; supported = $false; error = $_.Exception.Message } }
}

Write-Step 'Creating restricted local node directories'
foreach ($dir in @($Root, $ConfigDir, $SecretsDir, $LogsDir, $EvidenceDir)) {
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}
& icacls.exe $Root /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' /T /C | Out-Null

$scriptBlockPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging'
$autoRunPath = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer'
$rdpPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server'

if (-not (Test-Path $SnapshotPath)) {
  Write-Step 'Capturing pre-change security snapshot'
  $remoteRegistry = Get-CimInstance Win32_Service -Filter "Name='RemoteRegistry'" -ErrorAction SilentlyContinue
  $winrm = Get-CimInstance Win32_Service -Filter "Name='WinRM'" -ErrorAction SilentlyContinue
  $snapshot = [ordered]@{
    createdAt = (Get-Date).ToUniversalTime().ToString('o')
    computerName = $env:COMPUTERNAME
    firewall = @(Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction, LogBlocked, LogAllowed, LogFileName, LogMaxSizeKilobytes)
    defender = Get-DefenderSnapshot
    remoteRegistry = if ($remoteRegistry) { @{ StartMode = $remoteRegistry.StartMode; State = $remoteRegistry.State } } else { $null }
    winrm = if ($winrm) { @{ StartMode = $winrm.StartMode; State = $winrm.State } } else { $null }
    rdp = Get-RegistryValueState $rdpPath 'fDenyTSConnections'
    scriptBlockLogging = Get-RegistryValueState $scriptBlockPath 'EnableScriptBlockLogging'
    autorun = Get-RegistryValueState $autoRunPath 'NoDriveTypeAutoRun'
    smb1 = if (Get-Command Get-WindowsOptionalFeature -ErrorAction SilentlyContinue) {
      try { [string](Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol).State } catch { 'UNKNOWN' }
    } else { 'UNAVAILABLE' }
  }
  $snapshot | ConvertTo-Json -Depth 10 | Set-Content -Path $SnapshotPath -Encoding UTF8
}
else {
  Write-Step 'Pre-change snapshot already exists; preserving first snapshot'
}

$warnings = @()
Write-Step 'Applying reversible safe hardening baseline'
Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True -DefaultInboundAction Block -DefaultOutboundAction Allow
Set-NetFirewallProfile -Profile Domain,Private,Public -LogBlocked True -LogMaxSizeKilobytes 16384

Invoke-BestEffort 'Defender real-time monitoring' { Set-MpPreference -DisableRealtimeMonitoring $false } ([ref]$warnings)
Invoke-BestEffort 'Defender behavior monitoring' { Set-MpPreference -DisableBehaviorMonitoring $false } ([ref]$warnings)
Invoke-BestEffort 'Defender script scanning' { Set-MpPreference -DisableScriptScanning $false } ([ref]$warnings)
Invoke-BestEffort 'Defender downloaded-file scanning' { Set-MpPreference -DisableIOAVProtection $false } ([ref]$warnings)
Invoke-BestEffort 'Defender block-at-first-seen' { Set-MpPreference -DisableBlockAtFirstSeen $false } ([ref]$warnings)
Invoke-BestEffort 'Defender PUA protection' { Set-MpPreference -PUAProtection Enabled } ([ref]$warnings)
Invoke-BestEffort 'Defender network protection' { Set-MpPreference -EnableNetworkProtection Enabled } ([ref]$warnings)
Invoke-BestEffort 'Controlled Folder Access audit mode' { Set-MpPreference -EnableControlledFolderAccess AuditMode } ([ref]$warnings)
Invoke-BestEffort 'Defender cloud protection' { Set-MpPreference -MAPSReporting Advanced } ([ref]$warnings)
Invoke-BestEffort 'Defender safe sample submission' { Set-MpPreference -SubmitSamplesConsent SendSafeSamples } ([ref]$warnings)

Invoke-BestEffort 'Remote Registry disable' {
  Stop-Service -Name RemoteRegistry -Force -ErrorAction SilentlyContinue
  Set-Service -Name RemoteRegistry -StartupType Disabled
} ([ref]$warnings)

Set-RegistryDword $scriptBlockPath 'EnableScriptBlockLogging' 1
Set-RegistryDword $autoRunPath 'NoDriveTypeAutoRun' 255

if ($DisableLegacySMB1) {
  Invoke-BestEffort 'SMB1 disable' {
    Disable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -NoRestart | Out-Null
  } ([ref]$warnings)
}

if ($DisableRdp) {
  Set-RegistryDword $rdpPath 'fDenyTSConnections' 1
  Invoke-BestEffort 'Remote Desktop firewall disable' {
    Disable-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction Stop | Out-Null
  } ([ref]$warnings)
}

if ($DisableWinRM) {
  Invoke-BestEffort 'WinRM disable' {
    Stop-Service -Name WinRM -Force -ErrorAction SilentlyContinue
    Set-Service -Name WinRM -StartupType Disabled
  } ([ref]$warnings)
}

Write-Step 'Generating stable node identity and DPAPI-protected node-scoped credentials'
if (Test-Path $ConfigPath) {
  $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
  $nodeId = [string]$config.nodeId
  if (-not $nodeId) { throw 'Existing node-config.json has no nodeId' }
}
else {
  $nodeId = New-NodeId
  $config = [ordered]@{
    schemaVersion = 1
    nodeId = $nodeId
    state = 'STAGED_LOCAL_ONLY'
    createdAt = (Get-Date).ToUniversalTime().ToString('o')
    workerHost = '127.0.0.1'
    workerPort = $WorkerPort
    maxConcurrency = [Math]::Max(1, [Math]::Min($WorkerMaxConcurrency, 4))
    runtimeRef = $RuntimeRef
    remoteRoutable = $false
    secureTransport = $null
    heartbeatUrl = $null
    heartbeatSecretEnv = 'DEUS_NODE_HEARTBEAT_SECRET'
  }
  $config | ConvertTo-Json -Depth 8 | Set-Content -Path $ConfigPath -Encoding UTF8
}

if (-not (Test-Path $ExecutionSecretPath)) { Protect-MachineSecret (New-RandomSecret) $ExecutionSecretPath }
if (-not (Test-Path $HeartbeatSecretPath)) { Protect-MachineSecret (New-RandomSecret) $HeartbeatSecretPath }
& icacls.exe $SecretsDir /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' /T /C | Out-Null

$gitExe = Resolve-Executable 'git.exe' @("$env:ProgramFiles\Git\cmd\git.exe")
$nodeExe = Resolve-Executable 'node.exe' @("$env:ProgramFiles\nodejs\node.exe")
$npmExe = Resolve-Executable 'npm.cmd' @("$env:ProgramFiles\nodejs\npm.cmd")

if ($InstallDependencies) {
  if (-not $gitExe) { Write-Step 'Installing Git'; Install-WingetPackage 'Git.Git'; $gitExe = Resolve-Executable 'git.exe' @("$env:ProgramFiles\Git\cmd\git.exe") }
  if (-not $nodeExe) { Write-Step 'Installing Node.js LTS'; Install-WingetPackage 'OpenJS.NodeJS.LTS'; $nodeExe = Resolve-Executable 'node.exe' @("$env:ProgramFiles\nodejs\node.exe"); $npmExe = Resolve-Executable 'npm.cmd' @("$env:ProgramFiles\nodejs\npm.cmd") }
}

$runtimeReady = $false
if ($gitExe -and $nodeExe -and $npmExe) {
  Write-Step "Installing pinned BL-CF runtime $RuntimeRef"
  if (Test-Path $SourceDir) { Remove-Item $SourceDir -Recurse -Force }
  New-Item -ItemType Directory -Path $SourceDir -Force | Out-Null
  & $gitExe -C $SourceDir init | Out-Null
  & $gitExe -C $SourceDir remote add origin $RepoUrl
  & $gitExe -C $SourceDir fetch --depth 1 origin $RuntimeRef
  if ($LASTEXITCODE -ne 0) { throw 'Failed to fetch pinned BL-CF runtime' }
  & $gitExe -C $SourceDir checkout --detach FETCH_HEAD | Out-Null
  $runtimeDir = Join-Path $SourceDir 'runtime\federation'
  Push-Location $runtimeDir
  try {
    & $npmExe install --omit=dev --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'npm install failed for physical-node runtime' }
  } finally { Pop-Location }
  $runtimeReady = Test-Path (Join-Path $runtimeDir 'worker\server.mjs')
}
else {
  $warnings += 'Git and/or Node.js missing. Re-run bootstrap.ps1 -InstallDependencies to install the worker runtime.'
  Write-Warn 'Worker runtime not installed because Git/Node.js are unavailable.'
}

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
} finally {
  $env:BL_FEDERATION_SHARED_SECRET = $null
  $env:DEUS_NODE_HEARTBEAT_SECRET = $null
  Pop-Location
}
'@
$launcher | Set-Content -Path $LauncherPath -Encoding UTF8

if ($runtimeReady) {
  Write-Step 'Registering localhost-only physical worker startup task'
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  $action = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$LauncherPath`""
  $trigger = New-ScheduledTaskTrigger -AtStartup
  $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'DEUS BL-CF physical worker; localhost-only; node-scoped credentials; no control token.' | Out-Null
  Start-ScheduledTask -TaskName $TaskName
  Start-Sleep -Seconds 3
}

Write-Step 'Creating public-safe provider manifest candidate'
$manifest = [ordered]@{
  schema = 'BL_CF_PHYSICAL_NODE_CANDIDATE_V1'
  status = 'STAGED_LOCAL_ONLY'
  id = $nodeId
  kind = 'owner-device-windows'
  endpoint = @{
    transport = 'http-worker'
    url = "http://127.0.0.1:$WorkerPort"
    exposure = 'localhost-only'
    remoteRoutable = $false
  }
  capabilities = @('compute.echo', 'compute.sha256', 'json.project', 'text.stats')
  authorization = @{
    state = 'OWNER_DIRECTIVE_OBSERVED_LOCAL_CANDIDATE'
    consentRef = 'REQUIRES_BOUND_SIGNED_PROVIDER_GRANT_BEFORE_REMOTE_ROUTING'
    selfGrant = $false
  }
  dataPolicy = @{
    allowedDataClasses = @('public', 'internal')
    privateDataEgress = $false
    restrictedData = 'DENY_UNTIL_EXPLICIT_POLICY'
  }
  limits = @{
    maxConcurrency = [Math]::Max(1, [Math]::Min($WorkerMaxConcurrency, 4))
    maxTaskBytes = 262144
  }
  liveness = @{
    heartbeatRequiredBeforeRemoteRouting = $true
    heartbeatTtlMs = 60000
    heartbeatAuth = @{ mode = 'hmac-env'; secretEnv = 'DEUS_NODE_HEARTBEAT_SECRET' }
  }
  runtimeRef = $RuntimeRef
  secretsIncluded = $false
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $ManifestPath -Encoding UTF8

$localHealth = $null
$capabilities = $null
$listener = $null
if ($runtimeReady) {
  try { $localHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$WorkerPort/health" -Method Get -TimeoutSec 3 } catch { $warnings += "Local worker health check failed: $($_.Exception.Message)" }
  try { $capabilities = Invoke-RestMethod -Uri "http://127.0.0.1:$WorkerPort/v1/capabilities" -Method Get -TimeoutSec 3 } catch { $warnings += "Local capability check failed: $($_.Exception.Message)" }
  try {
    $listener = @(Get-NetTCPConnection -State Listen -LocalPort $WorkerPort -ErrorAction Stop | Select-Object LocalAddress, LocalPort, OwningProcess)
  } catch { $listener = @() }
}

$networkExposureSafe = $true
foreach ($entry in @($listener)) {
  if ($entry.LocalAddress -notin @('127.0.0.1', '::1')) { $networkExposureSafe = $false }
}
if (-not $networkExposureSafe) { throw 'Physical worker is listening beyond loopback; refusing readiness state' }

$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$report = [ordered]@{
  schema = 'DEUS_PHYSICAL_NODE_READINESS_V1'
  observedAt = (Get-Date).ToUniversalTime().ToString('o')
  nodeId = $nodeId
  machine = @{
    computerName = $env:COMPUTERNAME
    osCaption = $os.Caption
    osVersion = $os.Version
    osBuild = $os.BuildNumber
    cpuName = $cpu.Name
    logicalProcessors = $cpu.NumberOfLogicalProcessors
    totalMemoryGiB = [Math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
  }
  security = @{
    firewall = @(Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction, LogBlocked)
    defender = Get-DefenderSnapshot
    tpm = Get-TpmSummary
    secureBoot = Get-SecureBootSummary
    bitLocker = Get-BitLockerSummary
    remoteRegistry = (Get-CimInstance Win32_Service -Filter "Name='RemoteRegistry'" -ErrorAction SilentlyContinue | Select-Object StartMode, State)
  }
  runtime = @{
    pinnedRef = $RuntimeRef
    installed = $runtimeReady
    scheduledTask = [bool](Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)
    localHealth = $localHealth
    capabilities = $capabilities
    listeners = @($listener)
    localhostOnly = $networkExposureSafe
    remoteRoutable = $false
    remoteAuthorityGranted = $false
    firstAuthenticatedHeartbeatObserved = $false
  }
  warnings = @($warnings)
  secretsEmitted = $false
  controlTokenInstalled = $false
}
$report | ConvertTo-Json -Depth 12 | Set-Content -Path $ReportPath -Encoding UTF8

if ($runtimeReady -and $localHealth.ok -and $networkExposureSafe) {
  Write-Step "Physical node $nodeId is STAGED_LOCAL_ONLY and healthy on 127.0.0.1:$WorkerPort"
  Write-Host "Evidence: $ReportPath" -ForegroundColor Green
  Write-Host 'Remote routing remains disabled until secure transport + signed provider grant + authenticated heartbeat are bound.' -ForegroundColor Yellow
}
else {
  Write-Warn "Hardening applied, but worker is not locally healthy yet. Evidence: $ReportPath"
}
