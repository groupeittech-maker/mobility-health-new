# PowerShell script to start PostgreSQL, Redis, and Minio services
# This script starts the required services for the backend using Docker Compose

Write-Host "Starting Mobility Health Dependencies (PostgreSQL, Redis, Minio)..." -ForegroundColor Green
Write-Host ""

# Check if Docker is installed
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not installed or not in PATH"
    }
    Write-Host "Docker found: $dockerVersion" -ForegroundColor Cyan
} catch {
    Write-Host "Error: Docker is not installed or not accessible." -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Docker daemon is running
try {
    docker info > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker daemon is not running. Attempting to start Docker Desktop..." -ForegroundColor Yellow
        Write-Host "Please start Docker Desktop manually if this doesn't work." -ForegroundColor Yellow
        Write-Host ""
        
        # Try to start Docker Desktop (Windows)
        $dockerDesktopPath = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $dockerDesktopPath) {
            Start-Process $dockerDesktopPath
            Write-Host "Docker Desktop starting... Please wait for it to fully start (usually 30-60 seconds)." -ForegroundColor Yellow
            Write-Host "Waiting 10 seconds for Docker to initialize..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
            
            # Wait for Docker to be ready (max 60 seconds)
            $maxAttempts = 12
            $attempt = 0
            while ($attempt -lt $maxAttempts) {
                docker info > $null 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Docker is now ready!" -ForegroundColor Green
                    break
                }
                $attempt++
                Write-Host "Waiting for Docker to start... ($attempt/$maxAttempts)" -ForegroundColor Yellow
                Start-Sleep -Seconds 5
            }
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Docker Desktop is taking longer than expected to start." -ForegroundColor Yellow
                Write-Host "Please ensure Docker Desktop is running and try again." -ForegroundColor Yellow
                exit 1
            }
        } else {
            Write-Host "Could not find Docker Desktop. Please start it manually." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Docker daemon is running." -ForegroundColor Green
    }
} catch {
    Write-Host "Error checking Docker daemon: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Navigate to project root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Check if docker-compose.yml exists
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "Error: docker-compose.yml not found in $projectRoot" -ForegroundColor Red
    exit 1
}

# Start the services (db, redis, minio only)
Write-Host "Starting PostgreSQL, Redis, and Minio services..." -ForegroundColor Yellow
Write-Host ""

docker-compose up -d db redis minio

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service Status:" -ForegroundColor Cyan
    docker-compose ps db redis minio
    Write-Host ""
    Write-Host "Service URLs:" -ForegroundColor Cyan
    Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor White
    Write-Host "  Redis:      localhost:6379" -ForegroundColor White
    Write-Host "  Minio API:  localhost:9000" -ForegroundColor White
    Write-Host "  Minio Console: http://localhost:9001" -ForegroundColor White
    Write-Host ""
    Write-Host "To view logs, run: docker-compose logs -f [service_name]" -ForegroundColor Yellow
    Write-Host "To stop services, run: docker-compose stop db redis minio" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Error: Failed to start services. Please check the errors above." -ForegroundColor Red
    exit 1
}

