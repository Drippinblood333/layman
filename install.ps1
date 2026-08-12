param(
  [string]$Repository = 'Drippinblood333/layman',
  [string]$Version = 'latest',
  [ValidateSet('auto','plus','api')][string]$Mode = 'auto',
  [switch]$NoSetup,
  [switch]$NoPathUpdate
)
$ErrorActionPreference = 'Stop'
$assetName = 'layman-windows-x64.zip'
$releaseUrl = if ($Version -eq 'latest') {
  "https://api.github.com/repos/$Repository/releases/latest"
} else {
  "https://api.github.com/repos/$Repository/releases/tags/$Version"
}
$release = Invoke-RestMethod -Headers @{ 'User-Agent' = 'Layman-Installer' } -Uri $releaseUrl
$asset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
if (-not $asset) { throw "Release asset not found: $assetName" }
$checksumsAsset = $release.assets | Where-Object { $_.name -eq 'SHA256SUMS.txt' } | Select-Object -First 1
if (-not $checksumsAsset) { throw 'Release checksum manifest not found: SHA256SUMS.txt' }
$installRoot = Join-Path $env:LOCALAPPDATA 'Layman\bin'
$temporary = Join-Path ([IO.Path]::GetTempPath()) ("layman-" + [guid]::NewGuid())
New-Item -ItemType Directory -Force -Path $temporary,$installRoot | Out-Null
try {
  $archive = Join-Path $temporary $assetName
  $checksums = Join-Path $temporary 'SHA256SUMS.txt'
  Invoke-WebRequest -Headers @{ 'User-Agent' = 'Layman-Installer' } -Uri $asset.browser_download_url -OutFile $archive
  Invoke-WebRequest -Headers @{ 'User-Agent' = 'Layman-Installer' } -Uri $checksumsAsset.browser_download_url -OutFile $checksums
  $line = Get-Content -LiteralPath $checksums | Where-Object { $_ -match "^[A-Fa-f0-9]{64}\s+\*?$([regex]::Escape($assetName))$" } | Select-Object -First 1
  if (-not $line) { throw "Checksum entry not found for $assetName" }
  $expected = ($line -split '\s+')[0].ToUpperInvariant()
  $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToUpperInvariant()
  if ($actual -ne $expected) { throw "SHA-256 verification failed for $assetName" }
  Expand-Archive -LiteralPath $archive -DestinationPath $temporary -Force
  Copy-Item -LiteralPath (Join-Path $temporary 'layman.exe') -Destination (Join-Path $installRoot 'layman.exe') -Force
} finally {
  Remove-Item -LiteralPath $temporary -Recurse -Force -ErrorAction SilentlyContinue
}
if (-not $NoPathUpdate) {
  $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  $parts = @($userPath -split ';' | Where-Object { $_ })
  if ($parts -notcontains $installRoot) {
    [Environment]::SetEnvironmentVariable('Path', (($parts + $installRoot) -join ';'), 'User')
  }
  $env:Path = "$installRoot;$env:Path"
}
Write-Host "Installed Layman to $installRoot"
if (-not $NoSetup) { & (Join-Path $installRoot 'layman.exe') setup --mode $Mode }
Write-Host 'Restart Codex and open a new task so the updated plugin and PATH are loaded.'
