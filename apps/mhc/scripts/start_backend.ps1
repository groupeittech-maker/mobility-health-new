# PowerShell script to start the backend server
# This script starts the FastAPI backend server on port 8000

Write-Host "Starting Mobility Health Backend Server..." -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found. Creating from env.example..." -ForegroundColor Yellow
    if (Test-Path "env.example") {
        Copy-Item "env.example" ".env"
        Write-Host "Please update .env with your configuration before continuing." -ForegroundColor Yellow
    } else {
        Write-Host "Error: env.example file not found. Please create a .env file manually." -ForegroundColor Red
        exit 1
    }
}

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install/update dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt

# Reminder about database
Write-Host ""
Write-Host "Note: Make sure the database exists before starting the server." -ForegroundColor Yellow
Write-Host "If the database doesn't exist, run: .\scripts\create_database.ps1" -ForegroundColor Cyan
Write-Host ""

# Check if database is accessible (optional)
Write-Host "Starting backend server on http://localhost:8000" -ForegroundColor Green
Write-Host "API Documentation will be available at http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

