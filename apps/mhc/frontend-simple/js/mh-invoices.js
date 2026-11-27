const MH_ALLOWED_ROLES =
    window.MH_ALLOWED_ROLES_OVERRIDE || ['agent_comptable_mh', 'finance_manager', 'admin'];
const MH_ACTION_ROLES = ['agent_comptable_mh', 'finance_manager', 'admin'];
const MH_HISTORY_ACTIONS = {
    invoice_created: 'Facture créée',
    medical_validation_approved: 'Validation médecin-conseil',
    medical_validation_rejected: 'Refus médecin-conseil',
    sinistre_validation_approved: 'Validation affaires médicales',
    sinistre_validation_rejected: 'Refus affaires médicales',
    affaires_medicales_validation_approved: 'Validation affaires médicales',
    affaires_medicales_validation_rejected: 'Refus affaires médicales',
    compta_validation_approved: 'Validation comptable',
    compta_validation_rejected: 'Rejet comptable',
    invoice_paid: 'Facture payée',
    invoice_blocked: 'Facture bloquée',
    invoice_unblocked: 'Facture débloquée',
    reassureur_agrement_approved: 'Agrément réassureur accordé',
    reassureur_agrement_rejected: 'Agrément réassureur refusé',
};

let mhInvoices = [];
let mhFilteredInvoices = [];
let mhSelectedInvoiceId = null;
let mhStageFilter = 'all';
let mhSearchTerm = '';
let mhUserRole = null;

document.addEventListener('DOMContentLoaded', async () => {
    const allowed = window.MH_ALLOWED_ROLES_OVERRIDE
        ? await requireAnyRole(MH_ALLOWED_ROLES, 'login.html')
        : await requirePermission('facturation_medicale', 'consultation', 'bo-dashboard.html');
    if (!allowed) {
        return;
    }
    mhUserRole = localStorage.getItem('user_role');
    bindMhInvoiceEvents();
    await fetchMhInvoices();
});

function bindMhInvoiceEvents() {
    const stageSelect = document.getElementById('mhStageFilter');
    const searchInput = document.getElementById('mhInvoiceSearch');
    const refreshBtn = document.getElementById('mhRefreshBtn');

    stageSelect?.addEventListener('change', async (event) => {
        mhStageFilter = event.target.value;
        await fetchMhInvoices();
    });

    searchInput?.addEventListener('input', (event) => {
        mhSearchTerm = event.target.value.trim().toLowerCase();
        applyMhInvoiceFilter();
    });

    refreshBtn?.addEventListener('click', fetchMhInvoices);
}

function buildMhInvoiceParams() {
    const params = new URLSearchParams();
    params.set('limit', '200');
    if (['validated', 'rejected', 'paid'].includes(mhStageFilter)) {
        params.set('statut', mhStageFilter);
    } else if (mhStageFilter !== 'all') {
        // stage values accepted by API: medical, sinistre, compta
        params.set('stage', mhStageFilter);
    }
    return params.toString();
}

async function fetchMhInvoices() {
    const listEmpty = document.getElementById('mhInvoiceEmpty');
    const list = document.getElementById('mhInvoiceList');
    if (listEmpty) listEmpty.hidden = false;
    if (list) list.innerHTML = '';
    try {
        const data = await apiCall(`/invoices?${buildMhInvoiceParams()}`);
        mhInvoices = Array.isArray(data) ? data : [];
        applyMhInvoiceFilter();
    } catch (error) {
        console.error('Erreur chargement factures compta:', error);
        showAlert(error.message || 'Impossible de charger les factures.', 'error');
        mhInvoices = [];
        mhFilteredInvoices = [];
        renderMhInvoiceList();
        renderMhInvoiceDetail();
    }
}

function applyMhInvoiceFilter() {
    if (!mhSearchTerm) {
        mhFilteredInvoices = mhInvoices.slice();
    } else {
        mhFilteredInvoices = mhInvoices.filter((invoice) => {
            const facture = (invoice.numero_facture || '').toLowerCase();
            const sinistre = (invoice.sinistre?.numero_sinistre || '').toLowerCase();
            return facture.includes(mhSearchTerm) || sinistre.includes(mhSearchTerm);
        });
    }
    if (!mhFilteredInvoices.some((invoice) => invoice.id === mhSelectedInvoiceId)) {
        mhSelectedInvoiceId = mhFilteredInvoices.length ? mhFilteredInvoices[0].id : null;
    }
    renderMhInvoiceList();
    renderMhInvoiceDetail();
}

function renderMhInvoiceList() {
    const tbody = document.getElementById('mhInvoiceTableBody');
    const wrapper = document.getElementById('mhInvoiceTableWrapper');
    const empty = document.getElementById('mhInvoiceEmpty');
    const counter = document.getElementById('mhInvoiceCount');
    if (!tbody || !wrapper || !empty) {
        return;
    }
    empty.hidden = !!mhFilteredInvoices.length;
    wrapper.hidden = !mhFilteredInvoices.length;
    const label = mhFilteredInvoices.length <= 1 ? 'facture' : 'factures';
    if (counter) {
        counter.textContent = `${mhFilteredInvoices.length} ${label}`;
    }
    if (!mhFilteredInvoices.length) {
        tbody.innerHTML = '';
        return;
    }
    tbody.innerHTML = mhFilteredInvoices
        .map((invoice) => {
            const sinistreLabel =
                invoice.sinistre?.numero_sinistre || `Sinistre #${invoice.sinistre?.id || '—'}`;
            const hospitalName = invoice.hospital?.nom || `Hôpital #${invoice.hospital_id}`;
            const selectedClass = invoice.id === mhSelectedInvoiceId ? 'row-selected' : '';
            const blocked = invoice.bloquee ? ' <span class="pill pill-danger">Bloquée</span>' : '';
            return `
                <tr class="${selectedClass}" data-invoice-id="${invoice.id}">
                    <td><strong>${escapeHtml(invoice.numero_facture)}</strong></td>
                    <td>${escapeHtml(sinistreLabel)}</td>
                    <td>${escapeHtml(hospitalName)}</td>
                    <td>${formatCurrency(invoice.montant_ttc)}</td>
                    <td><span class="status-badge">${escapeHtml(getInvoiceStatusLabel(invoice.statut))}</span>${blocked}</td>
                    <td>${formatDateTime(invoice.created_at)}</td>
                    <td>
                        <button type="button" class="btn btn-outline btn-sm mh-detail-btn" data-invoice-id="${invoice.id}">
                            Détails &amp; validation
                        </button>
                    </td>
                </tr>
            `;
        })
        .join('');

    const selectInvoice = (invoiceId, scroll) => {
        if (!Number.isFinite(invoiceId)) return;
        mhSelectedInvoiceId = invoiceId;
        renderMhInvoiceList();
        renderMhInvoiceDetail();
        if (scroll) {
            document.getElementById('mhInvoiceDetail')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    tbody.querySelectorAll('tr[data-invoice-id]').forEach((row) => {
        row.addEventListener('click', (event) => {
            if (event.target.closest('.mh-detail-btn')) return;
            selectInvoice(Number(row.getAttribute('data-invoice-id')), false);
        });
    });
    tbody.querySelectorAll('.mh-detail-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            selectInvoice(Number(btn.getAttribute('data-invoice-id')), true);
        });
    });
}

function renderMhInvoiceDetail() {
    const container = document.getElementById('mhInvoiceDetail');
    if (!container) {
        return;
    }
    const closeDrawer = () => {
        container.hidden = true;
        container.innerHTML = '';
        document.body.classList.remove('mh-drawer-open');
        const backdrop = document.getElementById('mhDrawerBackdrop');
        if (backdrop) backdrop.hidden = true;
    };
    if (!mhSelectedInvoiceId) {
        closeDrawer();
        return;
    }
    const invoice = mhFilteredInvoices.find((item) => item.id === mhSelectedInvoiceId);
    if (!invoice) {
        closeDrawer();
        return;
    }
    container.hidden = false;
    document.body.classList.add('mh-drawer-open');
    const backdrop = document.getElementById('mhDrawerBackdrop');
    if (backdrop) {
        backdrop.hidden = false;
        backdrop.onclick = () => {
            mhSelectedInvoiceId = null;
            renderMhInvoiceList();
            renderMhInvoiceDetail();
        };
    }
    const hospitalName = invoice.hospital?.nom || `Hôpital #${invoice.hospital_id}`;
    const sinistreLabel =
        invoice.sinistre?.numero_sinistre || `Sinistre #${invoice.sinistre?.id || '—'}`;
    const dossierLink = invoice.sinistre?.alerte_id
        ? `<a href="hospital-alert-details.html?alert_id=${invoice.sinistre.alerte_id}">Ouvrir le dossier</a>`
        : '';

    container.innerHTML = `
        <div class="detail-header">
            <div>
                <h3>${escapeHtml(invoice.numero_facture)}</h3>
                <p class="muted">Montant TTC : ${formatCurrency(invoice.montant_ttc)}</p>
            </div>
            <div style="display:flex;align-items:center;gap:0.75rem;">
                <span class="status-badge">${escapeHtml(getInvoiceStatusLabel(invoice.statut))}</span>
                <button type="button" class="btn btn-outline btn-sm" id="mhCloseDetailBtn">✕ Fermer</button>
            </div>
        </div>
        <div class="mh-decision-block">
            ${invoice.bloquee ? '<p class="pill pill-danger">Facture bloquée</p>' : ''}
            ${invoice.reassureur_agrement === 'en_attente' ? '<p class="pill">Plafond dépassé — agrément du réassureur requis</p>' : ''}
            ${invoice.reassureur_agrement === 'approuve' ? '<p class="pill pill-success">Agrément réassureur accordé</p>' : ''}
            <div class="form-group">
                <label for="mhDecisionNotes">Notes internes</label>
                <textarea id="mhDecisionNotes" rows="2" placeholder="Commentaire interne"></textarea>
            </div>
            <div class="form-actions">
                <button class="btn btn-success" id="mhApproveBtn">Payer la facture</button>
                <button class="btn btn-danger" id="mhRejectBtn">Rejeter la facture</button>
                <button class="btn" id="mhBlockBtn">${invoice.bloquee ? 'Débloquer' : 'Bloquer'}</button>
                <button class="btn btn-success" id="mhAgrementBtn" hidden>Enregistrer l’agrément réassureur</button>
            </div>
        </div>
        <div class="mh-suivi-block">
            <h4>Suivi du dossier</h4>
            <div class="timeline">
                ${renderMhTimelineItem('Médecin-conseil', invoice.validation_medicale)}
                ${renderMhTimelineItem('Affaires médicales', invoice.validation_sinistre)}
                ${renderMhTimelineItem('Paiement', invoice.statut === 'paid' ? 'approved' : (invoice.statut === 'validated' ? 'pending' : null))}
            </div>
        </div>
        <div class="history-block">
            <h4>Historique des actions</h4>
            <div id="mhHistory" class="history-list"></div>
        </div>
        <div class="detail-grid">
            <div>
                <strong>Hôpital</strong>
                <p>${escapeHtml(hospitalName)}</p>
            </div>
            <div>
                <strong>Sinistre</strong>
                <p>${escapeHtml(sinistreLabel)}</p>
                ${dossierLink ? `<p>${dossierLink}</p>` : ''}
            </div>
            <div>
                <strong>Date facture</strong>
                <p>${formatDateTime(invoice.date_facture)}</p>
            </div>
            <div>
                <strong>Créée le</strong>
                <p>${formatDateTime(invoice.created_at)}</p>
            </div>
        </div>
        <div class="invoice-content-block">
            <h4>Contenu de la facture</h4>
            <div id="mhInvoiceItemsContainer"><p class="muted">Chargement du détail...</p></div>
            <div class="invoice-totals">
                <p><strong>Montant HT :</strong> ${formatCurrency(invoice.montant_ht)}</p>
                <p><strong>TVA :</strong> ${formatCurrency(invoice.montant_tva)}</p>
                <p><strong>Montant TTC :</strong> ${formatCurrency(invoice.montant_ttc)}</p>
            </div>
        </div>
    `;

    const closeBtn = document.getElementById('mhCloseDetailBtn');
    if (closeBtn) {
        closeBtn.onclick = () => {
            mhSelectedInvoiceId = null;
            renderMhInvoiceList();
            renderMhInvoiceDetail();
        };
    }

    const notesField = document.getElementById('mhDecisionNotes');
    const approveBtn = document.getElementById('mhApproveBtn');
    const rejectBtn = document.getElementById('mhRejectBtn');
    const blockBtn = document.getElementById('mhBlockBtn');
    const agrementBtn = document.getElementById('mhAgrementBtn');

    const canPay = canPayInvoice(invoice);
    const isLegacyCompta = invoice.statut === 'pending_compta';
    if (approveBtn) {
        approveBtn.hidden = !(canPay || isLegacyCompta);
        approveBtn.disabled = !(canPay || isLegacyCompta);
        if (isLegacyCompta) approveBtn.textContent = 'Valider comptablement';
        else approveBtn.textContent = 'Payer la facture';
        approveBtn.onclick = () => handleMhInvoiceDecision(true);
    }
    if (rejectBtn) {
        rejectBtn.hidden = !isLegacyCompta;
        rejectBtn.disabled = !isLegacyCompta;
        rejectBtn.onclick = () => handleMhInvoiceDecision(false);
    }
    const canBlock = invoice.statut !== 'paid' && canActOnInvoice();
    if (blockBtn) {
        blockBtn.hidden = !canBlock;
        blockBtn.onclick = () => handleMhInvoiceBlock(!invoice.bloquee);
    }
    if (agrementBtn) {
        agrementBtn.hidden = !(invoice.reassureur_agrement === 'en_attente' && canActOnInvoice());
        agrementBtn.onclick = () => handleMhAgrement();
    }

    loadInvoiceHistory(invoice.id, 'mhHistory', MH_HISTORY_ACTIONS);
    loadMhInvoiceItems(invoice.id);
}

async function loadMhInvoiceItems(invoiceId) {
    const container = document.getElementById('mhInvoiceItemsContainer');
    if (!container) {
        return;
    }
    try {
        const full = await apiCall(`/invoices/${invoiceId}`);
        const items = full.items || [];
        if (!items.length) {
            container.innerHTML = '<p class="muted">Aucune ligne de facture.</p>';
            return;
        }
        container.innerHTML = `
            <table class="invoice-items-table">
                <thead>
                    <tr>
                        <th>Libellé</th>
                        <th class="num">Qté</th>
                        <th class="num">Prix unitaire</th>
                        <th class="num">Montant HT</th>
                        <th class="num">Montant TTC</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map((item) => `
                        <tr>
                            <td>${escapeHtml(item.libelle)}</td>
                            <td class="num">${escapeHtml(String(item.quantite))}</td>
                            <td class="num">${formatCurrency(item.prix_unitaire)}</td>
                            <td class="num">${formatCurrency(item.montant_ht)}</td>
                            <td class="num">${formatCurrency(item.montant_ttc)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        console.error('Erreur chargement détail facture (compta):', error);
        container.innerHTML = '<p class="muted">Impossible d\'afficher le détail de la facture.</p>';
    }
}

function renderMhTimelineItem(label, state) {
    const map = {
        approved: { text: 'Validé', cls: 'pill-success' },
        rejected: { text: 'Rejeté', cls: 'pill-danger' },
        pending: { text: 'En attente', cls: 'pill' },
        null: { text: 'Non démarré', cls: 'pill' },
    };
    const key = state || 'null';
    const info = map[key] || map.null;
    return `
        <div class="timeline-item">
            <span class="timeline-label">${escapeHtml(label)}</span>
            <span class="pill ${info.cls}">${escapeHtml(info.text)}</span>
        </div>
    `;
}

function canActOnInvoice() {
    return (
        MH_ACTION_ROLES.includes(mhUserRole || '') ||
        (window.MhPermissions && window.MhPermissions.can('facturation_medicale', 'controle'))
    );
}

/** Étape 11 : facture validée, non bloquée, agrément réassureur obtenu si requis. */
function canPayInvoice(invoice) {
    return (
        invoice &&
        invoice.statut === 'validated' &&
        !invoice.bloquee &&
        [null, undefined, 'approuve'].includes(invoice.reassureur_agrement) &&
        canActOnInvoice()
    );
}

async function handleMhInvoiceDecision(approve) {
    const notesField = document.getElementById('mhDecisionNotes');
    const notes = notesField?.value.trim() || undefined;
    const approveBtn = document.getElementById('mhApproveBtn');
    const rejectBtn = document.getElementById('mhRejectBtn');
    const invoice = mhFilteredInvoices.find((item) => item.id === mhSelectedInvoiceId);
    const isLegacyCompta = invoice && invoice.statut === 'pending_compta';
    const endpoint = isLegacyCompta ? 'validate_compta' : 'pay';
    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;
    try {
        await apiCall(`/invoices/${mhSelectedInvoiceId}/${endpoint}`, {
            method: 'POST',
            body: JSON.stringify({ approve, notes }),
        });
        showAlert(
            isLegacyCompta
                ? (approve ? 'Facture validée comptablement.' : 'Facture rejetée par la comptabilité.')
                : 'Facture payée. Le dossier est réglé.',
            'success'
        );
        await fetchMhInvoices();
    } catch (error) {
        console.error('Erreur paiement facture:', error);
        showAlert(error.message || 'Impossible de traiter la facture.', 'error');
        if (approveBtn) approveBtn.disabled = false;
        if (rejectBtn) rejectBtn.disabled = false;
    }
}

async function handleMhInvoiceBlock(bloquee) {
    const notesField = document.getElementById('mhDecisionNotes');
    const notes = notesField?.value.trim() || undefined;
    try {
        await apiCall(`/invoices/${mhSelectedInvoiceId}/block`, {
            method: 'POST',
            body: JSON.stringify({ bloquee, notes }),
        });
        showAlert(bloquee ? 'Facture bloquée.' : 'Facture débloquée.', 'success');
        await fetchMhInvoices();
    } catch (error) {
        showAlert(error.message || 'Impossible de modifier le blocage.', 'error');
    }
}

async function handleMhAgrement() {
    const notesField = document.getElementById('mhDecisionNotes');
    const notes = notesField?.value.trim() || undefined;
    try {
        await apiCall(`/invoices/${mhSelectedInvoiceId}/reassureur-agrement`, {
            method: 'POST',
            body: JSON.stringify({ approve: true, notes }),
        });
        showAlert('Agrément du réassureur enregistré.', 'success');
        await fetchMhInvoices();
    } catch (error) {
        showAlert(error.message || 'Impossible d’enregistrer l’agrément.', 'error');
    }
}

async function loadInvoiceHistory(invoiceId, containerId, actionLabels) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    container.innerHTML = '<p class="muted">Chargement de l’historique...</p>';
    try {
        const history = await apiCall(`/invoices/${invoiceId}/history`);
        if (!history.length) {
            container.innerHTML = '<p class="muted">Aucun événement enregistré.</p>';
            return;
        }
        container.innerHTML = `
            <ul class="history-list">
                ${history.map((entry) => renderMhHistoryItem(entry, actionLabels)).join('')}
            </ul>
        `;
    } catch (error) {
        console.error('Erreur historique facture (compta):', error);
        container.innerHTML = '<p class="muted">Impossible de charger l’historique.</p>';
    }
}

function renderMhHistoryItem(entry, actionLabels) {
    const label = actionLabels[entry.action] || entry.action;
    const actor = entry.actor_name ? `par ${escapeHtml(entry.actor_name)}` : '';
    const statusLabel = entry.new_status ? getInvoiceStatusLabel(entry.new_status) : '';
    const notes = entry.notes ? `<div class="history-note">${escapeHtml(entry.notes)}</div>` : '';
    return `
        <li class="history-item">
            <span class="history-date">${formatDateTime(entry.created_at)}</span>
            <strong class="history-action">${escapeHtml(label)}</strong>
            ${statusLabel ? `<span class="pill">${escapeHtml(statusLabel)}</span>` : ''}
            <span class="history-actor muted">${actor}</span>
            ${notes}
        </li>
    `;
}

function getInvoiceStatusLabel(status) {
    const map = {
        pending_medical: 'En attente accord médical',
        pending_sinistre: 'En attente affaires médicales',
        pending_compta: 'En attente comptabilité MH',
        validated: 'Validée',
        rejected: 'Refusée',
        paid: 'Payée',
    };
    return map[status] || (status ? status : 'Inconnu');
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

function formatCurrency(value) {
    if (value === null || value === undefined) {
        return '—';
    }
    const numberValue = Number(value);
    if (Number.isNaN(numberValue)) {
        return value;
    }
    return numberValue.toLocaleString('fr-FR', { style: 'currency', currency: 'XAF' });
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
        minute: '2-digit',
    });
}

