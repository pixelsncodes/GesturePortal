param([switch]$PreviewOnly, [string]$Config = '')
$ErrorActionPreference = 'Stop'
if (-not $Config) { $Config = Join-Path $PSScriptRoot 'config.json' }
$settings = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$backendUri = [Uri]$settings.comfy_url
if ($backendUri.Scheme -ne 'http' -or $backendUri.Host -notin @('127.0.0.1', 'localhost', '[::1]', '::1')) {
    throw 'comfy_url must be an HTTP loopback address; remote inference is disabled.'
}
$ownedBackend = $null
try {
    if (-not $PreviewOnly) {
        $ready = $false
        try {
            $health = Invoke-RestMethod -Uri ($settings.comfy_url + '/gesture_portal/health') -TimeoutSec 2
            $ready = $health.version -in @(1, 2, 3, 4, 5)
        } catch {}
        if ($ready -and $health.version -lt 5) {
            throw 'Close the old ComfyUI backend, then restart this launcher to load the new image editors.'
        }
        $engine = if ($settings.engine) { $settings.engine } else { 'diffusion' }
        if ($ready -and $health.engines -notcontains $engine) {
            throw 'Close the old ComfyUI backend, then restart this launcher to load the new anime models.'
        }
        if (-not $ready) {
            $port = ([Uri]$settings.comfy_url).Port
            Write-Host 'Starting the local AI backend...'
            $ownedBackend = & (Join-Path $PSScriptRoot 'Start-Comfy.ps1') -Port $port -Background
            # The viewer opens immediately and shows its animated loader while the
            # inference thread waits for the local backend and warms the workflow.
        }
    }
    Write-Host 'Opening the camera. Make two L shapes with your index fingers and thumbs.'
    & (Join-Path $PSScriptRoot 'Start-Portal.ps1') -PreviewOnly:$PreviewOnly -Config $Config
} finally {
    if ($null -ne $ownedBackend -and -not $ownedBackend.HasExited) {
        Stop-Process -Id $ownedBackend.Id
    }
}
