# Smart Traffic Management - Run on localhost
# Optionally set $env:GOOGLE_MAPS_API_KEY before running to supply a Google Maps API key.
Set-Location $PSScriptRoot
# load .env if present
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $name = $matches[1]; $value = $matches[2]
            Set-Item -Path env:$name -Value $value
        }
    }
}
$env:PYTHONUNBUFFERED = "1"
Write-Host "Starting Smart Traffic Management on http://localhost:8000" -ForegroundColor Green
Write-Host "Open this URL in your browser. Press CTRL+C to stop the server." -ForegroundColor Gray
Write-Host ""
& .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $env:PORT
if ($LASTEXITCODE -ne 0) {
    Write-Host "Server exited with an error. Press any key to close."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
