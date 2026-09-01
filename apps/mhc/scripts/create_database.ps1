# PowerShell script to create the PostgreSQL database if it doesn't exist

Write-Host "Creating PostgreSQL database if it doesn't exist..." -ForegroundColor Green

# Load environment variables from .env file
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Get database configuration from environment or use defaults
$dbName = $env:POSTGRES_DB
if (-not $dbName) {
    $dbName = "mobility_health"
}

$dbUser = $env:POSTGRES_USER
if (-not $dbUser) {
    $dbUser = "postgres"
}

$dbPassword = $env:POSTGRES_PASSWORD
if (-not $dbPassword) {
    $dbPassword = "postgres"
}

Write-Host "Database: $dbName" -ForegroundColor Cyan
Write-Host "User: $dbUser" -ForegroundColor Cyan

# Check if psql is available
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Host "Warning: psql command not found in PATH" -ForegroundColor Yellow
    Write-Host "Please install PostgreSQL client tools or use Docker Compose:" -ForegroundColor Yellow
    Write-Host "  docker-compose up -d db" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Alternatively, create the database manually:" -ForegroundColor Yellow
    Write-Host "  psql -U $dbUser -c `"CREATE DATABASE $dbName;`"" -ForegroundColor Cyan
    exit 1
}

# Try to create the database
Write-Host "Attempting to create database..." -ForegroundColor Yellow

# Set PGPASSWORD environment variable for psql
$env:PGPASSWORD = $dbPassword

# Check if database exists and create if it doesn't
$checkDb = psql -U $dbUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$dbName'" 2>&1

if ($LASTEXITCODE -eq 0 -and $checkDb -eq "1") {
    Write-Host "Database '$dbName' already exists." -ForegroundColor Green
} else {
    Write-Host "Creating database '$dbName'..." -ForegroundColor Yellow
    $createResult = psql -U $dbUser -d postgres -c "CREATE DATABASE $dbName;" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Database '$dbName' created successfully!" -ForegroundColor Green
    } else {
        Write-Host "Error creating database:" -ForegroundColor Red
        Write-Host $createResult -ForegroundColor Red
        Write-Host ""
        Write-Host "Please ensure PostgreSQL is running and credentials are correct." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Run migrations: alembic upgrade head" -ForegroundColor Cyan
Write-Host "  2. Start the backend: .\scripts\start_backend.ps1" -ForegroundColor Cyan


















