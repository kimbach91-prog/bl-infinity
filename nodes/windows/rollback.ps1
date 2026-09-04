#requires -Version 5.1
#requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
  [switch]$PurgeNodeData
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = Join-Path $env:ProgramData 'DEUSNode'
$SnapshotPath = Join-Path $Root 'evidence\pre-change-snapshot.json'
$ConfigPath = Join-Path $Root 'config\node-config.json'
$TaskName = 'DEUS-PhysicalNode'
$errors = @()

function Try-Restore([string]$Label, [scriptblock]$Action) {
  try { & $Action; Write-Host "[ROLLBACK] restored $Label" -ForegroundColor Green }
  catch { $script:errors += "$Label: $($_.Exception.Message)"; Write-Warning "[ROLLBACK] $Label: $($_.Exception.Message)" }
}

function Restore-RegistryValue($State) {
  if (-not $State) { return }
  $path = [string]$State.path
  $name = [string]$State.name
  if ([bool]$State.valueExisted) {
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    New-ItemProperty -Path $path -Name $name -PropertyType DWord -Value ([int]$State.value) -Force | Out-Null
  }
  else {
    if (Test-Path $path) { Remove-ItemProperty -Path $path -Name $name -ErrorAction SilentlyContinue }
  }
}

if (-not (Test-Path $SnapshotPath)) { throw "Rollback snapshot not found: $SnapshotPath" }
$snapshot = Get-Content $SnapshotPath -Raw | ConvertFrom-Json

Write-Host '[ROLLBACK] stopping physical node worker' -ForegroundColor Cyan
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$port = 8790
if (Test-Path $ConfigPath) {
  try { $port = [int](Get-Content $ConfigPath -Raw | ConvertFrom-Json).workerPort } catch {}
}
try {
  foreach ($listener in @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
    if ($proc -and [string]$proc.CommandLine -like '*DEUSNode*runtime*federation*worker*server.mjs*') {
      Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
    }
  }
} catch {}

Write-Host '[ROLLBACK] restoring captured security state' -ForegroundColor Cyan
foreach ($profile in @($snapshot.firewall)) {
  $name = [string]$profile.Name
  Try-Restore "Firewall $name" {
    Set-NetFirewallProfile -Profile $name `
      -Enabled ([bool]$profile.Enabled) `
      -DefaultInboundAction ([string]$profile.DefaultInboundAction) `
      -DefaultOutboundAction ([string]$profile.DefaultOutboundAction) `
      -LogBlocked ([bool]$profile.LogBlocked) `
      -LogAllowed ([bool]$profile.LogAllowed) `
      -LogFileName ([string]$profile.LogFileName) `
      -LogMaxSizeKilobytes ([int]$profile.LogMaxSizeKilobytes)
  }
}

if ($snapshot.defender -and [bool]$snapshot.defender.available -and (Get-Command Set-MpPreference -ErrorAction SilentlyContinue)) {
  $p = $snapshot.defender.preference
  Try-Restore 'Defender real-time monitoring' { Set-MpPreference -DisableRealtimeMonitoring ([bool]$p.DisableRealtimeMonitoring) }
  Try-Restore 'Defender behavior monitoring' { Set-MpPreference -DisableBehaviorMonitoring ([bool]$p.DisableBehaviorMonitoring) }
  Try-Restore 'Defender script scanning' { Set-MpPreference -DisableScriptScanning ([bool]$p.DisableScriptScanning) }
  Try-Restore 'Defender IOAV protection' { Set-MpPreference -DisableIOAVProtection ([bool]$p.DisableIOAVProtection) }
  Try-Restore 'Defender block-at-first-seen' { Set-MpPreference -DisableBlockAtFirstSeen ([bool]$p.DisableBlockAtFirstSeen) }
  Try-Restore 'Defender PUA protection' { Set-MpPreference -PUAProtection ([int]$p.PUAProtection) }
  Try-Restore 'Defender network protection' { Set-MpPreference -EnableNetworkProtection ([int]$p.EnableNetworkProtection) }
  Try-Restore 'Controlled Folder Access' { Set-MpPreference -EnableControlledFolderAccess ([int]$p.EnableControlledFolderAccess) }
  Try-Restore 'Defender MAPS' { Set-MpPreference -MAPSReporting ([int]$p.MAPSReporting) }
  Try-Restore 'Defender sample submission' { Set-MpPreference -SubmitSamplesConsent ([int]$p.SubmitSamplesConsent) }
}

if ($snapshot.remoteRegistry) {
  Try-Restore 'Remote Registry startup' {
    $mode = [string]$snapshot.remoteRegistry.StartMode
    $startup = switch ($mode) { 'Auto' { 'Automatic' } 'Manual' { 'Manual' } default { 'Disabled' } }
    Set-Service -Name RemoteRegistry -StartupType $startup
    if ([string]$snapshot.remoteRegistry.State -eq 'Running') { Start-Service -Name RemoteRegistry }
    else { Stop-Service -Name RemoteRegistry -Force -ErrorAction SilentlyContinue }
  }
}

if ($snapshot.winrm) {
  Try-Restore 'WinRM startup' {
    $mode = [string]$snapshot.winrm.StartMode
    $startup = switch ($mode) { 'Auto' { 'Automatic' } 'Manual' { 'Manual' } default { 'Disabled' } }
    Set-Service -Name WinRM -StartupType $startup
    if ([string]$snapshot.winrm.State -eq 'Running') { Start-Service -Name WinRM }
    else { Stop-Service -Name WinRM -Force -ErrorAction SilentlyContinue }
  }
}

Try-Restore 'RDP policy' {
  Restore-RegistryValue $snapshot.rdp
  if ($snapshot.rdp.valueExisted -and [int]$snapshot.rdp.value -eq 0) {
    Enable-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue | Out-Null
  }
}
Try-Restore 'PowerShell Script Block Logging policy' { Restore-RegistryValue $snapshot.scriptBlockLogging }
Try-Restore 'AutoRun policy' { Restore-RegistryValue $snapshot.autorun }

if ([string]$snapshot.smb1 -eq 'Enabled' -and (Get-Command Enable-WindowsOptionalFeature -ErrorAction SilentlyContinue)) {
  Try-Restore 'SMB1 feature state' { Enable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -NoRestart | Out-Null }
}

$rollbackReceipt = [ordered]@{
  schema = 'DEUS_PHYSICAL_NODE_ROLLBACK_V1'
  observedAt = (Get-Date).ToUniversalTime().ToString('o')
  snapshotCreatedAt = $snapshot.createdAt
  taskRemoved = -not [bool](Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)
  purgeRequested = [bool]$PurgeNodeData
  errors = @($errors)
}
if (Test-Path (Join-Path $Root 'evidence')) {
  $rollbackReceipt | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $Root 'evidence\rollback-receipt.json') -Encoding UTF8
}

if ($PurgeNodeData) {
  if ($PSCmdlet.ShouldProcess($Root, 'Permanently delete DEUS node secrets, source, logs, configuration and evidence')) {
    Remove-Item $Root -Recurse -Force
    Write-Host '[ROLLBACK] node data purged' -ForegroundColor Yellow
  }
}
else {
  Write-Host "[ROLLBACK] node stopped and security settings restored. Evidence retained under $Root" -ForegroundColor Green
}

if ($errors.Count -gt 0) { exit 1 }
exit 0
