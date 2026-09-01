# PowerShell script to initialize Alembic for the project

Write-Host "Initializing Alembic..." -ForegroundColor Green

# Check if alembic directory exists
if (-not (Test-Path "alembic")) {
    Write-Host "Creating alembic directory structure..." -ForegroundColor Yellow
    alembic init alembic
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found. Please create one from .env.example" -ForegroundColor Yellow
}

# Create initial migration
Write-Host "Creating initial migration..." -ForegroundColor Yellow
alembic revision --autogenerate -m "Initial migration"

Write-Host "Alembic initialized successfully!" -ForegroundColor Green
Write-Host "To apply migrations, run: alembic upgrade head" -ForegroundColor Cyan


















