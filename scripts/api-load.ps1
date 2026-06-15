param(
    [string]$BaseUrl = "http://localhost:8000",
    [int]$Seconds = 90,
    [int]$DelayMs = 300
)

$ErrorActionPreference = "Stop"
$endAt = (Get-Date).AddSeconds($Seconds)
$ok = 0
$fail = 0

Write-Host "Sending API traffic to $BaseUrl for $Seconds seconds..."

while ((Get-Date) -lt $endAt) {
    try {
        Invoke-RestMethod -Method GET -Uri "$BaseUrl/api/vehicles" | Out-Null
        Invoke-RestMethod -Method GET -Uri "$BaseUrl/api/chaos/health" | Out-Null
        $ok += 2
    }
    catch {
        $fail += 1
        Write-Host "Request failed: $($_.Exception.Message)"
    }
    Start-Sleep -Milliseconds $DelayMs
}

Write-Host "Load finished. ok=$ok fail=$fail"
