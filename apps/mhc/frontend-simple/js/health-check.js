// Script de vérification de santé du backend
// À inclure dans les pages HTML pour vérifier la connexion au backend

async function checkBackendHealth() {
    const API_BASE_URL = window.API_BASE_URL || 'https://api.srv1324425.hstgr.cloud/api/v1';
    // Appeler /api/v1/health (proxyfié) pour éviter /health qui renvoie la page HTML du frontend
    const healthUrl = `${API_BASE_URL.replace(/\/$/, '')}/health`;
    try {
        const response = await fetch(healthUrl, { method: 'GET' });
        if (!response.ok) return false;
        const contentType = response.headers.get('Content-Type') || '';
        if (!contentType.includes('application/json')) return false;
        const data = await response.json();
        if (data && data.status === 'healthy') {
            console.log('Backend is healthy:', data.status);
            return true;
        }
        return false;
    } catch (error) {
        console.warn('Backend health check:', error.message || error);
        return false;
    }
}

// Vérifier la santé du backend au chargement de la page
document.addEventListener('DOMContentLoaded', async () => {
    const isHealthy = await checkBackendHealth();
    
    if (!isHealthy) {
        // Afficher un avertissement en haut de la page
        const warningDiv = document.createElement('div');
        warningDiv.className = 'backend-warning';
        warningDiv.style.cssText = `
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 4px;
            padding: 1rem;
            margin: 1rem;
            color: #856404;
        `;
        const apiDocsUrl = (window.API_BASE_URL || '').replace('/api/v1', '') + '/api/v1/docs';
        warningDiv.innerHTML = `
            <strong>⚠️ Backend non accessible</strong>
            <p>Le serveur backend ne répond pas au health check.</p>
            <p><strong>Vérifications à effectuer :</strong></p>
            <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
                <li>Vérifiez que le backend est démarré et accessible</li>
                <li>Vérifiez votre connexion internet</li>
                <li>Contactez l'administrateur si le problème persiste</li>
            </ul>
            <p><a href="${apiDocsUrl}" target="_blank">Ouvrir la doc API</a></p>
        `;
        
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(warningDiv, container.firstChild);
    }
});

// Exposer la fonction globalement
window.checkBackendHealth = checkBackendHealth;

