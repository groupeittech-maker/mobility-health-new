function isEcardUrlUnusable(url) {
    if (!url || typeof url !== 'string') return true;
    return url.includes('minio:') || url.includes('localhost:9000') || url.includes('127.0.0.1:9000');
}

function getEcardImageSrc(attestation) {
    if (!attestation.carte_numerique_url) return '';
    if (isEcardUrlUnusable(attestation.carte_numerique_url)) return '';
    return attestation.carte_numerique_url;
}

document.addEventListener('DOMContentLoaded', async function() {
    const isValid = await requireAuth();
    if (!isValid) {
        return;
    }
    const container = document.getElementById('attestationContainer');
    
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
        const hasEcard = !!attestation.carte_numerique_url;
        var placeholderSvg = 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'200\' height=\'120\'%3E%3Crect fill=\'%23f0f0f0\' width=\'200\' height=\'120\'/%3E%3Ctext x=\'50%25\' y=\'50%25\' fill=\'%23999\' text-anchor=\'middle\' dy=\'.3em\'%3EChargement...%3C/text%3E%3C/svg%3E';
        const ecardSection = hasEcard ? `
            <div class="ecard-section">
                <div class="ecard-header">
                    <h3>Ma carte d'assurance numérique</h3>
                    <p>Présentez-la lors des contrôles ou scannez le QR code.</p>
                </div>
                <img data-attestation-id="${attestation.id}" data-ecard-load="1" src="${placeholderSvg}" alt="Carte numérique" class="ecard-image attestation-ecard-img">
                <div class="ecard-actions">
                    <a href="#" class="btn btn-secondary btn-sm ecard-download" data-attestation-id="${attestation.id}" data-numero="${(attestation.numero_attestation || attestation.id)}">Télécharger la carte</a>
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
        if (hasEcard) {
            setTimeout(function() {
                loadEcardViaApi(attestation.id);
                bindEcardDownload(attestation.id, attestation.numero_attestation || attestation.id);
            }, 0);
        }
    } catch (error) {
        container.innerHTML = `<div class="alert alert-error">Erreur: ${error.message}</div>`;
    }
});

function loadEcardViaApi(attestationId) {
    var img = document.querySelector('.attestation-ecard-img[data-attestation-id="' + attestationId + '"]');
    if (!img) return;
    var token = typeof localStorage !== 'undefined' && (localStorage.getItem('access_token') || localStorage.getItem('token'));
    var apiBase = (typeof window !== 'undefined' && window.API_BASE_URL) ? window.API_BASE_URL.replace(/\/$/, '') : '';
    if (!token || !apiBase) {
        img.alt = 'Connexion requise';
        return;
    }
    var url = apiBase + '/attestations/' + attestationId + '/ecard/download';
    fetch(url, { headers: { 'Authorization': 'Bearer ' + token } })
        .then(function(r) { if (!r.ok) throw new Error(r.status); return r.blob(); })
        .then(function(blob) { img.src = URL.createObjectURL(blob); })
        .catch(function(err) { console.warn('E-card load failed:', err); img.alt = 'Carte non disponible'; });
}

function bindEcardDownload(attestationId, numero) {
    const link = document.querySelector('.ecard-download[data-attestation-id="' + attestationId + '"]');
    if (!link) return;
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const token = localStorage.getItem('access_token') || localStorage.getItem('token');
        const apiBase = window.API_BASE_URL || '';
        if (!token || !apiBase) { alert('Session expirée'); return; }
        const url = apiBase.replace(/\/$/, '') + '/attestations/' + attestationId + '/ecard/download';
        fetch(url, { headers: { 'Authorization': 'Bearer ' + token } })
            .then(function(r) { if (!r.ok) throw new Error(r.status); return r.blob(); })
            .then(function(blob) {
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'carte-' + numero + '.png';
                a.click();
                URL.revokeObjectURL(a.href);
            })
            .catch(function() { alert('Téléchargement impossible'); });
    });
}

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

