# PowerShell script to start the frontend server
# This script starts a simple HTTP server for the frontend-simple directory on port 3000

Write-Host "Starting Mobility Health Frontend Server..." -ForegroundColor Green
Write-Host ""

# Navigate to project root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Check if frontend-simple directory exists
if (-not (Test-Path "frontend-simple")) {
    Write-Host "Error: frontend-simple directory not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Frontend directory: frontend-simple" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python is not installed or not in PATH"
    }
    Write-Host "Python found: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "Error: Python is not installed or not accessible." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Alternative: Use PHP server:" -ForegroundColor Yellow
    Write-Host "  cd frontend-simple" -ForegroundColor Cyan
    Write-Host "  php -S localhost:3000" -ForegroundColor Cyan
    exit 1
}

# Change to frontend-simple directory
$frontendDir = Join-Path $projectRoot "frontend-simple"
if (-not (Test-Path $frontendDir)) {
    Write-Host "Error: frontend-simple directory not found!" -ForegroundColor Red
    exit 1
}
Set-Location $frontendDir

# Check if port 3000 is already in use
$portInUse = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "Warning: Port 3000 is already in use!" -ForegroundColor Yellow
    Write-Host "Please stop the process using port 3000 or use a different port." -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Do you want to use port 8080 instead? (Y/N)"
    if ($response -eq "Y" -or $response -eq "y") {
        $port = 8080
    } else {
        Write-Host "Exiting..." -ForegroundColor Yellow
        exit 1
    }
} else {
    $port = 3000
}

Write-Host ""
Write-Host "Starting HTTP server on port $port..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Frontend URLs:" -ForegroundColor Cyan
Write-Host "  Homepage:      http://localhost:$port/index.html" -ForegroundColor White
Write-Host "  Login:         http://localhost:$port/login.html" -ForegroundColor White
Write-Host "  Admin Dashboard: http://localhost:$port/admin-dashboard.html" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the HTTP server in a new window
# Vérifier si server.py existe (serveur avec désactivation du cache)
$serverScript = Join-Path (Get-Location) "server.py"
if (Test-Path $serverScript) {
    Write-Host "Launching HTTP server with NO CACHE (development mode)..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$((Get-Location).Path)'; python server.py $port"
} else {
    Write-Host "Launching HTTP server (standard mode - cache may be active)..." -ForegroundColor Yellow
    Write-Host "Tip: Use Ctrl+F5 in browser to force reload without cache" -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$((Get-Location).Path)'; python -m http.server $port"
}

Write-Host ""
Write-Host "The server is starting in a new PowerShell window." -ForegroundColor Green
Write-Host "You can close this window, but keep the server window open." -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop the server, close the window or press Ctrl+C in the server window." -ForegroundColor Cyan
Write-Host ""

