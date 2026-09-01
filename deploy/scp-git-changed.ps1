# Envoie vers le VPS uniquement les fichiers suivis par Git modifiés / ajoutés (staging)
# et les non suivis pertinents, par rapport à HEAD — ou uniquement le dernier commit.
#
# Usage (depuis n'importe où, le script se place à la racine du projet) :
#   $env:H = "root@srv1324425.hstgr.cloud"
#   .\deploy\scp-git-changed.ps1
#   .\deploy\scp-git-changed.ps1 -DryRun
#   .\deploy\scp-git-changed.ps1 -LastCommitOnly
#
# Chemins serveur : deploy/SCP-DEPLOY-CHEMINS.md

param(
    [string]$Remote = $env:H,
    [string]$RemoteFrontend = "/var/www/mobility-health",
    [string]$RemoteBackend = "/var/www/Mobility_Health/Mobility_Health",
    [switch]$DryRun,
    [switch]$LastCommitOnly
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

if (-not $Remote) {
    Write-Host "Définissez la cible SSH, ex. :" -ForegroundColor Yellow
    Write-Host '  $env:H = "root@srv1324425.hstgr.cloud"' -ForegroundColor White
    Write-Host "  ou -Remote 'user@hôte'" -ForegroundColor White
    exit 1
}

Set-Location $ProjectRoot
$RemoteFrontend = $RemoteFrontend.TrimEnd("/")
$RemoteBackend = $RemoteBackend.TrimEnd("/")

$backendRootFiles = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($n in @(
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "Dockerfile",
        "Dockerfile.prod",
        "requirements.txt",
        "alembic.ini"
    )) {
    [void]$backendRootFiles.Add($n)
}

function Test-DeployablePath {
    param([string]$rel)
    if (-not $rel) { return $false }
    $n = $rel -replace "\\", "/"
    if ($n -match "^(frontend-simple|app|alembic)/") { return $true }
    foreach ($f in $backendRootFiles) {
        if ($n -eq $f) { return $true }
    }
    return $false
}

function Get-RemoteBaseForPath {
    param([string]$relUnix)
    foreach ($f in $backendRootFiles) {
        if ($relUnix -eq $f) { return $RemoteBackend }
    }
    if ($relUnix.StartsWith("frontend-simple/")) { return $RemoteFrontend }
    if ($relUnix.StartsWith("app/") -or $relUnix.StartsWith("alembic/")) { return $RemoteBackend }
    return $null
}

$files = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

if ($LastCommitOnly) {
    foreach ($line in (& git diff --name-only HEAD~1 HEAD 2>$null)) {
        if ($line) { [void]$files.Add(($line.Trim() -replace "\\", "/")) }
    }
}
else {
    foreach ($line in (& git diff --name-only HEAD 2>$null)) {
        if ($line) { [void]$files.Add(($line.Trim() -replace "\\", "/")) }
    }
    foreach ($line in (& git ls-files --others --exclude-standard 2>$null)) {
        if ($line) { [void]$files.Add(($line.Trim() -replace "\\", "/")) }
    }
}

$toCopy = [System.Collections.Generic.List[string]]::new()
foreach ($rel in ($files | Sort-Object)) {
    if (-not (Test-DeployablePath $rel)) { continue }
    $localPath = Join-Path $ProjectRoot $rel
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        continue
    }
    $toCopy.Add($rel)
}

if ($toCopy.Count -eq 0) {
    Write-Host "Aucun fichier déployable modifié (frontend-simple/, app/, alembic/, docker-compose, etc.)." -ForegroundColor Yellow
    Write-Host "Astuce : .\deploy\scp-frontend-changed.ps1 pour tout le non suivi sous frontend-simple/." -ForegroundColor DarkGray
    exit 0
}

Write-Host "Cible : ${Remote}" -ForegroundColor Cyan
Write-Host "Fichiers ($($toCopy.Count)) :" -ForegroundColor Cyan
$toCopy | ForEach-Object { Write-Host "  $_" }
Write-Host ""

foreach ($rel in $toCopy) {
    $unixRel = $rel -replace "\\", "/"
    $base = Get-RemoteBaseForPath $unixRel
    if (-not $base) { continue }

    $localPath = Join-Path $ProjectRoot $rel
    $parentUnix = Split-Path $unixRel -Parent
    $remoteDir = if ($parentUnix) { "$base/$parentUnix" -replace "//+", "/" } else { $base }

    if ($DryRun) {
        Write-Host "[DryRun] ssh mkdir -p $remoteDir" -ForegroundColor DarkGray
        Write-Host "[DryRun] scp $localPath ${Remote}:$base/$unixRel" -ForegroundColor DarkGray
        continue
    }

    if ($parentUnix) {
        & ssh -o StrictHostKeyChecking=no $Remote "mkdir -p `"$remoteDir`""
    }
    $dest = "${Remote}:${base}/${unixRel}"
    Write-Host "scp -> $dest" -ForegroundColor Gray
    & scp -o StrictHostKeyChecking=no $localPath $dest
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Échec SCP : $rel" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "Terminé." -ForegroundColor Green
if (-not $DryRun) {
    Write-Host "Backend : rebuild Docker / alembic si des fichiers sous app/, alembic/ ou docker-compose ont changé." -ForegroundColor DarkYellow
}
