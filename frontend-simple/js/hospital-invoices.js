const ACCOUNTANT_ROLES = ['agent_comptable_hopital', 'hospital_admin'];
const DEFAULT_TVA = 0.18;
const HOURLY_RATE = 15000;
const DEFAULT_ACT_PRICE = 20000;
const DEFAULT_EXAM_PRICE = 15000;

const ACT_PRICES = {
    'Consultation médicale': 25000,
    'Stabilisation des fonctions vitales': 40000,
    "Pose d'une perfusion": 18000,
    "Administration de médicaments": 15000,
    'Injection': 12000,
    'Immobilisation / plâtre': 35000,
    'Suture / pansement': 22000,
    'Surveillance post-opératoire': 30000,
};

const EXAM_PRICES = {
    'Analyse sanguine': 20000,
    'Analyse urinaire': 8000,
    'Radiographie': 28000,
    'Scanner': 60000,
    'IRM': 85000,
    'ECG': 18000,
    'Échographie': 32000,
    'Test COVID / grippe': 15000,
};

const numberFormatter = new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0,
});

const INVOICE_STATUS_LABELS = {
    pending_medical: 'En attente accord médical',
    pending_sinistre: 'En attente pôle sinistre',
    pending_compta: 'En attente comptabilité MH',
    validated: 'Validée',
    rejected: 'Refusée',
};

const VALIDATION_STAGE_LABELS = {
    validation_medicale: {
        approved: 'Accord médical',
        rejected: 'Refus médical',
        pending: 'En attente',
    },
    validation_sinistre: {
        approved: 'Bon pour paiement',
        rejected: 'Refus paiement',
        pending: 'En attente',
    },
    validation_compta: {
        approved: 'Paiement validé',
        rejected: 'Blocage comptable',
        pending: 'En attente',
    },
};

const VALIDATION_STATUS_LABELS = {
    approved: 'Validé',
    pending: 'En attente',
    rejected: 'Rejeté',
};

const ROWS_PER_PAGE = 6;
let currentPageStays = 0;

const state = {
    hospitalId: null,
    stays: [],
    filters: {
        status: 'validated',
        report: 'approved',
        invoice: 'none',
        search: '',
    },
    selectedStayId: null,
    tva: DEFAULT_TVA,
    notes: '',
    isLoading: false,
    isSubmitting: false,
    stats: {
        readyCount: 0,
        potentialHt: 0,
    },
    catalog: {
        hourlyRate: HOURLY_RATE,
        defaultActPrice: DEFAULT_ACT_PRICE,
        defaultExamPrice: DEFAULT_EXAM_PRICE,
    },
    invoiceDraft: {
        stayId: null,
        lines: [],
    },
    invoiceLineCounter: 0,
    actTarifs: {},
    actTarifsList: [],
    examTarifs: {},
    examTarifsList: [],
    isCatalogLoading: false,
    catalogError: '',
    catalogFeedback: '',
    catalogFeedbackType: 'success',
    catalogSections: {
        acts: true,
        exams: true,
    },
};

document.addEventListener('DOMContentLoaded', () => {
    initHospitalInvoicesPage();
});

async function initHospitalInvoicesPage() {
    const allowed = await requireAnyRole(ACCOUNTANT_ROLES, 'hospital-dashboard.html');
    if (!allowed) {
        return;
    }

    const hospitalId = parseInt(localStorage.getItem('hospital_id') || '', 10);
    if (!hospitalId) {
        showAlert('Aucun hôpital n’est rattaché à votre compte. Contactez un administrateur.', 'error');
        disableInterface();
        return;
    }

    state.hospitalId = hospitalId;
    bindFilterEvents();
    bindInvoiceEvents();
    bindCatalogEvents();
    await loadMedicalCatalog();

    const params = new URLSearchParams(window.location.search);
    const stayIdParam = params.get('stay_id');
    if (stayIdParam) {
        const stayId = parseInt(stayIdParam, 10);
        if (Number.isFinite(stayId)) {
            await openStayById(stayId);
            return;
        }
    }
    await fetchStays();
}

async function openStayById(stayId) {
    const loadingEl = document.getElementById('staysLoading');
    const empty = document.getElementById('staysEmpty');
    const list = document.getElementById('staysList');
    if (loadingEl) loadingEl.hidden = false;
    if (empty) empty.hidden = true;
    if (list) list.hidden = true;

    try {
        const stay = await apiCall(`/hospital-sinistres/hospital-stays/${stayId}`);
        state.stays = Array.isArray(stay) ? stay : [stay];
        state.selectedStayId = stay.id;
        computeStats();
        renderStats();
        renderStayList();
        renderDetails();
    } catch (error) {
        console.error('Erreur lors du chargement du séjour:', error);
        showAlert(error.message || 'Impossible de charger ce dossier.', 'error');
        state.stays = [];
        state.selectedStayId = null;
        await fetchStays();
    } finally {
        if (loadingEl) loadingEl.hidden = true;
    }
}

function disableInterface() {
    document.getElementById('staysLoading')?.classList.add('disabled');
    document.getElementById('detailsPlaceholder')?.classList.add('disabled');
    document.querySelectorAll('select, input, textarea, button').forEach((el) => {
        el.disabled = true;
    });
}

function bindFilterEvents() {
    const statusSelect = document.getElementById('filterStatus');
    const reportSelect = document.getElementById('filterReport');
    const invoiceSelect = document.getElementById('filterInvoice');
    const searchInput = document.getElementById('filterSearch');

    statusSelect?.addEventListener('change', (event) => {
        state.filters.status = event.target.value;
        fetchStays();
    });

    reportSelect?.addEventListener('change', (event) => {
        state.filters.report = event.target.value;
        fetchStays();
    });

    invoiceSelect?.addEventListener('change', (event) => {
        state.filters.invoice = event.target.value;
        fetchStays();
    });

    let searchTimer = null;
    searchInput?.addEventListener('input', (event) => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            state.filters.search = event.target.value.trim();
            fetchStays();
        }, 300);
    });
}

function bindInvoiceEvents() {
    const tvaInput = document.getElementById('tvaInput');
    const notesInput = document.getElementById('invoiceNotes');
    const generateBtn = document.getElementById('generateInvoiceBtn');

    tvaInput?.addEventListener('input', (event) => {
        const value = parseFloat(event.target.value);
        if (Number.isFinite(value)) {
            state.tva = clamp(value, 0, 1);
        } else {
            state.tva = DEFAULT_TVA;
        }
        updateTvaDisplay();
        renderDetails();
    });

    notesInput?.addEventListener('input', (event) => {
        state.notes = event.target.value;
    });

    generateBtn?.addEventListener('click', () => {
        if (!state.selectedStayId) {
            return;
        }
        createInvoice(state.selectedStayId);
    });

    bindInvoiceEditorEvents();
}

function bindInvoiceEditorEvents() {
    const linesContainer = document.getElementById('invoiceLines');
    const addLineBtn = document.getElementById('addCustomLineBtn');
    const resetBtn = document.getElementById('resetInvoiceLinesBtn');
    if (linesContainer) {
        linesContainer.addEventListener('input', handleInvoiceLineInput);
        linesContainer.addEventListener('click', handleInvoiceLineClick);
    }
    addLineBtn?.addEventListener('click', handleAddCustomLine);
    resetBtn?.addEventListener('click', handleResetInvoiceLines);
}

function handleInvoiceLineInput(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
        return;
    }
    const row = target.closest('tr[data-line-id]');
    const lineId = row?.getAttribute('data-line-id');
    if (!lineId || target.disabled) {
        return;
    }
    const stay = getSelectedStay();
    if (!stay || stay.invoice) {
        return;
    }
    let updatedLine = null;
    if (target.classList.contains('line-label-input')) {
        updatedLine = updateInvoiceLine(lineId, { label: target.value }, { skipRender: true });
    } else if (target.classList.contains('line-qty-input')) {
        updatedLine = updateInvoiceLine(lineId, { quantity: target.value }, { skipRender: true });
        if (updatedLine) {
            target.value = updatedLine.quantity.toString();
        }
    } else if (target.classList.contains('line-price-input')) {
        updatedLine = updateInvoiceLine(lineId, { unitPrice: target.value }, { skipRender: true });
        if (updatedLine) {
            target.value = updatedLine.unitPrice.toString();
        }
    }
    if (updatedLine) {
        refreshInvoiceSummary(stay);
    }
}

function handleInvoiceLineClick(event) {
    const button = event.target instanceof HTMLElement ? event.target.closest('button.line-delete-btn') : null;
    if (!button || button.disabled) {
        return;
    }
    const lineId = button.getAttribute('data-line-id') || button.closest('tr')?.getAttribute('data-line-id');
    if (!lineId) {
        return;
    }
    const stay = getSelectedStay();
    if (!stay || stay.invoice) {
        return;
    }
    removeInvoiceLine(lineId);
    renderInvoicePreview(stay);
}

function handleAddCustomLine() {
    const stay = getSelectedStay();
    if (!stay || stay.invoice) {
        return;
    }
    ensureInvoiceDraftForStay(stay);
    addInvoiceLine({
        label: 'Nouvelle ligne',
        quantity: 1,
        unitPrice: getDefaultActPrice(),
        category: 'custom',
        source: 'manual',
    });
    renderInvoicePreview(stay);
}

function handleResetInvoiceLines() {
    const stay = getSelectedStay();
    if (!stay || stay.invoice) {
        return;
    }
    const confirmed = window.confirm('Réinitialiser la facture selon le rapport validé ? Les modifications en cours seront perdues.');
    if (!confirmed) {
        return;
    }
    createInvoiceDraft(stay);
    renderInvoicePreview(stay);
}

function bindCatalogEvents() {
    const refreshBtn = document.getElementById('catalogRefreshBtn');
    const actForm = document.getElementById('actTarifForm');
    const examForm = document.getElementById('examTarifForm');
    const actTableBody = document.getElementById('actTarifsTableBody');
    const examTableBody = document.getElementById('examTarifsTableBody');

    refreshBtn?.addEventListener('click', () => {
        clearCatalogFeedback();
        loadMedicalCatalog();
    });
    actForm?.addEventListener('submit', handleActFormSubmit);
    examForm?.addEventListener('submit', handleExamFormSubmit);
    actTableBody?.addEventListener('click', (event) => handleCatalogDelete(event, 'act'));
    examTableBody?.addEventListener('click', (event) => handleCatalogDelete(event, 'exam'));
    document.querySelectorAll('.catalog-toggle').forEach((button) => {
        button.addEventListener('click', () => {
            const section = button.getAttribute('data-section');
            if (!section) {
                return;
            }
            toggleCatalogSection(section);
        });
    });
}

async function handleActFormSubmit(event) {
    event.preventDefault();
    clearCatalogFeedback();
    if (!state.hospitalId) {
        showAlert("Aucun hôpital n'est rattaché à votre compte.", 'error');
        return;
    }
    const nameInput = document.getElementById('actNameInput');
    const codeInput = document.getElementById('actCodeInput');
    const priceInput = document.getElementById('actPriceInput');
    const descriptionInput = document.getElementById('actDescriptionInput');

    const name = nameInput?.value.trim();
    const code = codeInput?.value.trim();
    const description = descriptionInput?.value.trim();
    const priceValue = parseFloat(priceInput?.value || '');

    if (!name || !Number.isFinite(priceValue)) {
        showAlert('Veuillez renseigner un acte et un montant valides.', 'warning');
        return;
    }

    const payload = { nom: name, montant: priceValue };
    if (code) {
        payload.code = code;
    }
    if (description) {
        payload.description = description;
    }

    try {
        await apiCall(`/hospitals/${state.hospitalId}/act-tarifs`, {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        event.target.reset();
        showCatalogFeedback('Acte ajouté avec succès.', 'success');
        await loadMedicalCatalog();
    } catch (error) {
        console.error('Erreur ajout acte:', error);
        showCatalogFeedback(error.message || "Impossible d'ajouter l'acte.", 'error');
    }
}

async function handleExamFormSubmit(event) {
    event.preventDefault();
    clearCatalogFeedback();
    if (!state.hospitalId) {
        showAlert("Aucun hôpital n'est rattaché à votre compte.", 'error');
        return;
    }
    const nameInput = document.getElementById('examNameInput');
    const priceInput = document.getElementById('examPriceInput');
    const name = nameInput?.value.trim();
    const priceValue = parseFloat(priceInput?.value || '');

    if (!name || !Number.isFinite(priceValue)) {
        showAlert('Veuillez renseigner un nom et un montant valides.', 'warning');
        return;
    }

    try {
        await apiCall(`/hospitals/${state.hospitalId}/exam-tarifs`, {
            method: 'POST',
            body: JSON.stringify({ nom: name, montant: priceValue }),
        });
        event.target.reset();
        showCatalogFeedback('Examen ajouté avec succès.', 'success');
        await loadMedicalCatalog();
    } catch (error) {
        console.error('Erreur ajout examen:', error);
        showCatalogFeedback(error.message || "Impossible d'ajouter l'examen.", 'error');
    }
}

async function handleCatalogDelete(event, entity) {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) {
        return;
    }
    if (!target.classList.contains('tarif-delete-btn')) {
        return;
    }
    const tarifId = target.getAttribute('data-tarif-id');
    if (!tarifId || !state.hospitalId) {
        return;
    }
    const confirmed = window.confirm('Supprimer ce tarif ?');
    if (!confirmed) {
        return;
    }
    clearCatalogFeedback();
    const endpoint =
        entity === 'act'
            ? `/hospitals/${state.hospitalId}/act-tarifs/${tarifId}`
            : `/hospitals/${state.hospitalId}/exam-tarifs/${tarifId}`;
    try {
        await apiCall(endpoint, { method: 'DELETE' });
        showCatalogFeedback('Tarif supprimé.', 'success');
        await loadMedicalCatalog();
    } catch (error) {
        console.error('Erreur suppression tarif:', error);
        showCatalogFeedback(error.message || 'Impossible de supprimer le tarif.', 'error');
    }
}

function showCatalogFeedback(message, type = 'success') {
    state.catalogFeedback = message || '';
    state.catalogFeedbackType = type;
    syncCatalogFeedback();
}

function clearCatalogFeedback() {
    state.catalogFeedback = '';
    syncCatalogFeedback();
}

function syncCatalogFeedback() {
    const box = document.getElementById('catalogFeedbackBox');
    if (!box) {
        return;
    }
    if (state.catalogFeedback) {
        box.textContent = state.catalogFeedback;
        box.className = `feedback ${state.catalogFeedbackType}`;
        box.hidden = false;
    } else {
        box.textContent = '';
        box.hidden = true;
    }
}

function setCatalogLoading(isLoading) {
    state.isCatalogLoading = Boolean(isLoading);
    const pill = document.getElementById('catalogLoadingPill');
    if (pill) {
        pill.hidden = !state.isCatalogLoading;
    }
}

async function loadMedicalCatalog() {
    if (!state.hospitalId) {
        state.actTarifsList = [];
        state.examTarifsList = [];
        state.actTarifs = {};
        state.examTarifs = {};
        renderMedicalCatalog();
        return;
    }
    setCatalogLoading(true);
    state.catalogError = '';
    try {
        const catalog = await apiCall(`/hospitals/${state.hospitalId}/medical-catalog`);
        const defaults = catalog?.defaults || {};
        state.catalog = {
            hourlyRate: parseAmount(defaults.hourly_rate, HOURLY_RATE),
            defaultActPrice: parseAmount(defaults.default_act_price, DEFAULT_ACT_PRICE),
            defaultExamPrice: parseAmount(defaults.default_exam_price, DEFAULT_EXAM_PRICE),
        };
        state.actTarifsList = Array.isArray(catalog?.actes) ? catalog.actes : [];
        state.examTarifsList = Array.isArray(catalog?.examens) ? catalog.examens : [];
        state.actTarifs = buildTarifMap(state.actTarifsList);
        state.examTarifs = buildTarifMap(state.examTarifsList);
    } catch (error) {
        console.error('Erreur catalogue médical:', error);
        state.catalogError = error.message || "Impossible de charger le catalogue médical.";
        state.catalog = {
            hourlyRate: HOURLY_RATE,
            defaultActPrice: DEFAULT_ACT_PRICE,
            defaultExamPrice: DEFAULT_EXAM_PRICE,
        };
        state.actTarifsList = [];
        state.examTarifsList = [];
        state.actTarifs = {};
        state.examTarifs = {};
    } finally {
        setCatalogLoading(false);
        renderMedicalCatalog();
        computeStats();
        renderStats();
        renderDetails();
    }
}

function renderMedicalCatalog() {
    const hospitalBadge = document.getElementById('catalogHospitalBadge');
    if (hospitalBadge) {
        if (state.hospitalId) {
            hospitalBadge.hidden = false;
            const hospitalName = localStorage.getItem('hospital_name');
            hospitalBadge.textContent = hospitalName || `Hôpital #${state.hospitalId}`;
        } else {
            hospitalBadge.hidden = true;
        }
    }

    const hourlyEl = document.getElementById('catalogHourlyRate');
    const defaultActEl = document.getElementById('catalogDefaultAct');
    const defaultExamEl = document.getElementById('catalogDefaultExam');
    if (hourlyEl) {
        hourlyEl.textContent = formatCurrency(state.catalog.hourlyRate);
    }
    if (defaultActEl) {
        defaultActEl.textContent = formatCurrency(state.catalog.defaultActPrice);
    }
    if (defaultExamEl) {
        defaultExamEl.textContent = formatCurrency(state.catalog.defaultExamPrice);
    }

    const actBadge = document.getElementById('actCountBadge');
    if (actBadge) {
        actBadge.textContent = formatCountLabel(state.actTarifsList.length, 'acte', 'actes');
    }
    const examBadge = document.getElementById('examCountBadge');
    if (examBadge) {
        examBadge.textContent = formatCountLabel(state.examTarifsList.length, 'examen', 'examens');
    }

    const errorBox = document.getElementById('catalogErrorBox');
    const errorMessage = document.getElementById('catalogErrorMessage');
    if (errorBox) {
        errorBox.hidden = !state.catalogError;
        if (state.catalogError && errorMessage) {
            errorMessage.textContent = state.catalogError;
        }
    }

    renderActTarifsTable();
    renderExamTarifsTable();
    syncCatalogFeedback();
    applyCatalogSectionState('acts');
    applyCatalogSectionState('exams');
}

function renderActTarifsTable() {
    const table = document.getElementById('actTarifsTable');
    const body = document.getElementById('actTarifsTableBody');
    const empty = document.getElementById('actTarifsEmpty');
    if (!table || !body || !empty) {
        return;
    }
    if (!state.actTarifsList.length) {
        table.hidden = true;
        empty.hidden = false;
        body.innerHTML = '';
        return;
    }
    table.hidden = false;
    empty.hidden = true;
    const rows = state.actTarifsList
        .slice()
        .sort((a, b) => (a.nom || '').localeCompare(b.nom || '', 'fr'))
        .map(
            (tarif) => `
            <tr>
                <td>
                    <div class="catalog-item-name">${escapeHtml(tarif.nom || '')}</div>
                    ${tarif.description ? `<small class="muted">${escapeHtml(tarif.description)}</small>` : ''}
                </td>
                <td>${tarif.code ? escapeHtml(tarif.code) : '—'}</td>
                <td>${formatCurrency(tarif.montant)}</td>
                <td>
                    <button type="button" class="danger-button tarif-delete-btn" data-tarif-id="${tarif.id}">
                        Supprimer
                    </button>
                </td>
            </tr>
        `,
        )
        .join('');
    body.innerHTML = rows;
}

function getCatalogSectionState(section) {
    if (!state.catalogSections) {
        state.catalogSections = {};
    }
    if (typeof state.catalogSections[section] === 'undefined') {
        state.catalogSections[section] = true;
    }
    return Boolean(state.catalogSections[section]);
}

function setCatalogSectionState(section, expanded) {
    if (!state.catalogSections) {
        state.catalogSections = {};
    }
    state.catalogSections[section] = Boolean(expanded);
    applyCatalogSectionState(section);
}

function toggleCatalogSection(section) {
    setCatalogSectionState(section, !getCatalogSectionState(section));
}

function applyCatalogSectionState(section) {
    const card = document.querySelector(`.catalog-card[data-section="${section}"]`);
    if (!card) {
        return;
    }
    const expanded = getCatalogSectionState(section);
    card.classList.toggle('collapsed', !expanded);
    const toggle = card.querySelector('.catalog-toggle');
    if (toggle) {
        toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    }
}

function renderExamTarifsTable() {
    const table = document.getElementById('examTarifsTable');
    const body = document.getElementById('examTarifsTableBody');
    const empty = document.getElementById('examTarifsEmpty');
    if (!table || !body || !empty) {
        return;
    }
    if (!state.examTarifsList.length) {
        table.hidden = true;
        empty.hidden = false;
        body.innerHTML = '';
        return;
    }
    table.hidden = false;
    empty.hidden = true;
    const rows = state.examTarifsList
        .slice()
        .sort((a, b) => (a.nom || '').localeCompare(b.nom || '', 'fr'))
        .map(
            (tarif) => `
            <tr>
                <td>${escapeHtml(tarif.nom || '')}</td>
                <td>${formatCurrency(tarif.montant)}</td>
                <td>
                    <button type="button" class="danger-button tarif-delete-btn" data-tarif-id="${tarif.id}">
                        Supprimer
                    </button>
                </td>
            </tr>
        `,
        )
        .join('');
    body.innerHTML = rows;
}

async function fetchStays() {
    if (!state.hospitalId) {
        return;
    }
    const loadingEl = document.getElementById('staysLoading');
    const refreshLabel = document.getElementById('staysRefreshLabel');
    loadingEl.hidden = false;
    refreshLabel.hidden = false;

    const params = new URLSearchParams();
    params.set('hospital_id', state.hospitalId.toString());
    params.set('limit', '100');
    if (state.filters.status !== 'all') {
        params.set('status', state.filters.status);
    }
    if (state.filters.report !== 'all') {
        params.set('report_status', state.filters.report);
    }
    if (state.filters.invoice !== 'all') {
        params.set('invoice_status', state.filters.invoice);
    }
    if (state.filters.search) {
        params.set('search', state.filters.search);
    }

    try {
        const result = await apiCall(`/hospital-sinistres/hospital-stays?${params.toString()}`);
        state.stays = Array.isArray(result) ? result : [];
        if (!state.stays.some((stay) => stay.id === state.selectedStayId)) {
            state.selectedStayId = state.stays.length ? state.stays[0].id : null;
            resetFormState();
        }
        computeStats();
        renderStats();
        renderStayList();
        renderDetails();
    } catch (error) {
        console.error('Erreur lors du chargement des séjours:', error);
        showAlert(error.message || "Impossible de charger les séjours hospitaliers.", 'error');
        state.stays = [];
        state.selectedStayId = null;
        renderStats();
        renderStayList();
        renderDetails();
    } finally {
        loadingEl.hidden = true;
        refreshLabel.hidden = true;
    }
}

function computeStats() {
    let readyCount = 0;
    let potential = 0;
    state.stays.forEach((stay) => {
        if (!stay.invoice) {
            readyCount += 1;
        }
        const preview = buildInvoicePreview(stay, DEFAULT_TVA);
        potential += preview.subtotal;
    });
    state.stats.readyCount = readyCount;
    state.stats.potentialHt = potential;
}

function renderStats() {
    const readyEl = document.getElementById('statReadyCount');
    const potentialEl = document.getElementById('statPotentialHt');
    if (readyEl) {
        readyEl.textContent = state.stats.readyCount.toString();
    }
    if (potentialEl) {
        potentialEl.textContent = numberFormatter.format(Math.round(state.stats.potentialHt));
    }
}

function renderStayList() {
    const list = document.getElementById('staysList');
    const empty = document.getElementById('staysEmpty');
    if (!list || !empty) {
        return;
    }
    if (!state.stays.length) {
        list.hidden = true;
        empty.hidden = false;
        list.innerHTML = '';
        return;
    }
    empty.hidden = true;
    list.hidden = false;

    list.innerHTML = state.stays.map((stay) => {
        const sinistre = stay.sinistre?.numero_sinistre || `Sinistre #${stay.sinistre_id}`;
        const statusClass = `status-badge ${getStatusClass(stay.status)}`;
        const statusLabel = getStatusLabel(stay.status);
        const reportLabel = getReportStatusLabel(stay.report_status);
        const doctor = stay.assigned_doctor?.full_name ? `Médecin : ${stay.assigned_doctor.full_name}` : '';
        const factureBadge = stay.invoice
            ? `<span class="pill pill-success">Facture #${escapeHtml(stay.invoice.numero_facture)} · ${escapeHtml(INVOICE_STATUS_LABELS[stay.invoice.statut] || stay.invoice.statut)}</span>`
            : '<span class="pill">Facture à créer</span>';
        return `
            <li class="stay-card ${state.selectedStayId === stay.id ? 'selected' : ''}" data-stay-id="${stay.id}">
                <div class="stay-card-header">
                    <strong>${escapeHtml(sinistre)}</strong>
                    <span class="${statusClass}">${statusLabel}</span>
                </div>
                <div class="stay-card-body">
                    <p class="muted">Rapport : ${reportLabel}</p>
                    ${doctor ? `<p class="muted">${escapeHtml(doctor)}</p>` : ''}
                </div>
                <div class="stay-card-footer">
                    ${factureBadge}
                </div>
            </li>
        `;
    }).join('');

    list.querySelectorAll('.stay-card').forEach((item) => {
        item.addEventListener('click', () => {
            const stayId = parseInt(item.getAttribute('data-stay-id'), 10);
            if (Number.isFinite(stayId) && stayId !== state.selectedStayId) {
                state.selectedStayId = stayId;
                resetFormState();
                renderStayList();
                renderDetails();
            }
        });
    });

    const pagEl = document.getElementById('staysPagination');
    if (pagEl) {
        if (state.stays.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, state.stays.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${state.stays.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="staysPrev" ${currentPageStays <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageStays + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="staysNext" ${currentPageStays >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('staysPrev')?.addEventListener('click', () => { currentPageStays--; renderStayList(); });
            document.getElementById('staysNext')?.addEventListener('click', () => { currentPageStays++; renderStayList(); });
        }
    }
}

function renderDetails() {
    const placeholder = document.getElementById('detailsPlaceholder');
    const content = document.getElementById('detailsContent');
    const stay = state.stays.find((s) => s.id === state.selectedStayId);
    if (!stay) {
        placeholder.hidden = false;
        content.hidden = true;
        return;
    }
    placeholder.hidden = true;
    content.hidden = false;

    document.getElementById('detailSinistre').textContent =
        stay.sinistre?.numero_sinistre || `#${stay.sinistre_id}`;
    const patient = stay.patient?.full_name || stay.patient?.email || 'Patient inconnu';
    document.getElementById('detailPatient').textContent = `Patient ${patient}`;
    const statusBadge = document.getElementById('detailStatus');
    statusBadge.textContent = getStatusLabel(stay.status);
    statusBadge.className = `status-badge ${getStatusClass(stay.status)}`;

    const invoiceBadge = document.getElementById('detailInvoiceBadge');
    const readOnlyBanner = document.getElementById('invoiceReadOnlyBanner');
    if (stay.invoice) {
        invoiceBadge.hidden = false;
        const label = INVOICE_STATUS_LABELS[stay.invoice.statut] || stay.invoice.statut;
        invoiceBadge.textContent = `Facture #${stay.invoice.numero_facture} · ${label}`;
        if (readOnlyBanner) {
            readOnlyBanner.style.display = 'block';
        }
    } else {
        invoiceBadge.hidden = true;
        if (readOnlyBanner) {
            readOnlyBanner.style.display = 'none';
        }
    }

    setTextOrDash('detailMotifConsultation', stay.report_motif_consultation);
    setTextOrDash('detailMotifHospitalisation', stay.report_motif_hospitalisation);
    const hours = stay.report_duree_sejour_heures;
    setTextOrDash('detailDuree', hours ? `${hours} h` : null);
    setTextOrDash('detailDoctor', stay.assigned_doctor?.full_name);

    const resumeCard = document.getElementById('detailResumeCard');
    if (stay.report_resume) {
        resumeCard.hidden = false;
        document.getElementById('detailResume').textContent = stay.report_resume;
    } else {
        resumeCard.hidden = true;
    }

    renderTags('detailActes', normalizeList(stay.report_actes), 'Aucun acte renseigné');
    renderTags('detailExamens', normalizeList(stay.report_examens), 'Aucun examen renseigné');

    ensureInvoiceDraftForStay(stay);
    document.getElementById('invoiceNotes').value = state.notes;
    const tvaInput = document.getElementById('tvaInput');
    if (tvaInput) {
        tvaInput.value = state.tva.toString();
        tvaInput.disabled = !!stay.invoice;
        tvaInput.readOnly = !!stay.invoice;
        tvaInput.title = stay.invoice ? 'Facture traitée : consultation uniquement' : '';
    }
    const notesInput = document.getElementById('invoiceNotes');
    if (notesInput) {
        notesInput.disabled = !!stay.invoice;
        notesInput.readOnly = !!stay.invoice;
    }
    updateTvaDisplay();
    renderInvoicePreview(stay);
}

function renderInvoicePreview(stay) {
    const overrideLines =
        stay && state.invoiceDraft?.stayId === stay.id ? state.invoiceDraft.lines : null;
    const preview = buildInvoicePreview(stay, state.tva, overrideLines);
    const table = document.getElementById('invoiceTable');
    const empty = document.getElementById('invoiceEmpty');
    const linesContainer = document.getElementById('invoiceLines');
    const generateBtn = document.getElementById('generateInvoiceBtn');
    const infoEl = document.getElementById('invoiceInfo');
    const feedback = document.getElementById('feedbackBox');
    const canEditLines = Boolean(stay) && !stay?.invoice;

    if (!preview.lines.length) {
        table.hidden = true;
        empty.hidden = false;
        if (linesContainer) {
            linesContainer.innerHTML = '';
        }
    } else {
        empty.hidden = true;
        table.hidden = false;
        if (linesContainer) {
            linesContainer.innerHTML = preview.lines
                .map((line) => renderInvoiceLineRow(line, canEditLines))
                .join('');
        }
    }
    syncInvoiceBuilderToolbar(stay, canEditLines);
    syncInvoiceSummary(preview);

    const canGenerate = Boolean(
        stay &&
        !stay.invoice &&
        preview.lines.length &&
        !state.isSubmitting
    );
    generateBtn.disabled = !canGenerate;
    infoEl.hidden = !stay.invoice;
    updateValidationBadges(stay.invoice);
    if (stay.invoice) {
        const statusLabel = INVOICE_STATUS_LABELS[stay.invoice.statut] || stay.invoice.statut;
        infoEl.innerHTML = `Facture #${escapeHtml(stay.invoice.numero_facture)} · ${escapeHtml(statusLabel)}`;
    }

    if (feedback) {
        feedback.hidden = !feedback.textContent;
    }
}

function updateValidationBadges(invoice) {
    const card = document.getElementById('invoiceValidationCard');
    if (!card) {
        return;
    }
    if (!invoice) {
        card.hidden = true;
        return;
    }
    card.hidden = false;
    const mappings = [
        { key: 'validation_medicale', elementId: 'validationMedicalBadge' },
        { key: 'validation_sinistre', elementId: 'validationSinistreBadge' },
        { key: 'validation_compta', elementId: 'validationComptaBadge' },
    ];
    mappings.forEach(({ key, elementId }) => {
        const badge = document.getElementById(elementId);
        if (!badge) {
            return;
        }
        const rawStatus = invoice[key] || 'pending';
        const status = VALIDATION_STAGE_LABELS[key] ? rawStatus : 'pending';
        const displayLabel =
            (VALIDATION_STAGE_LABELS[key] && VALIDATION_STAGE_LABELS[key][status]) || VALIDATION_STAGE_LABELS[key]?.pending || 'En attente';
        badge.textContent = `${displayLabel} · ${VALIDATION_STATUS_LABELS[status] || VALIDATION_STATUS_LABELS.pending}`;
        badge.className = `validation-pill validation-${status}`;
    });
}

async function createInvoice(stayId) {
    const stay = state.stays.find((s) => s.id === stayId);
    if (!stay) {
        return;
    }
    const draftLines =
        stay && state.invoiceDraft?.stayId === stay.id
            ? state.invoiceDraft.lines
            : buildDefaultInvoiceLines(stay, { withIds: false });
    if (!draftLines.length) {
        showAlert('Ajoutez au moins une ligne de facture avant de générer.', 'warning');
        return;
    }
    const hasEmptyLabel = draftLines.some((line) => !line.label || !line.label.trim());
    if (hasEmptyLabel) {
        showAlert('Complétez le libellé de chaque ligne avant de générer la facture.', 'warning');
        return;
    }
    const hasInvalidValues = draftLines.some(
        (line) => !Number.isFinite(line.quantity) || line.quantity <= 0 || !Number.isFinite(line.unitPrice) || line.unitPrice < 0,
    );
    if (hasInvalidValues) {
        showAlert('Vérifiez les quantités et montants de chaque ligne.', 'warning');
        return;
    }
    const preview = buildInvoicePreview(stay, state.tva, draftLines);
    if (!preview.lines.length) {
        showAlert('Impossible de générer la facture sans ligne valide.', 'warning');
        return;
    }

    state.isSubmitting = true;
    renderInvoicePreview(stay);
    const feedback = document.getElementById('feedbackBox');
    feedback.textContent = '';
    feedback.hidden = true;

    try {
        await apiCall(`/hospital-sinistres/hospital-stays/${stayId}/invoice`, {
            method: 'POST',
            body: JSON.stringify({
                taux_tva: state.tva,
                notes: state.notes || undefined,
                lines: draftLines.map((line) => ({
                    libelle: line.label.trim(),
                    quantite: sanitizeInvoiceQuantity(line.quantity, 1),
                    prix_unitaire: sanitizeInvoiceAmount(line.unitPrice, 0),
                })),
            }),
        });
        feedback.className = 'feedback success';
        feedback.textContent = 'Facture générée. Elle est transmise au pôle médical pour accord.';
        feedback.hidden = false;
        showAlert('Facture créée avec succès.', 'success');
        await fetchStays();
    } catch (error) {
        console.error('Erreur lors de la création de la facture:', error);
        feedback.className = 'feedback error';
        feedback.textContent = error.message || 'Échec de la génération de la facture.';
        feedback.hidden = false;
    } finally {
        state.isSubmitting = false;
        renderInvoicePreview(state.stays.find((s) => s.id === state.selectedStayId));
    }
}

function buildInvoicePreview(stay, tvaRate, overrideLines = null) {
    if (!stay && !overrideLines?.length) {
        return { lines: [], subtotal: 0, vatAmount: 0, total: 0 };
    }
    const baseLines =
        Array.isArray(overrideLines) && overrideLines.length
            ? overrideLines
            : buildDefaultInvoiceLines(stay, { withIds: false });
    const normalizedLines = baseLines
        .map((line, index) => {
            const quantity = sanitizeInvoiceQuantity(line.quantity, 1);
            const unitPrice = sanitizeInvoiceAmount(line.unitPrice, 0);
            const label = typeof line.label === 'string' ? line.label : '';
            return {
                ...line,
                id: line.id || line.key || `line-${index}`,
                key: line.key || line.id || `line-${index}`,
                label,
                quantity,
                unitPrice,
                total: quantity * unitPrice,
            };
        })
        .filter((line) => line.quantity > 0 && line.unitPrice >= 0 && line.label);
    const subtotal = normalizedLines.reduce((sum, line) => sum + line.total, 0);
    const safeTva = Number.isFinite(tvaRate) ? clamp(tvaRate, 0, 1) : DEFAULT_TVA;
    const vatAmount = Math.round(subtotal * safeTva);
    const total = subtotal + vatAmount;
    return { lines: normalizedLines, subtotal, vatAmount, total };
}

function buildDefaultInvoiceLines(stay, options = {}) {
    if (!stay) {
        return [];
    }
    const withIds = Boolean(options.withIds);
    const lines = [];
    const hourlyRate = getHourlyRate();
    const fallbackActPrice = getDefaultActPrice();
    const fallbackExamPrice = getDefaultExamPrice();

    const addLine = (payload) => {
        const quantity = sanitizeInvoiceQuantity(payload.quantity, 1);
        const unitPrice = sanitizeInvoiceAmount(payload.unitPrice, payload.fallback ?? 0);
        const line = {
            key: payload.key || null,
            label: payload.label || '',
            quantity,
            unitPrice,
            category: payload.category || 'custom',
            source: payload.source || 'report',
        };
        if (withIds) {
            line.id = generateInvoiceLineId();
            line.key = payload.key || line.id;
        }
        lines.push(line);
    };

    const hours = Number(stay.report_duree_sejour_heures) || 0;
    if (hours > 0) {
        addLine({
            key: 'duration',
            label: `Durée de séjour (${hours}h)`,
            quantity: hours,
            unitPrice: hourlyRate,
            fallback: hourlyRate,
            category: 'duration',
            source: 'report',
        });
    }

    const actes = normalizeList(stay.report_actes);
    actes.forEach((act, index) => {
        addLine({
            key: `act-${index}`,
            label: `Acte - ${act}`,
            quantity: 1,
            unitPrice: resolveActPrice(act),
            fallback: fallbackActPrice,
            category: 'act',
            source: 'report',
        });
    });

    const examens = normalizeList(stay.report_examens);
    examens.forEach((exam, index) => {
        addLine({
            key: `exam-${index}`,
            label: `Examen - ${exam}`,
            quantity: 1,
            unitPrice: resolveExamPrice(exam),
            fallback: fallbackExamPrice,
            category: 'exam',
            source: 'report',
        });
    });

    return lines;
}

function ensureInvoiceDraftForStay(stay) {
    if (!stay) {
        state.invoiceDraft = { stayId: null, lines: [] };
        state.invoiceLineCounter = 0;
        return;
    }
    if (state.invoiceDraft?.stayId === stay.id && Array.isArray(state.invoiceDraft.lines)) {
        return;
    }
    createInvoiceDraft(stay);
}

function createInvoiceDraft(stay) {
    state.invoiceLineCounter = 0;
    const lines = buildDefaultInvoiceLines(stay, { withIds: true });
    state.invoiceDraft = {
        stayId: stay?.id ?? null,
        lines,
    };
}

function generateInvoiceLineId() {
    state.invoiceLineCounter = (state.invoiceLineCounter || 0) + 1;
    return `line-${state.invoiceLineCounter}`;
}

function addInvoiceLine(overrides = {}) {
    if (!state.invoiceDraft) {
        state.invoiceDraft = { stayId: null, lines: [] };
    }
    const id = generateInvoiceLineId();
    const line = {
        id,
        key: id,
        label: typeof overrides.label === 'string' ? overrides.label : 'Nouvelle ligne',
        quantity: sanitizeInvoiceQuantity(overrides.quantity, 1),
        unitPrice: sanitizeInvoiceAmount(overrides.unitPrice, getDefaultActPrice()),
        category: overrides.category || 'custom',
        source: overrides.source || 'manual',
    };
    state.invoiceDraft.lines.push(line);
}

function removeInvoiceLine(lineId) {
    if (!state.invoiceDraft?.lines?.length) {
        return;
    }
    state.invoiceDraft.lines = state.invoiceDraft.lines.filter((line) => line.id !== lineId && line.key !== lineId);
}

function updateInvoiceLine(lineId, changes, options = {}) {
    if (!state.invoiceDraft?.lines?.length) {
        return null;
    }
    const index = state.invoiceDraft.lines.findIndex((line) => line.id === lineId || line.key === lineId);
    if (index === -1) {
        return null;
    }
    const current = state.invoiceDraft.lines[index];
    const next = { ...current };
    if (Object.prototype.hasOwnProperty.call(changes, 'label')) {
        next.label = typeof changes.label === 'string' ? changes.label : '';
    }
    if (Object.prototype.hasOwnProperty.call(changes, 'quantity')) {
        next.quantity = sanitizeInvoiceQuantity(changes.quantity, current.quantity);
    }
    if (Object.prototype.hasOwnProperty.call(changes, 'unitPrice')) {
        next.unitPrice = sanitizeInvoiceAmount(changes.unitPrice, current.unitPrice);
    }
    state.invoiceDraft.lines.splice(index, 1, next);
    if (!options.skipRender) {
        const stay = getSelectedStay();
        renderInvoicePreview(stay);
    }
    return next;
}

function refreshInvoiceSummary(stay) {
    if (!stay || !state.invoiceDraft) {
        return;
    }
    const preview = buildInvoicePreview(stay, state.tva, state.invoiceDraft.lines);
    syncInvoiceSummary(preview);
    preview.lines.forEach((line) => {
        const totalEl = document.querySelector(`.line-total-value[data-line-id="${line.id}"]`);
        if (totalEl) {
            totalEl.textContent = numberFormatter.format(line.total);
        }
    });
}

function syncInvoiceSummary(preview) {
    const subtotalEl = document.getElementById('invoiceSubtotal');
    const vatEl = document.getElementById('invoiceVat');
    const totalEl = document.getElementById('invoiceTotal');
    if (subtotalEl) {
        subtotalEl.textContent = numberFormatter.format(preview.subtotal);
    }
    if (vatEl) {
        vatEl.textContent = numberFormatter.format(preview.vatAmount);
    }
    if (totalEl) {
        totalEl.textContent = numberFormatter.format(preview.total);
    }
}

function renderInvoiceLineRow(line, canEdit) {
    const identifier = line.id || line.key || '';
    const disabledAttr = canEdit ? '' : 'disabled';
    const badgeLabel = getInvoiceLineBadgeLabel(line);
    return `
        <tr data-line-id="${identifier}">
            <td>
                <input type="text" class="invoice-line-input line-label-input" value="${escapeHtml(line.label || '')}" placeholder="Libellé de la ligne" ${disabledAttr}>
                ${badgeLabel ? `<small class="invoice-line-badge">${escapeHtml(badgeLabel)}</small>` : ''}
            </td>
            <td>
                <input type="number" class="invoice-line-input line-qty-input" min="1" step="1" value="${line.quantity}" ${disabledAttr}>
            </td>
            <td>
                <input type="number" class="invoice-line-input line-price-input" min="0" step="100" value="${line.unitPrice}" ${disabledAttr}>
            </td>
            <td>
                <div class="line-total-cell">
                    <span class="line-total-value" data-line-id="${identifier}">${numberFormatter.format(line.total)}</span>
                    <button type="button" class="icon-button line-delete-btn" data-line-id="${identifier}" aria-label="Supprimer la ligne" ${disabledAttr}>
                        &times;
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function getInvoiceLineBadgeLabel(line) {
    if (line.source !== 'report') {
        return '';
    }
    switch (line.category) {
        case 'duration':
            return 'Durée du séjour';
        case 'act':
            return 'Acte du rapport';
        case 'exam':
            return 'Examen du rapport';
        default:
            return 'Rapport';
    }
}

function syncInvoiceBuilderToolbar(stay, canEditLines) {
    const toolbar = document.getElementById('invoiceBuilderToolbar');
    if (toolbar) {
        toolbar.hidden = !stay;
    }
    const addBtn = document.getElementById('addCustomLineBtn');
    const resetBtn = document.getElementById('resetInvoiceLinesBtn');
    const helper = document.getElementById('invoiceBuilderHelper');
    if (helper) {
        if (!stay) {
            helper.textContent = 'Sélectionnez un séjour validé pour préparer la facture.';
        } else if (stay.invoice) {
            helper.textContent = 'Facture déjà envoyée : modifications désactivées.';
        } else {
            helper.textContent = "Ajustez librement les libellés, quantités ou montants avant l'envoi de la facture.";
        }
    }
    if (addBtn) {
        addBtn.disabled = !canEditLines || !stay;
    }
    if (resetBtn) {
        resetBtn.disabled = !canEditLines || !stay;
    }
    const lineInputs = document.querySelectorAll('#invoiceLines .invoice-line-input');
    lineInputs.forEach((input) => {
        input.disabled = !canEditLines;
    });
    const deleteButtons = document.querySelectorAll('.line-delete-btn');
    deleteButtons.forEach((button) => {
        button.disabled = !canEditLines;
    });
}

function getSelectedStay() {
    return state.stays.find((s) => s.id === state.selectedStayId) || null;
}

function getHourlyRate() {
    const value = Number(state.catalog?.hourlyRate);
    return Number.isFinite(value) ? value : HOURLY_RATE;
}

function getDefaultActPrice() {
    const value = Number(state.catalog?.defaultActPrice);
    return Number.isFinite(value) ? value : DEFAULT_ACT_PRICE;
}

function getDefaultExamPrice() {
    const value = Number(state.catalog?.defaultExamPrice);
    return Number.isFinite(value) ? value : DEFAULT_EXAM_PRICE;
}

function resolveActPrice(name) {
    if (name && Number.isFinite(state.actTarifs?.[name])) {
        return state.actTarifs[name];
    }
    if (name && Number.isFinite(ACT_PRICES[name])) {
        return ACT_PRICES[name];
    }
    return getDefaultActPrice();
}

function resolveExamPrice(name) {
    if (name && Number.isFinite(state.examTarifs?.[name])) {
        return state.examTarifs[name];
    }
    if (name && Number.isFinite(EXAM_PRICES[name])) {
        return EXAM_PRICES[name];
    }
    return getDefaultExamPrice();
}

function sanitizeInvoiceQuantity(value, fallback = 1) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        const fallbackValue = Number(fallback);
        return Math.max(1, Number.isFinite(fallbackValue) ? Math.round(fallbackValue) : 1);
    }
    return Math.max(1, Math.round(parsed));
}

function sanitizeInvoiceAmount(value, fallback = 0) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
        const fallbackValue = Number(fallback);
        if (Number.isFinite(fallbackValue) && fallbackValue >= 0) {
            return Math.round(fallbackValue);
        }
        return 0;
    }
    return Math.round(parsed);
}

function formatCurrency(value) {
    const amount = typeof value === 'number' ? value : parseFloat(value);
    if (!Number.isFinite(amount)) {
        return value;
    }
    return numberFormatter.format(amount);
}

function parseAmount(value, fallback) {
    const amount = Number(value);
    return Number.isFinite(amount) ? amount : fallback;
}

function buildTarifMap(list) {
    const map = {};
    (list || []).forEach((item) => {
        if (!item || !item.nom) {
            return;
        }
        const amount = parseFloat(item.montant);
        if (Number.isFinite(amount)) {
            map[item.nom] = amount;
        }
    });
    return map;
}

function formatCountLabel(count, singular, plural) {
    const safeCount = Number.isFinite(count) ? count : 0;
    const label = safeCount > 1 ? plural : singular;
    return `${safeCount} ${label}`;
}

function normalizeList(value) {
    if (!value) {
        return [];
    }
    if (Array.isArray(value)) {
        return value.filter(Boolean);
    }
    if (typeof value === 'string') {
        return value.split(',').map((v) => v.trim()).filter(Boolean);
    }
    return [];
}

function renderTags(containerId, values, emptyLabel) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    const list = values.length ? values : [emptyLabel];
    container.innerHTML = list.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join('');
}

function setTextOrDash(elementId, value) {
    const el = document.getElementById(elementId);
    if (!el) {
        return;
    }
    el.textContent = value ? value : '—';
}

function updateTvaDisplay() {
    const display = document.getElementById('tvaDisplay');
    if (display) {
        display.textContent = `${Math.round(state.tva * 100)}%`;
    }
}

function resetFormState() {
    state.tva = DEFAULT_TVA;
    state.notes = '';
    const notesInput = document.getElementById('invoiceNotes');
    if (notesInput) {
        notesInput.value = '';
    }
    const feedback = document.getElementById('feedbackBox');
    if (feedback) {
        feedback.textContent = '';
        feedback.hidden = true;
    }
}

function getStatusLabel(status) {
    const map = {
        validated: 'Validé',
        awaiting_validation: 'En validation',
        in_progress: 'En cours',
        invoiced: 'Facturé',
        rejected: 'Rejeté',
    };
    return map[status] || status || 'Inconnu';
}

function getStatusClass(status) {
    const allowed = ['validated', 'awaiting_validation', 'in_progress', 'invoiced', 'rejected'];
    if (allowed.includes(status)) {
        return `status-${status}`;
    }
    return 'status-awaiting_validation';
}

function getReportStatusLabel(status) {
    const map = {
        draft: 'Brouillon',
        submitted: 'Soumis',
        approved: 'Validé',
        rejected: 'Rejeté',
    };
    return map[status] || 'Non communiqué';
}

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
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

