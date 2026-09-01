// Vérifier l'authentification et les rôles autorisés
(async function() {
    // Les attestations peuvent être validées par les rôles de revue MH
    const isValid = await requireAnyRole(
        ['admin', 'doctor', 'hospital_admin', 'medical_reviewer', 'technical_reviewer', 'production_agent', 'finance_manager'],
        'index.html'
    );
    if (!isValid) {
        return; // requireAnyRole() a déjà redirigé
    }
})();

const userRole = localStorage.getItem('user_role');

// Rechercher les attestations
async function searchAttestations() {
    const subscriptionId = parseInt(document.getElementById('subscriptionIdSearch').value);
    const container = document.getElementById('attestationsContainer');
    
    if (!subscriptionId) {
        showAlert('Veuillez entrer un ID de souscription', 'error');
        return;
    }
    
    showLoading(container);
    
    try {
        const attestations = await attestationsAPI.getBySubscription(subscriptionId);
        
        if (attestations.length === 0) {
            container.innerHTML = '<p>Aucune attestation trouvée pour cette souscription.</p>';
            return;
        }
        
        let html = '<div style="display: grid; gap: 1.5rem;">';
        
        for (const attestation of attestations) {
            if (attestation.type_attestation !== 'provisoire') {
                continue; // On ne montre que les provisoires à valider
            }
            
            const validations = await attestationsAPI.getValidations(attestation.id);
            const date = new Date(attestation.created_at).toLocaleDateString('fr-FR');
            
            html += `
                <div style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h3>Attestation Provisoire - ${attestation.numero_attestation}</h3>
                    <p><strong>Date:</strong> ${date}</p>
                    
                    <div style="margin: 1rem 0;">
                        <h4>Validations requises:</h4>
                        <div style="display: grid; gap: 0.5rem; margin-top: 0.5rem;">
                            ${renderValidation('medecin', validations, attestation.id, userRole)}
                            ${renderValidation('production', validations, attestation.id, userRole)}
                        </div>
                    </div>
                    
                    <div style="margin-top: 1rem;">
                        <button class="btn btn-primary" onclick="viewAttestation(${attestation.id})">Voir l'attestation</button>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="alert alert-error">Erreur: ${error.message}</div>`;
    }
}

function renderValidation(type, validations, attestationId, userRole) {
    const validation = validations.find(v => v.type_validation === type);
    const isValid = validation && validation.est_valide;
    
    let canValidate = false;
    if (type === 'medecin' && (userRole === 'doctor' || userRole === 'medical_reviewer')) canValidate = true;
    if (type === 'technique' && ['admin', 'hospital_admin', 'technical_reviewer', 'finance_manager'].includes(userRole)) canValidate = true;
    if (type === 'production' && (userRole === 'admin' || userRole === 'production_agent')) canValidate = true;
    
    const typeLabels = {
        'medecin': 'Médecin',
        'technique': 'Technique',
        'production': 'Production'
    };
    
    const statusClass = isValid ? 'status-active' : 'status-pending';
    const statusText = isValid ? '✓ Validé' : '⏳ En attente';
    
    return `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--light-bg); border-radius: 4px;">
            <div>
                <strong>${typeLabels[type]}:</strong>
                <span class="status-badge ${statusClass}" style="margin-left: 0.5rem;">${statusText}</span>
            </div>
            ${canValidate && !isValid ? `
                <button class="btn btn-success btn-sm" onclick="validateAttestation(${attestationId}, '${type}')">
                    Valider
                </button>
            ` : ''}
        </div>
    `;
}

async function validateAttestation(attestationId, type) {
    if (!confirm(`Confirmer la validation ${type} pour cette attestation ?`)) {
        return;
    }
    
    try {
        await attestationsAPI.createValidation(attestationId, {
            type_validation: type,
            est_valide: true,
            commentaires: 'Validé via back office'
        });
        
        showAlert('Validation enregistrée avec succès', 'success');
        searchAttestations(); // Recharger
    } catch (error) {
        showAlert(`Erreur: ${error.message}`, 'error');
    }
}

async function viewAttestation(attestationId) {
    try {
        const attestation = await attestationsAPI.getWithUrl(attestationId);
        window.location.href = attestation.url_signee;
    } catch (error) {
        showAlert(`Erreur: ${error.message}`, 'error');
    }
}

