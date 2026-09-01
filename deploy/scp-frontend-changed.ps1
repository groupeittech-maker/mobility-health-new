# Envoie uniquement les fichiers frontend-simple modifiés ou non suivis (git), vers le VPS.
# Usage :
#   $env:H = "root@srv1324425.hstgr.cloud"
#   .\deploy\scp-frontend-changed.ps1
# Ou :
#   .\deploy\scp-frontend-changed.ps1 -Remote "root@ton-serveur.com" -RemoteBase "/var/www/mobility-health"

param(
    [string]$Remote = $env:H,
    [string]$RemoteBase = "/var/www/mobility-health"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

if (-not $Remote) {
    Write-Host "Définissez la cible SSH, ex. :" -ForegroundColor Yellow
    Write-Host '  $env:H = "root@srv1324425.hstgr.cloud"' -ForegroundColor White
    Write-Host "  ou passez -Remote 'user@hôte'" -ForegroundColor White
    exit 1
}

Set-Location $ProjectRoot
$RemoteBase = $RemoteBase.TrimEnd("/")

$files = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($line in (& git diff --name-only HEAD -- "frontend-simple/" 2>$null)) {
    if ($line) { [void]$files.Add($line.Trim()) }
}
foreach ($line in (& git ls-files --others --exclude-standard "frontend-simple/" 2>$null)) {
    if ($line) { [void]$files.Add($line.Trim()) }
}

$sorted = $files | Sort-Object
if (-not $sorted) {
    Write-Host "Aucun fichier modifié ou non suivi sous frontend-simple/ (git)." -ForegroundColor Yellow
    exit 0
}

Write-Host "Fichiers à copier ($($sorted.Count)) :" -ForegroundColor Cyan
$sorted | ForEach-Object { Write-Host "  $_" }

foreach ($rel in $sorted) {
    $localPath = Join-Path $ProjectRoot $rel
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        Write-Host "Ignoré (pas un fichier) : $rel" -ForegroundColor DarkYellow
        continue
    }
    $unixRel = $rel -replace "\\", "/"
    $parentUnix = Split-Path $unixRel -Parent
    if ($parentUnix) {
        $remoteDir = "$RemoteBase/$parentUnix" -replace "//+", "/"
        & ssh -o StrictHostKeyChecking=no $Remote "mkdir -p `"$remoteDir`""
    }
    $dest = "${Remote}:${RemoteBase}/${unixRel}"
    Write-Host "scp -> $dest" -ForegroundColor Gray
    & scp -o StrictHostKeyChecking=no $localPath $dest
}

Write-Host "Terminé." -ForegroundColor Green
