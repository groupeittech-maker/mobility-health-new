const accountingState = {
    transactions: [],
    filters: {
        search: '',
        status: 'all',
    },
};

const currencyHelper = window.CurrencyHelper || {
    getLocale: () => 'fr-FR',
    getCurrency: () => 'XOF',
    format: (value, options = {}) => {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return '—';
        }
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'XOF',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
            ...options,
        }).format(numeric);
    },
};

document.addEventListener('DOMContentLoaded', async () => {
    const allowedRoles = [
        'agent_comptable_mh',
        'agent_comptable_assureur',
        'finance_manager',
        'admin',
    ];

    const hasAccess = await requireAnyRole(allowedRoles, 'index.html');
    if (!hasAccess) {
        return;
    }

    const userName = localStorage.getItem('user_name') || '';
    const userNameTarget = document.getElementById('userName');
    if (userNameTarget) {
        userNameTarget.textContent = userName;
    }

    initFilters();
    loadTransactions();
});

function initFilters() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            accountingState.filters.search = event.target.value.toLowerCase();
            renderTransactions();
        });
    }

    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (event) => {
            accountingState.filters.status = event.target.value;
            renderTransactions();
        });
    }
}

async function loadTransactions() {
    const tbody = document.getElementById('transactionsBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="muted">Chargement des transactions...</td>
            </tr>
        `;
        paginateTable('transactionsBody');
    }

    try {
        const data = await apiCall('/payments/accounting/transactions');
        accountingState.transactions = Array.isArray(data) ? data : [];
        updateStats();
        renderTransactions();
    } catch (error) {
        console.error('Erreur lors du chargement des transactions:', error);
        showAlert(error.message || 'Impossible de charger les transactions', 'error');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="muted">Erreur de chargement. Réessayez plus tard.</td>
                </tr>
            `;
            paginateTable('transactionsBody');
        }
    }
}

function updateStats() {
    const { transactions } = accountingState;
    const totalAmount = transactions.reduce(
        (sum, item) => sum + Number(item.montant_total || 0),
        0,
    );
    const mhAmount = transactions.reduce(
        (sum, item) => sum + Number(item.montant_mh || 0),
        0,
    );
    const paidCount = transactions.filter((item) => item.status_code === 'paid').length;

    const setText = (id, value) => {
        const target = document.getElementById(id);
        if (target) {
            target.textContent = value;
        }
    };

    setText('transactionsCount', transactions.length);
    setText('totalAmount', formatAmount(totalAmount));
    setText('mhAmount', formatAmount(mhAmount));
    setText('paidTransactions', paidCount);
}

function renderTransactions() {
    const tbody = document.getElementById('transactionsBody');
    if (!tbody) {
        return;
    }

    const showActions = shouldShowActions();
    document.querySelectorAll('.column-action').forEach((cell) => {
        cell.style.display = showActions ? '' : 'none';
    });

    const filtered = accountingState.transactions.filter((item) => {
        const matchesSearch = filterBySearch(item);
        const matchesStatus =
            accountingState.filters.status === 'all' ||
            (item.status_code || '') === accountingState.filters.status;
        return matchesSearch && matchesStatus;
    });

    if (!filtered.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="muted">Aucune transaction trouvée avec les filtres appliqués.</td>
            </tr>
        `;
        paginateTable('transactionsBody');
        return;
    }

    tbody.innerHTML = filtered
        .map((item) => {
            const statusBadge = renderStatusBadge(
                item.statut_transaction,
                item.status_code,
            );
            const actionCell = showActions
                ? `<td class="column-action">${formatAction(item.action)}</td>`
                : '';

            const pctAssureur = item.commission_assureur_pct != null
                ? ` (${Number(item.commission_assureur_pct)} %)`
                : '';
            return `
                <tr>
                    <td>
                        <strong>${item.numero_souscription || '—'}</strong><br>
                        <small>${item.reference_transaction || ''}</small>
                    </td>
                    <td>${item.assure || '—'}</td>
                    <td>${item.assureur_nom || '—'}</td>
                    <td>${formatAmount(item.montant_total)}</td>
                    <td>${formatShareAmount(item.montant_assure)}</td>
                    <td>${formatAmount(item.montant_assureur)}${pctAssureur}</td>
                    <td>${formatAmount(item.montant_mh)}</td>
                    <td>${statusBadge}</td>
                    ${actionCell}
                </tr>
            `;
        })
        .join('');
    paginateTable('transactionsBody');
}

function filterBySearch(item) {
    const term = accountingState.filters.search;
    if (!term) {
        return true;
    }

    const haystack = [
        item.numero_souscription || '',
        item.assure || '',
        item.reference_transaction || '',
    ]
        .join(' ')
        .toLowerCase();

    return haystack.includes(term);
}

function formatAmount(value) {
    if (value === null || value === undefined || value === '') {
        return '—';
    }
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return '—';
    }
    try {
        return currencyHelper.format(numeric, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
    } catch {
        const currencyCode = currencyHelper.getCurrency ? currencyHelper.getCurrency() : 'XOF';
        return `${numeric.toFixed(0)} ${currencyCode}`;
    }
}

function formatShareAmount(value) {
    const numeric = Number(value);
    if (!numeric) {
        return '—';
    }
    return formatAmount(numeric);
}

function renderStatusBadge(label, code = '') {
    if (!label) {
        return '<span class="status-badge status-pending">—</span>';
    }
    let badgeClass = 'status-pending';
    if (code === 'paid') {
        badgeClass = 'status-active';
    } else if (code === 'refunded') {
        badgeClass = 'status-inactive';
    }
    return `<span class="status-badge ${badgeClass}">${label}</span>`;
}

function formatAction(action) {
    if (!action) {
        return '—';
    }
    return action.charAt(0).toUpperCase() + action.slice(1);
}

function shouldShowActions() {
    const role = localStorage.getItem('user_role');
    return ['agent_comptable_mh', 'finance_manager', 'admin'].includes(role);
}

