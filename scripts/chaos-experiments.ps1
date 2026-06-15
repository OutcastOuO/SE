param(
    [ValidateSet("kill", "restart", "stop", "pause", "delay")]
    [string]$Experiment = "restart",
    [int]$Seconds = 30
)

$ErrorActionPreference = "Stop"
$BaseUrl = $env:BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://localhost:8000"
}

docker inspect vms-api | Out-Null

function Wait-ApiHealth {
    param([int]$Tries = 45)
    for ($i = 0; $i -lt $Tries; $i++) {
        try {
            Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 3 | Out-Null
            Write-Host "API health recovered."
            return
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "API health did not recover at $BaseUrl/health"
}

Write-Host "Running chaos experiment: $Experiment"

switch ($Experiment) {
    "kill" {
        Write-Host "Simulating app process crash by killing PID 1 inside vms-api..."
        docker exec vms-api sh -c "kill -9 1" | Out-Null
        Wait-ApiHealth
    }
    "restart" {
        docker restart vms-api
        Wait-ApiHealth
    }
    "stop" {
        docker stop vms-api
        Start-Sleep -Seconds $Seconds
        docker start vms-api
        Wait-ApiHealth
    }
    "pause" {
        docker pause vms-api
        Start-Sleep -Seconds $Seconds
        docker unpause vms-api
        Wait-ApiHealth
    }
    "delay" {
        Write-Host "Starting Pumba network delay profile for about 45 seconds."
        docker compose --profile chaos rm -f -s pumba-delay | Out-Null
        docker compose --profile chaos up --force-recreate --abort-on-container-exit --exit-code-from pumba-delay pumba-delay
        if ($LASTEXITCODE -ne 0) {
            throw "Pumba delay failed. If the log says client version is too old, recreate the service after pulling the updated compose file with DOCKER_API_VERSION=1.44."
        }
        docker compose --profile chaos rm -f -s pumba-delay | Out-Null
        Wait-ApiHealth
    }
}

Write-Host "Chaos experiment completed. Check Grafana and Prometheus for impact and recovery."
