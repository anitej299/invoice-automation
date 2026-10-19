$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and wait for its Linux engine to be running, then retry.' }
    # Both modes use port 8000; stop only processes recorded by this project.
    & (Join-Path $PSScriptRoot 'Stop-Local.ps1')
    docker compose up --build -d --wait --wait-timeout 120
    if ($LASTEXITCODE -ne 0) { throw 'Docker startup failed. Run docker compose logs --tail 80 backend frontend.' }
    Write-Output 'Frontend: http://localhost:8080'
    Write-Output 'Backend:  http://localhost:8000/docs'
    Write-Output 'n8n:      http://localhost:5678'
} finally { Pop-Location }
