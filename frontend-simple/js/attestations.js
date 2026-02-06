document.addEventListener('DOMContentLoaded', function() {
    const searchBtn = document.getElementById('searchBtn');
    const attestationsList = document.getElementById('attestationsList');
    
    searchBtn.addEventListener('click', async function() {
        const subscriptionId = parseInt(document.getElementById('subscription_id_search').value);
        
        if (!subscriptionId) {
            showAlert('Veuillez entrer un ID de souscription', 'error');
            return;
        }
        
        showLoading(attestationsList);
        
        try {
            const attestations = await attestationsAPI.getBySubscription(subscriptionId);
            
            if (attestations.length === 0) {
                attestationsList.innerHTML = '<p>Aucune attestation trouvée pour cette souscription.</p>';
                return;
            }
            
            let html = '<div style="display: grid; gap: 1rem; margin-top: 1rem;">';
            
            attestations.forEach(attestation => {
                const date = new Date(attestation.created_at).toLocaleDateString('fr-FR');
                const typeLabel = attestation.type_attestation === 'provisoire' ? 'Provisoire' : 'Définitive';
                const badgeClass = attestation.type_attestation === 'provisoire' ? 'badge-provisoire' : 'badge-definitive';
                
                html += `
                    <div style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                            <h3>Attestation ${typeLabel}</h3>
                            <span class="badge ${badgeClass}">${typeLabel}</span>
                        </div>
                        <p><strong>Numéro:</strong> ${attestation.numero_attestation}</p>
                        <p><strong>Date d'émission:</strong> ${date}</p>
                        <button class="btn btn-primary" onclick="viewAttestation(${attestation.id})" style="margin-top: 1rem;">
                            Voir l'attestation
                        </button>
                    </div>
                `;
            });
            
            html += '</div>';
            attestationsList.innerHTML = html;
        } catch (error) {
            attestationsList.innerHTML = `<div class="alert alert-error">Erreur: ${error.message}</div>`;
        }
    });
});

async function viewAttestation(attestationId) {
    try {
        const attestation = await attestationsAPI.getWithUrl(attestationId);
        window.location.href = `attestation-view.html?id=${attestationId}`;
    } catch (error) {
        showAlert(`Erreur: ${error.message}`, 'error');
    }
}

