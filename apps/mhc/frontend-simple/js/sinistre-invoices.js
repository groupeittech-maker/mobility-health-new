const SINISTRE_ALLOWED_ROLES = ['sos_operator', 'agent_sinistre_mh', 'admin'];
const SINISTRE_ACTION_ROLES = ['sos_operator', 'agent_sinistre_mh', 'admin'];
const HISTORY_ACTION_LABELS = {
    invoice_created: 'Facture créée',
    medical_validation_approved: 'Accord médical',
    medical_validation_rejected: 'Rejet médical',
    sinistre_validation_approved: 'Validation pôle sinistre',
    sinistre_validation_rejected: 'Rejet pôle sinistre',
    compta_validation_approved: 'Validation comptable',
    compta_validation_rejected: 'Rejet comptable',
};

let invoices = [];
let filteredInvoices = [];
let selectedInvoiceId = null;
let currentStageFilter = 'sinistre';
let searchTerm = '';
let currentUserRole = null;

document.addEventListener('DOMContentLoaded', async () => {
    const allowed = await requireAnyRole(SINISTRE_ALLOWED_ROLES, 'login.html');
    if (!allowed) {
        return;
    }
    currentUserRole = localStorage.getItem('user_role');
    bindSinistreInvoiceEvents();
    await fetchSinistreInvoices();
    updateSosNavCounts();
});

async function updateSosNavCounts() {
    try {
        const [invoicesData, alertesData] = await Promise.all([
            apiCall('/invoices?stage=sinistre&limit=200'),
            apiCall('/sos/?realtime=true&limit=500'),
        ]);
        const facturesCount = Array.isArray(invoicesData) ? invoicesData.length : 0;
        const alertesCount = Array.isArray(alertesData) ? alertesData.length : 0;
        const navFactures = document.getElementById('navFactures');
        const navTableauSos = document.getElementById('navTableauSos');
        if (navFactures) navFactures.textContent = facturesCount > 0 ? `Factures (${facturesCount})` : 'Factures';
        if (navTableauSos) navTableauSos.textContent = alertesCount > 0 ? `Tableau SOS (${alertesCount})` : 'Tableau SOS';
    } catch (_) {
        const navFactures = document.getElementById('navFactures');
        const navTableauSos = document.getElementById('navTableauSos');
        if (navFactures) navFactures.textContent = 'Factures';
        if (navTableauSos) navTableauSos.textContent = 'Tableau SOS';
    }
}

function bindSinistreInvoiceEvents() {
    const stageFilter = document.getElementById('stageFilter');
    stageFilter?.addEventListener('change', async (event) => {
        currentStageFilter = event.target.value;
        await fetchSinistreInvoices();
    });

    const searchInput = document.getElementById('invoiceSearch');
    searchInput?.addEventListener('input', (event) => {
        searchTerm = event.target.value.trim().toLowerCase();
        applyInvoiceFilter();
    });

    document.getElementById('refreshInvoicesBtn')?.addEventListener('click', fetchSinistreInvoices);
}

async function fetchSinistreInvoices() {
    const listEmpty = document.getElementById('invoiceListEmpty');
    const list = document.getElementById('invoiceList');
    if (listEmpty) listEmpty.hidden = false;
    if (list) list.innerHTML = '';
    try {
        const params = new URLSearchParams();
        if (currentStageFilter && currentStageFilter !== 'all') {
            params.set('stage', currentStageFilter);
        }
        params.set('limit', '200');
        const data = await apiCall(`/invoices?${params.toString()}`);
        invoices = Array.isArray(data) ? data : [];
        applyInvoiceFilter();
        updateSosNavCounts();
    } catch (error) {
        console.error('Erreur chargement factures:', error);
        showAlert(error.message || 'Impossible de charger les factures.', 'error');
        invoices = [];
        filteredInvoices = [];
        renderInvoiceList();
        renderInvoiceDetail();
        updateSosNavCounts();
    }
}

function applyInvoiceFilter() {
    if (!searchTerm) {
        filteredInvoices = invoices.slice();
    } else {
        filteredInvoices = invoices.filter((invoice) => {
            const facture = (invoice.numero_facture || '').toLowerCase();
            const numeroSinistre = (invoice.sinistre?.numero_sinistre || '').toLowerCase();
            return facture.includes(searchTerm) || numeroSinistre.includes(searchTerm);
        });
    }
    if (!filteredInvoices.some((invoice) => invoice.id === selectedInvoiceId)) {
        selectedInvoiceId = filteredInvoices.length ? filteredInvoices[0].id : null;
    }
    renderInvoiceList();
    renderInvoiceDetail();
}

function renderInvoiceList() {
    const list = document.getElementById('invoiceList');
    const empty = document.getElementById('invoiceListEmpty');
    const counter = document.getElementById('invoiceCount');
    if (!list || !empty) {
        return;
    }
    empty.hidden = !!filteredInvoices.length;
    const countLabel = filteredInvoices.length <= 1 ? 'facture' : 'factures';
    if (counter) {
        counter.textContent = `${filteredInvoices.length} ${countLabel}`;
    }
    if (!filteredInvoices.length) {
        list.innerHTML = '';
        return;
    }
    list.innerHTML = filteredInvoices
        .map((invoice) => {
            const sinistreLabel =
                invoice.sinistre?.numero_sinistre || `Sinistre #${invoice.sinistre?.id || '—'}`;
            const hospitalName = invoice.hospital?.nom || `Hôpital #${invoice.hospital_id}`;
            const selectedClass = invoice.id === selectedInvoiceId ? 'selected' : '';
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
                selectedInvoiceId = invoiceId;
                renderInvoiceList();
                renderInvoiceDetail();
            }
        });
    });
}

function renderInvoiceDetail() {
    const panel = document.getElementById('invoiceDetailPanel');
    if (!panel) {
        return;
    }
    if (!selectedInvoiceId) {
        panel.innerHTML = '<p class="muted">Sélectionnez une facture pour afficher ses détails.</p>';
        return;
    }
    const invoice = filteredInvoices.find((item) => item.id === selectedInvoiceId);
    if (!invoice) {
        panel.innerHTML = '<p class="muted">Facture introuvable.</p>';
        return;
    }

    const hospitalName = invoice.hospital?.nom || `Hôpital #${invoice.hospital_id}`;
    const sinistreLabel =
        invoice.sinistre?.numero_sinistre || `Sinistre #${invoice.sinistre?.id || '—'}`;
    const dossierLink = invoice.sinistre?.alerte_id
        ? `<a href="hospital-alert-details.html?alert_id=${invoice.sinistre.alerte_id}">Ouvrir le dossier</a>`
        : '';

    panel.innerHTML = `
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
            <div id="invoiceItemsContainer"><p class="muted">Chargement du détail...</p></div>
            <div class="invoice-totals">
                <p><strong>Montant HT :</strong> ${formatCurrency(invoice.montant_ht)}</p>
                <p><strong>TVA :</strong> ${formatCurrency(invoice.montant_tva)}</p>
                <p><strong>Montant TTC :</strong> ${formatCurrency(invoice.montant_ttc)}</p>
            </div>
        </div>
        <div class="timeline">
            ${renderTimelineItem('Accord médical', invoice.validation_medicale)}
            ${renderTimelineItem('Pôle sinistre', invoice.validation_sinistre)}
            ${renderTimelineItem('Comptabilité', invoice.validation_compta)}
        </div>
        <div class="history-block">
            <h4>Historique des actions</h4>
            <div id="sinistreHistory" class="history-list"></div>
        </div>
        <div class="form-group">
            <label for="sinistreDecisionNotes">Notes pour l\'historique</label>
            <textarea id="sinistreDecisionNotes" rows="3" placeholder="Commentaire visible par les équipes"></textarea>
        </div>
        <div class="form-actions">
            <button class="btn btn-success" id="sinistreApproveBtn">Valider la facture</button>
            <button class="btn btn-danger" id="sinistreRejectBtn">Rejeter la facture</button>
        </div>
    `;

    const canAct = canValidateInvoiceSinistre(invoice);
    const approveBtn = document.getElementById('sinistreApproveBtn');
    const rejectBtn = document.getElementById('sinistreRejectBtn');
    const notesField = document.getElementById('sinistreDecisionNotes');
    if (!canAct) {
        approveBtn.disabled = true;
        rejectBtn.disabled = true;
        if (notesField) {
            notesField.disabled = true;
        }
    } else {
        approveBtn.onclick = () => handleSinistreInvoiceDecision(true);
        rejectBtn.onclick = () => handleSinistreInvoiceDecision(false);
    }
    loadInvoiceHistory(invoice.id, 'sinistreHistory');
    loadInvoiceItems(invoice.id);
}

async function loadInvoiceItems(invoiceId) {
    const container = document.getElementById('invoiceItemsContainer');
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
        console.error('Erreur chargement détail facture:', error);
        container.innerHTML = '<p class="muted">Impossible d\'afficher le détail de la facture.</p>';
    }
}

function renderTimelineItem(label, state) {
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

function canValidateInvoiceSinistre(invoice) {
    return (
        invoice &&
        invoice.statut === 'pending_sinistre' &&
        SINISTRE_ACTION_ROLES.includes(currentUserRole || '')
    );
}

async function handleSinistreInvoiceDecision(approve) {
    const notesField = document.getElementById('sinistreDecisionNotes');
    const notes = notesField?.value.trim() || undefined;
    const approveBtn = document.getElementById('sinistreApproveBtn');
    const rejectBtn = document.getElementById('sinistreRejectBtn');
    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;
    try {
        await apiCall(`/invoices/${selectedInvoiceId}/validate_sinistre`, {
            method: 'POST',
            body: JSON.stringify({ approve, notes }),
        });
        showAlert(
            approve ? 'Facture validée par le pôle sinistre.' : 'Facture rejetée par le pôle sinistre.',
            approve ? 'success' : 'warning'
        );
        await fetchSinistreInvoices();
    } catch (error) {
        console.error('Erreur validation sinistre:', error);
        showAlert(error.message || 'Impossible de traiter la facture.', 'error');
        if (approveBtn) approveBtn.disabled = false;
        if (rejectBtn) rejectBtn.disabled = false;
    }
}

async function loadInvoiceHistory(invoiceId, containerId) {
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
                ${history.map(renderHistoryItem).join('')}
            </ul>
        `;
    } catch (error) {
        console.error('Erreur historique facture:', error);
        container.innerHTML = '<p class="muted">Impossible de charger l’historique.</p>';
    }
}

function renderHistoryItem(entry) {
    const label = HISTORY_ACTION_LABELS[entry.action] || entry.action;
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

