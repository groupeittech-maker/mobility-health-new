// Script de diagnostic pour vérifier la connexion au backend
// À inclure dans les pages pour aider au débogage

function getDiagnosticToken() {
    return window.MobilityAuth?.getAccessToken
        ? window.MobilityAuth.getAccessToken()
        : localStorage.getItem('access_token');
}

async function checkBackendConnection() {
<<<<<<< HEAD
    const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
=======
    const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
    const baseUrl = apiUrl.replace('/api/v1', '');
    
    const results = {
        baseUrl: baseUrl,
        apiUrl: apiUrl,
        checks: []
    };
    
    // Check 1: Health endpoint
    try {
        const response = await fetch(`${baseUrl}/health`);
        if (response.ok) {
            results.checks.push({
                name: 'Health Check',
                status: 'OK',
                message: 'Le serveur backend répond'
            });
        } else {
            results.checks.push({
                name: 'Health Check',
                status: 'ERROR',
                message: `Réponse HTTP ${response.status}`
            });
        }
    } catch (error) {
        results.checks.push({
            name: 'Health Check',
            status: 'ERROR',
            message: `Impossible de se connecter: ${error.message}`
        });
    }
    
    // Check 2: API endpoint
    try {
        const diagnosticToken = getDiagnosticToken();
        const response = await fetch(`${apiUrl}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${diagnosticToken || 'test'}`
            }
        });
        if (response.status === 401) {
            results.checks.push({
                name: 'API Endpoint',
                status: 'OK',
                message: 'L\'endpoint API est accessible (401 attendu sans token valide)'
            });
        } else if (response.ok) {
            results.checks.push({
                name: 'API Endpoint',
                status: 'OK',
                message: 'L\'endpoint API est accessible et le token est valide'
            });
        } else {
            results.checks.push({
                name: 'API Endpoint',
                status: 'WARNING',
                message: `Réponse HTTP ${response.status}`
            });
        }
    } catch (error) {
        results.checks.push({
            name: 'API Endpoint',
            status: 'ERROR',
            message: `Erreur: ${error.message}`
        });
    }
    
    // Check 3: CORS
    try {
        const response = await fetch(`${apiUrl}/auth/me`, {
            method: 'OPTIONS'
        });
        results.checks.push({
            name: 'CORS',
            status: 'OK',
            message: 'Les en-têtes CORS sont configurés'
        });
    } catch (error) {
        results.checks.push({
            name: 'CORS',
            status: 'WARNING',
            message: `Vérification CORS échouée: ${error.message}`
        });
    }
    
    // Check 4: Token
    const token = getDiagnosticToken();
    if (token) {
        results.checks.push({
            name: 'Token',
            status: 'OK',
            message: 'Token présent dans localStorage'
        });
    } else {
        results.checks.push({
            name: 'Token',
            status: 'WARNING',
            message: 'Aucun token trouvé dans localStorage'
        });
    }
    
    return results;
}

// Fonction pour afficher les résultats de diagnostic
function displayDiagnosticResults(results) {
    const container = document.getElementById('diagnostic-results') || document.body;
    let html = '<div class="diagnostic-results" style="padding: 20px; background: #f5f5f5; border-radius: 5px; margin: 20px 0;">';
    html += '<h3>Diagnostic de connexion au backend</h3>';
    html += `<p><strong>URL Base:</strong> ${results.baseUrl}</p>`;
    html += `<p><strong>URL API:</strong> ${results.apiUrl}</p>`;
    html += '<h4>Résultats des vérifications:</h4>';
    html += '<ul>';
    
    results.checks.forEach(check => {
        const statusColor = check.status === 'OK' ? 'green' : 
                           check.status === 'WARNING' ? 'orange' : 'red';
        html += `<li style="color: ${statusColor}">
            <strong>${check.name}:</strong> ${check.status} - ${check.message}
        </li>`;
    });
    
    html += '</ul>';
    html += '<button onclick="runDiagnostic()" class="btn btn-primary">Réexécuter le diagnostic</button>';
    html += '</div>';
    
    const div = document.createElement('div');
    div.innerHTML = html;
    container.appendChild(div);
}

// Fonction globale pour exécuter le diagnostic
async function runDiagnostic() {
    const results = await checkBackendConnection();
    displayDiagnosticResults(results);
}

// Exposer la fonction globalement
window.runDiagnostic = runDiagnostic;
window.checkBackendConnection = checkBackendConnection;




