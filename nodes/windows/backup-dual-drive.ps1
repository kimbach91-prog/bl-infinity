param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$SourceRemote,

  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$DestinationRemote,

  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string[]]$SourcePaths,

  [string]$DestinationRoot = 'DEUS-DUAL-BACKUP',
  [string]$StagingRoot = "$env:ProgramData\DEUSNode\backup-staging",
  [switch]$DryRun,
  [switch]$KeepStaging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $Name"
  }
}

function Assert-SafeRemoteName([string]$Name) {
  if ($Name -notmatch '^[A-Za-z0-9._-]+$') {
    throw "Unsafe rclone remote name: $Name"
  }
}

function Assert-SafeRemotePath([string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path)) { return }
  $normalized = $Path.Replace('\\', '/')
  $segments = $normalized.Split('/')
  if ($segments -contains '..') {
    throw "Remote path may not contain '..' segments: $Path"
  }
  if ($normalized -match '[\x00-\x1F]') {
    throw "Remote path contains control characters."
  }
}

function Get-PathLabel([string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path)) { return 'ROOT' }
  $label = $Path -replace '[:\\/*?"<>|]', '_'
  $label = $label -replace '\s+', '_'
  $label = $label.Trim('_')
  if ([string]::IsNullOrWhiteSpace($label)) { $label = 'ROOT' }
  if ($label.Length -gt 80) { $label = $label.Substring(0, 80) }
  return $label
}

function Invoke-Rclone([string[]]$Arguments) {
  Write-Host ("rclone " + (($Arguments | ForEach-Object {
    if ($_ -match '\s') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
  }) -join ' '))
  & rclone @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "rclone failed with exit code $LASTEXITCODE"
  }
}

Assert-Command 'rclone'
Assert-SafeRemoteName $SourceRemote
Assert-SafeRemoteName $DestinationRemote
Assert-SafeRemotePath $DestinationRoot

if ($SourceRemote -eq $DestinationRemote) {
  throw 'SourceRemote and DestinationRemote must be different rclone remotes.'
}

$remoteLines = & rclone listremotes
if ($LASTEXITCODE -ne 0) { throw 'Unable to list rclone remotes.' }
$knownRemotes = @($remoteLines | ForEach-Object { $_.Trim().TrimEnd(':') })
if ($knownRemotes -notcontains $SourceRemote) { throw "Source rclone remote not configured: $SourceRemote" }
if ($knownRemotes -notcontains $DestinationRemote) { throw "Destination rclone remote not configured: $DestinationRemote" }

if ([string]::IsNullOrWhiteSpace($env:ProgramData)) {
  throw 'ProgramData is unavailable; refusing to choose an implicit evidence location.'
}

$nodeRoot = Join-Path $env:ProgramData 'DEUSNode'
$evidenceRoot = Join-Path $nodeRoot 'evidence'
New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
New-Item -ItemType Directory -Force -Path $StagingRoot | Out-Null

$timestamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$runId = "dual-drive-$timestamp"
$runStageRoot = Join-Path $StagingRoot $runId
New-Item -ItemType Directory -Force -Path $runStageRoot | Out-Null
$logPath = Join-Path $evidenceRoot "$runId-rclone.log"
$combinedReport = Join-Path $evidenceRoot "$runId-check.txt"
$receiptPath = Join-Path $evidenceRoot "$runId-receipt.json"

$items = @()
$index = 0

foreach ($requestedPath in $SourcePaths) {
  $index += 1
  $sourcePath = if ($requestedPath -eq 'ROOT') { '' } else { $requestedPath.Trim('/') }
  Assert-SafeRemotePath $sourcePath

  $label = Get-PathLabel $sourcePath
  $slot = ('{0:D3}-{1}' -f $index, $label)
  $stageDir = Join-Path $runStageRoot $slot
  New-Item -ItemType Directory -Force -Path $stageDir | Out-Null

  $sourceSpec = ('{0}:{1}' -f $SourceRemote, $sourcePath)
  $destinationPath = ('{0}/{1}/{2}' -f $DestinationRoot.Trim('/'), $timestamp, $slot)
  $destinationSpec = ('{0}:{1}' -f $DestinationRemote, $destinationPath)

  $downloadArgs = @(
    'copy', $sourceSpec, $stageDir,
    '--create-empty-src-dirs',
    '--check-first',
    '--fast-list',
    '--retries', '3',
    '--low-level-retries', '10',
    '--drive-export-formats', 'docx,xlsx,pptx,svg,pdf',
    '--log-file', $logPath,
    '--log-level', 'INFO'
  )
  if ($DryRun) { $downloadArgs += '--dry-run' }
  Invoke-Rclone $downloadArgs

  if ($DryRun) {
    $items += [pscustomobject]@{
      source = $sourceSpec
      destination = $destinationSpec
      state = 'DRY_RUN_ONLY'
      materializedFiles = 0
      materializedBytes = 0
    }
    continue
  }

  $materializedFiles = @(Get-ChildItem -LiteralPath $stageDir -File -Recurse)
  if ($materializedFiles.Count -eq 0) {
    throw "No materialized files produced for $sourceSpec. Refusing to write an empty backup snapshot."
  }

  $manifestEntries = @()
  foreach ($file in $materializedFiles) {
    $relativePath = $file.FullName.Substring($stageDir.Length).TrimStart('\\', '/')
    $hash = Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256
    $manifestEntries += [pscustomobject]@{
      path = $relativePath
      bytes = [int64]$file.Length
      sha256 = $hash.Hash.ToLowerInvariant()
    }
  }

  $manifest = [pscustomobject]@{
    schema = 'bl-dual-drive-materialized-manifest/v0.1'
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
    sourceRemote = $SourceRemote
    sourcePath = $sourcePath
    exportFormats = @('docx', 'xlsx', 'pptx', 'svg', 'pdf')
    note = 'Google-native files are deliberately materialized to independent standard files before upload. No destination import/conversion is requested.'
    files = $manifestEntries
  }
  $manifestPath = Join-Path $stageDir '__BL_BACKUP_MANIFEST.json'
  $manifest | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $manifestPath -Encoding utf8

  $uploadArgs = @(
    'copy', $stageDir, $destinationSpec,
    '--immutable',
    '--create-empty-src-dirs',
    '--check-first',
    '--fast-list',
    '--retries', '3',
    '--low-level-retries', '10',
    '--log-file', $logPath,
    '--log-level', 'INFO'
  )
  Invoke-Rclone $uploadArgs

  $checkArgs = @(
    'check', $stageDir, $destinationSpec,
    '--download',
    '--one-way',
    '--combined', $combinedReport,
    '--retries', '3',
    '--low-level-retries', '10',
    '--log-file', $logPath,
    '--log-level', 'INFO'
  )
  Invoke-Rclone $checkArgs

  $allFiles = @(Get-ChildItem -LiteralPath $stageDir -File -Recurse)
  $totalBytes = [int64](($allFiles | Measure-Object -Property Length -Sum).Sum)
  $items += [pscustomobject]@{
    source = $sourceSpec
    destination = $destinationSpec
    state = 'VERIFIED_MATERIALIZED_SNAPSHOT'
    materializedFiles = $allFiles.Count
    materializedBytes = $totalBytes
    manifest = '__BL_BACKUP_MANIFEST.json'
  }
}

$receipt = [pscustomobject]@{
  schema = 'bl-dual-account-backup-receipt/v0.1'
  runId = $runId
  createdAtUtc = [DateTime]::UtcNow.ToString('o')
  sourceRemote = $SourceRemote
  destinationRemote = $DestinationRemote
  destinationRoot = $DestinationRoot
  deletionSemantics = 'NONE_REMOTE_COPY_ONLY'
  nativeGoogleFilePolicy = 'MATERIALIZE_TO_STANDARD_FORMATS_NO_REIMPORT'
  dryRun = [bool]$DryRun
  verified = (-not $DryRun)
  rcloneLog = $logPath
  combinedCheckReport = if ($DryRun) { $null } else { $combinedReport }
  items = $items
  truthBoundary = 'A successful receipt proves rclone copied and checked the configured remotes. It does not prove the human-readable remote aliases correspond to particular Google accounts unless those remotes were independently configured and verified by the owner.'
}
$receipt | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $receiptPath -Encoding utf8

if ((-not $DryRun) -and (-not $KeepStaging)) {
  Remove-Item -LiteralPath $runStageRoot -Recurse -Force
}

Write-Host "Backup receipt: $receiptPath"
if ($DryRun) {
  Write-Host 'DRY_RUN_ONLY — no destination snapshot or verification claim was created.'
} else {
  Write-Host 'VERIFIED_MATERIALIZED_SNAPSHOT — destination was checked by downloading and comparing content.'
}
