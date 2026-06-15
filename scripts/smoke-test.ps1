param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $params = @{
        Method = $Method
        Uri = "$BaseUrl$Path"
        Headers = @{ "Content-Type" = "application/json" }
    }
    if ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }
    Invoke-RestMethod @params
}

Write-Host "Checking VMS API at $BaseUrl"

$health = Invoke-Json GET "/health"
Write-Host "Health: $($health.status), uptime=$($health.uptime_seconds)s"

$chaosHealth = Invoke-Json GET "/api/chaos/health"
Write-Host "Vehicles: $($chaosHealth.total_vehicles)"

$vehicles = Invoke-Json GET "/api/vehicles"
Write-Host "Vehicle API returned $($vehicles.Count) rows"

$metrics = Invoke-WebRequest -Uri "$BaseUrl/metrics" -UseBasicParsing
if ($metrics.Content -notmatch "vms_http_requests_total") {
    throw "Metrics endpoint did not expose vms_http_requests_total"
}
Write-Host "Metrics endpoint OK"

Write-Host "Smoke test passed"
