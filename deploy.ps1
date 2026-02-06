# Script de deploiement pour Mobility Health
# Deploie le frontend et le backend sur le serveur Hostinger VPS

# Configuration
$SSH_HOST = "82.112.242.86"
$SSH_USER = "deployer"
$FRONTEND_PATH = "frontend-simple"
$SERVER_FRONTEND = "/var/www/mobility-health/frontend-simple"
$SERVER_BACKEND = "/var/www/mobility-health/backend"

# Variable pour suivre les erreurs
$script:hasErrors = $false

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploiement Mobility Health" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verifier que OpenSSH est disponible
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur: OpenSSH n'est pas installe!" -ForegroundColor Red
    Write-Host "   Installez OpenSSH avec: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0" -ForegroundColor Yellow
    exit 1
}

if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur: SCP n'est pas disponible!" -ForegroundColor Red
    Write-Host "   Installez OpenSSH avec: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0" -ForegroundColor Yellow
    exit 1
}

# Verifier que les dossiers existent
if (-not (Test-Path $FRONTEND_PATH)) {
    Write-Host "Erreur: Le dossier '$FRONTEND_PATH' n'existe pas!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "app")) {
    Write-Host "Erreur: Le dossier 'app' (backend) n'existe pas!" -ForegroundColor Red
    exit 1
}

# Etape 1: Deployer le frontend
Write-Host "Etape 1/4: Deploiement du frontend..." -ForegroundColor Yellow
Write-Host "   Copie des fichiers vers le serveur..." -ForegroundColor Gray

# Creer une archive temporaire du frontend
$tempArchive = "frontend-temp.tar.gz"
Write-Host "   Creation de l'archive temporaire..." -ForegroundColor Gray

# Utiliser tar via Git Bash ou WSL si disponible
$tarCommand = "tar"
if (Get-Command $tarCommand -ErrorAction SilentlyContinue) {
    Push-Location $FRONTEND_PATH
    & tar czf "../$tempArchive" .
    Pop-Location
    
    if (Test-Path $tempArchive) {
        Write-Host "   Archive creee" -ForegroundColor Green
        
        # Afficher la taille de l'archive
        $archiveSize = (Get-Item $tempArchive).Length / 1MB
        Write-Host "   Archive creee (${archiveSize:N2} MB)" -ForegroundColor DarkGray
        
        # Copier l'archive vers le serveur
        Write-Host "   Transfert de l'archive vers le serveur..." -ForegroundColor Gray
        $scpResult = & scp -o StrictHostKeyChecking=no "$tempArchive" "${SSH_USER}@${SSH_HOST}:/tmp/frontend.tar.gz" 2>&1
        
        if ($?) {
            Write-Host "   Archive transferee" -ForegroundColor Green
            
            # Extraire l'archive sur le serveur
            Write-Host "   Extraction sur le serveur..." -ForegroundColor Gray
            $sshScript = @"
echo 'Extraction des fichiers frontend...'
sudo rm -rf $SERVER_FRONTEND/*
sudo tar xzf /tmp/frontend.tar.gz -C $SERVER_FRONTEND/
sudo chown -R deployer:deployer $SERVER_FRONTEND
rm /tmp/frontend.tar.gz
echo 'Frontend deploye'
"@
            $sshResult = & ssh -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" $sshScript 2>&1
            
            if ($?) {
                Write-Host "   Frontend deploye avec succes" -ForegroundColor Green
            } else {
                Write-Host "   Erreur lors de l'extraction sur le serveur" -ForegroundColor Red
                Write-Host "   Details: $sshResult" -ForegroundColor Red
                $script:hasErrors = $true
            }
        } else {
            Write-Host "   Erreur lors du transfert de l'archive" -ForegroundColor Red
            Write-Host "   Details: $scpResult" -ForegroundColor Red
            $script:hasErrors = $true
        }
        
        # Supprimer l'archive temporaire locale
        Remove-Item $tempArchive -ErrorAction SilentlyContinue
    } else {
        Write-Host "   Erreur lors de la creation de l'archive" -ForegroundColor Red
    }
} else {
    # Si tar n'est pas disponible, utiliser scp directement
    Write-Host "   tar non disponible, utilisation de scp direct..." -ForegroundColor Yellow
    Write-Host "   Transfert des fichiers frontend..." -ForegroundColor Gray
    
    # Creer une liste des fichiers a copier
    $files = Get-ChildItem -Path $FRONTEND_PATH -Recurse -File
    $fileCount = 0
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring((Resolve-Path $FRONTEND_PATH).Path.Length + 1)
        $serverPath = "${SERVER_FRONTEND}/${relativePath}".Replace('\', '/')
        
        # Creer le repertoire parent sur le serveur si necessaire
        $parentDir = Split-Path $serverPath -Parent
        & ssh -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" "mkdir -p ${parentDir}" 2>&1 | Out-Null
        
        # Copier le fichier
        $scpResult = & scp -o StrictHostKeyChecking=no "$($file.FullName)" "${SSH_USER}@${SSH_HOST}:${serverPath}" 2>&1
        if ($?) {
            $fileCount++
        }
    }
    
    Write-Host "   $fileCount fichiers copies" -ForegroundColor Gray
    
    # Definir les permissions
    & ssh -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" "sudo chown -R deployer:deployer ${SERVER_FRONTEND}" 2>&1 | Out-Null
    
    if ($?) {
        Write-Host "   Frontend deploye avec succes" -ForegroundColor Green
    } else {
        Write-Host "   Frontend copie mais erreur lors de la definition des permissions" -ForegroundColor Yellow
        $script:hasErrors = $true
    }
}

Write-Host ""

# Etape 2: Deployer le backend
Write-Host "Etape 2/4: Deploiement du backend..." -ForegroundColor Yellow
Write-Host "   Correction des permissions sur le serveur..." -ForegroundColor Gray

# S'assurer que le dossier backend a les bonnes permissions
$permScript = @"
sudo mkdir -p $SERVER_BACKEND
sudo chown -R deployer:deployer $SERVER_BACKEND
"@
& ssh -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" $permScript 2>&1 | Out-Null

Write-Host "   Copie des fichiers backend vers le serveur..." -ForegroundColor Gray

# Fichiers et dossiers backend a copier
$backendItems = @(
    "app",
    "alembic",
    "docker-compose.yml",
    "Dockerfile",
    "requirements.txt",
    "alembic.ini"
)

$itemCount = 0
$totalItems = $backendItems.Count

foreach ($item in $backendItems) {
    $itemCount++
    Write-Host "   [$itemCount/$totalItems] Copie de '$item'..." -ForegroundColor Gray
    
    if (Test-Path $item) {
        if (Test-Path $item -PathType Container) {
            # C'est un dossier - exclure __pycache__ et autres fichiers inutiles
            Write-Host "      Creation de l'archive (exclusion __pycache__)..." -ForegroundColor DarkGray
            $tempBackendArchive = "${item}-temp.tar.gz"
            $parentDir = Split-Path $item -Parent
            if ($parentDir) {
                Push-Location $parentDir
            } else {
                Push-Location "."
            }
            $itemName = Split-Path $item -Leaf
            & tar czf "$tempBackendArchive" --exclude="__pycache__" --exclude="*.pyc" --exclude="*.pyo" --exclude=".git" "$itemName" 2>&1 | Out-Null
            Pop-Location
            
            $archivePath = if ($parentDir) { Join-Path $parentDir $tempBackendArchive } else { $tempBackendArchive }
            
            if (Test-Path $archivePath) {
                $archiveSize = (Get-Item $archivePath).Length / 1MB
                Write-Host "      Archive creee (${archiveSize:N2} MB)" -ForegroundColor DarkGray
                Write-Host "      Transfert vers le serveur..." -ForegroundColor DarkGray
                
                # Copier l'archive vers le serveur
                $scpResult = & scp -o StrictHostKeyChecking=no "$archivePath" "${SSH_USER}@${SSH_HOST}:/tmp/${item}.tar.gz" 2>&1
                
                if ($?) {
                    Write-Host "      Extraction sur le serveur..." -ForegroundColor DarkGray
                    # Extraire sur le serveur
                    $extractScript = @"
cd $SERVER_BACKEND
sudo rm -rf ${item}
sudo tar xzf /tmp/${item}.tar.gz
sudo chown -R deployer:deployer ${item}
rm /tmp/${item}.tar.gz
"@
                    $extractResult = & ssh -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" $extractScript 2>&1
                    
                    if ($?) {
                        Write-Host "      '$item' copie avec succes" -ForegroundColor Green
                    } else {
                        Write-Host "      Erreur lors de l'extraction de '$item'" -ForegroundColor Yellow
                        $script:hasErrors = $true
                    }
                } else {
                    Write-Host "      Erreur lors du transfert de '$item'" -ForegroundColor Yellow
                    $script:hasErrors = $true
                }
                
                # Supprimer l'archive temporaire
                Remove-Item $archivePath -ErrorAction SilentlyContinue
            } else {
                # Si tar echoue, utiliser scp direct (les erreurs de __pycache__ seront ignorees)
                Write-Host "      Utilisation de scp direct (peut prendre du temps)..." -ForegroundColor DarkGray
                $scpResult = & scp -r -o StrictHostKeyChecking=no "$item" "${SSH_USER}@${SSH_HOST}:${SERVER_BACKEND}/" 2>&1
                # Les erreurs de __pycache__ ne sont pas critiques
                if ($scpResult -match "Permission denied" -and $scpResult -match "__pycache__") {
                    Write-Host "      '$item' copie (erreurs __pycache__ ignorees)" -ForegroundColor Green
                } elseif ($?) {
                    Write-Host "      '$item' copie" -ForegroundColor Green
                } else {
                    Write-Host "      Erreur lors de la copie de '$item'" -ForegroundColor Yellow
                    $script:hasErrors = $true
                }
            }
        } else {
            # C'est un fichier
            Write-Host "      Transfert du fichier..." -ForegroundColor DarkGray
            $scpResult = & scp -o StrictHostKeyChecking=no "$item" "${SSH_USER}@${SSH_HOST}:${SERVER_BACKEND}/" 2>&1
            
            if ($?) {
                Write-Host "      '$item' copie" -ForegroundColor Green
            } else {
                Write-Host "      Erreur lors de la copie de '$item'" -ForegroundColor Yellow
                Write-Host "         Details: $scpResult" -ForegroundColor Gray
                $script:hasErrors = $true
            }
        }
    } else {
        Write-Host "      '$item' n'existe pas, ignore" -ForegroundColor Yellow
    }
}

Write-Host "   Backend copie avec succes" -ForegroundColor Green
Write-Host ""

# Etape 3: Reconstruire et redemarrer les services Docker
Write-Host "Etape 3/5: Reconstruction et redemarrage des services..." -ForegroundColor Yellow
Write-Host "   Reconstruction des images Docker (cela peut prendre 2-5 minutes)..." -ForegroundColor Gray
Write-Host "   Veuillez patienter..." -ForegroundColor DarkGray

$dockerScript = @"
set -e
cd $SERVER_BACKEND

echo '[1/6] Reconstruction de l'image API...'
if sudo docker compose build --no-cache api; then
    echo '✓ Image API reconstruite avec succes'
else
    echo '✗ Erreur lors de la reconstruction de l'image API'
    exit 1
fi

echo '[2/6] Arret des services existants...'
sudo docker compose down || true
echo '✓ Services arretes'

echo '[3/6] Demarrage de tous les services (db, redis, minio, api, celery)...'
if sudo docker compose up -d; then
    echo '✓ Services demarres'
else
    echo '✗ Erreur lors du demarrage des services'
    exit 1
fi

echo '[4/6] Attente du demarrage complet des services (15 secondes)...'
sleep 15

echo '[5/6] Application des migrations Alembic...'
MIGRATION_RESULT=\$(sudo docker compose exec -T api alembic upgrade head 2>&1)
MIGRATION_EXIT_CODE=\$?
if [ \$MIGRATION_EXIT_CODE -eq 0 ]; then
    echo '✓ Migrations Alembic appliquees avec succes'
    echo "\$MIGRATION_RESULT"
else
    echo '✗ Erreur lors de l'application des migrations Alembic'
    echo "\$MIGRATION_RESULT"
    exit 1
fi

echo '[6/6] Redemarrage de l'API pour appliquer les changements...'
if sudo docker compose restart api; then
    echo '✓ API redemarree'
else
    echo '✗ Erreur lors du redemarrage de l'API'
    exit 1
fi

echo '[Verification] Verification de l'etat des services...'
sleep 5
SERVICES_STATUS=\$(sudo docker compose ps --format json)
echo "\$SERVICES_STATUS"

echo 'Tous les services sont redemarres'
"@

$dockerResult = & ssh -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" $dockerScript 2>&1

# Afficher la progression et vérifier les erreurs
$dockerOutput = $dockerResult -join "`n"
if ($dockerOutput -match "\[1/6\]") {
    Write-Host "   [1/6] Reconstruction de l'image API..." -ForegroundColor DarkGray
}
if ($dockerOutput -match "\[2/6\]") {
    Write-Host "   [2/6] Arret des services existants..." -ForegroundColor DarkGray
}
if ($dockerOutput -match "\[3/6\]") {
    Write-Host "   [3/6] Demarrage de tous les services..." -ForegroundColor DarkGray
}
if ($dockerOutput -match "\[4/6\]") {
    Write-Host "   [4/6] Attente du demarrage complet..." -ForegroundColor DarkGray
}
if ($dockerOutput -match "\[5/6\]") {
    Write-Host "   [5/6] Application des migrations Alembic..." -ForegroundColor DarkGray
}
if ($dockerOutput -match "\[6/6\]") {
    Write-Host "   [6/6] Redemarrage de l'API..." -ForegroundColor DarkGray
}

# Vérifier les résultats
if ($dockerOutput -match "✓ Migrations Alembic appliquees avec succes") {
    Write-Host "   ✓ Migrations Alembic appliquees avec succes" -ForegroundColor Green
} elseif ($dockerOutput -match "✗ Erreur lors de l'application des migrations") {
    Write-Host "   ✗ Erreur lors de l'application des migrations Alembic" -ForegroundColor Red
    Write-Host "   Details: $dockerOutput" -ForegroundColor Gray
    $script:hasErrors = $true
}

if ($dockerOutput -match "Tous les services sont redemarres" -and -not $script:hasErrors) {
    Write-Host "   ✓ Services reconstruits et redemarres" -ForegroundColor Green
} else {
    if (-not $script:hasErrors) {
        Write-Host "   ⚠ Services redemarres (verification en cours...)" -ForegroundColor Yellow
    } else {
        Write-Host "   ✗ Erreur lors de la reconstruction/redemarrage" -ForegroundColor Red
        Write-Host "   Details: $dockerOutput" -ForegroundColor Gray
    }
}

Write-Host ""

# Etape 4: Verifier l'etat des services Docker
Write-Host "Etape 4/5: Verification de l'etat des services Docker..." -ForegroundColor Yellow

$checkServicesScript = @"
cd $SERVER_BACKEND
echo 'Verification des services Docker...'
sudo docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
"@

$servicesStatus = & ssh -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" $checkServicesScript 2>&1
Write-Host "   Etat des services:" -ForegroundColor Gray
$servicesStatus | ForEach-Object {
    if ($_ -match "Up|running") {
        Write-Host "   $_" -ForegroundColor Green
    } elseif ($_ -match "Exit|Error|unhealthy") {
        Write-Host "   $_" -ForegroundColor Red
        $script:hasErrors = $true
    } else {
        Write-Host "   $_" -ForegroundColor Gray
    }
}

Write-Host ""

# Etape 5: Redemarrer Nginx et verifier
Write-Host "Etape 5/5: Redemarrage de Nginx et verification finale..." -ForegroundColor Yellow
Write-Host "   Redemarrage de Nginx..." -ForegroundColor Gray

$nginxResult = & ssh -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" "sudo systemctl reload nginx" 2>&1

if ($?) {
    Write-Host "   ✓ Nginx redemarre" -ForegroundColor Green
} else {
    Write-Host "   ✗ Erreur lors du redemarrage de Nginx" -ForegroundColor Yellow
    Write-Host "   Details: $nginxResult" -ForegroundColor Gray
    $script:hasErrors = $true
}

# Attendre que l'API soit complètement démarrée
Write-Host "   Attente du demarrage complet de l'API (15 secondes)..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# Verifier que l'API repond avec plusieurs tentatives
Write-Host "   Verification de l'API..." -ForegroundColor Gray
$apiHealthy = $false
$maxRetries = 3
$retryCount = 0

while (-not $apiHealthy -and $retryCount -lt $maxRetries) {
    $retryCount++
    try {
        $healthCheck = Invoke-WebRequest -Uri "https://srv1324425.hstgr.cloud/health" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($healthCheck.StatusCode -eq 200) {
            $apiHealthy = $true
            Write-Host "   ✓ API accessible et fonctionnelle" -ForegroundColor Green
            $healthData = $healthCheck.Content | ConvertFrom-Json
            if ($healthData.status -eq "healthy") {
                Write-Host "   ✓ API Health Check: $($healthData.status)" -ForegroundColor Green
            }
        }
    } catch {
        if ($retryCount -lt $maxRetries) {
            Write-Host "   Tentative $retryCount/$maxRetries - L'API ne repond pas encore, nouvelle tentative dans 5 secondes..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        } else {
            Write-Host "   ✗ L'API ne repond pas apres $maxRetries tentatives" -ForegroundColor Red
            Write-Host "   Vérifiez les logs: sudo docker compose logs api" -ForegroundColor Yellow
            $script:hasErrors = $true
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($script:hasErrors) {
    Write-Host "  Deploiement termine avec des avertissements" -ForegroundColor Yellow
} else {
    Write-Host "  Deploiement termine avec succes!" -ForegroundColor Green
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Site: https://srv1324425.hstgr.cloud" -ForegroundColor Cyan
Write-Host "API Health: https://srv1324425.hstgr.cloud/health" -ForegroundColor Cyan
Write-Host ""

if ($script:hasErrors) {
    Write-Host "Attention: Certaines erreurs se sont produites. Verifiez les messages ci-dessus." -ForegroundColor Yellow
    exit 1
} else {
    exit 0
}
