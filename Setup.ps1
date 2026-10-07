param(
    [string]$Python = 'C:\Users\pixel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [switch]$HandOnly,
    [switch]$PortraitOnly,
    [switch]$FluxOnly,
    [switch]$QwenResearch
)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        & $Python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'A Python 3.12 installation is required.' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & '.\.venv\Scripts\python.exe' download_models.py
    if ($LASTEXITCODE -ne 0) { throw 'Hand tracker download failed.' }
    if (-not $HandOnly -and -not $FluxOnly -and -not $QwenResearch) {
        & '.\.venv\Scripts\python.exe' download_portrait_models.py
        if ($LASTEXITCODE -ne 0) { throw 'Portrait download failed.' }
        & '.\.venv\Scripts\python.exe' download_face_assets.py
        if ($LASTEXITCODE -ne 0) { throw 'Face asset download failed.' }
    }
    if ($FluxOnly -or (-not $HandOnly -and -not $PortraitOnly -and -not $QwenResearch)) {
        & '.\.venv\Scripts\python.exe' download_edit_models.py flux
        if ($LASTEXITCODE -ne 0) { throw 'FLUX download failed.' }
    }
    if ($QwenResearch) {
        & '.\.venv\Scripts\python.exe' download_edit_models.py qwen --research-use
        if ($LASTEXITCODE -ne 0) { throw 'Qwen download failed.' }
    }
    Write-Host 'Setup complete. Double-click Start Portal.cmd.'
} finally { Pop-Location }
