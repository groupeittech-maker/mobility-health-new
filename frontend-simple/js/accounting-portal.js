const PORTAL_ALLOWED_ROLES =
    window.ACCOUNTING_PORTAL_ALLOWED_ROLES || ['agent_comptable_mh', 'finance_manager', 'admin'];

const invoiceHistoryState = {
    entries: [],
    filters: {
        status: 'all',
        search: '',
    },
};

const tabCounts = { fees: null, invoices: null, history: null };

function updateTabCounts(partial) {
    if (partial.fees !== undefined) tabCounts.fees = partial.fees;
    if (partial.invoices !== undefined) tabCounts.invoices = partial.invoices;
    if (partial.history !== undefined) tabCounts.history = partial.history;

    const tabFees = document.getElementById('tabFees');
    const tabInvoices = document.getElementById('tabInvoices');
    const tabHistory = document.getElementById('tabHistory');
    if (tabFees) tabFees.textContent = tabCounts.fees !== null ? `Frais & remboursements (${tabCounts.fees})` : 'Frais & remboursements';
    if (tabInvoices) tabInvoices.textContent = tabCounts.invoices !== null ? `Factures hospitalières (${tabCounts.invoices})` : 'Factures hospitalières';
    if (tabHistory) tabHistory.textContent = tabCounts.history !== null ? `Historique des factures (${tabCounts.history})` : 'Historique des factures';
}

async function fetchTabCounts() {
    try {
        const [transactions, invoicesCompta] = await Promise.all([
            apiCall('/payments/accounting/transactions').then((d) => (Array.isArray(d) ? d : [])),
            apiCall('/invoices?stage=compta&limit=200').then((d) => (Array.isArray(d) ? d : [])),
        ]);
        updateTabCounts({ fees: transactions.length, invoices: invoicesCompta.length });
    } catch (e) {
        console.warn('Erreur chargement comptages onglets:', e);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const allowed = await requireAnyRole(PORTAL_ALLOWED_ROLES, 'login.html');
    if (!allowed) {
        return;
    }
    initSectionTabs();
    initHistoryFilters();
    fetchTabCounts();
    await loadInvoiceHistoryEntries();
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
}

function initHistoryFilters() {
    const searchInput = document.getElementById('historySearchInput');
    const statusFilter = document.getElementById('historyStatusFilter');
    const reloadBtn = document.getElementById('historyReloadBtn');

    searchInput?.addEventListener('input', (event) => {
        invoiceHistoryState.filters.search = event.target.value.trim().toLowerCase();
        renderHistoryTable();
    });

    statusFilter?.addEventListener('change', (event) => {
        invoiceHistoryState.filters.status = event.target.value;
        renderHistoryTable();
    });

    reloadBtn?.addEventListener('click', loadInvoiceHistoryEntries);
}

const HISTORY_PAGE_SIZE = 200;

async function loadInvoiceHistoryEntries() {
    const tbody = document.getElementById('historyTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="muted">Chargement en cours...</td>
            </tr>
        `;
        paginateTable('historyTableBody');
    }
    try {
        const collected = [];
        const historyStatuses = ['validated', 'rejected', 'paid'];
        for (const statut of historyStatuses) {
            let skip = 0;
            while (true) {
                const params = new URLSearchParams();
                params.set('statut', statut);
                params.set('limit', HISTORY_PAGE_SIZE.toString());
                if (skip) params.set('skip', skip.toString());
                const batch = await apiCall(`/invoices?${params.toString()}`);
                const items = Array.isArray(batch) ? batch : [];
                collected.push(...items);
                if (items.length < HISTORY_PAGE_SIZE) break;
                skip += items.length;
            }
        }
        collected.sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at));
        invoiceHistoryState.entries = collected;
        renderHistoryTable();
        updateTabCounts({ history: collected.length });
    } catch (error) {
        console.error('Erreur chargement historique factures:', error);
        showAlert(error.message || 'Impossible de charger l’historique des factures.', 'error');
        updateTabCounts({ history: 0 });
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="muted">Erreur lors du chargement.</td>
                </tr>
            `;
            paginateTable('historyTableBody');
        }
    }
}

function renderHistoryTable() {
    const tbody = document.getElementById('historyTableBody');
    if (!tbody) {
        return;
    }
    const { status, search } = invoiceHistoryState.filters;
    const filtered = invoiceHistoryState.entries.filter((entry) => {
        const matchesStatus = status === 'all' || entry.statut === status;
        const haystack = [
            entry.numero_facture || '',
            entry.sinistre_numero || '',
            entry.client_name || '',
            entry.hospital?.nom || '',
        ]
            .join(' ')
            .toLowerCase();
        const matchesSearch = !search || haystack.includes(search);
        return matchesStatus && matchesSearch;
    });

    if (!filtered.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="muted">Aucune facture trouvée avec les filtres appliqués.</td>
            </tr>
        `;
        paginateTable('historyTableBody');
        return;
    }

    tbody.innerHTML = filtered
        .map((invoice) => {
            const sinistreLabel = invoice.sinistre_numero
                ? invoice.sinistre_numero
                : invoice.sinistre?.id
                ? `Sinistre #${invoice.sinistre.id}`
                : '—';
            const client = invoice.client_name || '—';
            const hospitalName = invoice.hospital?.nom || `Hôpital #${invoice.hospital_id}`;
            return `
                <tr>
                    <td>${formatPortalDate(invoice.date_facture)}</td>
                    <td>${escapeHtml(sinistreLabel)}</td>
                    <td>${escapeHtml(client)}</td>
                    <td>${escapeHtml(hospitalName)}</td>
                    <td>${formatPortalCurrency(invoice.montant_ttc)}</td>
                    <td>${renderPortalStatus(invoice.statut)}</td>
                </tr>
            `;
        })
        .join('');
    paginateTable('historyTableBody');
}

function renderPortalStatus(status) {
    const label = getInvoiceStatusLabel(status);
    return `<span class="pill">${escapeHtml(label)}</span>`;
}

function formatPortalDate(value) {
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

function formatPortalCurrency(value) {
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

