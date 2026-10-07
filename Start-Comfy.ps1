param(
    [string]$ComfyRoot = 'D:\AI\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI',
    [string]$Python = 'D:\AI\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\python_embeded\python.exe',
    [int]$Port = 8188,
    [switch]$Background
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath (Join-Path $ComfyRoot 'main.py'))) { throw 'Set -ComfyRoot to your ComfyUI folder.' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'Set -Python to the Python executable used by ComfyUI.' }
# JSON quoted strings are valid YAML scalar values, including paths with spaces.
$basePath = ($PSScriptRoot.Replace('\', '/') | ConvertTo-Json -Compress)
$yaml = "gesture_portal:`n  base_path: $basePath`n  is_default: true`n  custom_nodes: custom_nodes`n  diffusion_models: models/diffusion_models`n  text_encoders: models/text_encoders`n  vae: models/vae`n"
$pathsFile = Join-Path $PSScriptRoot 'comfy_paths.yaml'
[System.IO.File]::WriteAllText($pathsFile, $yaml)
foreach ($folder in @('.comfy-user', '.comfy-input', '.comfy-output', '.comfy-temp')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot $folder) | Out-Null
}
$comfyArgs = @(
    (Join-Path $ComfyRoot 'main.py'), '--listen', '127.0.0.1', '--port', "$Port",
    '--extra-model-paths-config', $pathsFile, '--offline', '--cache-lru', '20',
    '--disable-all-custom-nodes', '--whitelist-custom-nodes', 'gesture_portal',
    '--user-directory', (Join-Path $PSScriptRoot '.comfy-user'),
    '--input-directory', (Join-Path $PSScriptRoot '.comfy-input'),
    '--output-directory', (Join-Path $PSScriptRoot '.comfy-output'),
    '--temp-directory', (Join-Path $PSScriptRoot '.comfy-temp'), '--disable-auto-launch',
    '--database-url', ('sqlite:///' + ($PSScriptRoot.Replace('\', '/') + '/.comfy-user/comfyui.db'))
)
Push-Location $PSScriptRoot
try {
    if ($Background) {
        $quotedArgs = $comfyArgs | ForEach-Object { '"' + $_ + '"' }
        Start-Process -FilePath $Python -ArgumentList $quotedArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $PSScriptRoot '.comfy-stdout.log') `
            -RedirectStandardError (Join-Path $PSScriptRoot '.comfy-stderr.log')
    } else {
        & $Python @comfyArgs
        if ($LASTEXITCODE -ne 0) { throw 'ComfyUI failed to start. Check the messages above.' }
    }
} finally { Pop-Location }
