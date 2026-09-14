(function () {
    const API = window.API_BASE_URL || '';
    let currentData = null;

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    function formatMoney(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
        return Number(value).toLocaleString('fr-FR') + ' FCFA';
    }

    function formatNumber(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
        return Number(value).toLocaleString('fr-FR');
    }

    function renderCard(containerId, title, value, sub) {
        const container = $(containerId);
        if (!container) return;
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `<h3>${title}</h3><p>${value}</p>${sub ? `<small>${sub}</small>` : ''}`;
        container.appendChild(card);
    }

    function clearContainer(selector) {
        const el = $(selector);
        if (el) el.innerHTML = '';
    }

    function renderBarChart(containerId, dataMap, valueKey = null) {
        const container = $(containerId);
        if (!container) return;
        container.innerHTML = '';
        const entries = Object.entries(dataMap || {});
        if (!entries.length) {
            container.innerHTML = '<p class="muted">Aucune donnée</p>';
            return;
        }
        const max = Math.max(...entries.map(([, v]) => (valueKey && typeof v === 'object' ? v[valueKey] : v)) || [0]);
        entries.forEach(([key, value]) => {
            const val = valueKey && typeof value === 'object' ? value[valueKey] : value;
            const label = key === 'null' || key === 'None' ? 'Non renseigné' : key;
            const row = document.createElement('div');
            row.className = 'bar-row';
            const pct = max ? (Math.max(0, val) / max) * 100 : 0;
            row.innerHTML = `
                <div class="bar-label">${label}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:${pct}%"></div>
                </div>
                <div class="bar-value">${valueKey ? formatMoney(val) : formatNumber(val)}</div>
            `;
            container.appendChild(row);
        });
    }

    function renderTableBody(tbodyId, rows, columns) {
        const tbody = $(tbodyId);
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!rows || !rows.length) {
            tbody.innerHTML = `<tr><td colspan="${columns.length}" class="muted">Aucune donnée</td></tr>`;
            return;
        }
        rows.forEach((row) => {
            const tr = document.createElement('tr');
            tr.innerHTML = columns.map((col) => `<td${col.num ? ' class="num"' : ''}>${col.render(row)}</td>`).join('');
            tbody.appendChild(tr);
        });
    }

    function buildQueryParams() {
        const params = new URLSearchParams();
        const start = $('#filterStart').value;
        const end = $('#filterEnd').value;
        if (start) params.set('start_date', start);
        if (end) params.set('end_date', end);
        const produit = $('#filterProduit').value;
        if (produit) params.set('produit_id', produit);
        const assureur = $('#filterAssureur').value;
        if (assureur) params.set('assureur_id', assureur);
        const courtier = $('#filterCourtier').value;
        if (courtier) params.set('courtier_id', courtier);
        const pays = $('#filterPays').value.trim();
        if (pays) params.set('pays', pays);
        const canal = $('#filterCanal').value;
        if (canal) params.set('canal', canal);
        return params.toString();
    }

    async function loadFilters() {
        try {
            const [products, assureurs, courtiers] = await Promise.all([
                apiCall('/products'),
                apiCall('/admin/assureurs'),
                apiCall('/courtiers'),
            ]);
            const pSel = $('#filterProduit');
            (products || []).forEach((p) => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.nom || p.code || p.id;
                pSel.appendChild(opt);
            });
            const aSel = $('#filterAssureur');
            (assureurs || []).forEach((a) => {
                const opt = document.createElement('option');
                opt.value = a.id;
                opt.textContent = a.nom || a.id;
                aSel.appendChild(opt);
            });
            const cSel = $('#filterCourtier');
            (courtiers || []).forEach((c) => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.nom || c.id;
                cSel.appendChild(opt);
            });
        } catch (e) {
            console.error('Erreur chargement filtres:', e);
        }
    }

    async function loadStatistics() {
        const qs = buildQueryParams();
        try {
            currentData = await apiCall(`/admin/statistics?${qs}`, { method: 'GET' });
            renderAll(currentData);
            $('#statsExportBtn').disabled = false;
        } catch (e) {
            console.error('Erreur statistiques:', e);
            alert('Impossible de charger les statistiques.');
        }
    }

    function renderOverview(data) {
        const k = data.overview.kpis;
        clearContainer('#overviewCards');
        renderCard('#overviewCards', 'Souscriptions', formatNumber(k.total_subscriptions));
        renderCard('#overviewCards', 'Paiements confirmés', formatNumber(k.total_payments));
        renderCard('#overviewCards', 'Montant encaissé', formatMoney(k.collected_amount));
        renderCard('#overviewCards', 'En attente paiement', formatMoney(k.pending_payment_amount));
        renderCard('#overviewCards', 'Utilisateurs', formatNumber(k.total_users));
        renderCard('#overviewCards', 'Sinistres', formatNumber(k.total_claims));
        renderCard('#overviewCards', 'Taux conversion', `${k.conversion_rate}%`);
        renderBarChart('#overviewStatusBars', data.overview.subscriptions_by_status);
    }

    function renderSubscriptions(data) {
        const s = data.subscriptions.summary;
        clearContainer('#subscriptionsCards');
        renderCard('#subscriptionsCards', 'Total', formatNumber(s.total_count));
        renderCard('#subscriptionsCards', 'Montant total', formatMoney(s.total_prix));
        renderCard('#subscriptionsCards', 'Prime nette', formatMoney(s.total_prime));
        renderCard('#subscriptionsCards', 'Panier moyen', formatMoney(s.average_prix));
        renderCard('#subscriptionsCards', 'Taux refus', `${s.refused_rate}%`);
        renderTableBody('#subscriptionsByProduct', data.subscriptions.by_product, [
            { render: (r) => r.name },
            { num: true, render: (r) => formatNumber(r.count) },
            { num: true, render: (r) => formatMoney(r.amount) },
        ]);
        renderTableBody('#subscriptionsByAssureur', data.subscriptions.by_assureur, [
            { render: (r) => r.name },
            { num: true, render: (r) => formatNumber(r.count) },
            { num: true, render: (r) => formatMoney(r.amount) },
        ]);
        renderTableBody('#subscriptionsByCourtier', data.subscriptions.by_courtier, [
            { render: (r) => r.name },
            { num: true, render: (r) => formatNumber(r.count) },
            { num: true, render: (r) => formatMoney(r.amount) },
        ]);
    }

    function renderPayments(data) {
        const s = data.payments.summary;
        clearContainer('#paymentsCards');
        renderCard('#paymentsCards', 'Transactions', formatNumber(s.total_count));
        renderCard('#paymentsCards', 'Montant total', formatMoney(s.total_amount));
        renderCard('#paymentsCards', 'Moyenne', formatMoney(s.average_amount));
        renderCard('#paymentsCards', 'Taux succès', `${s.success_rate}%`);
        renderCard('#paymentsCards', 'Remboursements', formatMoney(s.refund_amount));
        renderBarChart('#paymentsStatusBars', data.payments.by_status, 'count');
        renderBarChart('#paymentsTypeBars', data.payments.by_type, 'count');
    }

    function renderClaims(data) {
        const s = data.claims.summary;
        clearContainer('#claimsCards');
        renderCard('#claimsCards', 'Sinistres', formatNumber(s.total_claims));
        renderCard('#claimsCards', 'Actives', formatNumber(s.active_subscriptions));
        renderCard('#claimsCards', 'Taux sinistralité', `${s.claims_rate}%`);
        renderCard('#claimsCards', 'Montant prestations', formatMoney(s.total_prestation_amount));
        renderCard('#claimsCards', 'Moyenne prestation', formatMoney(s.average_prestation_amount));
        renderTableBody('#claimsTopPrestations', data.claims.top_prestations, [
            { render: (r) => r.label },
            { num: true, render: (r) => r.code },
            { num: true, render: (r) => formatNumber(r.count) },
            { num: true, render: (r) => formatMoney(r.amount) },
        ]);
    }

    function renderReviews(data) {
        const s = data.reviews.summary;
        clearContainer('#reviewsCards');
        renderCard('#reviewsCards', 'En attente médical', formatNumber(s.medical_pending));
        renderCard('#reviewsCards', 'En attente production', formatNumber(s.production_pending));
        renderCard('#reviewsCards', 'Approbations médicales', formatNumber(s.medical_approved));
        renderCard('#reviewsCards', 'Rejets médicaux', formatNumber(s.medical_rejected));
        renderCard('#reviewsCards', 'Taux approbation', `${s.medical_approval_rate}%`);
        renderBarChart('#medicalStatusBars', data.reviews.medical_by_status);
        renderBarChart('#productionStatusBars', data.reviews.production_by_status);
    }

    function renderFinance(data) {
        const s = data.finance.summary;
        clearContainer('#financeCards');
        renderCard('#financeCards', 'Prix total', formatMoney(s.total_prix));
        renderCard('#financeCards', 'Prime nette', formatMoney(s.total_prime));
        renderCard('#financeCards', 'Encaissé', formatMoney(s.total_collected));
        renderCard('#financeCards', 'Chargement', formatMoney(s.chargement_total));
        renderCard('#financeCards', 'Frais eKYC estimés', formatMoney(s.ekyc_fees_estimate));
        renderTableBody('#financeByAssureur', data.finance.by_assureur, [
            { render: (r) => r.name },
            { num: true, render: (r) => formatNumber(r.count) },
            { num: true, render: (r) => formatMoney(r.prime) },
        ]);
        renderTableBody('#financeByCourtier', data.finance.by_courtier, [
            { render: (r) => r.name },
            { num: true, render: (r) => formatNumber(r.count) },
            { num: true, render: (r) => formatMoney(r.prime) },
        ]);
    }

    function renderUsers(data) {
        const s = data.users.summary;
        clearContainer('#usersCards');
        renderCard('#usersCards', 'Utilisateurs', formatNumber(s.total_users));
        renderCard('#usersCards', 'Souscriptions / utilisateur', formatNumber(s.subscriptions_per_user));
        renderBarChart('#usersCountryBars', data.users.by_country);
        renderBarChart('#usersRoleBars', data.users.by_role);
    }

    function renderProducts(data) {
        const s = data.products.summary;
        clearContainer('#productsCards');
        renderCard('#productsCards', 'Durée moyenne (jours)', formatNumber(s.average_trip_duration_days));
        renderBarChart('#topProductsBars', data.products.top_products.reduce((m, r) => { m[r.name] = r.count; return m; }, {}));
        renderBarChart('#topDestinationsBars', data.products.top_destinations.reduce((m, r) => { m[r.name] = r.count; return m; }, {}));
    }

    function renderEkyc(data) {
        const s = data.ekyc.summary;
        clearContainer('#ekycCards');
        renderCard('#ekycCards', 'Sessions', formatNumber(s.total_sessions));
        renderCard('#ekycCards', 'Taux succès', `${s.success_rate}%`);
        renderCard('#ekycCards', 'Bloquées', formatNumber(s.blocked_sessions));
        renderBarChart('#ekycStatusBars', data.ekyc.by_status);
    }

    function renderAll(data) {
        renderOverview(data);
        renderSubscriptions(data);
        renderPayments(data);
        renderClaims(data);
        renderReviews(data);
        renderFinance(data);
        renderUsers(data);
        renderProducts(data);
        renderEkyc(data);
    }

    function initTabs() {
        $$('.tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                $$('.tab-btn').forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                const section = btn.dataset.section;
                $$('main > .dashboard-section').forEach((sec) => {
                    if (sec.id === section) sec.removeAttribute('hidden');
                    else sec.setAttribute('hidden', '');
                });
            });
        });
    }

    function initExport() {
        $('#statsExportBtn').addEventListener('click', () => {
            if (!currentData) return;
            const blob = new Blob([JSON.stringify(currentData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `statistiques_${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
        });
    }

    async function init() {
        initTabs();
        await loadFilters();
        $('#statsReloadBtn').addEventListener('click', loadStatistics);
        initExport();
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        $('#filterStart').value = firstDay.toISOString().slice(0, 10);
        $('#filterEnd').value = today.toISOString().slice(0, 10);
        await loadStatistics();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
