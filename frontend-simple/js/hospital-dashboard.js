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
let searchInvoicesDashboard = '';
let searchProcessedInvoices = '';
const ROWS_PER_PAGE = 6;
let currentPagePending = 0;
let currentPageProcessed = 0;

document.addEventListener('DOMContentLoaded', () => {
    initHospitalDashboard();
});

async function initHospitalDashboard() {
    const isValid = await requireAnyRole(ALLOWED_HOSPITAL_ROLES, 'index.html');
    if (!isValid) {
        return;
    }
    currentUserRole = localStorage.getItem('user_role');
    displayUserContext();
    await loadHospitalContext();
    await loadHospitalInvoices();
    bindDashboardEvents();
    renderRoleActions();
}

function bindDashboardEvents() {
    const refreshBtn = document.getElementById('refreshInvoicesBtn');
    refreshBtn?.addEventListener('click', () => loadHospitalInvoices(true));

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
    const errorEl = document.getElementById('invoicesError');

    if (errorEl) errorEl.hidden = true;

    const hospitalId = parseInt(localStorage.getItem('hospital_id') || '', 10);
    if (!hospitalId) {
        showInvoicesError('Aucun hôpital n’est rattaché à votre compte. Contactez un administrateur.');
        hospitalInvoices = [];
        pendingInvoices = [];
        processedInvoices = [];
        staysReadyToBillCount = 0;
        renderInvoiceTables();
        updateInvoiceStats();
        hideLoading(pendingLoading);
        hideLoading(processedLoading);
        return;
    }

    showLoading(pendingLoading);
    showLoading(processedLoading);

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
        pendingInvoices = hospitalInvoices.filter(inv => !isInvoiceProcessed(inv.statut));
        processedInvoices = hospitalInvoices.filter(inv => isInvoiceProcessed(inv.statut));
        staysReadyToBillCount = Array.isArray(staysNoInvoice)
            ? staysNoInvoice.filter((s) => (s?.status || '') === 'validated').length
            : 0;
        updateInvoiceStats();
        renderInvoiceTables();
        if (showToast) {
            showAlert('Liste des factures mise à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des factures hospitalières:', error);
        showInvoicesError(error.message || 'Impossible de charger les factures.');
        hospitalInvoices = [];
        pendingInvoices = [];
        processedInvoices = [];
        staysReadyToBillCount = 0;
        updateInvoiceStats();
        renderInvoiceTables();
    } finally {
        hideLoading(pendingLoading);
        hideLoading(processedLoading);
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
    if (pendingEl) {
        pendingEl.textContent = pendingInvoices.length.toString();
    }
    if (processedEl) {
        processedEl.textContent = processedInvoices.length.toString();
    }
    const tabFacturer = document.getElementById('tabFacturerSejours');
    const tabEnCours = document.getElementById('tabFacturesEnCours');
    const tabHistorique = document.getElementById('tabHistoriqueFactures');
    if (tabFacturer) {
        tabFacturer.textContent = `Facturer les séjours (${staysReadyToBillCount})`;
    }
    if (tabEnCours) {
        tabEnCours.textContent = `Factures hospitalières (${pendingInvoices.length})`;
    }
    if (tabHistorique) {
        tabHistorique.textContent = `Historique des factures (${processedInvoices.length})`;
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
    const table = document.getElementById(`${type}InvoicesTable`);
    const body = document.getElementById(`${type}InvoicesTableBody`);
    const emptyState = document.getElementById(`${type}InvoicesEmpty`);
    const paginationEl = document.getElementById(`${type}InvoicesPagination`);
    if (!table || !body || !emptyState) {
        return;
    }

    if (!list.length) {
        table.hidden = true;
        emptyState.hidden = false;
        body.innerHTML = '';
        if (paginationEl) { paginationEl.hidden = true; paginationEl.innerHTML = ''; }
        return;
    }

    emptyState.hidden = true;
    table.hidden = false;

    const sorted = list.slice().sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
    const currentPage = type === 'pending' ? currentPagePending : currentPageProcessed;
    const totalPages = Math.max(1, Math.ceil(sorted.length / ROWS_PER_PAGE));
    const safePage = Math.min(currentPage, totalPages - 1);
    const start = safePage * ROWS_PER_PAGE;
    const pageItems = sorted.slice(start, start + ROWS_PER_PAGE);

    if (type === 'pending') currentPagePending = safePage;
    else currentPageProcessed = safePage;

    const rows = pageItems.map((invoice) => `
        <tr>
            <td>
                <strong>${escapeHtml(invoice.numero)}</strong>
                <div class="muted">${escapeHtml(invoice.sinistre)}</div>
            </td>
            <td>${escapeHtml(invoice.patient)}</td>
            <td>${formatCurrency(invoice.montant)}</td>
            <td>
                <span class="status-badge ${getInvoiceStatusClass(invoice.statut)}">
                    ${getInvoiceStatusLabel(invoice.statut)}
                </span>
            </td>
            <td>${formatDateTime(invoice.createdAt)}</td>
            <td>
                <a class="btn btn-outline btn-sm" href="hospital-invoices.html?stay_id=${invoice.stayId}">Ouvrir</a>
            </td>
        </tr>
    `).join('');
    body.innerHTML = rows;

    if (paginationEl) {
        if (totalPages <= 1) {
            paginationEl.hidden = true;
            paginationEl.innerHTML = '';
        } else {
            paginationEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, sorted.length);
            paginationEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${sorted.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" data-pag-type="${type}" data-pag-dir="-1" ${safePage <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${safePage + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" data-pag-type="${type}" data-pag-dir="1" ${safePage >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            paginationEl.querySelectorAll('[data-pag-type]').forEach(btn => {
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

function isInvoiceProcessed(status) {
    return ['validated', 'paid', 'rejected'].includes(status || '');
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

