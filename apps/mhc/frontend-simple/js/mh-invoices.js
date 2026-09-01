const MH_ALLOWED_ROLES =
    window.MH_ALLOWED_ROLES_OVERRIDE || ['agent_comptable_mh', 'finance_manager', 'admin'];
const MH_ACTION_ROLES = ['agent_comptable_mh', 'finance_manager', 'admin'];
const MH_HISTORY_ACTIONS = {
    invoice_created: 'Facture créée',
    medical_validation_approved: 'Accord médical',
    medical_validation_rejected: 'Rejet médical',
    sinistre_validation_approved: 'Validation pôle sinistre',
    sinistre_validation_rejected: 'Rejet pôle sinistre',
    compta_validation_approved: 'Validation comptable',
    compta_validation_rejected: 'Rejet comptable',
};

let mhInvoices = [];
let mhFilteredInvoices = [];
let mhSelectedInvoiceId = null;
let mhStageFilter = 'compta';
let mhSearchTerm = '';
let mhUserRole = null;

document.addEventListener('DOMContentLoaded', async () => {
    const allowed = await requireAnyRole(MH_ALLOWED_ROLES, 'login.html');
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
    if (mhStageFilter === 'validated' || mhStageFilter === 'rejected') {
        params.set('statut', mhStageFilter === 'validated' ? 'validated' : 'rejected');
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
    const list = document.getElementById('mhInvoiceList');
    const empty = document.getElementById('mhInvoiceEmpty');
    const counter = document.getElementById('mhInvoiceCount');
    if (!list || !empty) {
        return;
    }
    empty.hidden = !!mhFilteredInvoices.length;
    const label = mhFilteredInvoices.length <= 1 ? 'facture' : 'factures';
    if (counter) {
        counter.textContent = `${mhFilteredInvoices.length} ${label}`;
    }
    if (!mhFilteredInvoices.length) {
        list.innerHTML = '';
        return;
    }
    list.innerHTML = mhFilteredInvoices
        .map((invoice) => {
            const sinistreLabel =
                invoice.sinistre?.numero_sinistre || `Sinistre #${invoice.sinistre?.id || '—'}`;
            const hospitalName = invoice.hospital?.nom || `Hôpital #${invoice.hospital_id}`;
            const selectedClass = invoice.id === mhSelectedInvoiceId ? 'selected' : '';
            return `
                <li class="card ${selectedClass}" data-invoice-id="${invoice.id}">
                    <div class="card-title">
                        <strong>${escapeHtml(invoice.numero_facture)}</strong>
                        <span class="status-badge">${escapeHtml(getInvoiceStatusLabel(invoice.statut))}</span>
                    </div>
                    <p class="muted">${escapeHtml(sinistreLabel)}</p>
                    <p class="muted">${escapeHtml(hospitalName)}</p>
                    <p class="muted">Montant TTC : ${formatCurrency(invoice.montant_ttc)}</p>
                </li>
            `;
        })
        .join('');

    list.querySelectorAll('li.card').forEach((item) => {
        item.addEventListener('click', () => {
            const invoiceId = Number(item.getAttribute('data-invoice-id'));
            if (Number.isFinite(invoiceId)) {
                mhSelectedInvoiceId = invoiceId;
                renderMhInvoiceList();
                renderMhInvoiceDetail();
            }
        });
    });
}

function renderMhInvoiceDetail() {
    const container = document.getElementById('mhInvoiceDetail');
    if (!container) {
        return;
    }
    if (!mhSelectedInvoiceId) {
        container.innerHTML = '<p class="muted">Sélectionnez une facture pour afficher ses détails.</p>';
        return;
    }
    const invoice = mhFilteredInvoices.find((item) => item.id === mhSelectedInvoiceId);
    if (!invoice) {
        container.innerHTML = '<p class="muted">Facture introuvable.</p>';
        return;
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
            <span class="status-badge">${escapeHtml(getInvoiceStatusLabel(invoice.statut))}</span>
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
        <div class="timeline">
            ${renderMhTimelineItem('Accord médical', invoice.validation_medicale)}
            ${renderMhTimelineItem('Pôle sinistre', invoice.validation_sinistre)}
            ${renderMhTimelineItem('Comptabilité', invoice.validation_compta)}
        </div>
        <div class="history-block">
            <h4>Historique des actions</h4>
            <div id="mhHistory" class="history-list"></div>
        </div>
        <div class="form-group">
            <label for="mhDecisionNotes">Notes internes</label>
            <textarea id="mhDecisionNotes" rows="3" placeholder="Commentaire visible par le pôle sinistre"></textarea>
        </div>
        <div class="form-actions">
            <button class="btn btn-success" id="mhApproveBtn">Valider (payer)</button>
            <button class="btn btn-danger" id="mhRejectBtn">Rejeter la facture</button>
        </div>
    `;

    const canAct = canValidateInvoiceCompta(invoice);
    const approveBtn = document.getElementById('mhApproveBtn');
    const rejectBtn = document.getElementById('mhRejectBtn');
    const notesField = document.getElementById('mhDecisionNotes');
    if (!canAct) {
        if (approveBtn) approveBtn.disabled = true;
        if (rejectBtn) rejectBtn.disabled = true;
        if (notesField) notesField.disabled = true;
    } else {
        approveBtn.onclick = () => handleMhInvoiceDecision(true);
        rejectBtn.onclick = () => handleMhInvoiceDecision(false);
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

function canValidateInvoiceCompta(invoice) {
    return (
        invoice &&
        invoice.statut === 'pending_compta' &&
        MH_ACTION_ROLES.includes(mhUserRole || '')
    );
}

async function handleMhInvoiceDecision(approve) {
    const notesField = document.getElementById('mhDecisionNotes');
    const notes = notesField?.value.trim() || undefined;
    const approveBtn = document.getElementById('mhApproveBtn');
    const rejectBtn = document.getElementById('mhRejectBtn');
    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;
    try {
        await apiCall(`/invoices/${mhSelectedInvoiceId}/validate_compta`, {
            method: 'POST',
            body: JSON.stringify({ approve, notes }),
        });
        showAlert(
            approve ? 'Facture validée comptablement.' : 'Facture rejetée par la comptabilité.',
            approve ? 'success' : 'warning'
        );
        await fetchMhInvoices();
    } catch (error) {
        console.error('Erreur validation comptable:', error);
        showAlert(error.message || 'Impossible de traiter la facture.', 'error');
        if (approveBtn) approveBtn.disabled = false;
        if (rejectBtn) rejectBtn.disabled = false;
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
            <div class="history-item-header">
                <strong>${escapeHtml(label)}</strong> <span class="muted">${actor}</span>
            </div>
            <div class="history-meta">
                <span>${formatDateTime(entry.created_at)}</span>
                ${statusLabel ? `<span class="pill">${escapeHtml(statusLabel)}</span>` : ''}
            </div>
            ${notes}
        </li>
    `;
}

function getInvoiceStatusLabel(status) {
    const map = {
        pending_medical: 'En attente accord médical',
        pending_sinistre: 'En attente pôle sinistre',
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

