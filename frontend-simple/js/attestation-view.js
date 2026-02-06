document.addEventListener('DOMContentLoaded', async function() {
    const isValid = await requireAuth();
    if (!isValid) {
        return;
    }
    const container = document.getElementById('attestationContainer');
    
    // Récupérer l'ID depuis l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const attestationId = parseInt(urlParams.get('id'));
    
    if (!attestationId) {
        container.innerHTML = '<div class="alert alert-error">ID d\'attestation manquant</div>';
        return;
    }
    
    try {
        const attestation = await attestationsAPI.getWithUrl(attestationId);
        
        const date = new Date(attestation.created_at).toLocaleDateString('fr-FR');
        const typeLabel = attestation.type_attestation === 'provisoire' ? 'Provisoire' : 'Définitive';
        const badgeClass = attestation.type_attestation === 'provisoire' ? 'badge-provisoire' : 'badge-definitive';
        const ecardSection = attestation.carte_numerique_url ? `
            <div class="ecard-section">
                <div class="ecard-header">
                    <h3>Ma carte d'assurance numérique</h3>
                    <p>Présentez-la lors des contrôles ou scannez le QR code.</p>
                </div>
                <img src="${attestation.carte_numerique_url}" alt="Carte numérique" class="ecard-image">
                <div class="ecard-actions">
                    <a href="${attestation.carte_numerique_url}" download="carte-${attestation.numero_attestation || attestation.id}.png" class="btn btn-secondary btn-sm">Télécharger la carte</a>
                </div>
            </div>
        ` : '';
        
        container.innerHTML = `
            <div class="form-container">
                <div style="margin-bottom: 1.5rem;">
                    <h2>Attestation ${typeLabel}</h2>
                    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1rem;">
                        <span class="badge ${badgeClass}">${typeLabel}</span>
                        <span style="color: #666;">Émise le ${date}</span>
                    </div>
                </div>
                
                <div class="pdf-viewer-container">
                    <div class="pdf-viewer-header">
                        <h3>${attestation.numero_attestation}</h3>
                        <button type="button" class="btn btn-primary" 
                           onclick="handleAttestationDownload(event, ${attestation.id})">
                            Télécharger
                        </button>
                    </div>
                    ${attestation.url_signee ? `
                        <iframe class="pdf-iframe" src="${attestation.url_signee}" title="Attestation PDF"></iframe>
                    ` : `
                        <div class="alert alert-warning">
                            L'aperçu du PDF n'est pas disponible. Vous pouvez toujours télécharger l'attestation.
                        </div>
                    `}
                </div>
                ${ecardSection}
            </div>
        `;
    } catch (error) {
        container.innerHTML = `<div class="alert alert-error">Erreur: ${error.message}</div>`;
    }
});

// Fonction pour gérer le téléchargement d'une attestation
async function handleAttestationDownload(event, attestationId) {
    // Le téléchargement se fait via l'endpoint API qui gère l'authentification
    // et récupère le fichier depuis Minio de manière sécurisée
    event.preventDefault();
    
    try {
        // Récupérer le token d'authentification
        const token = localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || localStorage.getItem('token');
        if (!token) {
            alert('Vous devez être connecté pour télécharger l\'attestation');
            return;
        }
        
        // Construire l'URL de téléchargement
        const apiBaseUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
        const downloadUrl = `${apiBaseUrl}/attestations/${attestationId}/download`;
        
        // Récupérer le numéro d'attestation depuis l'élément DOM si disponible
        const container = document.getElementById('attestationContainer');
        let numeroAttestation = attestationId;
        if (container) {
            const numeroElement = container.querySelector('h3');
            if (numeroElement) {
                numeroAttestation = numeroElement.textContent.trim() || attestationId;
            }
        }
        
        // Ajouter le token dans les headers via fetch puis créer un blob
        const response = await fetch(downloadUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                alert('Votre session a expiré. Veuillez vous reconnecter.');
                window.location.href = '/login.html';
                return;
            }
            const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
            throw new Error(errorData.detail || `Erreur ${response.status}`);
        }
        
        // Créer un blob et télécharger
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `attestation-${numeroAttestation}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Erreur lors du téléchargement:', error);
        alert(`Erreur lors du téléchargement: ${error.message}`);
    }
}

