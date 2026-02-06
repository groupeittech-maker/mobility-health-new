document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('subscriptionDetailsContainer');
    
    if (!container) {
        console.error('Container subscriptionDetailsContainer non trouvé');
        document.body.innerHTML = '<div style="padding: 2rem; text-align: center;"><h1>Erreur</h1><p>Le conteneur de la page n\'a pas été trouvé. Veuillez recharger la page.</p></div>';
        return;
    }

    // Timeout de sécurité : si rien ne se passe après 30 secondes, afficher un message
    const timeoutId = setTimeout(() => {
        if (container.querySelector('.loading')) {
            container.innerHTML = `
                <div class="alert alert-error">
                    <h3>Délai d'attente dépassé</h3>
                    <p>Le chargement de la souscription prend trop de temps.</p>
                    <p>Vérifiez votre connexion et réessayez.</p>
                    <button class="btn btn-primary" onclick="window.location.reload()">Recharger la page</button>
                </div>
            `;
        }
    }, 30000);

    const attestationsLink = document.getElementById('attestationsLink');
    const sosLink = document.getElementById('sosLink');
    const resiliationBtn = document.getElementById('resiliationBtn');

    try {
        const isValid = await requireAuth();
        if (!isValid) {
            clearTimeout(timeoutId);
            container.innerHTML = '<div class="alert alert-error">Authentification requise. Redirection en cours...</div>';
            return;
        }
    } catch (authError) {
        clearTimeout(timeoutId);
        console.error('Erreur d\'authentification:', authError);
        container.innerHTML = `
            <div class="alert alert-error">
                <h3>Erreur d'authentification</h3>
                <p>Veuillez vous reconnecter.</p>
                <a href="login.html" class="btn btn-primary">Se connecter</a>
            </div>
        `;
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const subscriptionId = parseInt(params.get('id'), 10);

    if (!subscriptionId || isNaN(subscriptionId)) {
        clearTimeout(timeoutId);
        container.innerHTML = `
            <div class="alert alert-error">
                <h3>Identifiant manquant</h3>
                <p>Identifiant de souscription manquant ou invalide dans l'URL.</p>
                <p>URL actuelle: <code>${escapeHtml(window.location.href)}</code></p>
                <p>Format attendu: <code>subscription-details.html?id=38</code></p>
                <a href="user-dashboard.html" class="btn btn-primary">Retour au tableau de bord</a>
            </div>
        `;
        return;
    }

    console.log('Chargement de la souscription ID:', subscriptionId);

    try {
        const subscription = await apiCall(`/subscriptions/${subscriptionId}`);
        clearTimeout(timeoutId);
        console.log('Souscription chargée:', subscription);
        
        if (!subscription) {
            container.innerHTML = `
                <div class="alert alert-error">
                    <h3>Aucune donnée</h3>
                    <p>Aucune donnée de souscription reçue du serveur.</p>
                    <p>La souscription #${subscriptionId} n'existe peut-être pas ou vous n'avez pas les permissions nécessaires.</p>
                </div>
            `;
            return;
        }

        renderSubscriptionDetails(subscription, container);
        updateActionLinks(subscription, attestationsLink, sosLink, resiliationBtn);
        await maybeAttachEcardSection(subscription, container);
    } catch (error) {
        clearTimeout(timeoutId);
        console.error('Erreur lors du chargement de la souscription:', error);
        const errorMessage = error.message || 'Erreur inconnue';
        const errorStatus = error.status || 'N/A';
        container.innerHTML = `
            <div class="alert alert-error">
                <h3>Impossible de charger la souscription</h3>
                <p><strong>Erreur:</strong> ${escapeHtml(errorMessage)}</p>
                <p><strong>Code HTTP:</strong> ${errorStatus}</p>
                <p>Vérifiez que:</p>
                <ul style="text-align: left; margin: 1rem 0;">
                    <li>La souscription #${subscriptionId} existe</li>
                    <li>Vous avez les permissions nécessaires</li>
                    <li>Le serveur backend est accessible</li>
                    <li>Vous êtes bien connecté</li>
                </ul>
                <div style="margin-top: 1rem;">
                    <a href="user-dashboard.html" class="btn btn-secondary">Retour au tableau de bord</a>
                    <button class="btn btn-primary" onclick="window.location.reload()">Réessayer</button>
                </div>
            </div>
        `;
    }
});

function renderSubscriptionDetails(subscription, container) {
    if (!subscription) {
        container.innerHTML = '<div class="alert alert-error">Aucune donnée de souscription disponible.</div>';
        return;
    }

    try {
        const product = subscription.produit_assurance || null;
        const project = subscription.projet_voyage || null;
        const statusInfo = getStatusInfo(subscription.statut || 'pending');

        container.innerHTML = `
            <div class="details-header">
                <div>
                    <p class="subtitle">Souscription ${escapeHtml(subscription.numero_souscription || `#${subscription.id || 'N/A'}`)}</p>
                    <h2>${escapeHtml(product?.nom || `Souscription #${subscription.id || 'N/A'}`)}</h2>
                    <p class="muted-text">Créée le ${formatDate(subscription.created_at, { includeTime: true })}</p>
                </div>
                <div class="details-meta">
                    <span class="status-badge ${statusInfo.class}">${statusInfo.label}</span>
                    <div class="price-chip">${formatPrice(subscription.prix_applique || 0)} €</div>
                </div>
            </div>

            <section class="detail-section">
                <h3>Informations principales</h3>
                <div class="info-grid">
                    ${renderInfoCard('Statut actuel', `<span class="status-badge ${statusInfo.class}">${statusInfo.label}</span>`, { isHtml: true })}
                    ${renderInfoCard('Numéro de souscription', subscription.numero_souscription || `#${subscription.id || 'N/A'}`)}
                    ${renderInfoCard('Prix appliqué', `${formatPrice(subscription.prix_applique || 0)} €`)}
                    ${renderInfoCard('Début de couverture', formatDate(subscription.date_debut))}
                    ${renderInfoCard('Fin de couverture', formatDate(subscription.date_fin))}
                    ${renderInfoCard('Créée le', formatDate(subscription.created_at, { includeTime: true }))}
                    ${renderInfoCard('Dernière mise à jour', formatDate(subscription.updated_at, { includeTime: true }))}
                    ${renderInfoCard('Projet associé', project ? (project.titre || `Projet #${project.id || 'N/A'}`) : 'Aucun projet')}
                </div>
            </section>

            ${renderProductSection(product, subscription)}
            ${renderProjectSection(project)}
            ${renderValidationsSection(subscription)}
            ${renderResiliationSection(subscription)}
            ${subscription.notes ? `
                <div class="detail-section">
                    <h3>Notes internes</h3>
                    <div class="notes-card">${escapeHtml(subscription.notes)}</div>
                </div>
            ` : ''}
        `;
    } catch (error) {
        console.error('Erreur lors du rendu des détails de souscription:', error);
        container.innerHTML = `
            <div class="alert alert-error">
                <h3>Erreur lors de l'affichage</h3>
                <p>${escapeHtml(error.message || 'Erreur inconnue lors du rendu')}</p>
                <pre style="margin-top: 1rem; font-size: 0.85rem; overflow-x: auto;">${escapeHtml(JSON.stringify(subscription, null, 2))}</pre>
            </div>
        `;
    }
}

function renderProductSection(product, subscription) {
    if (!product) {
        return `
            <div class="detail-section">
                <h3>Produit d’assurance</h3>
                <div class="project-empty">Aucun produit n’est associé à cette souscription (ID produit ${subscription.produit_assurance_id}).</div>
            </div>
        `;
    }

    return `
        <div class="detail-section">
            <h3>Produit d’assurance</h3>
            <p class="muted-text">Toutes les informations liées au contrat choisi.</p>
            <div class="info-grid">
                ${renderInfoCard('Nom du produit', product.nom || 'Produit sans nom')}
                ${renderInfoCard('Code produit', product.code || '—')}
                ${renderInfoCard('Assureur', product.assureur || '—')}
                ${renderInfoCard('Version', product.version || '—')}
                ${renderInfoCard('Prix catalogue', `${formatPrice(product.cout)} €`)}
                ${renderInfoCard('Durée de validité', product.duree_validite_jours ? `${product.duree_validite_jours} jours` : 'Non précisé')}
                ${renderInfoCard('Couverture multi-entrées', product.couverture_multi_entrees ? 'Oui' : 'Non')}
                ${renderInfoCard('Reconduction possible', product.reconduction_possible ? 'Oui' : 'Non')}
            </div>
            ${product.description ? `<p class="muted-text">${escapeHtml(product.description)}</p>` : ''}
        </div>
    `;
}

function renderProjectSection(project) {
    if (!project) {
        return `
            <div class="detail-section">
                <h3>Projet de voyage</h3>
                <div class="project-empty">Cette souscription n’est pas encore rattachée à un projet de voyage.</div>
            </div>
        `;
    }

    const statusLabel = getProjectStatusLabel(project.statut);

    return `
        <div class="detail-section">
            <h3>Projet de voyage</h3>
            <div class="info-grid">
                ${renderInfoCard('Titre du projet', project.titre || `Projet #${project.id}`)}
                ${renderInfoCard('Destination', project.destination || '—')}
                ${renderInfoCard('Date de départ', formatDate(project.date_depart))}
                ${renderInfoCard('Date de retour', formatDate(project.date_retour))}
                ${renderInfoCard('Participants', project.nombre_participants != null ? project.nombre_participants.toString() : '—')}
                ${renderInfoCard('Statut du projet', statusLabel)}
                ${renderInfoCard('Budget estimé', project.budget_estime ? `${formatPrice(project.budget_estime)} €` : 'Non défini')}
            </div>
            ${project.description ? `<p class="muted-text">${escapeHtml(project.description)}</p>` : ''}
            ${project.notes ? `<p class="muted-text">${escapeHtml(project.notes)}</p>` : ''}
        </div>
    `;
}

function renderValidationsSection(subscription) {
    const steps = [
        {
            label: 'Validation médicale',
            subtitle: 'Effectuée à l\'inscription',
            status: subscription.validation_medicale,
            date: subscription.validation_medicale_date,
            approver: subscription.validation_medicale_par,
            notes: subscription.validation_medicale_notes,
        },
        {
            label: 'Validation technique et définitive',
            status: subscription.validation_finale,
            date: subscription.validation_finale_date,
            approver: subscription.validation_finale_par,
            notes: subscription.validation_finale_notes,
        },
    ];

    return `
        <div class="detail-section">
            <h3>Validations & contrôles</h3>
            <div class="validation-timeline">
                ${steps.map(renderValidationCard).join('')}
            </div>
        </div>
    `;
}

function renderValidationCard(step) {
    const status = getValidationStatus(step.status);
    return `
        <div class="validation-card">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;">
                <h4>${escapeHtml(step.label)}</h4>
                <span class="validation-chip ${status.class}">${status.label}</span>
            </div>
            ${step.subtitle ? `<p class="muted-text small">${escapeHtml(step.subtitle)}</p>` : ''}
            <ul class="validation-meta">
                <li>Dernière mise à jour : ${formatDate(step.date, { includeTime: true })}</li>
                <li>Traitée par : ${step.approver ? `Agent #${escapeHtml(step.approver)}` : 'Non renseigné'}</li>
            </ul>
            ${step.notes ? `<p class="validation-notes">${escapeHtml(step.notes)}</p>` : ''}
        </div>
    `;
}

function renderInfoCard(label, value, options = {}) {
    const { isHtml = false } = options;
    const safeValue = isHtml ? value : escapeHtml(value);
    return `
        <div class="info-card">
            <span>${escapeHtml(label)}</span>
            <strong>${safeValue}</strong>
        </div>
    `;
}

function updateActionLinks(subscription, attestationsLink, sosLink, resiliationBtn) {
    if (attestationsLink) {
        attestationsLink.href = `user-attestations.html?subscription_id=${subscription.id}`;
    }

    if (sosLink) {
        if (subscription.statut === 'active') {
            sosLink.href = `sos-alert.html?subscription_id=${subscription.id}`;
            sosLink.classList.remove('disabled');
            sosLink.removeAttribute('aria-disabled');
            sosLink.removeAttribute('title');
        } else {
            sosLink.href = '#';
            sosLink.classList.add('disabled');
            sosLink.setAttribute('aria-disabled', 'true');
            sosLink.title = 'La déclaration de sinistre sera disponible une fois la souscription activée.';
        }
    }

    // Gérer le bouton de résiliation
    if (resiliationBtn) {
        const demandeResiliation = subscription.demande_resiliation;
        const isActive = subscription.statut === 'active';
        const canRequestResiliation = isActive && (!demandeResiliation || demandeResiliation === 'rejected');

        if (canRequestResiliation) {
            resiliationBtn.style.display = 'inline-block';
            resiliationBtn.onclick = () => showResiliationModal(subscription);
            resiliationBtn.textContent = 'Demander la résiliation';
        } else if (demandeResiliation === 'pending') {
            resiliationBtn.style.display = 'inline-block';
            resiliationBtn.disabled = true;
            resiliationBtn.textContent = 'Résiliation en cours...';
            resiliationBtn.title = 'Une demande de résiliation est en cours de traitement';
        } else if (demandeResiliation === 'approved') {
            resiliationBtn.style.display = 'none';
        } else {
            resiliationBtn.style.display = 'none';
        }
    }
}

function getStatusInfo(status) {
    const map = {
        active: { label: 'En cours', class: 'active' },
        en_attente: { label: 'En attente', class: 'en_attente' },
        pending: { label: 'En attente', class: 'pending' },
        expiree: { label: 'Expirée', class: 'expiree' },
        expired: { label: 'Expirée', class: 'expired' },
        suspendue: { label: 'Suspendue', class: 'suspendue' },
        resiliee: { label: 'Résiliée', class: 'resiliee' },
    };
    return map[status] || { label: status || 'Inconnu', class: 'pending' };
}

function getValidationStatus(status) {
    const map = {
        approved: { label: 'Validée', class: 'approved' },
        rejected: { label: 'Rejetée', class: 'rejected' },
        pending: { label: 'En attente', class: 'pending' },
    };
    return map[status] || { label: status ? status : 'En attente', class: 'pending' };
}

function getProjectStatusLabel(status) {
    const map = {
        en_planification: 'En planification',
        confirme: 'Confirmé',
        en_cours: 'En cours',
        termine: 'Terminé',
        annule: 'Annulé',
    };
    return map[status] || (status ? status : 'Non défini');
}

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

async function maybeAttachEcardSection(subscription, container) {
    if (!shouldAttemptEcardFetch(subscription)) {
        const existing = container.querySelector('#subscriptionEcardSection');
        if (existing) {
            existing.remove();
        }
        return;
    }

    const section = getOrCreateEcardSection(container);
    section.innerHTML = `
        <div class="ecard-section">
            <div class="ecard-header">
                <h3>Carte d'assurance numérique</h3>
                <p class="muted-text">Chargement de votre carte numérique...</p>
            </div>
            <div class="loading"><div class="spinner"></div></div>
        </div>
    `;

    try {
        const ecard = await apiCall(`/subscriptions/${subscription.id}/ecard`);
        section.innerHTML = renderEcardSection(ecard);
    } catch (error) {
        if (error?.status === 404) {
            section.innerHTML = renderEcardPendingSection();
            return;
        }
        section.innerHTML = `
            <div class="ecard-section">
                <div class="ecard-header">
                    <h3>Carte d'assurance numérique</h3>
                    <p class="muted-text">Une erreur s'est produite lors du chargement.</p>
                </div>
                <div class="alert alert-error">
                    ${escapeHtml(error?.message || 'Impossible de récupérer la carte numérique.')}
                </div>
            </div>
        `;
    }
}

function renderEcardSection(ecard) {
    const expiresText = ecard.card_expires_at
        ? formatDate(ecard.card_expires_at, { includeTime: true })
        : 'Selon disponibilité';
    const coverageText = formatDate(ecard.coverage_end_date);
    const cardUrl = ecard.card_url ? escapeHtml(ecard.card_url) : '';
    const metaCards = [
        renderInfoCard('Titulaire', ecard.holder_name || '—'),
        renderInfoCard('N° de souscription', ecard.numero_souscription || '—'),
        renderInfoCard('Validité du lien', expiresText),
        renderInfoCard('Fin de couverture', coverageText),
    ].join('');

    return `
        <div class="ecard-section">
            <div class="ecard-header">
                <h3>Carte d'assurance numérique</h3>
                <p class="muted-text">Présentez-la lors des contrôles ou scannez le QR code affiché.</p>
            </div>
            <img src="${cardUrl}" alt="Carte numérique Mobility Health" class="ecard-image" loading="lazy">
            <div class="info-grid">
                ${metaCards}
            </div>
            <div class="ecard-actions" style="gap: 0.75rem; margin-top: 1rem;">
                <a href="${cardUrl}" download="carte-${escapeHtml(ecard.numero_souscription || 'mobility')}.png" class="btn btn-secondary btn-sm">
                    Télécharger la carte
                </a>
            </div>
        </div>
    `;
}

function renderEcardPendingSection() {
    return `
        <div class="ecard-section">
            <div class="ecard-header">
                <h3>Carte d'assurance numérique</h3>
                <p class="muted-text">La carte sera disponible une fois la validation technique et définitive effectuée par l'agent de production.</p>
            </div>
            <div class="alert alert-info" style="margin-top: 1rem;">
                Carte en cours de génération. Revenez dans quelques instants.
            </div>
        </div>
    `;
}

function shouldAttemptEcardFetch(subscription) {
    const finalDecision = (subscription.validation_finale || '').toLowerCase();
    const status = (subscription.statut || '').toLowerCase();
    const statusEligible = new Set(['active', 'expiree', 'resiliee']);
    return finalDecision === 'approved' || statusEligible.has(status);
}

function getOrCreateEcardSection(container) {
    let section = container.querySelector('#subscriptionEcardSection');
    if (!section) {
        section = document.createElement('section');
        section.id = 'subscriptionEcardSection';
        section.className = 'detail-section';
        container.appendChild(section);
    }
    return section;
}

function renderResiliationSection(subscription) {
    const demandeResiliation = subscription.demande_resiliation;
    
    if (!demandeResiliation || demandeResiliation === 'none' || demandeResiliation === null) {
        return '';
    }

    let statusInfo = '';
    let statusClass = '';
    let dateInfo = '';
    let notesInfo = '';

    if (demandeResiliation === 'pending') {
        statusInfo = 'En attente de traitement';
        statusClass = 'pending';
        if (subscription.demande_resiliation_date) {
            dateInfo = `Demandée le ${formatDate(subscription.demande_resiliation_date, { includeTime: true })}`;
        }
        if (subscription.demande_resiliation_notes) {
            notesInfo = `<p class="validation-notes"><strong>Raison de la demande:</strong> ${escapeHtml(subscription.demande_resiliation_notes)}</p>`;
        }
    } else if (demandeResiliation === 'approved') {
        statusInfo = 'Résiliation approuvée';
        statusClass = 'approved';
        if (subscription.demande_resiliation_date_traitement) {
            dateInfo = `Traitée le ${formatDate(subscription.demande_resiliation_date_traitement, { includeTime: true })}`;
        }
        if (subscription.demande_resiliation_notes) {
            notesInfo = `<p class="validation-notes">${escapeHtml(subscription.demande_resiliation_notes)}</p>`;
        }
    } else if (demandeResiliation === 'rejected') {
        statusInfo = 'Résiliation refusée';
        statusClass = 'rejected';
        if (subscription.demande_resiliation_date_traitement) {
            dateInfo = `Refusée le ${formatDate(subscription.demande_resiliation_date_traitement, { includeTime: true })}`;
        }
        if (subscription.demande_resiliation_notes) {
            notesInfo = `<p class="validation-notes"><strong>Raison du refus:</strong> ${escapeHtml(subscription.demande_resiliation_notes)}</p>`;
        }
    } else {
        return '';
    }

    return `
        <div class="detail-section">
            <h3>Demande de résiliation</h3>
            <div class="validation-card">
                <div class="validation-card-header">
                    <h4>Statut de la demande</h4>
                    <span class="validation-chip ${statusClass}">${statusInfo}</span>
                </div>
                ${dateInfo ? `<ul class="validation-meta"><li>${dateInfo}</li></ul>` : ''}
                ${notesInfo}
            </div>
        </div>
    `;
}

let currentResiliationSubscription = null;

function showResiliationModal(subscription) {
    currentResiliationSubscription = subscription;
    const modal = document.getElementById('resiliationModal');
    const notesTextarea = document.getElementById('resiliationNotes');
    const confirmBtn = document.getElementById('confirmResiliationBtn');
    
    if (!modal) {
        console.error('Modal de résiliation non trouvé');
        return;
    }
    
    // Réinitialiser le formulaire
    if (notesTextarea) {
        notesTextarea.value = '';
    }
    
    // Réinitialiser le bouton
    if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Confirmer la demande';
    }
    
    // Afficher le modal
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    
    // Focus sur le textarea
    if (notesTextarea) {
        setTimeout(() => notesTextarea.focus(), 100);
    }
    
    // Gérer la soumission
    if (confirmBtn) {
        confirmBtn.onclick = () => submitResiliationRequest(subscription);
    }
    
    // Fermer en cliquant sur le fond
    modal.onclick = (e) => {
        if (e.target === modal) {
            closeResiliationModal();
        }
    };
    
    // Fermer avec Escape
    const handleEscape = (e) => {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            closeResiliationModal();
        }
    };
    document.addEventListener('keydown', handleEscape);
    modal._escapeHandler = handleEscape;
}

function closeResiliationModal() {
    const modal = document.getElementById('resiliationModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
        
        // Retirer le handler Escape
        if (modal._escapeHandler) {
            document.removeEventListener('keydown', modal._escapeHandler);
            delete modal._escapeHandler;
        }
    }
    currentResiliationSubscription = null;
}

async function submitResiliationRequest(subscription) {
    const notesTextarea = document.getElementById('resiliationNotes');
    const confirmBtn = document.getElementById('confirmResiliationBtn');
    const notes = notesTextarea ? notesTextarea.value.trim() : '';
    
    if (!confirmBtn) {
        return;
    }
    
    // Désactiver le bouton pendant l'envoi
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Envoi en cours...';
    
    try {
        await apiCall(`/subscriptions/${subscription.id}/request-resiliation`, {
            method: 'POST',
            body: JSON.stringify({
                notes: notes || null
            })
        });
        
        // Afficher un message de succès
        if (typeof showAlert === 'function') {
            showAlert('Demande de résiliation envoyée avec succès. Elle sera examinée par un agent.', 'success');
        }
        
        // Fermer le modal
        closeResiliationModal();
        
        // Recharger la page après un court délai pour afficher la mise à jour
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    } catch (error) {
        console.error('Erreur lors de la demande de résiliation:', error);
        
        // Réactiver le bouton
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Confirmer la demande';
        
        // Afficher l'erreur
        const errorMessage = error.message || 'Impossible de demander la résiliation';
        if (typeof showAlert === 'function') {
            showAlert(`Erreur: ${errorMessage}`, 'error');
        } else {
            alert(`Erreur: ${errorMessage}`);
        }
    }
}

