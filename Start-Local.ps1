param([string]$NodePath)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeDirectory = Join-Path $projectRoot '.local'
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$backendScript = Join-Path $projectRoot 'scripts\run_local.py'
$frontendDirectory = Join-Path $projectRoot 'frontend'
$viteScript = Join-Path $frontendDirectory 'node_modules\vite\bin\vite.js'
$statePath = Join-Path $runtimeDirectory 'dev-processes.json'

if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Python environment missing. Follow the local dependency setup in README.md.' }
if (!(Test-Path -LiteralPath $viteScript)) { throw 'Frontend dependencies missing. Run npm ci in frontend first.' }
if (!(Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) { throw 'Configuration missing. Run python scripts/setup_env.py first.' }
if (!$NodePath) {
    # Prefer the bundled LTS runtime when available; otherwise use Node on PATH.
    $bundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
    $NodePath = if (Test-Path -LiteralPath $bundledNode) { $bundledNode } else { (Get-Command node -ErrorAction Stop).Source }
}
$nodeVersion = [version]((& $NodePath --version).Trim().TrimStart('v'))
if ($nodeVersion.Major -lt 22 -or ($nodeVersion.Major -eq 22 -and $nodeVersion.Minor -lt 12)) {
    throw 'Install Node 22.12+ or Node 24 LTS, or pass -NodePath with its executable path.'
}

function Test-Endpoint([string]$Url) {
    try { return (Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 }
    catch { return $false }
}

$existing = @()
if (Test-Path -LiteralPath $statePath) {
    $records = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    foreach ($record in $records) {
        $running = Get-Process -Id $record.id -ErrorAction SilentlyContinue
        if ($running -and $running.StartTime.ToUniversalTime().ToString('o') -eq $record.startedAt) { $existing += $record }
    }
}
if ($existing.Count -gt 0) {
    if ((Test-Endpoint 'http://127.0.0.1:8000/api/health') -and (Test-Endpoint 'http://127.0.0.1:5173/api/health')) {
        Write-Output 'Already running: http://127.0.0.1:5173 (API docs: http://127.0.0.1:8000/docs)'
        exit 0
    }
    throw 'A previous local process is still running but not healthy. Run .\Stop-Local.ps1, then start again. Logs are in .local.'
}
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is already occupied by another process. Stop that service before starting this project."
    }
}
New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
$started = @()
try {
    $backend = Start-Process -FilePath $pythonPath -ArgumentList @('-u', ('"' + $backendScript + '"')) -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDirectory 'backend.stdout.log') -RedirectStandardError (Join-Path $runtimeDirectory 'backend.stderr.log') -PassThru
    $started += [pscustomobject]@{ name = 'backend'; id = $backend.Id; startedAt = $backend.StartTime.ToUniversalTime().ToString('o') }
    $frontend = Start-Process -FilePath $NodePath -ArgumentList @(('"' + $viteScript + '"')) -WorkingDirectory $frontendDirectory -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDirectory 'frontend.stdout.log') -RedirectStandardError (Join-Path $runtimeDirectory 'frontend.stderr.log') -PassThru
    $started += [pscustomobject]@{ name = 'frontend'; id = $frontend.Id; startedAt = $frontend.StartTime.ToUniversalTime().ToString('o') }
    ConvertTo-Json -InputObject @($started) | Set-Content -LiteralPath $statePath -Encoding UTF8
    $deadline = (Get-Date).AddSeconds(45)
    do {
        if ((Test-Endpoint 'http://127.0.0.1:8000/api/health') -and (Test-Endpoint 'http://127.0.0.1:5173/api/health')) {
            Write-Output 'Frontend: http://127.0.0.1:5173'
            Write-Output 'Backend:  http://127.0.0.1:8000/docs'
            Write-Output 'Both services are healthy. Login credentials are in .env. Logs are in .local.'
            exit 0
        }
        foreach ($record in $started) {
            if (!(Get-Process -Id $record.id -ErrorAction SilentlyContinue)) { throw "$($record.name) exited. Inspect .local/$($record.name).stderr.log." }
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw 'Startup timed out. Inspect backend/frontend logs in .local.'
} catch {
    foreach ($record in $started) {
        $running = Get-Process -Id $record.id -ErrorAction SilentlyContinue
        if ($running -and $running.StartTime.ToUniversalTime().ToString('o') -eq $record.startedAt) { Stop-Process -Id $record.id -ErrorAction SilentlyContinue }
    }
    throw
}
