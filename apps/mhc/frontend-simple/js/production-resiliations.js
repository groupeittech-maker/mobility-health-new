// Gestion des demandes de résiliation pour les agents de production

let pendingResiliations = [];
let currentResiliationId = null;

// Fonctions utilitaires (définies en premier pour éviter les erreurs de référence)
function formatDate(value, options = {}) {
    if (!value) {
        return 'Non renseigné';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return 'Non renseigné';
    }

    const { includeTime = false } = options;
    const datePart = date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
    });

    if (!includeTime) {
        return datePart;
    }

    const timePart = date.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
    });

    return `${datePart} à ${timePart}`;
}

function formatPrice(value) {
    if (value === null || value === undefined) {
        return '0,00';
    }
    const numericValue = typeof value === 'number' ? value : parseFloat(value);
    if (Number.isNaN(numericValue)) {
        return escapeHtml(value);
    }
    return numericValue.toLocaleString('fr-FR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function escapeHtml(value) {
    if (value === null || value === undefined) {
        return '—';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Fonction pour mettre à jour le compteur de résiliations
function updateResiliationsCount(count) {
    const countEl = document.getElementById('resiliationsCount');
    if (countEl) {
        countEl.textContent = `(${count})`;
        // Masquer si 0, sinon afficher
        if (count === 0) {
            countEl.style.display = 'none';
        } else {
            countEl.style.display = 'inline';
        }
    }
}

async function loadPendingResiliations() {
    console.log('🔄 loadPendingResiliations() appelée');
    const container = document.getElementById('resiliationsContainer');
    
    if (!container) {
        console.error('❌ Container resiliationsContainer non trouvé');
        return;
    }
    
    try {
        console.log('📡 Appel API: /subscriptions/pending-resiliations');
        container.innerHTML = '<div class="alert alert-info">Chargement des demandes de résiliation...</div>';
        
        const resiliations = await apiCall('/subscriptions/pending-resiliations');
        console.log('✅ Réponse API reçue:', resiliations);
        pendingResiliations = resiliations;
        
        // Mettre à jour le compteur de résiliations
        const resiliationsCount = resiliations.length || 0;
        updateResiliationsCount(resiliationsCount);
        console.log(`📊 Compteur de résiliations mis à jour: ${resiliationsCount} demande(s)`);
        
        if (resiliations.length === 0) {
            container.innerHTML = '<div class="alert alert-info">Aucune demande de résiliation en attente.</div>';
            console.log('ℹ️ Aucune demande de résiliation en attente');
            return;
        }
        
        console.log(`📋 Rendu de ${resiliations.length} demande(s) de résiliation`);
        renderResiliations(resiliations, container);
    } catch (error) {
        console.error('❌ Erreur lors du chargement des demandes de résiliation:', error);
        console.error('Détails de l\'erreur:', {
            message: error.message,
            status: error.status,
            payload: error.payload
        });
        const errorMessage = error.message || error.detail || 'Erreur inconnue';
        container.innerHTML = `<div class="alert alert-error">Erreur lors du chargement: ${escapeHtml(errorMessage)}</div>`;
    }
}

function renderResiliations(resiliations, container) {
    let html = '';
    
    resiliations.forEach(subscription => {
        const product = subscription.produit_assurance || {};
        const user = subscription.user || {};
        const demandeDate = subscription.demande_resiliation_date 
            ? formatDate(subscription.demande_resiliation_date, { includeTime: true })
            : 'Date inconnue';
        
        html += `
            <div class="resiliation-card" data-subscription-id="${subscription.id}">
                <div class="resiliation-card-header">
                    <div>
                        <h3 class="resiliation-card-title">
                            Souscription ${subscription.numero_souscription || '#' + subscription.id}
                        </h3>
                        <p class="resiliation-card-date">Demandée le ${demandeDate}</p>
                    </div>
                </div>
                
                <div class="resiliation-card-info">
                    <div class="resiliation-card-info-item">
                        <span class="resiliation-card-info-label">Client</span>
                        <span class="resiliation-card-info-value">${escapeHtml(user.full_name || user.username || 'N/A')}</span>
                    </div>
                    <div class="resiliation-card-info-item">
                        <span class="resiliation-card-info-label">Email</span>
                        <span class="resiliation-card-info-value">${escapeHtml(user.email || 'N/A')}</span>
                    </div>
                    <div class="resiliation-card-info-item">
                        <span class="resiliation-card-info-label">Produit</span>
                        <span class="resiliation-card-info-value">${escapeHtml(product.nom || 'N/A')}</span>
                    </div>
                    <div class="resiliation-card-info-item">
                        <span class="resiliation-card-info-label">Prix</span>
                        <span class="resiliation-card-info-value">${formatMontantDevis(subscription.prix_applique, product.currency)}</span>
                    </div>
                    <div class="resiliation-card-info-item">
                        <span class="resiliation-card-info-label">Date de début</span>
                        <span class="resiliation-card-info-value">${formatDate(subscription.date_debut)}</span>
                    </div>
                    <div class="resiliation-card-info-item">
                        <span class="resiliation-card-info-label">Date de fin prévue</span>
                        <span class="resiliation-card-info-value">${subscription.date_fin ? formatDate(subscription.date_fin) : 'N/A'}</span>
                    </div>
                </div>
                
                ${subscription.demande_resiliation_notes ? `
                    <div class="resiliation-card-notes">
                        <div class="resiliation-card-notes-label">Raison de la demande</div>
                        <div class="resiliation-card-notes-text">${escapeHtml(subscription.demande_resiliation_notes)}</div>
                    </div>
                ` : ''}
                
                <div class="resiliation-card-actions">
                    <button class="btn btn-danger btn-sm" onclick="openResiliationProcessModal(${subscription.id})">
                        Traiter la demande
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function showResiliationsTab() {
    console.log('🔄 showResiliationsTab() appelée');
    const validationsTab = document.getElementById('validationsTab');
    const resiliationsTab = document.getElementById('resiliationsTab');
    const validationsSection = document.getElementById('validationsSection');
    const resiliationsSection = document.getElementById('resiliationsSection');
    
    if (validationsTab) validationsTab.classList.remove('active');
    if (resiliationsTab) resiliationsTab.classList.add('active');
    if (validationsSection) validationsSection.style.display = 'none';
    if (resiliationsSection) resiliationsSection.style.display = 'block';
    
    // Charger les demandes de résiliation
    console.log('📥 Chargement des demandes de résiliation...');
    loadPendingResiliations();
}

function showValidationsTab() {
    console.log('🔄 showValidationsTab() appelée');
    const validationsTab = document.getElementById('validationsTab');
    const resiliationsTab = document.getElementById('resiliationsTab');
    const validationsSection = document.getElementById('validationsSection');
    const resiliationsSection = document.getElementById('resiliationsSection');
    
    if (validationsTab) validationsTab.classList.add('active');
    if (resiliationsTab) resiliationsTab.classList.remove('active');
    if (validationsSection) validationsSection.style.display = 'block';
    if (resiliationsSection) resiliationsSection.style.display = 'none';
}

// Fonction pour mettre à jour le compteur de résiliations
function updateResiliationsCount(count) {
    const countEl = document.getElementById('resiliationsCount');
    if (countEl) {
        countEl.textContent = `(${count})`;
        // Masquer si 0, sinon afficher
        if (count === 0) {
            countEl.style.display = 'none';
        } else {
            countEl.style.display = 'inline';
        }
    }
}

// Charger le badge au chargement de la page
async function loadResiliationsBadge() {
    console.log('🔄 loadResiliationsBadge() appelée');
    
    try {
        console.log('📡 Appel API pour le badge: /subscriptions/pending-resiliations');
        const resiliations = await apiCall('/subscriptions/pending-resiliations');
        console.log('✅ Badge - Réponse API reçue:', resiliations);
        
        const count = resiliations.length || 0;
        updateResiliationsCount(count);
        console.log(`📊 Compteur de résiliations mis à jour: ${count} demande(s)`);
    } catch (error) {
        console.error('❌ Erreur lors du chargement du badge:', error);
        updateResiliationsCount(0);
    }
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM charge, initialisation du module de resiliations');
    
    // Exposer les fonctions globalement
    window.showResiliationsTab = showResiliationsTab;
    window.showValidationsTab = showValidationsTab;
    window.loadPendingResiliations = loadPendingResiliations;
    
    // Charger le badge après un court délai pour laisser le temps aux autres scripts de se charger
    setTimeout(function() {
        console.log('⏰ Chargement du badge après délai');
        loadResiliationsBadge();
    }, 500);
});

function openResiliationProcessModal(subscriptionId) {
    const subscription = pendingResiliations.find(s => s.id === subscriptionId);
    if (!subscription) {
        console.error('Souscription non trouvée');
        return;
    }
    
    currentResiliationId = subscriptionId;
    const modal = document.getElementById('resiliationProcessModal');
    const detailsDiv = document.getElementById('resiliationProcessDetails');
    const notesTextarea = document.getElementById('resiliationProcessNotes');
    
    if (!modal || !detailsDiv) {
        console.error('Modal non trouvé');
        return;
    }
    
    const product = subscription.produit_assurance || {};
    const user = subscription.user || {};
    
    detailsDiv.innerHTML = `
        <div class="resiliation-card-info">
            <div class="resiliation-card-info-item">
                <span class="resiliation-card-info-label">Souscription</span>
                <span class="resiliation-card-info-value">${subscription.numero_souscription || '#' + subscription.id}</span>
            </div>
            <div class="resiliation-card-info-item">
                <span class="resiliation-card-info-label">Client</span>
                <span class="resiliation-card-info-value">${escapeHtml(user.full_name || user.username || 'N/A')}</span>
            </div>
            <div class="resiliation-card-info-item">
                <span class="resiliation-card-info-label">Email</span>
                <span class="resiliation-card-info-value">${escapeHtml(user.email || 'N/A')}</span>
            </div>
            <div class="resiliation-card-info-item">
                <span class="resiliation-card-info-label">Produit</span>
                <span class="resiliation-card-info-value">${escapeHtml(product.nom || 'N/A')}</span>
            </div>
        </div>
        ${subscription.demande_resiliation_notes ? `
            <div class="resiliation-card-notes" style="margin-top: 1rem;">
                <div class="resiliation-card-notes-label">Raison de la demande</div>
                <div class="resiliation-card-notes-text">${escapeHtml(subscription.demande_resiliation_notes)}</div>
            </div>
        ` : ''}
    `;
    
    if (notesTextarea) {
        notesTextarea.value = '';
    }
    
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Fermer en cliquant sur le fond (mais pas sur le contenu du modal)
    const handleModalClick = (e) => {
        if (e.target === modal) {
            closeResiliationProcessModal();
        }
    };
    
    // Retirer l'ancien handler s'il existe
    if (modal._clickHandler) {
        modal.removeEventListener('click', modal._clickHandler);
    }
    modal.addEventListener('click', handleModalClick);
    modal._clickHandler = handleModalClick;
    
    // S'assurer que les clics sur les boutons ne ferment pas le modal
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.onclick = (e) => {
            e.stopPropagation();
        };
    }
}

function closeResiliationProcessModal() {
    const modal = document.getElementById('resiliationProcessModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
    currentResiliationId = null;
}

async function approveResiliation() {
    if (!currentResiliationId) {
        return;
    }
    
    const notesTextarea = document.getElementById('resiliationProcessNotes');
    const notes = notesTextarea ? notesTextarea.value.trim() : null;
    
    try {
        await apiCall(`/subscriptions/${currentResiliationId}/process-resiliation`, {
            method: 'POST',
            body: JSON.stringify({
                approved: true,
                notes: notes || null
            })
        });
        
        if (typeof showAlert === 'function') {
            showAlert('Résiliation approuvée avec succès.', 'success');
        }
        
        closeResiliationProcessModal();
        await loadPendingResiliations();
    } catch (error) {
        console.error('Erreur lors de l\'approbation:', error);
        const errorMessage = error.message || 'Impossible d\'approuver la résiliation';
        if (typeof showAlert === 'function') {
            showAlert(`Erreur: ${errorMessage}`, 'error');
        } else {
            alert(`Erreur: ${errorMessage}`);
        }
    }
}

async function rejectResiliation() {
    console.log('🔄 rejectResiliation() appelée');
    console.log('📋 currentResiliationId:', currentResiliationId);
    
    if (!currentResiliationId) {
        console.error('❌ Aucun ID de résiliation en cours');
        alert('Erreur: Aucune demande de résiliation sélectionnée.');
        return;
    }
    
    const notesTextarea = document.getElementById('resiliationProcessNotes');
    const notes = notesTextarea ? notesTextarea.value.trim() : null;
    
    console.log('📝 Notes saisies:', notes);
    
    // Les notes sont recommandées mais pas obligatoires pour le refus
    if (!notes || notes.length === 0) {
        const confirmRefus = confirm('Vous êtes sur le point de refuser cette demande sans notes explicatives. Souhaitez-vous continuer ?\n\n(Il est recommandé d\'ajouter des notes pour expliquer le refus.)');
        if (!confirmRefus) {
            console.log('⚠️ Refus annulé par l\'utilisateur');
            return;
        }
    }
    
    try {
        console.log('📡 Envoi de la requête de refus...');
        const response = await apiCall(`/subscriptions/${currentResiliationId}/process-resiliation`, {
            method: 'POST',
            body: JSON.stringify({
                approved: false,
                notes: notes || null
            })
        });
        
        console.log('✅ Réponse reçue:', response);
        
        if (typeof showAlert === 'function') {
            showAlert('Résiliation refusée avec succès.', 'success');
        } else {
            alert('Résiliation refusée avec succès.');
        }
        
        closeResiliationProcessModal();
        await loadPendingResiliations();
    } catch (error) {
        console.error('❌ Erreur lors du refus:', error);
        console.error('Détails:', {
            message: error.message,
            status: error.status,
            payload: error.payload
        });
        const errorMessage = error.message || error.detail || 'Impossible de refuser la résiliation';
        if (typeof showAlert === 'function') {
            showAlert(`Erreur: ${errorMessage}`, 'error');
        } else {
            alert(`Erreur: ${errorMessage}`);
        }
    }
}

function viewSubscriptionDetails(subscriptionId) {
    window.location.href = `subscription-details.html?id=${subscriptionId}`;
}

// Exposer les fonctions globalement pour les appels depuis le HTML
window.showResiliationsTab = showResiliationsTab;
window.showValidationsTab = showValidationsTab;
window.loadPendingResiliations = loadPendingResiliations;
window.openResiliationProcessModal = openResiliationProcessModal;
window.closeResiliationProcessModal = closeResiliationProcessModal;
window.approveResiliation = approveResiliation;
window.rejectResiliation = rejectResiliation;
window.viewSubscriptionDetails = viewSubscriptionDetails;

