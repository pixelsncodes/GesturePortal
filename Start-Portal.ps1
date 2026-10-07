param([switch]$PreviewOnly, [string]$Video = '', [string]$Config = '')
$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run Setup.ps1 first.' }
$portalArgs = @((Join-Path $PSScriptRoot 'run_portal.py'))
if ($PreviewOnly) { $portalArgs += '--preview-only' }
if ($Video) { $portalArgs += @('--video', $Video) }
if ($Config) { $portalArgs += @('--config', $Config) }
& $pythonPath @portalArgs
if ($LASTEXITCODE -ne 0) { throw 'Portal stopped. Check the messages above.' }
