param(
    [int]$LoadSeconds = 120
)

$ErrorActionPreference = "Stop"

Write-Host "Starting VMS chaos stack..."
docker compose up -d --build

Write-Host "Waiting for API health..."
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/health" | Out-Null
        break
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

.\scripts\smoke-test.ps1

Write-Host "Start another terminal with: .\scripts\api-load.ps1 -Seconds $LoadSeconds"
Write-Host "Then run one experiment, for example: .\scripts\chaos-experiments.ps1 -Experiment restart"
Write-Host "URLs:"
Write-Host "  API        http://localhost:8000"
Write-Host "  Prometheus http://localhost:9090"
Write-Host "  Grafana    http://localhost:3000 admin/admin"
Write-Host "  Portainer  http://localhost:9000"
