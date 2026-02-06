// Script de vérification de santé du backend
// À inclure dans les pages HTML pour vérifier la connexion au backend

async function checkBackendHealth() {
<<<<<<< HEAD
    const API_BASE_URL = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
=======
    const API_BASE_URL = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
    const baseUrl = API_BASE_URL.replace('/api/v1', '');
    
    try {
        const response = await fetch(`${baseUrl}/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('Backend is healthy:', data);
            return true;
        } else {
            console.warn('Backend health check failed:', response.status);
            return false;
        }
    } catch (error) {
        console.error('Backend health check error:', error);
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
        warningDiv.innerHTML = `
            <strong>⚠️ Backend non accessible</strong>
<<<<<<< HEAD
            <p>Le serveur backend n'est pas accessible sur https://srv1324425.hstgr.cloud</p>
            <p><strong>Pour démarrer le backend :</strong></p>
=======
            <p>Le serveur backend n'est pas accessible sur https://mobility-health.ittechmed.com</p>
            <p><strong>Vérifications à effectuer :</strong></p>
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
            <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
                <li>Vérifiez que le backend est démarré et accessible</li>
                <li>Vérifiez votre connexion internet</li>
                <li>Contactez l'administrateur si le problème persiste</li>
            </ul>
<<<<<<< HEAD
            <p><a href="https://srv1324425.hstgr.cloud/docs" target="_blank">Vérifier l'API (ouvre dans un nouvel onglet)</a></p>
=======
            <p><a href="https://mobility-health.ittechmed.com/docs" target="_blank">Vérifier l'API (ouvre dans un nouvel onglet)</a></p>
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
        `;
        
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(warningDiv, container.firstChild);
    }
});

// Exposer la fonction globalement
window.checkBackendHealth = checkBackendHealth;

