const PORTAL_ALLOWED_ROLES =
    window.ASSUREUR_SINISTRES_ALLOWED_ROLES || ['agent_sinistre_assureur', 'admin'];

const sinistresState = {
    entries: [],
    filters: {
        status: 'all',
        search: '',
    },
    selectedSinistreId: null,
};

document.addEventListener('DOMContentLoaded', async () => {
    const allowed = await requireAnyRole(PORTAL_ALLOWED_ROLES, 'login.html');
    if (!allowed) {
        return;
    }
    initSectionTabs();
    initSinistresFilters();
    await loadSinistres();
});

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
        loadWorkflowSinistres();
    }
}

function initSinistresFilters() {
    const searchInput = document.getElementById('sinistreSearchInput');
    const statusFilter = document.getElementById('sinistreStatusFilter');
    const refreshBtn = document.getElementById('sinistreRefreshBtn');

    searchInput?.addEventListener('input', (event) => {
        sinistresState.filters.search = event.target.value.trim().toLowerCase();
        renderSinistresTable();
    });

    statusFilter?.addEventListener('change', (event) => {
        sinistresState.filters.status = event.target.value;
        renderSinistresTable();
    });

    refreshBtn?.addEventListener('click', loadSinistres);
}

const SINISTRES_PAGE_SIZE = 100;

async function loadSinistres() {
    const tbody = document.getElementById('sinistresTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="muted">Chargement en cours...</td>
            </tr>
        `;
    }
    try {
        let skip = 0;
        const collected = [];
        while (true) {
            const params = new URLSearchParams();
            params.set('limit', SINISTRES_PAGE_SIZE.toString());
            if (skip) {
                params.set('skip', skip.toString());
            }
            const batch = await apiCall(`/assureur/sinistres?${params.toString()}`);
            const items = Array.isArray(batch) ? batch : [];
            collected.push(...items);
            if (items.length < SINISTRES_PAGE_SIZE) {
                break;
            }
            skip += items.length;
        }
        sinistresState.entries = collected;
        renderSinistresTable();
    } catch (error) {
        console.error('Erreur chargement sinistres:', error);
        showAlert(error.message || 'Impossible de charger les sinistres.', 'error');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="muted">Erreur lors du chargement.</td>
                </tr>
            `;
        }
    }
}

function renderSinistresTable() {
    const tbody = document.getElementById('sinistresTableBody');
    if (!tbody) {
        return;
    }
    const { status, search } = sinistresState.filters;
    const filtered = sinistresState.entries.filter((entry) => {
        const matchesStatus = status === 'all' || entry.statut === status;
        const haystack = [
            entry.numero_sinistre || '',
            entry.alerte?.numero_alerte || '',
            entry.souscription?.user?.full_name || entry.souscription?.user?.email || '',
        ]
            .join(' ')
            .toLowerCase();
        const matchesSearch = !search || haystack.includes(search);
        return matchesStatus && matchesSearch;
    });

    if (!filtered.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="muted">Aucun sinistre trouvé avec les filtres appliqués.</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered
        .map((sinistre) => {
            const numeroSinistre = sinistre.numero_sinistre || 'En attente';
            const numeroAlerte = sinistre.alerte?.numero_alerte || '—';
            const assure = sinistre.souscription?.user?.full_name || sinistre.souscription?.user?.email || '—';
            const dateDeclenchement = sinistre.created_at ? formatDate(sinistre.created_at) : '—';
            const statutLabel = getStatutLabel(sinistre.statut);
            return `
                <tr>
                    <td>${escapeHtml(numeroSinistre)}</td>
                    <td>${escapeHtml(numeroAlerte)}</td>
                    <td>${escapeHtml(assure)}</td>
                    <td>${escapeHtml(dateDeclenchement)}</td>
                    <td>${statutLabel}</td>
                    <td>
                        <button class="btn btn-sm" onclick="viewSinistreWorkflow(${sinistre.id})">Voir workflow</button>
                    </td>
                </tr>
            `;
        })
        .join('');
}

function getStatutLabel(statut) {
    const labels = {
        'en_cours': '<span class="pill pill-warning">En cours</span>',
        'resolu': '<span class="pill pill-success">Résolu</span>',
        'annule': '<span class="pill pill-danger">Annulé</span>',
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
        hour: '2-digit',
        minute: '2-digit',
    });
}

async function loadWorkflowSinistres() {
    const list = document.getElementById('workflowSinistreList');
    const empty = document.getElementById('workflowSinistreEmpty');
    const counter = document.getElementById('workflowSinistreCount');
    
    if (list) list.innerHTML = '';
    if (empty) empty.hidden = false;
    
    try {
        const data = await apiCall('/assureur/sinistres?limit=100');
        const sinistres = Array.isArray(data) ? data : [];
        
        if (counter) {
            counter.textContent = `${sinistres.length} sinistre${sinistres.length > 1 ? 's' : ''}`;
        }
        
        if (!sinistres.length) {
            if (empty) empty.hidden = false;
            return;
        }
        
        if (empty) empty.hidden = true;
        if (list) {
            list.innerHTML = sinistres
                .map((sinistre) => {
                    const numeroSinistre = sinistre.numero_sinistre || `Sinistre #${sinistre.id}`;
                    const assure = sinistre.souscription?.user?.full_name || sinistre.souscription?.user?.email || '—';
                    return `
                        <li class="card-item" onclick="viewSinistreWorkflow(${sinistre.id})">
                            <div>
                                <strong>${escapeHtml(numeroSinistre)}</strong>
                                <p class="muted">${escapeHtml(assure)}</p>
                            </div>
                        </li>
                    `;
                })
                .join('');
        }
        
        if (sinistres.length > 0 && !sinistresState.selectedSinistreId) {
            viewSinistreWorkflow(sinistres[0].id);
        }
    } catch (error) {
        console.error('Erreur chargement sinistres workflow:', error);
        showAlert(error.message || 'Impossible de charger les sinistres.', 'error');
    }
}

async function viewSinistreWorkflow(sinistreId) {
    sinistresState.selectedSinistreId = sinistreId;
    const detailPanel = document.getElementById('workflowDetail');
    if (!detailPanel) {
        return;
    }
    
    detailPanel.innerHTML = '<p class="muted">Chargement des détails...</p>';
    
    try {
        const sinistre = await apiCall(`/assureur/sinistres/${sinistreId}`);
        const workflowSteps = await apiCall(`/assureur/sinistres/${sinistreId}/workflow`);
        
        const numeroSinistre = sinistre.numero_sinistre || `Sinistre #${sinistre.id}`;
        const numeroAlerte = sinistre.alerte?.numero_alerte || '—';
        const assure = sinistre.souscription?.user?.full_name || sinistre.souscription?.user?.email || '—';
        const produit = sinistre.souscription?.produit_assurance?.nom || '—';
        const statut = sinistre.statut || '—';
        
        const stepsHtml = workflowSteps
            .sort((a, b) => a.ordre - b.ordre)
            .map((step) => {
                const statutClass = {
                    'pending': 'pill-warning',
                    'in_progress': 'pill-info',
                    'completed': 'pill-success',
                    'cancelled': 'pill-danger',
                }[step.statut] || '';
                const statutLabel = {
                    'pending': 'En attente',
                    'in_progress': 'En cours',
                    'completed': 'Terminé',
                    'cancelled': 'Annulé',
                }[step.statut] || step.statut;
                const completedDate = step.completed_at ? formatDate(step.completed_at) : '—';
                return `
                    <div class="workflow-step">
                        <div class="workflow-step-header">
                            <strong>${escapeHtml(step.titre)}</strong>
                            <span class="pill ${statutClass}">${escapeHtml(statutLabel)}</span>
                        </div>
                        <p class="muted">${escapeHtml(step.description || '')}</p>
                        ${completedDate !== '—' ? `<p class="small muted">Terminé le: ${escapeHtml(completedDate)}</p>` : ''}
                    </div>
                `;
            })
            .join('');
        
        detailPanel.innerHTML = `
            <div class="detail-header">
                <div>
                    <p class="section-index text-muted">Détails du sinistre</p>
                    <h3>${escapeHtml(numeroSinistre)}</h3>
                </div>
            </div>
            <div class="detail-content">
                <div class="info-group">
                    <label>N° d'alerte</label>
                    <p>${escapeHtml(numeroAlerte)}</p>
                </div>
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
                    <h4>Étapes du workflow</h4>
                    ${stepsHtml}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur chargement workflow:', error);
        detailPanel.innerHTML = `<p class="muted">Erreur lors du chargement: ${escapeHtml(error.message || 'Erreur inconnue')}</p>`;
    }
}

