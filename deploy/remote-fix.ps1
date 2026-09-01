# Connexion SSH au VPS et execution du correctif production.
# Usage :
#   .\deploy\remote-fix.ps1
#   .\deploy\remote-fix.ps1 -SshUser deployer
#
# Ou via variable d'environnement :
#   $env:MH_SSH_PASSWORD = "..."
#   .\deploy\remote-fix.ps1

param(
    [string]$SshHost = "srv1324425.hstgr.cloud",
    [string]$SshUser = "root"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$password = $env:MH_SSH_PASSWORD
if (-not $password) {
    $secure = Read-Host "Mot de passe SSH pour ${SshUser}@${SshHost}" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $password = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

if (-not $password) {
    Write-Error "Mot de passe requis."
}

# Test rapide OpenSSH (si une cle est deja autorisee)
Write-Host "Test connexion OpenSSH..." -ForegroundColor DarkGray
$sshTest = ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no "${SshUser}@${SshHost}" "echo OK" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Cle SSH detectee — utilisation de OpenSSH natif." -ForegroundColor Green
    $fixLocal = Join-Path $ScriptDir "fix-server-production.sh"
    $nginxLocal = Join-Path $ScriptDir "nginx\mobility-health-production.conf"
    $remotePayload = @"
set -e
TMP=`$(mktemp -d)
mkdir -p "`$TMP/nginx"
cat > "`$TMP/fix-server-production.sh" << 'EOFSCRIPT'
$((Get-Content $fixLocal -Raw))
EOFSCRIPT
cat > "`$TMP/nginx/mobility-health-production.conf" << 'EOFNGINX'
$((Get-Content $nginxLocal -Raw))
EOFNGINX
chmod +x "`$TMP/fix-server-production.sh"
cd "`$TMP" && bash fix-server-production.sh
"@
    ssh -o StrictHostKeyChecking=no "${SshUser}@${SshHost}" $remotePayload
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "OpenSSH sans cle — connexion par mot de passe (paramiko)..." -ForegroundColor DarkGray
    $env:MH_SSH_PASSWORD = $password
    $env:MH_SSH_HOST = $SshHost
    $env:MH_SSH_USER = $SshUser
    Write-Host "Correctif production sur ${SshUser}@${SshHost}..." -ForegroundColor Cyan
    python (Join-Path $ScriptDir "remote_fix.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Echec authentification. Essayez :" -ForegroundColor Yellow
        Write-Host "  1. Verifier le mot de passe dans hPanel Hostinger (VPS > SSH)" -ForegroundColor Yellow
        Write-Host "  2. Autre utilisateur : .\deploy\remote-fix.ps1 -SshUser deployer" -ForegroundColor Yellow
        Write-Host "  3. Test manuel : ssh ${SshUser}@${SshHost}" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "Verification externe..." -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "https://srv1324425.hstgr.cloud/api/v1/health" -UseBasicParsing -TimeoutSec 20
    Write-Host "API: $($r.StatusCode) — $($r.Content)" -ForegroundColor Green
} catch {
    Write-Host "L'API ne repond pas encore: $_" -ForegroundColor Red
    exit 1
}
