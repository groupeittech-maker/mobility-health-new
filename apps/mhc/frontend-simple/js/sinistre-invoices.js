const SINISTRE_ALLOWED_ROLES = ['sos_operator', 'agent_sinistre_mh', 'agent_medical_mhc', 'superviseur_affaires_medicales', 'agent_conformite_medical', 'admin'];
const SINISTRE_ACTION_ROLES = ['agent_medical_mhc', 'superviseur_affaires_medicales', 'agent_conformite_medical', 'admin'];
const HISTORY_ACTION_LABELS = {
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

let invoices = [];
let filteredInvoices = [];
let selectedInvoiceId = null;
let currentStageFilter = 'all';
let searchTerm = '';
let currentUserRole = null;

document.addEventListener('DOMContentLoaded', async () => {
    const isValid = await requireAuth();
    // Même règle que le backend (_invoice_query_with_access) : la consultation
    // des factures hospitalières exige facturation_medicale OU sinistres —
    // le médecin-conseil (medecin_referent_mh) y accède pour la validation.
    const allowed = isValid && window.MhPermissions && (
        window.MhPermissions.can('facturation_medicale', 'consultation') ||
        window.MhPermissions.can('sinistres', 'consultation')
    );
    if (!allowed) {
        if (isValid) {
            alert('Accès refusé. Permission requise : facturation_medicale ou sinistres (consultation).');
            redirectForbidden('bo-dashboard.html');
        }
        return;
    }
    currentUserRole = localStorage.getItem('user_role');
    bindSinistreInvoiceEvents();
    await fetchSinistreInvoices();
    updateSosNavCounts();
});

async function updateSosNavCounts() {
    try {
        // Le médecin-conseil traite l'étape « accord médical » (pending_medical),
        // les affaires médicales l'étape sinistre (pending_sinistre).
        const pendingStage = (localStorage.getItem('user_role') === 'medecin_referent_mh') ? 'medical' : 'sinistre';
        const [invoicesData, alertesData] = await Promise.all([
            apiCall(`/invoices?stage=${pendingStage}&limit=200`),
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
    const tbody = document.getElementById('invoiceTableBody');
    const wrapper = document.getElementById('invoiceTableWrapper');
    const empty = document.getElementById('invoiceListEmpty');
    const counter = document.getElementById('invoiceCount');
    if (!tbody || !wrapper || !empty) {
        return;
    }
    empty.hidden = !!filteredInvoices.length;
    wrapper.hidden = !filteredInvoices.length;
    const countLabel = filteredInvoices.length <= 1 ? 'facture' : 'factures';
    if (counter) {
        counter.textContent = `${filteredInvoices.length} ${countLabel}`;
    }
    if (!filteredInvoices.length) {
        tbody.innerHTML = '';
        return;
    }
    tbody.innerHTML = filteredInvoices
        .map((invoice) => {
            const sinistreLabel =
                invoice.sinistre?.numero_sinistre || `Sinistre #${invoice.sinistre?.id || '—'}`;
            const hospitalName = invoice.hospital?.nom || `Hôpital #${invoice.hospital_id}`;
            const selectedClass = invoice.id === selectedInvoiceId ? 'row-selected' : '';
            return `
                <tr class="${selectedClass}" data-invoice-id="${invoice.id}">
                    <td><strong>${escapeHtml(invoice.numero_facture)}</strong></td>
                    <td>${escapeHtml(sinistreLabel)}</td>
                    <td>${escapeHtml(hospitalName)}</td>
                    <td>${formatCurrency(invoice.montant_ttc)}</td>
                    <td><span class="status-badge">${escapeHtml(getInvoiceStatusLabel(invoice.statut))}</span></td>
                    <td>${formatDateTime(invoice.created_at)}</td>
                    <td>
                        <button type="button" class="btn btn-outline btn-sm sinistre-detail-btn" data-invoice-id="${invoice.id}">
                            Détails &amp; validation
                        </button>
                    </td>
                </tr>
            `;
        })
        .join('');

    const selectInvoice = (invoiceId) => {
        if (!Number.isFinite(invoiceId)) return;
        selectedInvoiceId = invoiceId;
        renderInvoiceList();
        renderInvoiceDetail();
    };

    tbody.querySelectorAll('tr[data-invoice-id]').forEach((row) => {
        row.addEventListener('click', (event) => {
            if (event.target.closest('.sinistre-detail-btn')) return;
            selectInvoice(Number(row.getAttribute('data-invoice-id')));
        });
    });
    tbody.querySelectorAll('.sinistre-detail-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            selectInvoice(Number(btn.getAttribute('data-invoice-id')));
        });
    });
}

function renderInvoiceDetail() {
    const panel = document.getElementById('invoiceDetailPanel');
    if (!panel) {
        return;
    }
    const closeDrawer = () => {
        panel.hidden = true;
        panel.innerHTML = '';
        document.body.classList.remove('mh-drawer-open');
        const backdrop = document.getElementById('invoiceDrawerBackdrop');
        if (backdrop) backdrop.hidden = true;
    };
    if (!selectedInvoiceId) {
        closeDrawer();
        return;
    }
    const invoice = filteredInvoices.find((item) => item.id === selectedInvoiceId);
    if (!invoice) {
        closeDrawer();
        return;
    }
    panel.hidden = false;
    document.body.classList.add('mh-drawer-open');
    const backdrop = document.getElementById('invoiceDrawerBackdrop');
    if (backdrop) {
        backdrop.hidden = false;
        backdrop.onclick = () => {
            selectedInvoiceId = null;
            renderInvoiceList();
            renderInvoiceDetail();
        };
    }

    const hospitalName = invoice.hospital?.nom || `Hôpital #${invoice.hospital_id}`;
    const sinistreLabel =
        invoice.sinistre?.numero_sinistre || `Sinistre #${invoice.sinistre?.id || '—'}`;
    const dossierLink = invoice.sinistre?.id
        ? `<a href="sinistre-detail.html?id=${invoice.sinistre.id}">Ouvrir le dossier</a>`
        : '';

    panel.innerHTML = `
        <div class="detail-header">
            <div>
                <h3>${escapeHtml(invoice.numero_facture)}</h3>
                <p class="muted">Montant TTC : ${formatCurrency(invoice.montant_ttc)}</p>
            </div>
            <div style="display:flex;align-items:center;gap:0.75rem;">
                <span class="status-badge">${escapeHtml(getInvoiceStatusLabel(invoice.statut))}</span>
                <button type="button" class="btn btn-outline btn-sm" id="sinistreCloseDetailBtn">✕ Fermer</button>
            </div>
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
        ${renderDecisionBlock(invoice)}
        <div class="mh-suivi-block">
            <h4>Suivi du dossier</h4>
            <div class="timeline">
                ${renderTimelineItem('Médecin-conseil', invoice.validation_medicale)}
                ${renderTimelineItem('Affaires médicales', invoice.validation_sinistre)}
                ${renderTimelineItem('Comptabilité', comptaTimelineState(invoice))}
            </div>
        </div>
        <div class="history-block">
            <h4>Historique des actions</h4>
            <div id="sinistreHistory" class="history-list"></div>
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
    `;

    const closeBtn = document.getElementById('sinistreCloseDetailBtn');
    if (closeBtn) {
        closeBtn.onclick = () => {
            selectedInvoiceId = null;
            renderInvoiceList();
            renderInvoiceDetail();
        };
    }

    const approveBtn = document.getElementById('sinistreApproveBtn');
    const rejectBtn = document.getElementById('sinistreRejectBtn');
    if (approveBtn) approveBtn.onclick = () => handleSinistreInvoiceDecision(true);
    if (rejectBtn) rejectBtn.onclick = () => handleSinistreInvoiceDecision(false);
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

function comptaTimelineState(invoice) {
    // Le circuit actuel ne passe plus par validation_compta : la comptabilité
    // paie directement la facture validée. L'étape suit donc le statut réel —
    // sinon une facture payée affichait « Non démarré ».
    if (invoice.statut === 'paid') return 'paid';
    if (invoice.statut === 'validated') return 'pending';
    return invoice.validation_compta || null;
}

function renderTimelineItem(label, state) {
    const map = {
        approved: { text: 'Validé', cls: 'pill-success' },
        paid: { text: 'Payée', cls: 'pill-success' },
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

function renderDecisionBlock(invoice) {
    // Bloc contextuel : visible uniquement si l'utilisateur a une action réelle —
    // des boutons « Valider » désactivés sur une facture déjà validée étaient
    // contradictoires avec le suivi du dossier. Le paiement du comptable se
    // fait sur « Factures médicales », pas ici.
    const canValidate = canValidateInvoiceMedical(invoice) || canValidateInvoiceSinistre(invoice);
    if (!canValidate) return '';
    return `
        <div class="mh-decision-block">
            <div class="form-group">
                <label for="sinistreDecisionNotes">Notes pour l'historique</label>
                <textarea id="sinistreDecisionNotes" rows="2" placeholder="Commentaire visible par les équipes"></textarea>
            </div>
            <div class="form-actions">
                <button class="btn btn-success" id="sinistreApproveBtn">Valider la facture</button>
                <button class="btn btn-danger" id="sinistreRejectBtn">Rejeter la facture</button>
            </div>
        </div>
    `;
}

function canValidateInvoiceMedical(invoice) {
    // Étape 9 : première validation — médecin-conseil (require_medecin_conseil).
    return (
        invoice &&
        invoice.statut === 'pending_medical' &&
        ['medecin_referent_mh', 'admin'].includes(currentUserRole || '')
    );
}

function canValidateInvoiceSinistre(invoice) {
    return (
        invoice &&
        invoice.statut === 'pending_sinistre' &&
        (SINISTRE_ACTION_ROLES.includes(currentUserRole || '') ||
            (window.MhPermissions && window.MhPermissions.can('sinistres', 'controle')))
    );
}

async function handleSinistreInvoiceDecision(approve) {
    const notesField = document.getElementById('sinistreDecisionNotes');
    const notes = notesField?.value.trim() || undefined;
    const approveBtn = document.getElementById('sinistreApproveBtn');
    const rejectBtn = document.getElementById('sinistreRejectBtn');
    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;
    const invoice = invoices.find(i => i.id === selectedInvoiceId);
    const endpoint = invoice && invoice.statut === 'pending_medical' ? 'validate_medical' : 'validate_sinistre';
    try {
        await apiCall(`/invoices/${selectedInvoiceId}/${endpoint}`, {
            method: 'POST',
            body: JSON.stringify({ approve, notes }),
        });
        const actor = endpoint === 'validate_medical' ? 'le médecin-conseil' : 'les affaires médicales';
        showAlert(
            approve ? `Facture validée par ${actor}.` : `Facture refusée par ${actor}.`,
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

