# Test de connexion SSH au VPS (diagnostic rapide)
param(
    [string]$SshHost = "srv1324425.hstgr.cloud",
    [string]$SshUser = "root"
)

Write-Host "=== Test SSH ${SshUser}@${SshHost} ===" -ForegroundColor Cyan

Write-Host "`n1. Ping reseau..." -ForegroundColor Yellow
Test-Connection -ComputerName $SshHost -Count 2 -Quiet

Write-Host "`n2. Cle SSH (sans mot de passe)..." -ForegroundColor Yellow
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no "${SshUser}@${SshHost}" "echo CLE_OK; hostname" 2>&1

Write-Host "`n3. Connexion interactive (mot de passe)..." -ForegroundColor Yellow
Write-Host "   Lancez manuellement : ssh ${SshUser}@${SshHost}" -ForegroundColor Gray
Write-Host "   Si root echoue, essayez : ssh deployer@${SshHost}" -ForegroundColor Gray

Write-Host "`n4. Port 22 ouvert ?" -ForegroundColor Yellow
$tcp = Test-NetConnection -ComputerName $SshHost -Port 22 -WarningAction SilentlyContinue
Write-Host "   TcpTestSucceeded : $($tcp.TcpTestSucceeded)" -ForegroundColor $(if ($tcp.TcpTestSucceeded) { "Green" } else { "Red" })
