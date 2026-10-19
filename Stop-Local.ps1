$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot '.local\dev-processes.json'
if (!(Test-Path -LiteralPath $statePath)) { Write-Output 'No managed local services found.'; exit 0 }
$records = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
foreach ($record in $records) {
    $running = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    # Verify process identity so an old PID can never stop an unrelated application.
    if ($running -and $running.StartTime.ToUniversalTime().ToString('o') -eq $record.startedAt) {
        Stop-Process -Id $record.id
        Write-Output "Stopped $($record.name)."
    }
}
Set-Content -LiteralPath $statePath -Value '[]' -Encoding UTF8
