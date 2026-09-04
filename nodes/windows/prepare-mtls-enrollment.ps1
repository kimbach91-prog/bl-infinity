#requires -Version 5.1
[CmdletBinding()]
param(
  [string]$NodeName = $env:COMPUTERNAME,
  [string]$OutputDirectory = "$env:ProgramData\DEUS\enrollment"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-Administrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this enrollment preparation in an elevated PowerShell session.'
  }
}

function Get-SafeDefenderState {
  try {
    $d = Get-MpComputerStatus
    return @{
      available = $true
      antimalware = [bool]$d.AMServiceEnabled -and [bool]$d.AntivirusEnabled -and [bool]$d.RealTimeProtectionEnabled
      antivirusEnabled = [bool]$d.AntivirusEnabled
      realtimeEnabled = [bool]$d.RealTimeProtectionEnabled
      signaturesAgeDays = [int]$d.AntivirusSignatureAge
    }
  } catch {
    return @{ available = $false; antimalware = $false; error = 'DEFENDER_STATUS_UNAVAILABLE' }
  }
}

function Get-SafeBitLockerState {
  try {
    $vol = Get-BitLockerVolume -MountPoint $env:SystemDrive
    $protected = ($vol.ProtectionStatus -eq 'On') -and ($vol.VolumeStatus -in @('FullyEncrypted','EncryptionInProgress'))
    return @{ available = $true; diskEncryption = [bool]$protected; protectionStatus = [string]$vol.ProtectionStatus; volumeStatus = [string]$vol.VolumeStatus }
  } catch {
    return @{ available = $false; diskEncryption = $false; error = 'BITLOCKER_STATUS_UNAVAILABLE' }
  }
}

function Get-SafeSecureBootState {
  try { return @{ available = $true; secureBoot = [bool](Confirm-SecureBootUEFI) } }
  catch { return @{ available = $false; secureBoot = $false; error = 'SECURE_BOOT_STATUS_UNAVAILABLE' } }
}

function Get-SafeFirewallState {
  try {
    $profiles = @(Get-NetFirewallProfile)
    $enabled = ($profiles.Count -gt 0) -and (($profiles | Where-Object { -not $_.Enabled }).Count -eq 0)
    return @{ available = $true; firewall = [bool]$enabled; profiles = @($profiles | ForEach-Object { @{ name = $_.Name; enabled = [bool]$_.Enabled } }) }
  } catch {
    return @{ available = $false; firewall = $false; error = 'FIREWALL_STATUS_UNAVAILABLE' }
  }
}

Assert-Administrator
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$tpm = Get-Tpm
$secureBoot = Get-SafeSecureBootState
$bitlocker = Get-SafeBitLockerState
$firewall = Get-SafeFirewallState
$defender = Get-SafeDefenderState

$posture = [ordered]@{
  collectedAt = (Get-Date).ToUniversalTime().ToString('o')
  nodeName = $NodeName
  os = [Environment]::OSVersion.VersionString
  tpmPresent = [bool]$tpm.TpmPresent
  tpmReady = [bool]$tpm.TpmReady
  secureBoot = [bool]$secureBoot.secureBoot
  diskEncryption = [bool]$bitlocker.diskEncryption
  firewall = [bool]$firewall.firewall
  antimalware = [bool]$defender.antimalware
  privateKeyNonExportable = $true
  keyProvider = 'Microsoft Platform Crypto Provider'
  keyAttestation = 'required'
  details = @{ secureBoot = $secureBoot; bitlocker = $bitlocker; firewall = $firewall; defender = $defender }
}

if (-not $posture.tpmPresent -or -not $posture.tpmReady) { throw 'TPM is not present/ready. Production node enrollment is fail-closed.' }
if (-not $posture.secureBoot) { throw 'Secure Boot is not verified. Production node enrollment is fail-closed.' }
if (-not $posture.diskEncryption) { throw 'System volume encryption is not verified. Production node enrollment is fail-closed.' }
if (-not $posture.firewall) { throw 'Windows Firewall is not enabled for every profile. Production node enrollment is fail-closed.' }
if (-not $posture.antimalware) { throw 'Antimalware realtime protection is not verified. Production node enrollment is fail-closed.' }

$sanitizedNodeName = ($NodeName -replace '[^A-Za-z0-9._-]', '-')
$inf = Join-Path $OutputDirectory 'node-request.inf'
$csr = Join-Path $OutputDirectory 'node-request.csr.pem'
$bundle = Join-Path $OutputDirectory 'node-enrollment-bundle.json'

$infText = @"
[Version]
Signature="$Windows NT$"

[NewRequest]
Subject = "CN=DEUS-NODE-$sanitizedNodeName"
KeyAlgorithm = RSA
KeyLength = 3072
HashAlgorithm = sha256
MachineKeySet = TRUE
Exportable = FALSE
ProviderName = "Microsoft Platform Crypto Provider"
RequestType = PKCS10
KeyAttestation = required
SMIME = FALSE

[Extensions]
2.5.29.17 = "{text}DNS=deus-node-$sanitizedNodeName"
"@
Set-Content -LiteralPath $inf -Value $infText -Encoding ascii

& certreq.exe -new $inf $csr | Out-Host
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $csr)) { throw "certreq failed with exit code $LASTEXITCODE" }

$csrText = Get-Content -LiteralPath $csr -Raw
$csrHash = (Get-FileHash -LiteralPath $csr -Algorithm SHA256).Hash.ToLowerInvariant()

$payload = [ordered]@{
  nodeName = $NodeName
  csrPem = $csrText
  csrSha256 = $csrHash
  posture = $posture
  grant = @{
    eligibleIdleComputeCap = 0.10
    localWorkloadPriority = $true
    dataPolicy = 'local'
    arbitraryInboundShell = $false
    revocable = $true
  }
}
$payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $bundle -Encoding utf8

Write-Host "DEUS node enrollment bundle created: $bundle"
Write-Host "CSR SHA-256: $csrHash"
Write-Host 'The private key remains non-exportable in the Windows/TPM provider. Do not copy private key material.'
Write-Host 'Submit the JSON bundle only through an authenticated AAL2 DEUS Human OS enrollment session.'
