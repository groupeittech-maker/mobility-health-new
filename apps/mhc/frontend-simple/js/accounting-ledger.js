const accountingState = {
    transactions: [],
    filters: {
        search: '',
        status: 'all',
    },
};
const brokerLookupCache = new Map();
const brokerByIdCache = new Map();

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
            useGrouping: true,
            ...options,
        }).format(numeric);
    },
};

const TRANSACTIONS_LIST_ID = 'transactionsCardList';

function escapeHtml(s) {
    if (s == null) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = String(s);
    return div.innerHTML;
}

function formatIntegerGrouped(n) {
    const num = Number(n);
    if (!Number.isFinite(num)) {
        return '—';
    }
    return new Intl.NumberFormat('fr-FR', { useGrouping: true, maximumFractionDigits: 0 }).format(num);
}

document.addEventListener('DOMContentLoaded', async () => {
    const allowedRoles = [
        'agent_comptable_mh',
        'agent_comptable_assureur',
        'agent_comptable_courtier',
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

function setListPlaceholder(message) {
    const list = document.getElementById(TRANSACTIONS_LIST_ID);
    if (!list) {
        return;
    }
    list.innerHTML = `<li class="accounting-tx-card--placeholder"><p class="muted">${escapeHtml(message)}</p></li>`;
    if (typeof paginateList === 'function') {
        paginateList(TRANSACTIONS_LIST_ID);
    }
}

async function loadTransactions() {
    setListPlaceholder('Chargement des transactions…');

    try {
        const data = await apiCall('/payments/accounting/transactions');
        const transactions = Array.isArray(data) ? data : [];
        accountingState.transactions = await enrichTransactionsWithCourtiers(transactions);
        updateStats();
        renderTransactions();
    } catch (error) {
        console.error('Erreur lors du chargement des transactions:', error);
        showAlert(error.message || 'Impossible de charger les transactions', 'error');
        setListPlaceholder('Erreur de chargement. Réessayez plus tard.');
    }
}

async function enrichTransactionsWithCourtiers(transactions) {
    const role = (localStorage.getItem('user_role') || '').toLowerCase().trim();
    const strictCourtierScope = role === 'agent_comptable_courtier';
    const out = [];
    for (const item of transactions) {
        const next = { ...item };
        const isRefunded = (next.status_code || '') === 'refunded';
        const total = Number(next.montant_total || 0);
        const mh = Number(next.montant_mh || 0);
        const assureur = Number(next.montant_assureur || 0);
        const computedBroker = total - mh - assureur;

        if (isRefunded) {
            next.montant_assureur = 0;
            next.montant_courtier = 0;
        } else if ((!next.montant_courtier || Number(next.montant_courtier) <= 0) && computedBroker > 0.009) {
            next.montant_courtier = computedBroker;
        }

        // Ne pas deviner un courtier via le 1er assureur si l'API a déjà un courtier_id,
        // ni pour les comptables assureur/courtier (risque d'afficher un mauvais nom).
        const hasCourtierId =
            next.courtier_id !== null && next.courtier_id !== undefined && String(next.courtier_id).trim() !== '';

        // Si l'API renvoie un courtier_id sans nom, résoudre le nom par ID
        // pour éviter l'affichage "Courtier : —".
        if (hasCourtierId && (!next.courtier_nom || String(next.courtier_nom).trim() === '')) {
            const courtierById = await getCourtierById(next.courtier_id, next.assureur_id);
            if (courtierById) {
                next.courtier_nom = courtierById.nom || next.courtier_nom;
                if (
                    (next.commission_courtier_pct === null || next.commission_courtier_pct === undefined) &&
                    courtierById.commission_pct !== undefined
                ) {
                    next.commission_courtier_pct = courtierById.commission_pct;
                }
            }
        }

        if (
            !strictCourtierScope &&
            !hasCourtierId &&
            (!next.courtier_nom || String(next.courtier_nom).trim() === '') &&
            next.assureur_id
        ) {
            const courtier = await getFirstCourtierForAssureur(next.assureur_id);
            if (courtier) {
                next.courtier_id = courtier.id || null;
                next.courtier_nom = courtier.nom || next.courtier_nom;
                if (
                    (next.commission_courtier_pct === null || next.commission_courtier_pct === undefined) &&
                    courtier.commission_pct !== undefined
                ) {
                    next.commission_courtier_pct = courtier.commission_pct;
                }
            }
        }

        // Garde-fou UI: un comptable courtier ne doit afficher que les lignes
        // réellement rattachées à un courtier (courtier_id explicite).
        if (strictCourtierScope && !hasCourtierId) {
            continue;
        }

        out.push(next);
    }
    return out;
}

async function getCourtierById(courtierId, assureurId) {
    const key = String(courtierId || '');
    if (!key) return null;
    if (brokerByIdCache.has(key)) {
        return brokerByIdCache.get(key);
    }
    try {
        let rows = null;
        if (assureurId) {
            rows = await apiCall(`/courtiers/?assureur_id=${encodeURIComponent(String(assureurId))}`);
        } else {
            rows = await apiCall('/courtiers/');
        }
        const found = Array.isArray(rows)
            ? rows.find((r) => String(r?.id ?? '') === key) || null
            : null;
        brokerByIdCache.set(key, found);
        return found;
    } catch (error) {
        console.warn('Impossible de résoudre le courtier par ID', courtierId, error);
        brokerByIdCache.set(key, null);
        return null;
    }
}

async function getFirstCourtierForAssureur(assureurId) {
    const key = String(assureurId || '');
    if (!key) return null;
    if (brokerLookupCache.has(key)) {
        return brokerLookupCache.get(key);
    }
    try {
        const rows = await apiCall(`/courtiers/?assureur_id=${encodeURIComponent(key)}`);
        const first = Array.isArray(rows) && rows.length ? rows[0] : null;
        brokerLookupCache.set(key, first);
        return first;
    } catch (error) {
        console.warn('Impossible de résoudre le courtier pour assureur', assureurId, error);
        brokerLookupCache.set(key, null);
        return null;
    }
}

function updateStats() {
    const { transactions } = accountingState;
    const totalAmount = transactions.reduce(
        (sum, item) => sum + Number(item.montant_total || 0),
        0,
    );
    const assureurAmount = transactions.reduce(
        (sum, item) => sum + Number(item.montant_assureur || 0),
        0,
    );
    const courtierAmount = transactions.reduce(
        (sum, item) => sum + Number(item.montant_courtier || 0),
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

    setText('transactionsCount', formatIntegerGrouped(transactions.length));
    setText('totalAmount', formatAmount(totalAmount));
    setText('assureurAmount', formatAmount(assureurAmount));
    setText('courtierAmount', formatAmount(courtierAmount));
    setText('mhAmount', formatAmount(mhAmount));
    setText('paidTransactions', formatIntegerGrouped(paidCount));
}

function buildTransactionCard(item, showActions) {
    const statusBadge = renderStatusBadge(item.statut_transaction, item.status_code);
    const refLine = item.reference_transaction
        ? `<p class="muted small">${escapeHtml(item.reference_transaction)}</p>`
        : '';
    const actionBlock = showActions
        ? `<div class="reception-alert-card__actions"><span class="accounting-tx-card__action-pill" title="Action">${escapeHtml(formatAction(item.action))}</span></div>`
        : '';

    return `
        <li class="card reception-alert-card accounting-tx-card">
            <div class="reception-alert-card__body">
                <div class="reception-alert-card__main">
                    <div class="reception-alert-card__head">
                        <strong class="reception-alert-card__numero">${escapeHtml(item.numero_souscription || '—')}</strong>
                        ${statusBadge}
                    </div>
                    <p class="reception-alert-card__patient">${escapeHtml(item.assure || '—')}</p>
                    <p class="muted small"><strong>Assureur :</strong> ${escapeHtml(item.assureur_nom || '—')}</p>
                    <p class="muted small"><strong>Courtier :</strong> ${escapeHtml(item.courtier_nom || '—')}${
                        item.commission_courtier_pct != null
                            ? ` (${escapeHtml(String(item.commission_courtier_pct))}%)`
                            : ''
                    }</p>
                    ${refLine}
                    <div class="accounting-tx-card__grid">
                        <div>
                            <span class="sos-alert-card__label">Prime assurance (total)</span>
                            <div class="sos-alert-card__value">${formatAmount(item.montant_total)}</div>
                        </div>
                        <div>
                            <span class="sos-alert-card__label">Montant reversé à l'assuré</span>
                            <div class="sos-alert-card__value">${formatShareAmount(item.montant_assure)}</div>
                        </div>
                        <div>
                            <span class="sos-alert-card__label">Part assureur</span>
                            <div class="sos-alert-card__value">${formatAmount(item.montant_assureur)}</div>
                        </div>
                        <div>
                            <span class="sos-alert-card__label">Commision perçu par le courtier</span>
                            <div class="sos-alert-card__value">${formatShareAmount(item.montant_courtier)}</div>
                        </div>
                        <div>
                            <span class="sos-alert-card__label">Frais de service MHC</span>
                            <div class="sos-alert-card__value">${formatAmount(item.montant_mh)}</div>
                        </div>
                    </div>
                </div>
                ${actionBlock}
            </div>
        </li>`;
}

function renderTransactions() {
    const list = document.getElementById(TRANSACTIONS_LIST_ID);
    if (!list) {
        return;
    }

    const showActions = shouldShowActions();

    const filtered = accountingState.transactions.filter((item) => {
        const matchesSearch = filterBySearch(item);
        const matchesStatus =
            accountingState.filters.status === 'all' ||
            (item.status_code || '') === accountingState.filters.status;
        return matchesSearch && matchesStatus;
    });

    if (!filtered.length) {
        setListPlaceholder('Aucune transaction trouvée avec les filtres appliqués.');
        return;
    }

    list.innerHTML = filtered.map((item) => buildTransactionCard(item, showActions)).join('');
    if (typeof paginateList === 'function') {
        paginateList(TRANSACTIONS_LIST_ID);
    }
}

function filterBySearch(item) {
    const term = accountingState.filters.search;
    if (!term) {
        return true;
    }

    const haystack = [
        item.numero_souscription || '',
        item.assure || '',
        item.assureur_nom || '',
        item.produit_nom || '',
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
            useGrouping: true,
        });
    } catch {
        return new Intl.NumberFormat('fr-FR', {
            maximumFractionDigits: 0,
            useGrouping: true,
        }).format(numeric) + (currencyHelper.getSymbol ? ` ${currencyHelper.getSymbol()}` : ' F\u00a0CFA');
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
    return `<span class="status-badge ${badgeClass}">${escapeHtml(label)}</span>`;
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

