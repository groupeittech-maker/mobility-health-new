# Quick Fix Script for Flutter Build Error
# This script addresses the "Accès refusé" and "Unable to determine engine version" errors

Write-Host "🔧 Quick Fix for Flutter Build Error" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "⚠️  Warning: Not running as administrator. Some operations may fail." -ForegroundColor Yellow
    Write-Host "   Consider running PowerShell as administrator for better results." -ForegroundColor Gray
    Write-Host ""
}

# Step 1: Stop all Java/Gradle/Dart processes
Write-Host "1️⃣  Stopping Java/Gradle/Dart processes..." -ForegroundColor Yellow
$processes = Get-Process -Name "java","gradle*","dart","flutter" -ErrorAction SilentlyContinue
if ($processes) {
    $processes | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ Stopped $($processes.Count) process(es)" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  No processes to stop" -ForegroundColor Gray
}
Start-Sleep -Seconds 3

# Step 2: Verify Flutter installation
Write-Host ""
Write-Host "2️⃣  Verifying Flutter installation..." -ForegroundColor Yellow
$flutterPath = "C:\src\flutter\bin\flutter.bat"
if (Test-Path $flutterPath) {
    Write-Host "   ✅ Flutter found at: $flutterPath" -ForegroundColor Green
    try {
        $version = & $flutterPath --version 2>&1 | Select-Object -First 1
        Write-Host "   ✅ Flutter version: $version" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ Cannot execute Flutter. Check permissions on C:\src\flutter" -ForegroundColor Red
        Write-Host "   💡 Try: icacls 'C:\src\flutter' /grant '${env:USERNAME}:(OI)(CI)F' /T" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ❌ Flutter not found at: $flutterPath" -ForegroundColor Red
    Write-Host "   💡 Check your Flutter installation" -ForegroundColor Yellow
    exit 1
}

# Step 3: Clean Flutter
Write-Host ""
Write-Host "3️⃣  Cleaning Flutter project..." -ForegroundColor Yellow
try {
    flutter clean
    Write-Host "   ✅ Flutter clean completed" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Flutter clean had issues: $_" -ForegroundColor Yellow
}

# Step 4: Clean Gradle caches
Write-Host ""
Write-Host "4️⃣  Cleaning Gradle caches..." -ForegroundColor Yellow
$gradleDirs = @(
    "android\.gradle",
    "android\app\build",
    "android\build",
    "$env:USERPROFILE\.gradle\caches"
)

foreach ($dir in $gradleDirs) {
    if (Test-Path $dir) {
        try {
            Remove-Item -Recurse -Force $dir -ErrorAction Stop
            Write-Host "   ✅ Removed: $dir" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️  Could not remove $dir (may be locked): $_" -ForegroundColor Yellow
        }
    }
}

# Step 5: Clean Dart tool cache
Write-Host ""
Write-Host "5️⃣  Cleaning Dart tool cache..." -ForegroundColor Yellow
if (Test-Path ".dart_tool") {
    try {
        Remove-Item -Recurse -Force .dart_tool -ErrorAction Stop
        Write-Host "   ✅ Removed .dart_tool" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️  Could not remove .dart_tool: $_" -ForegroundColor Yellow
    }
}

# Step 6: Get dependencies
Write-Host ""
Write-Host "6️⃣  Getting Flutter dependencies..." -ForegroundColor Yellow
try {
    flutter pub get
    Write-Host "   ✅ Dependencies retrieved" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to get dependencies: $_" -ForegroundColor Red
    exit 1
}

# Step 7: Verify Flutter Doctor
Write-Host ""
Write-Host "7️⃣  Running Flutter Doctor..." -ForegroundColor Yellow
flutter doctor

# Step 8: Try building
Write-Host ""
Write-Host "8️⃣  Attempting build..." -ForegroundColor Yellow
Write-Host "   This may take a few minutes..." -ForegroundColor Gray
Write-Host ""

# Try with --no-gradle-daemon first (more stable)
Write-Host "   Trying build without Gradle daemon..." -ForegroundColor Cyan
$buildResult = flutter build apk --debug --no-gradle-daemon 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run the app with:" -ForegroundColor Cyan
    Write-Host "  flutter run" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "❌ Build failed. Error details:" -ForegroundColor Red
    Write-Host $buildResult -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💡 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Try running with verbose output:" -ForegroundColor White
    Write-Host "      flutter run --verbose" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   2. Check if you need to restart your computer" -ForegroundColor White
    Write-Host "      (This releases all file locks)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   3. Verify Flutter installation:" -ForegroundColor White
    Write-Host "      flutter doctor -v" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   4. Check disk space:" -ForegroundColor White
    Write-Host "      Get-PSDrive C | Select-Object Used,Free" -ForegroundColor Gray
}








