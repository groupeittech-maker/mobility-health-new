const ALLOWED_HOSPITAL_ROLES = [
    'hospital_admin',
    'medecin_referent_mh',
    'agent_comptable_hopital'
];

const currencyFormatter = new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0
});

let currentUserRole = null;
let myHospitals = [];
let hospitalInvoices = [];
let pendingInvoices = [];
let processedInvoices = [];
let staysReadyToBillCount = 0;
let staysToBill = [];
let searchInvoicesDashboard = '';
let searchProcessedInvoices = '';
let searchToBill = '';
const ROWS_PER_PAGE = 6;
const ROWS_PER_PAGE_TO_BILL = 8;
let currentPagePending = 0;
let currentPageProcessed = 0;
let currentPageToBill = 0;

document.addEventListener('DOMContentLoaded', () => {
    initHospitalDashboard();
});

function initHospitalDashboardTabs() {
    const tabs = document.querySelectorAll('#dashboardTabs .tab-btn[data-tab-panel]');
    tabs.forEach((btn) => {
        btn.addEventListener('click', () => {
            const panelId = btn.getAttribute('data-tab-panel');
            if (panelId) {
                switchHospitalDashboardPanel(panelId);
            }
        });
    });
}

function switchHospitalDashboardPanel(panelId) {
    document.querySelectorAll('.hospital-accountant-panel').forEach((p) => {
        const show = p.id === panelId;
        p.hidden = !show;
        p.setAttribute('aria-hidden', show ? 'false' : 'true');
    });
    document.querySelectorAll('#dashboardTabs .tab-btn[data-tab-panel]').forEach((b) => {
        const active = b.getAttribute('data-tab-panel') === panelId;
        b.classList.toggle('active', active);
        b.setAttribute('aria-selected', active ? 'true' : 'false');
    });
}

async function initHospitalDashboard() {
    const isValid = await requireAnyRole(ALLOWED_HOSPITAL_ROLES, 'index.html');
    if (!isValid) {
        return;
    }
    currentUserRole = localStorage.getItem('user_role');
    displayUserContext();
    applyAccountantDashboardLayout();
    await loadHospitalContext();
    await loadHospitalInvoices();
    bindDashboardEvents();
    initHospitalDashboardTabs();
    renderRoleActions();
}

const ACCOUNTANT_LIKE_ROLES = ['agent_comptable_hopital', 'hospital_admin'];

function applyAccountantDashboardLayout() {
    const showBilling = ACCOUNTANT_LIKE_ROLES.includes(currentUserRole);
    const panelToBill = document.getElementById('panelToBill');
    const tabToBill = document.getElementById('tabToBill');
    const tabOpen = document.getElementById('tabOpenInvoicesPage');
    const tabPending = document.getElementById('tabFacturesEnCours');
    const tabHistorique = document.getElementById('tabHistoriqueFactures');
    const sub = document.getElementById('dashboardSubtitle');
    if (!showBilling) {
        panelToBill?.setAttribute('hidden', '');
        tabToBill?.setAttribute('hidden', '');
        tabOpen?.setAttribute('hidden', '');
        tabToBill?.classList.remove('active');
        tabToBill?.setAttribute('aria-selected', 'false');
        tabPending?.classList.add('active');
        tabPending?.setAttribute('aria-selected', 'true');
        tabHistorique?.classList.remove('active');
        tabHistorique?.setAttribute('aria-selected', 'false');
        switchHospitalDashboardPanel('panelFactured');
        if (sub) {
            sub.textContent = 'Suivez les dossiers facturés et l’historique des factures validées.';
        }
    } else {
        switchHospitalDashboardPanel('panelToBill');
        tabToBill?.classList.add('active');
        tabToBill?.setAttribute('aria-selected', 'true');
        tabPending?.classList.remove('active');
        tabPending?.setAttribute('aria-selected', 'false');
        tabHistorique?.classList.remove('active');
        tabHistorique?.setAttribute('aria-selected', 'false');
        panelToBill?.removeAttribute('hidden');
        panelToBill?.setAttribute('aria-hidden', 'false');
        if (sub) {
            sub.textContent = 'Dossiers à facturer, factures en suivi (validation ou refus), puis historique des factures validées.';
        }
    }
}

function bindDashboardEvents() {
    const refreshBtn = document.getElementById('refreshInvoicesBtn');
    refreshBtn?.addEventListener('click', () => loadHospitalInvoices(true));
    const refreshToBill = document.getElementById('refreshToBillBtn');
    refreshToBill?.addEventListener('click', () => loadHospitalInvoices(true));

    const searchPending = document.getElementById('searchInvoicesDashboard');
    if (searchPending) {
        searchPending.addEventListener('input', () => {
            searchInvoicesDashboard = (searchPending.value || '').trim().toLowerCase();
            renderInvoiceTables();
        });
    }
    const searchProcessed = document.getElementById('searchProcessedInvoices');
    if (searchProcessed) {
        searchProcessed.addEventListener('input', () => {
            searchProcessedInvoices = (searchProcessed.value || '').trim().toLowerCase();
            renderInvoiceTables();
        });
    }
    const searchToBillEl = document.getElementById('searchToBill');
    if (searchToBillEl) {
        searchToBillEl.addEventListener('input', () => {
            searchToBill = (searchToBillEl.value || '').trim().toLowerCase();
            currentPageToBill = 0;
            renderToBillCards();
        });
    }
}

function displayUserContext() {
    const userName = localStorage.getItem('user_name') || 'Utilisateur Hôpital';
    const nameTarget = document.getElementById('userName');
    if (nameTarget) {
        nameTarget.textContent = userName;
    }
    const badge = document.getElementById('userRoleBadge');
    if (badge) {
        badge.textContent = getRoleLabel(currentUserRole);
    }
    const title = document.getElementById('dashboardTitle');
    if (title) {
        title.textContent = `Tableau de bord ${getRoleLabel(currentUserRole)}`;
    }
}

function getRoleLabel(role) {
    switch (role) {
        case 'hospital_admin':
            return 'Administrateur Hôpital';
        case 'agent_reception_hopital':
            return 'Réception Hôpital';
        case 'medecin_referent_mh':
            return 'Médecin référent';
        case 'agent_comptable_hopital':
            return 'Comptable Hôpital';
        default:
            return 'Équipe Hôpital';
    }
}

async function loadHospitalContext() {
    try {
        const hospitals = await apiCall('/hospitals/?limit=500');
        const hospitalId = parseInt(localStorage.getItem('hospital_id') || '', 10);
        const userId = parseInt(localStorage.getItem('user_id') || '', 10);

    if (['hospital_admin', 'agent_comptable_hopital'].includes(currentUserRole)) {
            myHospitals = hospitals.filter(h => h.id === hospitalId);
        } else if (currentUserRole === 'medecin_referent_mh') {
            myHospitals = hospitals.filter(h => h.medecin_referent_id === userId);
        }

        const contextEl = document.getElementById('hospitalContext');
        if (contextEl) {
            if (myHospitals.length) {
                const names = myHospitals.map(h => h.nom).join(', ');
                contextEl.textContent = `Établissement${myHospitals.length > 1 ? 's' : ''}: ${names}`;
            } else {
                contextEl.textContent = `Aucun établissement associé à votre compte.`;
            }
        }
    } catch (error) {
        console.error('Erreur lors du chargement du contexte hôpital:', error);
    }
}

async function loadHospitalInvoices(showToast = false) {
    const pendingLoading = document.getElementById('pendingInvoicesLoading');
    const processedLoading = document.getElementById('processedInvoicesLoading');
    const toBillLoading = document.getElementById('toBillLoading');
    const errorEl = document.getElementById('invoicesError');
    const toBillError = document.getElementById('toBillError');

    if (errorEl) errorEl.hidden = true;
    if (toBillError) toBillError.hidden = true;

    const hospitalId = parseInt(localStorage.getItem('hospital_id') || '', 10);
    if (!hospitalId) {
        showInvoicesError('Aucun hôpital n’est rattaché à votre compte. Contactez un administrateur.');
        showToBillError('Aucun hôpital n’est rattaché à votre compte. Contactez un administrateur.');
        hospitalInvoices = [];
        pendingInvoices = [];
        processedInvoices = [];
        staysReadyToBillCount = 0;
        staysToBill = [];
        renderInvoiceTables();
        renderToBillCards();
        updateInvoiceStats();
        hideLoading(pendingLoading);
        hideLoading(processedLoading);
        hideLoading(toBillLoading);
        return;
    }

    showLoading(pendingLoading);
    showLoading(processedLoading);
    showLoading(toBillLoading);

    const params = new URLSearchParams({
        hospital_id: hospitalId.toString(),
        limit: '200'
    });
    const paramsNoInvoice = new URLSearchParams({
        hospital_id: hospitalId.toString(),
        limit: '200',
        invoice_status: 'none'
    });

    try {
        const [stays, staysNoInvoice] = await Promise.all([
            apiCall(`/hospital-sinistres/hospital-stays?${params.toString()}`),
            apiCall(`/hospital-sinistres/hospital-stays?${paramsNoInvoice.toString()}`)
        ]);
        hospitalInvoices = Array.isArray(stays)
            ? stays.map(mapStayToInvoice).filter(Boolean)
            : [];
        pendingInvoices = hospitalInvoices.filter((inv) => isInvoiceFollowUp(inv.statut));
        processedInvoices = hospitalInvoices.filter((inv) => isInvoiceHistory(inv.statut));
        const rawToBill = Array.isArray(staysNoInvoice)
            ? staysNoInvoice.filter((s) => (s?.status || '') === 'validated')
            : [];
        staysToBill = rawToBill;
        staysReadyToBillCount = rawToBill.length;
        updateInvoiceStats();
        renderInvoiceTables();
        renderToBillCards();
        if (showToast) {
            showAlert('Listes mises à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des factures hospitalières:', error);
        showInvoicesError(error.message || 'Impossible de charger les factures.');
        showToBillError(error.message || 'Impossible de charger les dossiers à facturer.');
        hospitalInvoices = [];
        pendingInvoices = [];
        processedInvoices = [];
        staysReadyToBillCount = 0;
        staysToBill = [];
        updateInvoiceStats();
        renderInvoiceTables();
        renderToBillCards();
    } finally {
        hideLoading(pendingLoading);
        hideLoading(processedLoading);
        hideLoading(toBillLoading);
    }
}

function showToBillError(message) {
    const el = document.getElementById('toBillError');
    if (!el) return;
    if (message) {
        el.textContent = message;
        el.hidden = false;
    } else {
        el.hidden = true;
    }
}

function getReportStatusLabel(status) {
    const map = {
        draft: 'Brouillon',
        submitted: 'Soumis',
        approved: 'Validé',
        rejected: 'Rejeté',
    };
    return map[status] || '—';
}

function getReportStatusClassForBadge(status) {
    if (status === 'approved') return 'status-validated';
    if (status === 'rejected') return 'status-rejected';
    if (status === 'submitted') return 'status-in_progress';
    return 'status-awaiting_validation';
}

function filterStaysToBillBySearch(list, term) {
    if (!term) return list;
    return list.filter((stay) => {
        const num = (stay.sinistre?.numero_sinistre || '').toString().toLowerCase();
        const patient = (stay.patient?.full_name || stay.patient?.email || '').toLowerCase();
        return num.includes(term) || patient.includes(term);
    });
}

function buildHospitalAccountantToBillCard(stay) {
    const sinistre = stay.sinistre?.numero_sinistre
        ? `Sinistre ${stay.sinistre.numero_sinistre}`
        : `Séjour #${stay.id}`;
    const patient = stay.patient?.full_name || stay.patient?.email || 'Patient non renseigné';
    const report = getReportStatusLabel(stay.report_status);
    const reportClass = getReportStatusClassForBadge(stay.report_status);
    const when = formatDateTime(stay.updated_at || stay.created_at);
    return `
        <li class="card reception-alert-card hospital-accountant-card">
            <div class="reception-alert-card__body hospital-accountant-card__body">
                <div class="reception-alert-card__main">
                    <div class="reception-alert-card__head">
                        <strong class="reception-alert-card__numero">${escapeHtml(sinistre)}</strong>
                        <span class="status-badge ${reportClass}">${escapeHtml(report)}</span>
                    </div>
                    <p class="reception-alert-card__patient">${escapeHtml(patient)}</p>
                    <p class="muted small hospital-accountant-card__meta">Dernière mise à jour · ${when}</p>
                </div>
                <div class="reception-alert-card__actions">
                    <a class="btn btn-primary btn-sm" href="hospital-invoices.html?stay_id=${stay.id}">Facturer</a>
                </div>
            </div>
        </li>`;
}

function buildHospitalAccountantInvoiceCard(invoice, listType) {
    const statusLabel = escapeHtml(getInvoiceStatusLabel(invoice.statut));
    const statusClass = getInvoiceStatusClass(invoice.statut);
    const footerNote = listType === 'processed'
        ? '<p class="muted small hospital-accountant-card__meta">Historique · facture classée</p>'
        : '';
    return `
        <li class="card reception-alert-card hospital-accountant-card">
            <div class="reception-alert-card__body hospital-accountant-card__body">
                <div class="reception-alert-card__main">
                    <div class="reception-alert-card__head">
                        <strong class="reception-alert-card__numero">${escapeHtml(invoice.numero)}</strong>
                        <span class="status-badge ${statusClass}">${statusLabel}</span>
                    </div>
                    <p class="muted small">${escapeHtml(invoice.sinistre)}</p>
                    <p class="reception-alert-card__patient">${escapeHtml(invoice.patient)}</p>
                    <div class="hospital-accountant-card__grid">
                        <div>
                            <span class="sos-alert-card__label">Montant TTC</span>
                            <div class="sos-alert-card__value">${formatCurrency(invoice.montant)}</div>
                        </div>
                        <div>
                            <span class="sos-alert-card__label">Créée le</span>
                            <div class="sos-alert-card__value">${formatDateTime(invoice.createdAt)}</div>
                        </div>
                    </div>
                    ${footerNote}
                </div>
                <div class="reception-alert-card__actions">
                    <a class="btn btn-outline btn-sm" href="hospital-invoices.html?stay_id=${invoice.stayId}">Ouvrir</a>
                </div>
            </div>
        </li>`;
}

function renderToBillCards() {
    const listEl = document.getElementById('toBillCardList');
    const emptyState = document.getElementById('toBillEmpty');
    const paginationEl = document.getElementById('toBillPagination');
    if (!listEl || !emptyState) {
        return;
    }

    const filtered = filterStaysToBillBySearch(staysToBill, searchToBill);
    if (!filtered.length) {
        listEl.hidden = true;
        listEl.innerHTML = '';
        emptyState.hidden = false;
        if (paginationEl) {
            paginationEl.hidden = true;
            paginationEl.innerHTML = '';
        }
        return;
    }

    emptyState.hidden = true;
    listEl.hidden = false;

    const sorted = filtered.slice().sort((a, b) => {
        const da = new Date(b.updated_at || b.created_at || 0);
        const db = new Date(a.updated_at || a.created_at || 0);
        return da - db;
    });
    const totalPages = Math.max(1, Math.ceil(sorted.length / ROWS_PER_PAGE_TO_BILL));
    const safePage = Math.min(currentPageToBill, totalPages - 1);
    const start = safePage * ROWS_PER_PAGE_TO_BILL;
    currentPageToBill = safePage;
    const pageItems = sorted.slice(start, start + ROWS_PER_PAGE_TO_BILL);

    listEl.innerHTML = pageItems.map((stay) => buildHospitalAccountantToBillCard(stay)).join('');

    if (paginationEl) {
        if (totalPages <= 1) {
            paginationEl.hidden = true;
            paginationEl.innerHTML = '';
        } else {
            paginationEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE_TO_BILL, sorted.length);
            paginationEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Dossiers ${start + 1}-${end} sur ${sorted.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" data-to-bill-pag="-1" ${safePage <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${safePage + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" data-to-bill-pag="1" ${safePage >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            paginationEl.querySelectorAll('[data-to-bill-pag]').forEach((btn) => {
                btn.onclick = () => {
                    const dir = parseInt(btn.getAttribute('data-to-bill-pag'), 10);
                    currentPageToBill = Math.max(0, Math.min(totalPages - 1, currentPageToBill + dir));
                    renderToBillCards();
                };
            });
        }
    }
}

function showInvoicesError(message) {
    const errorEl = document.getElementById('invoicesError');
    if (!errorEl) {
        return;
    }
    if (message) {
        errorEl.textContent = message;
        errorEl.hidden = false;
    } else {
        errorEl.hidden = true;
    }
}

function updateInvoiceStats() {
    const pendingEl = document.getElementById('pendingInvoicesCount');
    const processedEl = document.getElementById('processedInvoicesCount');
    const toBillCountEl = document.getElementById('toBillCount');
    if (pendingEl) {
        pendingEl.textContent = pendingInvoices.length.toString();
    }
    if (processedEl) {
        processedEl.textContent = processedInvoices.length.toString();
    }
    if (toBillCountEl) {
        toBillCountEl.textContent = staysReadyToBillCount.toString();
    }
    const tabToBill = document.getElementById('tabToBill');
    const tabEnCours = document.getElementById('tabFacturesEnCours');
    const tabHistorique = document.getElementById('tabHistoriqueFactures');
    if (tabToBill) {
        tabToBill.textContent = `1 · Dossiers à facturer (${staysReadyToBillCount})`;
    }
    if (tabEnCours) {
        tabEnCours.textContent = `2 · Dossiers facturés (${pendingInvoices.length})`;
    }
    if (tabHistorique) {
        tabHistorique.textContent = `3 · Historique des factures (${processedInvoices.length})`;
    }
}

function renderInvoiceTables() {
    const pendingFiltered = filterInvoiceListBySearch(pendingInvoices, searchInvoicesDashboard);
    const processedFiltered = filterInvoiceListBySearch(processedInvoices, searchProcessedInvoices);
    renderInvoiceList(pendingFiltered, 'pending');
    renderInvoiceList(processedFiltered, 'processed');
}

function filterInvoiceListBySearch(list, term) {
    if (!term) {
        return list;
    }
    return list.filter((inv) => {
        const numero = (inv.numero || '').toLowerCase();
        const sinistre = (inv.sinistre || '').toLowerCase();
        const patient = (inv.patient || '').toLowerCase();
        const statut = (getInvoiceStatusLabel(inv.statut) || '').toLowerCase();
        return numero.includes(term) || sinistre.includes(term) || patient.includes(term) || statut.includes(term);
    });
}

function renderInvoiceList(list, type) {
    const listEl = document.getElementById(`${type}InvoicesCardList`);
    const emptyState = document.getElementById(`${type}InvoicesEmpty`);
    const paginationEl = document.getElementById(`${type}InvoicesPagination`);
    if (!listEl || !emptyState) {
        return;
    }

    if (!list.length) {
        listEl.hidden = true;
        listEl.innerHTML = '';
        emptyState.hidden = false;
        if (paginationEl) {
            paginationEl.hidden = true;
            paginationEl.innerHTML = '';
        }
        return;
    }

    emptyState.hidden = true;
    listEl.hidden = false;

    const sorted = list.slice().sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
    const currentPage = type === 'pending' ? currentPagePending : currentPageProcessed;
    const totalPages = Math.max(1, Math.ceil(sorted.length / ROWS_PER_PAGE));
    const safePage = Math.min(currentPage, totalPages - 1);
    const start = safePage * ROWS_PER_PAGE;
    const pageItems = sorted.slice(start, start + ROWS_PER_PAGE);

    if (type === 'pending') currentPagePending = safePage;
    else currentPageProcessed = safePage;

    listEl.innerHTML = pageItems.map((invoice) => buildHospitalAccountantInvoiceCard(invoice, type)).join('');

    if (paginationEl) {
        if (totalPages <= 1) {
            paginationEl.hidden = true;
            paginationEl.innerHTML = '';
        } else {
            paginationEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, sorted.length);
            paginationEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Dossiers ${start + 1}-${end} sur ${sorted.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" data-pag-type="${type}" data-pag-dir="-1" ${safePage <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${safePage + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" data-pag-type="${type}" data-pag-dir="1" ${safePage >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            paginationEl.querySelectorAll('[data-pag-type]').forEach((btn) => {
                btn.onclick = () => {
                    const dir = parseInt(btn.dataset.pagDir, 10);
                    if (type === 'pending') currentPagePending = Math.max(0, Math.min(totalPages - 1, currentPagePending + dir));
                    else currentPageProcessed = Math.max(0, Math.min(totalPages - 1, currentPageProcessed + dir));
                    renderInvoiceTables();
                };
            });
        }
    }
}

function mapStayToInvoice(stay) {
    if (!stay || !stay.invoice) {
        return null;
    }
    const invoice = stay.invoice;
    return {
        id: invoice.id,
        stayId: stay.id,
        numero: invoice.numero_facture || `Facture #${invoice.id}`,
        statut: invoice.statut || 'pending',
        montant: Number(invoice.montant_ttc) || 0,
        createdAt: invoice.created_at || stay.updated_at || stay.created_at,
        sinistre: stay.sinistre?.numero_sinistre
            ? `Sinistre ${stay.sinistre.numero_sinistre}`
            : `Séjour #${stay.id}`,
        patient: stay.patient?.full_name || stay.patient?.email || 'Patient non renseigné'
    };
}

/** Validées ou payées → onglet historique uniquement */
function isInvoiceHistory(status) {
    return ['validated', 'paid'].includes(status || '');
}

/** En attente de validation (tous circuits) ou refusée → onglet dossiers facturés */
function isInvoiceFollowUp(status) {
    return !isInvoiceHistory(status);
}

function formatCurrency(value) {
    return currencyFormatter.format(Number(value) || 0);
}

function showLoading(element) {
    if (!element) {
        return;
    }
    element.hidden = false;
    element.style.display = 'flex';
}

function hideLoading(element) {
    if (!element) {
        return;
    }
    element.hidden = true;
    element.style.display = 'none';
}

function getInvoiceStatusLabel(statut) {
    const map = {
        pending_medical: 'Accord médical',
        pending_sinistre: 'Validation sinistre',
        pending_compta: 'Validation compta',
        validated: 'Validée',
        paid: 'Payée',
        rejected: 'Refusée'
    };
    return map[statut] || 'En cours';
}

function getInvoiceStatusClass(statut) {
    const map = {
        pending_medical: 'status-awaiting_validation',
        pending_sinistre: 'status-in_progress',
        pending_compta: 'status-in_progress',
        validated: 'status-validated',
        paid: 'status-validated',
        rejected: 'status-rejected'
    };
    return map[statut] || 'status-awaiting_validation';
}

function renderRoleActions() {
    const container = document.getElementById('actionsContainer');
    if (!container) {
        return;
    }
    const actions = [];
    if (currentUserRole === 'hospital_admin') {
        actions.push({
            href: 'admin-hospitals.html',
            title: 'Gérer mon hôpital',
            description: 'Mettre à jour la fiche hôpital et les équipes'
        });
        actions.push({
            href: 'hospital-invoices.html',
            title: 'Facturation hospitalière',
            description: 'Créer et suivre les factures des séjours'
        });
        actions.push({
            href: 'admin-attestations.html',
            title: 'Valider attestations',
            description: 'Consulter les attestations en attente'
        });
    }
    if (currentUserRole === 'agent_comptable_hopital') {
        actions.push({
            href: 'hospital-invoices.html',
            title: 'Facturer les séjours',
            description: 'Générer et mettre à jour les factures en attente'
        });
    }
    if (currentUserRole === 'medecin_referent_mh') {
        actions.push({
            href: 'hospital-invoices.html',
            title: 'Rapports hospitaliers',
            description: 'Vérifier les rapports validés avant facturation'
        });
    }
    container.innerHTML = actions.map(action => `
        <a href="${action.href}" class="action-card">
            <h4>${escapeHtml(action.title)}</h4>
            <p>${escapeHtml(action.description)}</p>
        </a>
    `).join('') || '<p class="muted">Aucune action spécifique pour votre rôle.</p>';
}


function formatDateTime(value) {
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
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    if (typeof text !== 'string') {
        return '';
    }
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

