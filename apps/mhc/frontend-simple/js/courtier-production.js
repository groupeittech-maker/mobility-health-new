
function escapeHtml(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const PORTAL_ALLOWED_ROLES =
    window.COURTIER_PRODUCTION_ALLOWED_ROLES || ['agent_production_courtier', 'assistant_souscription', 'admin'];

const subscriptionsState = {
    entries: [],
    filters: {
        status: 'all',
        search: '',
    },
    selectedSubscriptionId: null,
};

document.addEventListener('DOMContentLoaded', async () => {
    const allowed = await requireAnyRole(PORTAL_ALLOWED_ROLES, 'login.html');
    if (!allowed) {
        return;
    }
    initSectionTabs();
    initSubscriptionsFilters();
    initNewSubscriptionModal();
    await loadSubscriptions();
});

// ------------------------------------------------------------------
// Nouvelle souscription pour un tiers (assistant de souscription)
// ------------------------------------------------------------------

function canCreateSubscription() {
    const perms = window.MhPermissions;
    if (perms && perms.can) {
        return perms.can('production', 'edition');
    }
    return true;
}

function initNewSubscriptionModal() {
    const btn = document.getElementById('newSubscriptionBtn');
    const modal = document.getElementById('subscriptionModal');
    if (!btn || !modal) {
        return;
    }
    if (!canCreateSubscription()) {
        return; // bouton masqué par défaut dans le HTML
    }
    btn.hidden = false;

    const closeBtn = document.getElementById('subscriptionModalClose');
    const cancelBtn = document.getElementById('subscriptionCancelBtn');
    const form = document.getElementById('subscriptionForm');
    const searchInput = document.getElementById('clientSearchInput');
    const resultsList = document.getElementById('clientSearchResults');
    const clientIdInput = document.getElementById('subscriptionClientId');
    const clientLabel = document.getElementById('clientSelectedLabel');

    const open = async () => {
        form.reset();
        clientIdInput.value = '';
        clientLabel.textContent = '';
        resultsList.innerHTML = '';
        modal.classList.add('open');
        await loadSubscriptionProducts();
        searchInput.focus();
    };
    const close = () => modal.classList.remove('open');

    btn.addEventListener('click', open);
    closeBtn?.addEventListener('click', close);
    const wizardBtn = document.getElementById('subscriptionWizardBtn');
    wizardBtn?.addEventListener('click', () => {
        const uid = document.getElementById('subscriptionClientId').value;
        if (uid) {
            window.location.href = `subscription-wizard.html?for_user_id=${uid}`;
        }
    });
    cancelBtn?.addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

    // Création d'un compte voyageur (sans smartphone / sans compte existant)
    document.getElementById('toggleNewTraveler')?.addEventListener('click', (e) => {
        e.preventDefault();
        const block = document.getElementById('newTravelerBlock');
        block.hidden = !block.hidden;
    });
    document.getElementById('createTravelerBtn')?.addEventListener('click', async () => {
        const msg = document.getElementById('createTravelerMsg');
        const name = document.getElementById('newTravelerName').value.trim();
        const email = document.getElementById('newTravelerEmail').value.trim();
        if (!name || !email) {
            msg.textContent = 'Nom complet et email requis.';
            return;
        }
        try {
            const user = await apiCall('/auth/register', {
                method: 'POST',
                body: JSON.stringify({
                    email,
                    username: email,
                    full_name: name,
                    password: `MHC-${Math.random().toString(36).slice(2, 10)}`,
                    telephone: document.getElementById('newTravelerPhone').value.trim() || null,
                    date_naissance: document.getElementById('newTravelerBirth').value || null,
                    pays_residence: document.getElementById('newTravelerCountry').value.trim() || null,
                }),
            });
            clientIdInput.value = user.id;
            clientLabel.textContent = `Nouveau voyageur créé : ${user.full_name || name} (${user.email})`;
            document.getElementById('subscriptionWizardBtn').disabled = false;
            document.getElementById('newTravelerBlock').hidden = true;
            msg.textContent = '';
        } catch (err) {
            msg.textContent = err?.message || 'Création du compte impossible.';
        }
    });

    let searchTimer = null;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimer);
        const q = searchInput.value.trim();
        if (q.length < 3) {
            resultsList.innerHTML = '';
            return;
        }
        searchTimer = setTimeout(() => searchClients(q), 300);
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('subscriptionSubmitBtn');
        const payload = {
            produit_assurance_id: Number(document.getElementById('subscriptionProductId').value),
            user_id: Number(clientIdInput.value),
            date_debut: document.getElementById('subscriptionDateDebut').value
                ? `${document.getElementById('subscriptionDateDebut').value}T00:00:00`
                : null,
            notes: document.getElementById('subscriptionNotes').value.trim() || null,
            canal_distribution: 'courtier',
        };
        if (!payload.user_id) {
            alert('Sélectionnez un assuré dans les résultats de recherche.');
            return;
        }
        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Création…';
            const sub = await apiCall('/subscriptions/start', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            close();
            alert(`Souscription ${sub.numero_souscription || sub.id} créée (en attente).`);
            await loadSubscriptions();
        } catch (err) {
            alert(err?.message || 'Erreur lors de la création de la souscription.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Créer la souscription';
        }
    });
}

async function loadSubscriptionProducts() {
    const select = document.getElementById('subscriptionProductId');
    if (!select || select.options.length > 1) {
        return;
    }
    try {
        const products = await apiCall('/products/');
        (products || []).forEach((p) => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.nom || `Produit ${p.id}`;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error('Produits non chargés', err);
    }
}

async function searchClients(q) {
    const resultsList = document.getElementById('clientSearchResults');
    const clientIdInput = document.getElementById('subscriptionClientId');
    const clientLabel = document.getElementById('clientSelectedLabel');
    try {
        const clients = await apiCall(`/subscriptions/clients/search?q=${encodeURIComponent(q)}`);
        resultsList.innerHTML = '';
        if (!clients.length) {
            resultsList.innerHTML = '<li class="muted">Aucun assuré trouvé</li>';
            return;
        }
        clients.forEach((c) => {
            const li = document.createElement('li');
            li.className = 'client-search-item';
            li.textContent = `${c.full_name || c.username || ''} — ${c.email || ''} ${c.telephone ? '· ' + c.telephone : ''}`;
            li.addEventListener('click', () => {
                clientIdInput.value = c.id;
                clientLabel.textContent = `Assuré sélectionné : ${c.full_name || c.username} (${c.email})`;
                const wizardBtn = document.getElementById('subscriptionWizardBtn');
                if (wizardBtn) wizardBtn.disabled = false;
                resultsList.innerHTML = '';
                document.getElementById('clientSearchInput').value = '';
            });
            resultsList.appendChild(li);
        });
    } catch (err) {
        resultsList.innerHTML = '<li class="muted">Recherche indisponible</li>';
    }
}

function initSectionTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const sectionId = button.getAttribute('data-section');
            if (!sectionId) {
                return;
            }
            tabButtons.forEach((btn) => btn.classList.toggle('active', btn === button));
            switchSection(sectionId);
        });
    });
}

function switchSection(sectionId) {
    document.querySelectorAll('main .dashboard-section').forEach((section) => {
        section.hidden = section.id !== sectionId;
    });
    if (sectionId === 'workflowSection') {
        loadWorkflowSubscriptions();
    }
}

function initSubscriptionsFilters() {
    const searchInput = document.getElementById('subscriptionSearchInput');
    const statusFilter = document.getElementById('subscriptionStatusFilter');
    const refreshBtn = document.getElementById('subscriptionRefreshBtn');

    searchInput?.addEventListener('input', (event) => {
        subscriptionsState.filters.search = event.target.value.trim().toLowerCase();
        renderSubscriptionsTable();
    });

    statusFilter?.addEventListener('change', (event) => {
        subscriptionsState.filters.status = event.target.value;
        renderSubscriptionsTable();
    });

    refreshBtn?.addEventListener('click', loadSubscriptions);
}

const SUBSCRIPTIONS_PAGE_SIZE = 100;

async function loadSubscriptions() {
    const tbody = document.getElementById('subscriptionsTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="muted">Chargement en cours...</td>
            </tr>
        `;
    }
    try {
        let skip = 0;
        const collected = [];
        while (true) {
            const params = new URLSearchParams();
            params.set('limit', SUBSCRIPTIONS_PAGE_SIZE.toString());
            if (skip) {
                params.set('skip', skip.toString());
            }
            const batch = await apiCall(`/courtier/production/subscriptions?${params.toString()}`);
            const items = Array.isArray(batch) ? batch : [];
            collected.push(...items);
            if (items.length < SUBSCRIPTIONS_PAGE_SIZE) {
                break;
            }
            skip += items.length;
        }
        subscriptionsState.entries = collected;
        renderSubscriptionsTable();
    } catch (error) {
        console.error('Erreur chargement souscriptions:', error);
        showAlert(error.message || 'Impossible de charger les souscriptions.', 'error');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="muted">Erreur lors du chargement.</td>
                </tr>
            `;
        }
    }
}

function renderSubscriptionsTable() {
    const tbody = document.getElementById('subscriptionsTableBody');
    if (!tbody) {
        return;
    }
    const { status, search } = subscriptionsState.filters;
    const filtered = subscriptionsState.entries.filter((entry) => {
        const matchesStatus = status === 'all' || entry.statut === status;
        const haystack = [
            entry.numero_souscription || '',
            entry.user?.full_name || entry.user?.email || '',
        ]
            .join(' ')
            .toLowerCase();
        const matchesSearch = !search || haystack.includes(search);
        return matchesStatus && matchesSearch;
    });

    if (!filtered.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="muted">Aucune souscription trouvée avec les filtres appliqués.</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered
        .map((subscription) => {
            const numeroSouscription = subscription.numero_souscription || '—';
            const assure = subscription.user?.full_name || subscription.user?.email || '—';
            const produit = subscription.produit_assurance?.nom || '—';
            const dateDebut = subscription.date_debut ? formatDate(subscription.date_debut) : '—';
            const dateFin = subscription.date_fin ? formatDate(subscription.date_fin) : '—';
            const statutLabel = getStatutLabel(subscription.statut);
            return `
                <tr>
                    <td>${escapeHtml(numeroSouscription)}</td>
                    <td>${escapeHtml(assure)}</td>
                    <td>${escapeHtml(produit)}</td>
                    <td>${escapeHtml(dateDebut)}</td>
                    <td>${escapeHtml(dateFin)}</td>
                    <td>${statutLabel}</td>
                    <td>
                        <button class="btn btn-sm" onclick="viewSubscriptionWorkflow(${subscription.id})">Voir workflow</button>
                    </td>
                </tr>
            `;
        })
        .join('');
}

function getStatutLabel(statut) {
    const labels = {
        'en_attente': '<span class="pill pill-warning">En attente</span>',
        'pending': '<span class="pill pill-warning">En attente</span>',
        'active': '<span class="pill pill-success">Active</span>',
        'resiliee': '<span class="pill pill-danger">Résiliée</span>',
        'expiree': '<span class="pill pill-secondary">Expirée</span>',
    };
    return labels[statut] || `<span class="pill">${escapeHtml(statut || '—')}</span>`;
}

function formatDate(value) {
    if (!value) {
        return '—';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return '—';
    }
    return date.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
    });
}

async function loadWorkflowSubscriptions() {
    const list = document.getElementById('workflowSubscriptionList');
    const empty = document.getElementById('workflowSubscriptionEmpty');
    const counter = document.getElementById('workflowSubscriptionCount');
    
    if (list) list.innerHTML = '';
    if (empty) empty.hidden = false;
    
    try {
        const data = await apiCall('/courtier/production/subscriptions?limit=100');
        const subscriptions = Array.isArray(data) ? data : [];
        
        if (counter) {
            counter.textContent = `${subscriptions.length} souscription${subscriptions.length > 1 ? 's' : ''}`;
        }
        
        if (!subscriptions.length) {
            if (empty) empty.hidden = false;
            return;
        }
        
        if (empty) empty.hidden = true;
        if (list) {
            list.innerHTML = subscriptions
                .map((subscription) => {
                    const numeroSouscription = subscription.numero_souscription || `Souscription #${subscription.id}`;
                    const assure = subscription.user?.full_name || subscription.user?.email || '—';
                    return `
                        <li class="card-item" onclick="viewSubscriptionWorkflow(${subscription.id})">
                            <div>
                                <strong>${escapeHtml(numeroSouscription)}</strong>
                                <p class="muted">${escapeHtml(assure)}</p>
                            </div>
                        </li>
                    `;
                })
                .join('');
        }
        
        if (subscriptions.length > 0 && !subscriptionsState.selectedSubscriptionId) {
            viewSubscriptionWorkflow(subscriptions[0].id);
        }
    } catch (error) {
        console.error('Erreur chargement souscriptions workflow:', error);
        showAlert(error.message || 'Impossible de charger les souscriptions.', 'error');
    }
}

async function viewSubscriptionWorkflow(subscriptionId) {
    subscriptionsState.selectedSubscriptionId = subscriptionId;
    const detailPanel = document.getElementById('workflowDetail');
    if (!detailPanel) {
        return;
    }
    
    detailPanel.innerHTML = '<p class="muted">Chargement des détails...</p>';
    
    try {
        const subscription = await apiCall(`/courtier/production/subscriptions/${subscriptionId}`);
        const workflow = await apiCall(`/courtier/production/subscriptions/${subscriptionId}/workflow`);
        
        const numeroSouscription = subscription.numero_souscription || `Souscription #${subscription.id}`;
        const assure = subscription.user?.full_name || subscription.user?.email || '—';
        const produit = subscription.produit_assurance?.nom || '—';
        const statut = subscription.statut || '—';
        
        const validationsHtml = `
            <div class="info-group">
                <label>Validation médicale</label>
                <p>${workflow.souscription.validation_medicale ? getValidationLabel(workflow.souscription.validation_medicale) : 'En attente'}</p>
                <p class="muted small">(Effectuée à l'inscription)</p>
            </div>
            <div class="info-group">
                <label>Validation technique</label>
                <p>${workflow.souscription.validation_technique ? getValidationLabel(workflow.souscription.validation_technique) : 'En attente'}</p>
            </div>
            <div class="info-group">
                <label>Validation finale</label>
                <p>${workflow.souscription.validation_finale ? getValidationLabel(workflow.souscription.validation_finale) : 'En attente'}</p>
            </div>
        `;
        
        const paiementsHtml = workflow.paiements && workflow.paiements.length > 0
            ? workflow.paiements.map((p) => `
                <div class="workflow-step">
                    <div class="workflow-step-header">
                        <strong>Paiement #${p.id}</strong>
                        <span class="pill ${p.statut === 'valide' ? 'pill-success' : 'pill-warning'}">${escapeHtml(p.statut || '—')}</span>
                    </div>
                    <p class="muted">Montant: ${formatCurrency(p.montant)}</p>
                    <p class="muted">Type: ${escapeHtml(p.type_paiement || '—')}</p>
                    ${p.date_paiement ? `<p class="small muted">Date: ${formatDate(p.date_paiement)}</p>` : ''}
                </div>
            `).join('')
            : '<p class="muted">Aucun paiement enregistré.</p>';
        
        const attestationsHtml = workflow.attestations && workflow.attestations.length > 0
            ? workflow.attestations.map((a) => `
                <div class="workflow-step">
                    <div class="workflow-step-header">
                        <strong>Attestation ${a.numero_attestation || `#${a.id}`}</strong>
                        <span class="pill ${a.est_valide ? 'pill-success' : 'pill-warning'}">${a.est_valide ? 'Valide' : 'En attente'}</span>
                    </div>
                    <p class="muted">Type: ${escapeHtml(a.type_attestation || '—')}</p>
                    ${a.created_at ? `<p class="small muted">Créée le: ${formatDate(a.created_at)}</p>` : ''}
                </div>
            `).join('')
            : '<p class="muted">Aucune attestation générée.</p>';

        const docTypeLabels = {
            passport: 'Passeport',
            id_card: 'Carte d\'identité',
            residence_permit: 'Carte de résident',
            travel_booking: 'Réservation du voyage',
            photo_identity: 'Photo d\'identité',
            other: 'Autre',
        };
        const documentsProjet = workflow.documents_projet_voyage || [];
        const documentsProjetHtml = documentsProjet.length > 0
            ? documentsProjet.map((doc) => {
                const typeLabel = docTypeLabels[doc.doc_type] || doc.display_name || doc.doc_type;
                const name = doc.doc_type === 'other' ? (doc.display_name || typeLabel) : typeLabel;
                const link = doc.download_url
                    ? `<a href="${escapeHtml(doc.download_url)}">Ouvrir / Télécharger</a>`
                    : '<span class="muted">Lien indisponible</span>';
                return `
                <div class="workflow-step">
                    <div class="workflow-step-header">
                        <strong>${escapeHtml(name)}</strong>
                    </div>
                    <p class="muted">Type: ${escapeHtml(typeLabel)}</p>
                    <p>${link}</p>
                    ${doc.uploaded_at ? `<p class="small muted">Déposé le: ${formatDate(doc.uploaded_at)}</p>` : ''}
                </div>
            `;
            }).join('')
            : '<p class="muted">Aucune pièce justificative déposée pour ce projet de voyage.</p>';

        detailPanel.innerHTML = `
            <div class="detail-header">
                <div>
                    <p class="section-index text-muted">Détails de la souscription</p>
                    <h3>${escapeHtml(numeroSouscription)}</h3>
                </div>
            </div>
            <div class="detail-content">
                <div class="info-group">
                    <label>Assuré</label>
                    <p>${escapeHtml(assure)}</p>
                </div>
                <div class="info-group">
                    <label>Produit</label>
                    <p>${escapeHtml(produit)}</p>
                </div>
                <div class="info-group">
                    <label>Statut</label>
                    <p>${getStatutLabel(statut)}</p>
                </div>
                <div class="workflow-steps">
                    <h4>Validations</h4>
                    ${validationsHtml}
                </div>
                <div class="workflow-steps">
                    <h4>Paiements</h4>
                    ${paiementsHtml}
                </div>
                <div class="workflow-steps">
                    <h4>Attestations</h4>
                    ${attestationsHtml}
                </div>
                <div class="workflow-steps">
                    <h4>Pièces justificatives du voyage</h4>
                    ${documentsProjetHtml}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur chargement workflow:', error);
        detailPanel.innerHTML = `<p class="muted">Erreur lors du chargement: ${escapeHtml(error.message || 'Erreur inconnue')}</p>`;
    }
}

function getValidationLabel(validation) {
    const labels = {
        'approved': '<span class="pill pill-success">Approuvé</span>',
        'rejected': '<span class="pill pill-danger">Rejeté</span>',
        'pending': '<span class="pill pill-warning">En attente</span>',
    };
    return labels[validation] || `<span class="pill">${escapeHtml(validation || '—')}</span>`;
}

function formatCurrency(value) {
    if (value === null || value === undefined) {
        return '—';
    }
    const numeric = Number(value);
    if (Number.isNaN(numeric)) {
        return '—';
    }
    return numeric.toLocaleString('fr-FR', {
        style: 'currency',
        currency: 'XAF',
        maximumFractionDigits: 0,
    });
}

