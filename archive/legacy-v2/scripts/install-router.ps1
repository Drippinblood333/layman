param([switch]$SkipDev)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Get-Command python -ErrorAction Stop
$Version = & $Python.Source -c "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(sys.version_info < (3,11))"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ is required; found $Version" }
$Venv = Join-Path $Root '.venv'
if (-not (Test-Path (Join-Path $Venv 'Scripts\python.exe'))) { & $Python.Source -m venv $Venv }
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
& $VenvPython -m pip install --upgrade pip
$Target = if ($SkipDev) { Join-Path $Root 'services\layman-router' } else { (Join-Path $Root 'services\layman-router') + '[dev]' }
& $VenvPython -m pip install -e $Target
& $VenvPython -m layman_router.cli doctor
Write-Host "`nInstalled Layman Router. Generate a dashboard token with:"
Write-Host "  .\.venv\Scripts\layman-router admin-token"
Write-Host "Then set OPENAI_API_KEY and LAYMAN_ROUTER_ADMIN_TOKEN before starting the service."
