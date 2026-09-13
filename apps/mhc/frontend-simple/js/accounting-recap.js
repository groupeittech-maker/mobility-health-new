/**
 * Onglet « Récapitulatif » du portail comptable MH.
 * Agrège /payments/accounting/transactions avec filtres dynamiques :
 * période, poste (assureur / courtier / réassureur / produit / mois / statut)
 * et présente les montants totaux par groupe + ligne TOTAL.
 */
const recapState = {
    transactions: [],
    loaded: false,
    filters: {
        period: 'all',
        dateFrom: '',
        dateTo: '',
        groupBy: 'assureur',
        assureur: 'all',
        courtier: 'all',
        reassureur: 'all',
        status: 'all',
    },
};

const RECAP_SHARE_KEYS = [
    'montant_total',
    'montant_assureur',
    'montant_courtier',
    'montant_reassureur',
    'montant_ekyc',
    'montant_mh',
    'montant_assure',
];

function escapeHtmlRecap(s) {
    if (s == null) return '';
    const div = document.createElement('div');
    div.textContent = String(s);
    return div.innerHTML;
}

function formatRecapAmount(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '—';
    try {
        if (typeof formatPortalCurrency === 'function') {
            return formatPortalCurrency(numeric);
        }
    } catch (_) {}
    return numeric.toLocaleString('fr-FR', {
        style: 'currency',
        currency: 'XAF',
        maximumFractionDigits: 0,
    });
}

function parseRecapDate(value) {
    if (!value) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
}

function recapPeriodRange() {
    const now = new Date();
    const { period, dateFrom, dateTo } = recapState.filters;
    if (period === 'custom') {
        return {
            from: dateFrom ? new Date(`${dateFrom}T00:00:00`) : null,
            to: dateTo ? new Date(`${dateTo}T23:59:59`) : null,
        };
    }
    if (period === 'month') {
        return {
            from: new Date(now.getFullYear(), now.getMonth(), 1),
            to: null,
        };
    }
    if (period === 'last_month') {
        return {
            from: new Date(now.getFullYear(), now.getMonth() - 1, 1),
            to: new Date(now.getFullYear(), now.getMonth(), 0, 23, 59, 59),
        };
    }
    if (period === 'quarter') {
        const qStart = Math.floor(now.getMonth() / 3) * 3;
        return { from: new Date(now.getFullYear(), qStart, 1), to: null };
    }
    if (period === 'year') {
        return { from: new Date(now.getFullYear(), 0, 1), to: null };
    }
    return { from: null, to: null };
}

function recapMatchesFilters(item) {
    const { assureur, courtier, reassureur, status } = recapState.filters;
    if (status !== 'all' && (item.status_code || '') !== status) return false;
    if (assureur !== 'all' && (item.assureur_nom || '—') !== assureur) return false;
    if (courtier !== 'all' && (item.courtier_nom || '—') !== courtier) return false;
    if (reassureur !== 'all' && (item.reassureur_nom || '—') !== reassureur) return false;

    const { from, to } = recapPeriodRange();
    if (from || to) {
        const d = parseRecapDate(item.date_paiement);
        if (!d) return false;
        if (from && d < from) return false;
        if (to && d > to) return false;
    }
    return true;
}

function recapGroupKey(item) {
    switch (recapState.filters.groupBy) {
        case 'assureur':
            return item.assureur_nom || '—';
        case 'courtier':
            return item.courtier_nom || '—';
        case 'reassureur':
            return item.reassureur_nom || '—';
        case 'produit':
            return item.produit_nom || '—';
        case 'mois': {
            const d = parseRecapDate(item.date_paiement);
            if (!d) return '—';
            return `${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
        }
        case 'statut':
            return item.statut_transaction || item.status_code || '—';
        default:
            return 'Toutes les transactions';
    }
}

const RECAP_GROUP_LABELS = {
    assureur: 'Assureur',
    courtier: 'Courtier',
    reassureur: 'Réassureur',
    produit: 'Produit',
    mois: 'Mois',
    statut: 'Statut',
    all: 'Périmètre',
};

function populateRecapSelect(selectId, values) {
    const el = document.getElementById(selectId);
    if (!el) return;
    const current = el.value;
    el.innerHTML =
        '<option value="all">Tous</option>' +
        values.map((v) => `<option value="${escapeHtmlRecap(v)}">${escapeHtmlRecap(v)}</option>`).join('');
    el.value = values.includes(current) ? current : 'all';
}

function populateRecapFilters() {
    const txs = recapState.transactions;
    const unique = (fn) =>
        [...new Set(txs.map(fn).filter((v) => v && v !== '—'))].sort((a, b) => a.localeCompare(b, 'fr'));
    populateRecapSelect('recapAssureur', unique((t) => t.assureur_nom || '—'));
    populateRecapSelect('recapCourtier', unique((t) => t.courtier_nom || '—'));
    populateRecapSelect('recapReassureur', unique((t) => t.reassureur_nom || '—'));
}

function renderRecapTable() {
    const tbody = document.getElementById('recapTableBody');
    const tfoot = document.getElementById('recapTableFoot');
    const groupHeader = document.getElementById('recapGroupHeader');
    if (!tbody || !tfoot) return;

    if (groupHeader) {
        groupHeader.textContent =
            RECAP_GROUP_LABELS[recapState.filters.groupBy] || 'Groupe';
    }

    const filtered = recapState.transactions.filter(recapMatchesFilters);

    // Agrégation par groupe
    const groups = new Map();
    for (const tx of filtered) {
        const key = recapGroupKey(tx);
        if (!groups.has(key)) {
            const acc = { count: 0 };
            for (const k of RECAP_SHARE_KEYS) acc[k] = 0;
            groups.set(key, acc);
        }
        const acc = groups.get(key);
        acc.count += 1;
        for (const k of RECAP_SHARE_KEYS) acc[k] += Number(tx[k] || 0);
    }

    const rows = [...groups.entries()].sort((a, b) => b[1].montant_total - a[1].montant_total);

    if (!rows.length) {
        tbody.innerHTML =
            '<tr><td colspan="9" class="muted">Aucune transaction avec les filtres appliqués.</td></tr>';
        tfoot.innerHTML = '';
        return;
    }

    tbody.innerHTML = rows
        .map(
            ([key, acc]) => `
            <tr>
                <td>${escapeHtmlRecap(key)}</td>
                <td>${acc.count}</td>
                <td><strong>${formatRecapAmount(acc.montant_total)}</strong></td>
                <td>${formatRecapAmount(acc.montant_assureur)}</td>
                <td>${formatRecapAmount(acc.montant_courtier)}</td>
                <td>${formatRecapAmount(acc.montant_reassureur)}</td>
                <td>${formatRecapAmount(acc.montant_ekyc)}</td>
                <td>${formatRecapAmount(acc.montant_mh)}</td>
                <td>${formatRecapAmount(acc.montant_assure)}</td>
            </tr>`
        )
        .join('');

    const total = { count: 0 };
    for (const k of RECAP_SHARE_KEYS) total[k] = 0;
    for (const [, acc] of rows) {
        total.count += acc.count;
        for (const k of RECAP_SHARE_KEYS) total[k] += acc[k];
    }
    tfoot.innerHTML = `
        <tr style="font-weight:700; border-top:2px solid var(--border-color);">
            <td>TOTAL</td>
            <td>${total.count}</td>
            <td>${formatRecapAmount(total.montant_total)}</td>
            <td>${formatRecapAmount(total.montant_assureur)}</td>
            <td>${formatRecapAmount(total.montant_courtier)}</td>
            <td>${formatRecapAmount(total.montant_reassureur)}</td>
            <td>${formatRecapAmount(total.montant_ekyc)}</td>
            <td>${formatRecapAmount(total.montant_mh)}</td>
            <td>${formatRecapAmount(total.montant_assure)}</td>
        </tr>`;

    if (typeof paginateTable === 'function') {
        paginateTable('recapTableBody');
    }
}

async function loadRecapTransactions() {
    const tbody = document.getElementById('recapTableBody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="9" class="muted">Chargement en cours...</td></tr>';
    }
    try {
        // Réutilise les transactions déjà chargées/enrichies par l'onglet
        // « Frais & remboursements » si disponibles, sinon appel dédié.
        if (
            window.accountingState &&
            Array.isArray(window.accountingState.transactions) &&
            window.accountingState.transactions.length
        ) {
            recapState.transactions = window.accountingState.transactions;
        } else {
            const data = await apiCall('/payments/accounting/transactions');
            recapState.transactions = Array.isArray(data) ? data : [];
        }
        recapState.loaded = true;
        populateRecapFilters();
        renderRecapTable();
    } catch (error) {
        console.error('Erreur chargement récapitulatif:', error);
        if (tbody) {
            tbody.innerHTML =
                '<tr><td colspan="9" class="muted">Erreur lors du chargement.</td></tr>';
        }
    }
}

function initRecapFilters() {
    const bind = (id, key, rerender = true) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('change', (e) => {
            recapState.filters[key] = e.target.value;
            if (key === 'period') {
                const custom = e.target.value === 'custom';
                const fromWrap = document.getElementById('recapFromWrap');
                const toWrap = document.getElementById('recapToWrap');
                if (fromWrap) fromWrap.hidden = !custom;
                if (toWrap) toWrap.hidden = !custom;
            }
            if (rerender) renderRecapTable();
        });
    };

    bind('recapPeriod', 'period');
    bind('recapDateFrom', 'dateFrom');
    bind('recapDateTo', 'dateTo');
    bind('recapGroupBy', 'groupBy');
    bind('recapAssureur', 'assureur');
    bind('recapCourtier', 'courtier');
    bind('recapReassureur', 'reassureur');
    bind('recapStatus', 'status');

    document
        .getElementById('recapReloadBtn')
        ?.addEventListener('click', loadRecapTransactions);
}

document.addEventListener('DOMContentLoaded', () => {
    // L'accès est déjà contrôlé par accounting-portal.js (rôles comptables MH).
    initRecapFilters();
    loadRecapTransactions();
});
