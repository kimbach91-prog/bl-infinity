#requires -Version 5.1
[CmdletBinding()]
param(
  [string]$RuntimeUrl = 'https://deus-railway-controller-production.up.railway.app'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ExpectedServerCommit = '9cf798db6a3df63e961a0d25fa92350c85650e91'
$ExpectedSchema = 'deus-workstation-benchmark/1'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RecoveryStarted = (Get-Date).ToUniversalTime().ToString('o')

function Step([string]$m) { Write-Host "[DEUS-RECOVERY] $m" -ForegroundColor Cyan }
function Pass([string]$m) { Write-Host "[PASS] $m" -ForegroundColor Green }
function Fail([string]$m) { Write-Host "[FAIL] $m" -ForegroundColor Red; throw $m }

function UniqueExistingDirs([string[]]$dirs) {
  $seen = @{}
  $out = New-Object System.Collections.Generic.List[string]
  foreach ($d in $dirs) {
    if (-not $d) { continue }
    try { $full = [IO.Path]::GetFullPath($d) } catch { continue }
    if ((Test-Path -LiteralPath $full -PathType Container) -and -not $seen.ContainsKey($full.ToLowerInvariant())) {
      $seen[$full.ToLowerInvariant()] = $true
      [void]$out.Add($full)
    }
  }
  return $out
}

function Find-BenchmarkReport([string[]]$roots) {
  $hits = New-Object System.Collections.Generic.List[IO.FileInfo]
  foreach ($root in $roots) {
    try {
      Get-ChildItem -LiteralPath $root -Recurse -File -Filter 'benchmark-1t-latest.json' -ErrorAction SilentlyContinue |
        ForEach-Object { [void]$hits.Add($_) }
    } catch {}
  }
  if ($hits.Count -eq 0) { return $null }
  return $hits | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
}

function Get-JsonPropRecursive($obj, [string[]]$names) {
  if ($null -eq $obj) { return $null }
  if ($obj -is [System.Collections.IDictionary]) {
    foreach ($name in $names) {
      if ($obj.Contains($name) -and $obj[$name]) { return [string]$obj[$name] }
    }
    foreach ($k in $obj.Keys) {
      $v = Get-JsonPropRecursive $obj[$k] $names
      if ($v) { return $v }
    }
    return $null
  }
  if ($obj -is [System.Collections.IEnumerable] -and -not ($obj -is [string])) {
    foreach ($item in $obj) {
      $v = Get-JsonPropRecursive $item $names
      if ($v) { return $v }
    }
    return $null
  }
  $props = $obj.PSObject.Properties
  foreach ($name in $names) {
    $p = $props[$name]
    if ($p -and $p.Value) { return [string]$p.Value }
  }
  foreach ($p in $props) {
    $v = Get-JsonPropRecursive $p.Value $names
    if ($v) { return $v }
  }
  return $null
}

function Read-DpapiString([string]$path) {
  Add-Type -AssemblyName System.Security
  $cipher = [IO.File]::ReadAllBytes($path)
  $plain = $null
  try {
    foreach ($scope in @(
      [Security.Cryptography.DataProtectionScope]::CurrentUser,
      [Security.Cryptography.DataProtectionScope]::LocalMachine
    )) {
      try {
        $plain = [Security.Cryptography.ProtectedData]::Unprotect($cipher, $null, $scope)
        if ($plain) {
          $s = [Text.Encoding]::UTF8.GetString($plain).Trim()
          if ($s.Length -ge 24) { return $s }
          [Array]::Clear($plain,0,$plain.Length); $plain = $null
        }
      } catch {}
    }
    return $null
  } finally {
    if ($plain) { [Array]::Clear($plain,0,$plain.Length) }
  }
}

function Resolve-RuntimeToken([string[]]$packageRoots) {
  $envNames = @(
    'DEUS_WORKSTATION_001_TOKEN',
    'DEUS_WORKSTATION_RUNTIME_TOKEN',
    'DEUS_SCOPED_RUNTIME_TOKEN',
    'DEUS_RUNTIME_TOKEN'
  )
  foreach ($n in $envNames) {
    $v = [Environment]::GetEnvironmentVariable($n, 'Process')
    if (-not $v) { $v = [Environment]::GetEnvironmentVariable($n, 'User') }
    if (-not $v) { $v = [Environment]::GetEnvironmentVariable($n, 'Machine') }
    if ($v -and $v.Length -ge 24) { return @{ Token=$v; Source="env:$n" } }
  }

  $candidateDirs = New-Object System.Collections.Generic.List[string]
  foreach ($r in $packageRoots) {
    foreach ($d in @($r, (Join-Path $r 'config'), (Join-Path $r 'state'), (Join-Path $r 'secrets'))) {
      if (Test-Path -LiteralPath $d -PathType Container) { [void]$candidateDirs.Add($d) }
    }
  }
  $pd = Join-Path $env:ProgramData 'DEUSNode'
  foreach ($d in @((Join-Path $pd 'config'), (Join-Path $pd 'state'), (Join-Path $pd 'secrets'))) {
    if (Test-Path -LiteralPath $d -PathType Container) { [void]$candidateDirs.Add($d) }
  }

  $nameRx = '(?i)(workstation.*token|runtime.*token|scoped.*token|token.*workstation|token.*runtime|token.*scoped)'
  foreach ($dir in $candidateDirs) {
    try {
      Get-ChildItem -LiteralPath $dir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match $nameRx -and $_.Length -le 65536 } |
        Sort-Object LastWriteTimeUtc -Descending |
        ForEach-Object {
          if ($_.Extension -ieq '.dpapi') {
            $s = Read-DpapiString $_.FullName
            if ($s) { return @{ Token=$s; Source="dpapi:$($_.FullName)" } }
          } else {
            try {
              $s = (Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop).Trim()
              if ($s.Length -ge 24 -and $s -notmatch '[\r\n]') {
                return @{ Token=$s; Source="file:$($_.FullName)" }
              }
            } catch {}
          }
        }
    } catch {}
  }

  $jsonNames = @('workstationToken','workstation_token','runtimeToken','scopedRuntimeToken','runtime_token','scoped_runtime_token','deusRuntimeToken')
  $envRefNames = @('runtimeTokenEnv','scopedRuntimeTokenEnv','runtime_token_env','scoped_runtime_token_env')
  $pathRefNames = @('runtimeTokenPath','scopedRuntimeTokenPath','runtime_token_path','scoped_runtime_token_path')

  foreach ($dir in $candidateDirs) {
    try {
      Get-ChildItem -LiteralPath $dir -File -Filter '*.json' -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -le 262144 } |
        Sort-Object LastWriteTimeUtc -Descending |
        ForEach-Object {
          try {
            $j = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
            $direct = Get-JsonPropRecursive $j $jsonNames
            if ($direct -and $direct.Length -ge 24) { return @{ Token=$direct; Source="json:$($_.FullName)" } }

            $envRef = Get-JsonPropRecursive $j $envRefNames
            if ($envRef) {
              $ev = [Environment]::GetEnvironmentVariable($envRef,'Process')
              if (-not $ev) { $ev = [Environment]::GetEnvironmentVariable($envRef,'User') }
              if (-not $ev) { $ev = [Environment]::GetEnvironmentVariable($envRef,'Machine') }
              if ($ev -and $ev.Length -ge 24) { return @{ Token=$ev; Source="json-envref:$($_.FullName)" } }
            }

            $pathRef = Get-JsonPropRecursive $j $pathRefNames
            if ($pathRef) {
              $p = $pathRef
              if (-not [IO.Path]::IsPathRooted($p)) { $p = Join-Path $_.DirectoryName $p }
              if (Test-Path -LiteralPath $p -PathType Leaf) {
                if ([IO.Path]::GetExtension($p) -ieq '.dpapi') {
                  $s = Read-DpapiString $p
                  if ($s) { return @{ Token=$s; Source="json-dpapi-ref:$($_.FullName)" } }
                } else {
                  $s = (Get-Content -LiteralPath $p -Raw).Trim()
                  if ($s.Length -ge 24 -and $s -notmatch '[\r\n]') {
                    return @{ Token=$s; Source="json-file-ref:$($_.FullName)" }
                  }
                }
              }
            }
          } catch {}
        }
    } catch {}
  }

  return $null
}

function Assert-NoSensitiveKeys($obj, [string]$path='') {
  if ($null -eq $obj) { return }
  if ($obj -is [System.Collections.IEnumerable] -and -not ($obj -is [string]) -and -not ($obj -is [pscustomobject])) {
    $i=0
    foreach ($item in $obj) { Assert-NoSensitiveKeys $item "$path[$i]"; $i++ }
    return
  }
  foreach ($p in $obj.PSObject.Properties) {
    $name = [string]$p.Name
    $next = if ($path) { "$path.$name" } else { $name }
    if ($name -match '(?i)(token|secret|password|api[_-]?key|credential|private[_-]?key)') {
      throw "Sensitive field present in benchmark report: $next"
    }
    if ($p.Value -is [pscustomobject] -or ($p.Value -is [System.Collections.IEnumerable] -and -not ($p.Value -is [string]))) {
      Assert-NoSensitiveKeys $p.Value $next
    }
  }
}

Step 'Locating existing 1T benchmark report; benchmark will NOT be rerun.'
$download = Join-Path $env:USERPROFILE 'Downloads'
$downloadPackages = @()
if (Test-Path -LiteralPath $download -PathType Container) {
  $downloadPackages = @(Get-ChildItem -LiteralPath $download -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like 'DEUS_V5_WORKSTATION_NODE*' } |
    Select-Object -ExpandProperty FullName)
}
$roots = UniqueExistingDirs @(
  $ScriptDir,
  (Split-Path $ScriptDir -Parent),
  (Get-Location).Path,
  $downloadPackages
)
$reportFile = Find-BenchmarkReport $roots
if (-not $reportFile) {
  Fail 'benchmark-1t-latest.json not found in the recovery folder/current package/DEUS workstation package under Downloads. Recovery refuses to rerun the benchmark automatically.'
}
Pass "Found benchmark report: $($reportFile.FullName)"

$raw = Get-Content -LiteralPath $reportFile.FullName -Raw
$report = $raw | ConvertFrom-Json
if ([string]$report.schema -ne $ExpectedSchema) { Fail "Unexpected report schema: $($report.schema)" }
if (-not $report.workstationId) { Fail 'workstationId missing from report.' }
if (-not $report.receiptDigest) { Fail 'receiptDigest missing from report.' }
Assert-NoSensitiveKeys $report
Pass "Report schema/workstationId/receiptDigest present."

Step 'Checking DEUS Runtime health.'
$RuntimeUrl = $RuntimeUrl.TrimEnd('/')
$health = Invoke-RestMethod -Method Get -Uri "$RuntimeUrl/health" -TimeoutSec 20
if (-not $health.ok) { Fail 'DEUS Runtime health did not return ok=true.' }
if ([string]$health.workstationReceiptApi -ne $ExpectedSchema) { Fail "Runtime health marker mismatch: workstationReceiptApi=$($health.workstationReceiptApi) expected=$ExpectedSchema" }
Pass "Runtime healthy and workstation receipt API marker verified: $RuntimeUrl"

Step 'Resolving scoped runtime token without printing it.'
$tokenInfo = Resolve-RuntimeToken $roots
if ($tokenInfo -is [Array]) { $tokenInfo = @($tokenInfo | Where-Object { $_ -and $_.Token }) | Select-Object -First 1 }
if (-not $tokenInfo) {
  Fail 'Scoped runtime token was not found in DEUS runtime environment/package/DEUSNode scoped-token files. Do not paste credentials into chat. Keep the existing workstation node running and place the scoped runtime token only in a local DEUS_*_RUNTIME_TOKEN environment variable or package token file, then rerun this recovery.'
}
$token = [string]$tokenInfo.Token
Pass "Scoped token resolved from protected/local source (value hidden)."

$headers = @{ Authorization = "Bearer $token" }
try {
  Step 'Submitting existing benchmark receipt to /workstations/report.'
  $post = Invoke-RestMethod -Method Post -Uri "$RuntimeUrl/workstations/report" -Headers $headers -ContentType 'application/json' -Body $raw -TimeoutSec 60
  if (-not $post.accepted) { Fail 'Runtime did not return accepted=true.' }
  Pass "Receipt accepted; audit seq=$($post.record.seq)."

  Step 'Reading back /workstations/latest and verifying exact receiptDigest.'
  $latest = Invoke-RestMethod -Method Get -Uri "$RuntimeUrl/workstations/latest" -Headers $headers -TimeoutSec 30
  if (-not $latest.record) { Fail 'No workstation.report record returned by runtime.' }
  if ([string]$latest.record.type -ne 'workstation.report') { Fail "Unexpected audit record type: $($latest.record.type)" }
  $remote = $latest.record.data
  if (-not $remote) { Fail 'Audit record has no data payload.' }

  $localDigest = [string]$report.receiptDigest
  $remoteDigest = [string]$remote.receiptDigest
  if ($remoteDigest -ne $localDigest) {
    Fail "receiptDigest mismatch. local=$localDigest remote=$remoteDigest"
  }
  if ([string]$remote.workstationId -ne [string]$report.workstationId) {
    Fail "workstationId mismatch. local=$($report.workstationId) remote=$($remote.workstationId)"
  }

  $outPath = Join-Path $reportFile.DirectoryName 'benchmark-1t-recovery-receipt-1.4.1.json'
  $receipt = [ordered]@{
    schema = 'deus-workstation-receipt-recovery/1'
    recoveredAt = (Get-Date).ToUniversalTime().ToString('o')
    recoveryStartedAt = $RecoveryStarted
    verdict = 'PASS_RECEIPT_DIGEST_READBACK'
    workstationId = [string]$report.workstationId
    receiptDigest = $localDigest
    reportPath = $reportFile.FullName
    runtime = $RuntimeUrl
    serverCommit = $ExpectedServerCommit
    postRecord = @{
      seq = $post.record.seq
      ts = $post.record.ts
      hash = $post.record.hash
    }
    readbackRecord = @{
      seq = $latest.record.seq
      ts = $latest.record.ts
      hash = $latest.record.hash
      type = $latest.record.type
    }
    tokenSourceClass = ([string]$tokenInfo.Source -split ':',2)[0]
    secretsIncluded = $false
  }
  $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8

  Write-Host ''
  Write-Host '============================================================' -ForegroundColor Green
  Write-Host ' DEUS 1T WORKSTATION RECEIPT RECOVERY 1.4.1 - VERIFIED' -ForegroundColor Green
  Write-Host '============================================================' -ForegroundColor Green
  Write-Host "Workstation:  $($report.workstationId)"
  Write-Host "ReceiptDigest: $localDigest"
  Write-Host "Audit seq:     $($latest.record.seq)"
  Write-Host "Audit hash:    $($latest.record.hash)"
  Write-Host "Receipt file:  $outPath"
  Write-Host ''
  Write-Host '[DEUS] Existing benchmark summary:' -ForegroundColor Cyan
  foreach ($name in @('system','resources','benchmark','supercell')) {
    $p = $report.PSObject.Properties[$name]
    if ($p) {
      Write-Host ("--- {0} ---" -f $name)
      $p.Value | ConvertTo-Json -Depth 12
    }
  }
  Write-Host ''
  Pass 'REMOTE RECEIPT + DIGEST READBACK VERIFIED. Physical promotion may now use only measured workstation scope.'
}
finally {
  $token = $null
  $headers = $null
}
