const ALLOWED_DOCTOR_ROLES = ['doctor', 'medecin_hopital'];
const MEDICAL_FIELD_LABELS = {
    chronicDiseases: 'Maladies chroniques',
    regularTreatment: 'Traitement régulier',
    treatmentDetails: 'Détails du traitement',
    recentHospitalization: 'Hospitalisation récente',
    hospitalizationDetails: 'Détails hospitalisation',
    recentSurgery: 'Chirurgie récente',
    surgeryDetails: 'Détails chirurgie',
    symptoms: 'Symptômes signalés',
    symptomOther: 'Précision symptômes',
    pregnancy: 'Grossesse',
    infectiousDiseases: 'Maladies infectieuses',
    contactRisk: 'Contacts à risque',
    surgeryLast6Months: 'Opération chirurgicale (6 derniers mois)',
    surgeryLast6MonthsDetails: 'Précisions opération',
    photoMedicale: 'Photo',
    honourDeclaration: "Déclaration sur l'honneur",
    maladies_chroniques: 'Maladies chroniques',
    traitements_en_cours: 'Traitement médical régulier',
    antecedents_recents:
        'Hospitalisation (12 mois), tabac, alcool, activité physique, allergies, santé mentale',
    declaration_sante: 'Je déclare que les informations fournies sont exactes et complètes',
    date_soumission: 'Date de soumission du questionnaire',
    enceinte: 'Êtes-vous enceinte ? (si concerné)',
    photo_medicale: 'Photo',
    photo_identity: 'Photo'
};

const MEDICAL_FIELD_DISPLAY_LABELS = {
    antecedents_recents: 'Antécédents et habitudes de vie',
};

/** Champs retirés du questionnaire médical (risques particuliers, voyage avec équipement) — non affichés. */
const REMOVED_MEDICAL_KEYS = new Set(['riskySports', 'medicalEquipment', 'equipmentDetails']);
/** Déclarations/consentements — non affichés dans le dossier patient (médecin). */
const CONSENT_KEYS = new Set(['honourDeclaration', 'technicalConsents']);

let doctorCases = [];
let activeDoctorCases = [];
let historyDoctorCases = [];
let currentDoctorTab = 'to_treat'; // 'to_treat' | 'treated'
let searchDoctorToTreat = '';
let searchDoctorTreated = '';
const ROWS_PER_PAGE = 6;
let currentPageDoctorToTreat = 0;
let currentPageDoctorTreated = 0;
let selectedCaseId = null;
let hospitalStayOptions = { actes: [], examens: [] };
let associatedHospitalIds = new Set();
let associatedHospitals = [];

const currentUserId = Number(localStorage.getItem('user_id') || 0);
const currentUserRole = localStorage.getItem('user_role') || '';
const currentHospitalId = Number(localStorage.getItem('hospital_id') || 0);

function isDoctorReportPage() {
    return document.body?.getAttribute('data-hospital-doctor-page') === 'report';
}

document.addEventListener('DOMContentLoaded', () => {
    if (isDoctorReportPage()) {
        initHospitalDoctorReportPage();
    } else {
        initHospitalDoctorPage();
    }
});

async function initHospitalDoctorPage() {
    const allowed = await requireAnyRole(ALLOWED_DOCTOR_ROLES, 'index.html');
    if (!allowed) {
        return;
    }

    displayDoctorIdentity();
    bindStaticEvents();
    await loadAssociatedHospitals();
    await loadHospitalStayOptions();
    await loadDoctorCases();
}

async function initHospitalDoctorReportPage() {
    const allowed = await requireAnyRole(ALLOWED_DOCTOR_ROLES, 'index.html');
    if (!allowed) {
        return;
    }

    displayDoctorIdentity();
    bindStaticEvents();

    const loadingEl = document.getElementById('reportPageLoading');
    const errorEl = document.getElementById('reportPageError');
    const section = document.getElementById('caseDetailsSection');

    const params = new URLSearchParams(window.location.search);
    const alertId = Number(params.get('alert_id'));
    if (!Number.isFinite(alertId) || alertId <= 0) {
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
        if (errorEl) {
            errorEl.style.display = 'block';
            errorEl.textContent = 'Paramètre alert_id manquant ou invalide.';
        }
        return;
    }

    if (loadingEl) {
        loadingEl.style.display = 'block';
    }
    if (errorEl) {
        errorEl.style.display = 'none';
        errorEl.textContent = '';
    }
    if (section) {
        section.hidden = true;
    }

    await loadAssociatedHospitals();
    await loadHospitalStayOptions();

    try {
        const alert = await apiCall(`/sos/${alertId}`);
        const sinistre = await apiCall(`/sos/${alertId}/sinistre`);
        if (!sinistre?.hospital_stay || !canAccessCase(sinistre)) {
            throw new Error("Ce dossier n'est pas accessible ou vous n'y êtes pas assigné.");
        }
        doctorCases = [{ alert, sinistre }];
        selectedCaseId = alertId;
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
        if (errorEl) {
            errorEl.style.display = 'none';
        }
        renderSelectedCase({ alert, sinistre });
    } catch (error) {
        console.error('Erreur chargement dossier rapport:', error);
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
        if (errorEl) {
            errorEl.style.display = 'block';
            errorEl.textContent = error.message || 'Impossible de charger le dossier.';
        }
    }
}

function bindStaticEvents() {
    const refreshBtn = document.getElementById('refreshCasesBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadDoctorCases(true));
    }

    const searchToTreat = document.getElementById('searchDoctorToTreat');
    if (searchToTreat) {
        searchToTreat.addEventListener('input', () => {
            searchDoctorToTreat = (searchToTreat.value || '').trim().toLowerCase();
            renderDoctorCases();
        });
        searchToTreat.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchToTreat.value = '';
                searchDoctorToTreat = '';
                renderDoctorCases();
            }
        });
    }
    const searchTreated = document.getElementById('searchDoctorTreated');
    if (searchTreated) {
        searchTreated.addEventListener('input', () => {
            searchDoctorTreated = (searchTreated.value || '').trim().toLowerCase();
            renderHistoryCases();
        });
        searchTreated.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchTreated.value = '';
                searchDoctorTreated = '';
                renderHistoryCases();
            }
        });
    }

    const tabToTreat = document.getElementById('tabDoctorToTreat');
    const tabTreated = document.getElementById('tabDoctorTreated');
    [tabToTreat, tabTreated].forEach((btn) => {
        if (!btn) return;
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-doctor-tab');
            if (tab !== 'to_treat' && tab !== 'treated') return;
            currentDoctorTab = tab;
            const toTreatPanel = document.getElementById('doctorToTreatPanel');
            const treatedPanel = document.getElementById('doctorTreatedPanel');
            if (toTreatPanel) toTreatPanel.hidden = tab !== 'to_treat';
            if (treatedPanel) treatedPanel.hidden = tab !== 'treated';
            tabToTreat.classList.toggle('active', tab === 'to_treat');
            tabToTreat.setAttribute('aria-selected', tab === 'to_treat' ? 'true' : 'false');
            tabTreated.classList.toggle('active', tab === 'treated');
            tabTreated.setAttribute('aria-selected', tab === 'treated' ? 'true' : 'false');
        });
    });

    const openBtn = document.getElementById('openAlertFileBtn');
    if (openBtn) {
        openBtn.addEventListener('click', () => {
            if (!selectedCaseId) {
                showAlert('Veuillez sélectionner un dossier.', 'warning');
                return;
            }
            window.location.href = `hospital-alert-details.html?alert_id=${selectedCaseId}`;
        });
    }

    const reportForm = document.getElementById('doctorReportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', handleDoctorReportSubmit);
    }
}

function displayDoctorIdentity() {
    const doctorName = localStorage.getItem('user_name') || 'Médecin';
    const target = document.getElementById('doctorName');
    if (target) {
        target.textContent = doctorName;
    }
}

async function loadAssociatedHospitals() {
    associatedHospitalIds = new Set();
    associatedHospitals = [];

    if (currentHospitalId) {
        associatedHospitalIds.add(currentHospitalId);
    }

    try {
        const hospitals = await apiCall('/hospitals/?limit=500');
        if (Array.isArray(hospitals)) {
            if (currentHospitalId) {
                const primary = hospitals.find((h) => h.id === currentHospitalId);
                if (primary) {
                    associatedHospitals.push(primary);
                }
            }
            // Les médecins référents n'ont pas accès à cette page.
        }
    } catch (error) {
        console.warn('Impossible de charger les hôpitaux associés:', error);
        if (!associatedHospitalIds.size && currentHospitalId) {
            associatedHospitalIds.add(currentHospitalId);
        }
    }

    const context = document.getElementById('doctorHospitalContext');
    if (context) {
        if (!associatedHospitals.length && !associatedHospitalIds.size) {
            context.textContent = "Aucun hôpital n'est encore associé à votre profil.";
        } else {
            const names = associatedHospitals.length
                ? associatedHospitals.map((h) => h.nom).join(', ')
                : 'Hôpital non renseigné';
            context.textContent = `Établissement${associatedHospitalIds.size > 1 ? 's' : ''} suivi${associatedHospitalIds.size > 1 ? 's' : ''}: ${names}`;
        }
    }
}

async function loadHospitalStayOptions() {
    try {
        const options = await apiCall('/hospital-sinistres/hospital-stays/options');
        hospitalStayOptions = options || { actes: [], examens: [] };
    } catch (error) {
        console.warn('Impossible de charger les options de séjour:', error);
        hospitalStayOptions = { actes: [], examens: [] };
    }
}

async function loadDoctorCases(showToast = false) {
    setCasesLoading(true);
    clearCasesError();
    try {
        const alerts = await apiCall('/sos/?limit=200');
        const relevantAlerts = filterAlertsForDoctor(alerts);
        const casePromises = relevantAlerts.map((alert) => fetchDoctorCase(alert));
        const resolvedCases = (await Promise.all(casePromises)).filter(Boolean);
        doctorCases = resolvedCases;
        splitDoctorCases();
        renderDoctorCases();
        renderHistoryCases();
        updateStats();

        if (selectedCaseId) {
            const stillExists = doctorCases.some((item) => item.alert.id === selectedCaseId);
            if (!stillExists) {
                selectedCaseId = null;
                document.getElementById('caseDetailsSection').hidden = true;
            }
        }

        if (showToast) {
            showAlert('Dossiers mis à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des dossiers médecin:', error);
        displayCasesError(error.message || 'Impossible de charger les dossiers.');
    } finally {
        setCasesLoading(false);
    }
}

function setCasesLoading(state) {
    const loader = document.getElementById('casesLoading');
    if (loader) {
        loader.style.display = state ? 'block' : 'none';
    }
}

function clearCasesError() {
    const errorEl = document.getElementById('casesError');
    if (errorEl) {
        errorEl.style.display = 'none';
        errorEl.textContent = '';
    }
}

function displayCasesError(message) {
    const errorEl = document.getElementById('casesError');
    if (errorEl) {
        errorEl.style.display = 'block';
        errorEl.textContent = message;
    }
}

function filterAlertsForDoctor(alerts = []) {
    if (!Array.isArray(alerts)) {
        return [];
    }
    if (!associatedHospitalIds.size) {
        return [];
    }
    return alerts.filter((alert) => {
        const hospitalId = alert?.assigned_hospital?.id;
        if (!hospitalId) {
            return false;
        }
        return associatedHospitalIds.has(hospitalId);
    });
}

async function fetchDoctorCase(alert) {
    try {
        const sinistre = await apiCall(`/sos/${alert.id}/sinistre`);
        if (!sinistre?.hospital_stay) {
            return null;
        }
        if (!canAccessCase(sinistre)) {
            return null;
        }
        return { alert, sinistre };
    } catch (error) {
        console.error(`Erreur lors du chargement du sinistre ${alert.id}:`, error);
        return null;
    }
}

function canAccessCase(sinistre) {
    const stay = sinistre?.hospital_stay;
    if (!stay) {
        return false;
    }
    const isAssignedDoctor = stay.doctor_id === currentUserId;
    return isAssignedDoctor;
}

function setDoctorTab(tab) {
    currentDoctorTab = tab;
    const toTreatPanel = document.getElementById('doctorToTreatPanel');
    const treatedPanel = document.getElementById('doctorTreatedPanel');
    const tabToTreat = document.getElementById('tabDoctorToTreat');
    const tabTreated = document.getElementById('tabDoctorTreated');
    if (toTreatPanel) toTreatPanel.hidden = tab !== 'to_treat';
    if (treatedPanel) treatedPanel.hidden = tab !== 'treated';
    if (tabToTreat) {
        tabToTreat.classList.toggle('active', tab === 'to_treat');
        tabToTreat.setAttribute('aria-selected', tab === 'to_treat' ? 'true' : 'false');
    }
    if (tabTreated) {
        tabTreated.classList.toggle('active', tab === 'treated');
        tabTreated.setAttribute('aria-selected', tab === 'treated' ? 'true' : 'false');
    }
}

function renderPriorityBadgeHtml(priority) {
    return `<span class="priority-badge ${getPriorityClass(priority)}">${escapeHtml(getPriorityLabel(priority))}</span>`;
}

function buildDoctorToTreatCard(alert, sinistre) {
    const patient = alert.user_full_name || `Utilisateur #${alert.user_id}`;
    const description = alert.description ? truncate(alert.description, 120) : 'Aucune description';
    const priorityBadge = renderPriorityBadgeHtml(alert.priorite);
    const stayStatus = getStayStatusBadge(sinistre.hospital_stay?.status);
    const hospitalName = alert.assigned_hospital?.nom || '—';
    const alertLabel = escapeHtml(alert.numero_alerte || `Alerte #${alert.id}`);
    const updated = formatDateTime(alert.updated_at);
    const dossierUrl = `hospital-alert-details.html?alert_id=${alert.id}`;
    const isSelected = selectedCaseId === alert.id;
    return `
        <li class="card reception-alert-card doctor-case-card${isSelected ? ' selected' : ''}" data-row-alert-id="${alert.id}" tabindex="0" role="group" aria-label="Dossier ${alertLabel}">
            <div class="reception-alert-card__body">
                <div class="reception-alert-card__main">
                    <div class="reception-alert-card__head">
                        <strong class="reception-alert-card__numero">${alertLabel}</strong>
                        <span class="reception-alert-card__priority">${priorityBadge}</span>
                    </div>
                    <p class="reception-alert-card__patient">${escapeHtml(patient)}</p>
                    <p class="muted small doctor-case-card__description">${escapeHtml(description)}</p>
                    <div class="doctor-case-card__meta">
                        <span class="doctor-case-card__meta-item"><strong>Hôpital</strong> ${escapeHtml(hospitalName)}</span>
                        <span class="doctor-case-card__meta-sep" aria-hidden="true">·</span>
                        <span class="doctor-case-card__meta-item">${stayStatus}</span>
                    </div>
                    <p class="muted small reception-alert-card__date">Mis à jour le ${updated}</p>
                </div>
                <div class="reception-alert-card__actions">
                    <a class="btn btn-primary btn-sm" href="hospital-doctor-report.html?alert_id=${alert.id}">Traiter</a>
                    <a class="btn btn-outline btn-sm" href="${dossierUrl}">Voir la fiche</a>
                </div>
            </div>
        </li>
    `;
}

function bindDoctorToTreatCardList(cardList) {
    cardList.querySelectorAll('.doctor-case-card[data-row-alert-id]').forEach((li) => {
        li.addEventListener('click', (e) => {
            if (e.target.closest('a, button')) {
                return;
            }
            const id = Number(li.getAttribute('data-row-alert-id'));
            selectDoctorCase(id);
        });
        li.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter' && e.key !== ' ') {
                return;
            }
            if (e.target !== li) {
                return;
            }
            e.preventDefault();
            const id = Number(li.getAttribute('data-row-alert-id'));
            selectDoctorCase(id);
        });
    });
}

function renderDoctorCases() {
    const cardList = document.getElementById('doctorCasesCardList');
    const emptyState = document.getElementById('casesEmpty');
    const toTreatPanel = document.getElementById('doctorToTreatPanel');
    if (!cardList || !emptyState) {
        return;
    }
    if (toTreatPanel) toTreatPanel.hidden = currentDoctorTab !== 'to_treat';

    let casesToShow = activeDoctorCases;
    if (searchDoctorToTreat) {
        casesToShow = casesToShow.filter((entry) => matchDoctorCaseSearch(entry, searchDoctorToTreat));
    }

    if (!casesToShow.length) {
        cardList.innerHTML = '';
        cardList.hidden = true;
        emptyState.hidden = false;
        return;
    }

    emptyState.hidden = true;
    cardList.hidden = false;

    const totalPages = Math.max(1, Math.ceil(casesToShow.length / ROWS_PER_PAGE));
    currentPageDoctorToTreat = Math.min(currentPageDoctorToTreat, totalPages - 1);
    const start = currentPageDoctorToTreat * ROWS_PER_PAGE;
    const pageData = casesToShow.slice(start, start + ROWS_PER_PAGE);

    cardList.innerHTML = pageData
        .map(({ alert, sinistre }) => buildDoctorToTreatCard(alert, sinistre))
        .join('');

    bindDoctorToTreatCardList(cardList);
    const pagEl = document.getElementById('doctorToTreatPagination');
    if (pagEl) {
        if (casesToShow.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, casesToShow.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${casesToShow.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="docPrev" ${currentPageDoctorToTreat <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageDoctorToTreat + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="docNext" ${currentPageDoctorToTreat >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('docPrev')?.addEventListener('click', () => { currentPageDoctorToTreat--; renderDoctorCases(); });
            document.getElementById('docNext')?.addEventListener('click', () => { currentPageDoctorToTreat++; renderDoctorCases(); });
        }
    }
}

function splitDoctorCases() {
    activeDoctorCases = [];
    historyDoctorCases = [];
    doctorCases.forEach((entry) => {
        const stay = entry.sinistre?.hospital_stay;
        const status = stay?.status || '';
        if (isHistoryStatus(status)) {
            historyDoctorCases.push(entry);
        } else {
            activeDoctorCases.push(entry);
        }
    });
}

function isHistoryStatus(status) {
    return ['awaiting_validation', 'validated', 'rejected', 'invoiced'].includes(status);
}

function matchDoctorCaseSearch(entry, term) {
    if (!term) return true;
    const t = term.toLowerCase();
    const { alert, sinistre } = entry;
    const numero = (alert.numero_alerte || `Alerte #${alert.id}`).toLowerCase();
    const patient = (alert.user_full_name || `Utilisateur #${alert.user_id}`).toLowerCase();
    const hospital = (alert.assigned_hospital?.nom || '').toLowerCase();
    const stayStatus = (sinistre?.hospital_stay?.status || '').toLowerCase();
    const reportStatus = (sinistre?.hospital_stay?.report_status || '').toLowerCase();
    return numero.includes(t) || patient.includes(t) || hospital.includes(t) || stayStatus.includes(t) || reportStatus.includes(t);
}

function buildDoctorHistoryCard(alert, sinistre) {
    const stay = sinistre.hospital_stay;
    const patient = alert.user_full_name || `Utilisateur #${alert.user_id}`;
    const statusBadge = getStayStatusBadge(stay?.status);
    const reportStatus = stay?.report_status ? escapeHtml(stay.report_status) : '—';
    const updated = formatDateTime(stay?.updated_at || alert.updated_at);
    const dossierUrl = `hospital-alert-details.html?alert_id=${alert.id}`;
    const alertLabel = escapeHtml(alert.numero_alerte || `Alerte #${alert.id}`);
    return `
        <li class="card reception-alert-card doctor-history-card" role="group" aria-label="Dossier traité ${alertLabel}">
            <div class="reception-alert-card__body">
                <div class="reception-alert-card__main">
                    <div class="reception-alert-card__head">
                        <strong class="reception-alert-card__numero">${alertLabel}</strong>
                    </div>
                    <p class="reception-alert-card__patient">${escapeHtml(patient)}</p>
                    <div class="doctor-case-card__meta">
                        <span class="doctor-case-card__meta-item">${statusBadge}</span>
                        <span class="doctor-case-card__meta-sep" aria-hidden="true">·</span>
                        <span class="doctor-case-card__meta-item">Rapport <span class="badge">${reportStatus}</span></span>
                    </div>
                    <p class="muted small reception-alert-card__date">Dernière mise à jour · ${updated}</p>
                </div>
                <div class="reception-alert-card__actions">
                    <a class="btn btn-primary btn-sm" href="${dossierUrl}">Voir le dossier</a>
                </div>
            </div>
        </li>
    `;
}

function renderHistoryCases() {
    const treatedPanel = document.getElementById('doctorTreatedPanel');
    const cardList = document.getElementById('doctorHistoryCardList');
    const empty = document.getElementById('historyEmpty');
    if (!cardList || !empty) {
        return;
    }
    if (treatedPanel) treatedPanel.hidden = currentDoctorTab !== 'treated';

    let casesToShow = historyDoctorCases;
    if (searchDoctorTreated) {
        casesToShow = casesToShow.filter((entry) => matchDoctorCaseSearch(entry, searchDoctorTreated));
    }

    if (!casesToShow.length) {
        cardList.innerHTML = '';
        cardList.hidden = true;
        empty.hidden = false;
        return;
    }

    empty.hidden = true;
    cardList.hidden = false;

    const totalPages = Math.max(1, Math.ceil(casesToShow.length / ROWS_PER_PAGE));
    currentPageDoctorTreated = Math.min(currentPageDoctorTreated, totalPages - 1);
    const start = currentPageDoctorTreated * ROWS_PER_PAGE;
    const pageData = casesToShow.slice(start, start + ROWS_PER_PAGE);

    cardList.innerHTML = pageData
        .map(({ alert, sinistre }) => buildDoctorHistoryCard(alert, sinistre))
        .join('');
    const pagEl = document.getElementById('doctorTreatedPagination');
    if (pagEl) {
        if (casesToShow.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, casesToShow.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${casesToShow.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="histPrev" ${currentPageDoctorTreated <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageDoctorTreated + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="histNext" ${currentPageDoctorTreated >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('histPrev')?.addEventListener('click', () => { currentPageDoctorTreated--; renderHistoryCases(); });
            document.getElementById('histNext')?.addEventListener('click', () => { currentPageDoctorTreated++; renderHistoryCases(); });
        }
    }
}

function getStayStatusBadge(status) {
    if (!status) {
        return '<span class="status-badge status-pending">En attente</span>';
    }
    const labels = {
        in_progress: 'En cours',
        awaiting_validation: 'Rapport envoyé',
        validated: 'Validé',
        rejected: 'Rejeté',
        invoiced: 'Facturé',
        completed: 'Clôturé',
    };
    const label = labels[status] || status;
    const cls = ['validated', 'invoiced', 'completed'].includes(status) ? 'status-active' : 'status-pending';
    return `<span class="status-badge ${cls}">${escapeHtml(label)}</span>`;
}

function selectDoctorCase(alertId) {
    const match = doctorCases.find((item) => item.alert.id === Number(alertId));
    if (!match) {
        showAlert("Impossible d'ouvrir ce dossier.", 'error');
        return;
    }
    selectedCaseId = alertId;
    renderSelectedCase(match);
    document.querySelectorAll('.doctor-case-card[data-row-alert-id]').forEach((card) => {
        const rowId = Number(card.getAttribute('data-row-alert-id'));
        card.classList.toggle('selected', rowId === Number(alertId));
    });
}

function renderSelectedCase(caseEntry) {
    const section = document.getElementById('caseDetailsSection');
    if (!section) {
        return;
    }
    section.hidden = false;

    const { alert, sinistre } = caseEntry;
    renderCaseMeta(alert, sinistre);
    renderCaseOverview(alert, sinistre);
    renderPatientDetails(alert, sinistre);
    renderMedicalData(sinistre?.medical_questionnaire);
    populateReportForm(sinistre?.hospital_stay);
}

function renderCaseMeta(alert, sinistre) {
    const meta = document.getElementById('caseMeta');
    if (!meta) {
        return;
    }
    const alertLabel = alert.numero_alerte || `Alerte #${alert.id}`;
    const sinistreLabel = sinistre?.numero_sinistre || `Sinistre #${sinistre?.id || '—'}`;
    const lastUpdate = formatDateTime(alert.updated_at);
    meta.textContent = `${alertLabel} • ${sinistreLabel} • Mise à jour ${lastUpdate}`;
}

function renderCaseOverview(alert, sinistre) {
    const container = document.getElementById('caseOverview');
    if (!container) {
        return;
    }
    const patientName = alert.user_full_name || sinistre?.patient?.full_name || `Utilisateur #${alert.user_id}`;
    const hospitalName = alert.assigned_hospital?.nom || sinistre?.hospital?.nom || 'Non défini';
    const priorityBadge = `<span class="priority-badge ${getPriorityClass(alert.priorite)}">${getPriorityLabel(alert.priorite)}</span>`;
    const workflowState = (sinistre?.workflow_steps || []).find((step) => step.step_key === 'verification_urgence');
    const workflowStatus = workflowState
        ? `<span class="status-badge ${workflowState.statut === 'completed' ? 'status-active' : 'status-pending'}">${translateWorkflowStatus(workflowState.statut)}</span>`
        : '<span class="status-badge status-pending">Décision en attente</span>';

    container.innerHTML = `
        <div class="case-overview-card">
            <h5>Patient</h5>
            <p><strong>${escapeHtml(patientName)}</strong></p>
            <p class="muted">${sinistre?.numero_souscription ? escapeHtml(sinistre.numero_souscription) : (sinistre?.souscription_id ? `Souscription #${sinistre.souscription_id}` : '—')}</p>
        </div>
        <div class="case-overview-card">
            <h5>Hôpital assigné</h5>
            <p><strong>${escapeHtml(hospitalName)}</strong></p>
            <p class="muted">${priorityBadge}</p>
        </div>
        <div class="case-overview-card">
            <h5>Validation médicale</h5>
            <p>${workflowStatus}</p>
            <p class="muted">${workflowState?.details?.notes ? escapeHtml(workflowState.details.notes) : 'Aucune note'}</p>
        </div>
    `;
}

function translateWorkflowStatus(status) {
    switch (status) {
        case 'completed':
            return 'Validée';
        case 'in_progress':
            return 'En cours';
        case 'cancelled':
            return 'Refusée';
        default:
            return status || 'Indéterminé';
    }
}

function renderPatientDetails(alert, sinistre) {
    const container = document.getElementById('patientDetails');
    const notesTarget = document.getElementById('orientationNotes');
    if (!container) {
        return;
    }

    const patient = sinistre?.patient || {
        id: alert.user_id,
        full_name: alert.user_full_name,
        email: alert.user_email
    };

    const rows = [
        { label: 'Patient', value: patient.full_name || `Utilisateur #${patient.id}` },
        { label: 'Email', value: patient.email || '—' },
        { label: 'Numéro de sinistre', value: sinistre?.numero_sinistre || '—' },
        { label: 'Numéro d’alerte', value: alert.numero_alerte || `#${alert.id}` },
        { label: 'Priorité', value: getPriorityLabel(alert.priorite) },
        { label: 'Adresse', value: alert.adresse || '—' },
        {
            label: 'Coordonnées GPS',
            value:
                alert.latitude && alert.longitude
                    ? `${Number(alert.latitude).toFixed(4)}, ${Number(alert.longitude).toFixed(4)}`
                    : '—',
            fullWidth: true
        }
    ];

    container.innerHTML = `<div class="patient-dossier-grid" role="list">${rows
        .map(({ label, value, fullWidth }) =>
            renderPatientDossierField(label, escapeHtml(String(value ?? '—')), Boolean(fullWidth))
        )
        .join('')}</div>`;

    if (notesTarget) {
        const stay = sinistre?.hospital_stay;
        notesTarget.textContent = stay?.orientation_notes ? stay.orientation_notes : 'Aucune note partagée.';
    }
}

/** Retourne l'URL data:image d'une valeur (string ou objet avec url/data) ou null */
function getMedicalImageDataUrl(value) {
    if (typeof value === 'string' && value.trim().startsWith('data:image')) {
        return value.trim();
    }
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        const u = value.url || value.src || value.data;
        if (typeof u === 'string' && u.trim().startsWith('data:image')) return u.trim();
    }
    return null;
}

function renderMedicalData(questionnaire) {
    const container = document.getElementById('medicalDataContent');
    if (!container) {
        return;
    }
    if (!questionnaire?.reponses) {
        container.innerHTML = '<p class="muted">Aucune donnée médicale disponible.</p>';
        return;
    }
    const responses = questionnaire.reponses;
    const entries = Object.entries(responses).filter(
        ([key]) => key !== 'mode' && !REMOVED_MEDICAL_KEYS.has(key) && !CONSENT_KEYS.has(key)
    );
    if (!entries.length) {
        container.innerHTML = '<p class="muted">Aucune donnée médicale disponible.</p>';
        return;
    }
    const map = Object.fromEntries(entries);
    const used = new Set();

    function hasMedicalValue(v) {
        if (v === null || v === undefined) {
            return false;
        }
        if (typeof v === 'string') {
            return v.trim() !== '';
        }
        if (typeof v === 'boolean' || typeof v === 'number') {
            return true;
        }
        if (Array.isArray(v)) {
            return v.length > 0;
        }
        if (typeof v === 'object') {
            return Object.keys(v).length > 0;
        }
        return true;
    }

    const mobilePairs = [];
    for (const k of ['maladies_chroniques', 'traitements_en_cours', 'enceinte', 'antecedents_recents']) {
        if (hasMedicalValue(map[k])) {
            mobilePairs.push([k, map[k]]);
            used.add(k);
        }
    }
    let photoKey = null;
    if (hasMedicalValue(map.photo_medicale)) {
        photoKey = 'photo_medicale';
    } else if (hasMedicalValue(map.photo_identity)) {
        photoKey = 'photo_identity';
    } else if (hasMedicalValue(map.photoMedicale)) {
        photoKey = 'photoMedicale';
    }
    if (photoKey) {
        mobilePairs.push([photoKey, map[photoKey]]);
        used.add('photo_medicale');
        used.add('photo_identity');
        used.add('photoMedicale');
    }
    for (const k of ['declaration_sante', 'date_soumission']) {
        if (hasMedicalValue(map[k])) {
            mobilePairs.push([k, map[k]]);
            used.add(k);
        }
    }

    const symptomsSection = [];
    const surgerySection = [];
    const otherEntries = [];
    entries.forEach(([key, value]) => {
        if (used.has(key)) {
            return;
        }
        if (['symptoms', 'symptomOther', 'pregnancy'].includes(key)) {
            symptomsSection.push([key, value]);
        } else if (['surgeryLast6Months', 'surgeryLast6MonthsDetails'].includes(key)) {
            surgerySection.push([key, value]);
        } else {
            otherEntries.push([key, value]);
        }
    });

    function subsection(title, description, pairs) {
        if (!pairs.length) return '';
        const rows = pairs
            .map(([key, value]) => {
                const label =
                    MEDICAL_FIELD_DISPLAY_LABELS[key] ||
                    MEDICAL_FIELD_LABELS[key] ||
                    formatKeyLabel(key);
                return renderQuestionRowMedicalCard(label, formatDisplayValue(value, key, label));
            })
            .join('');
        return `
            <div class="questionnaire-subsection questionnaire-subsection--medical">
                <div class="questionnaire-subsection__header">
                    <h6>${escapeHtml(title)}</h6>
                    ${description ? `<p class="questionnaire-subsection__desc">${escapeHtml(description)}</p>` : ''}
                </div>
                <div class="questionnaire-content questionnaire-content--medical-dossier">${rows}</div>
            </div>`;
    }

    let html = '';
    if (mobilePairs.length > 0) {
        html += subsection(
            'Questionnaire médical (souscription mobile)',
            'Maladies chroniques, traitements, antécédents et mode de vie, photo, confirmation — comme sur l’application.',
            mobilePairs
        );
    }
    if (symptomsSection.length > 0) {
        html += subsection('Maladies et symptômes récents', 'Symptômes signalés, précisions et grossesse.', symptomsSection);
    }
    if (surgerySection.length > 0) {
        html += subsection('Opération chirurgicale', 'Opération dans les 6 derniers mois et précisions.', surgerySection);
    }
    if (otherEntries.length > 0) {
        html += subsection('Autres informations', '', otherEntries);
    }
    container.innerHTML = html || '<p class="muted">Aucune donnée médicale disponible.</p>';
}

/** Ligne type dossier médical (aligné médecin référent) */
function renderQuestionRow(label, valueHtml) {
    return `<div class="question-row"><span class="question-label">${escapeHtml(label)}</span><div class="question-value-cell">${valueHtml}</div></div>`;
}

function normalizeMedicalLabelMatch(s) {
    return String(s || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

function stripRedundantLabelFromPlainText(fieldLabel, plain) {
    if (!fieldLabel || typeof plain !== 'string') {
        return plain;
    }
    const trimmed = plain.trim();
    const colonIdx = trimmed.indexOf(':');
    if (colonIdx < 1) {
        return plain;
    }
    const left = trimmed.slice(0, colonIdx).trim();
    const right = trimmed.slice(colonIdx + 1).trim();
    if (normalizeMedicalLabelMatch(left) === normalizeMedicalLabelMatch(fieldLabel)) {
        return right || '—';
    }
    return plain;
}

function formatAntecedentsListHtml(plain) {
    const lines = plain.split(/\n/).map((l) => l.trim()).filter(Boolean);
    if (!lines.length) {
        return '<span class="muted">—</span>';
    }
    return `<ul class="medical-antecedents-list">${lines
        .map((line) => {
            const m = line.match(/^([^:]+):\s*(.*)$/);
            if (m) {
                const q = m[1].trim();
                const a = m[2].trim();
                return `<li><span class="medical-antecedents-list__q">${escapeHtml(q)}</span><span class="medical-antecedents-list__a">${escapeHtml(a || '—')}</span></li>`;
            }
            return `<li class="medical-antecedents-list__plain">${escapeHtml(line)}</li>`;
        })
        .join('')}</ul>`;
}

function renderQuestionRowMedicalCard(label, valueHtml) {
    return `<div class="question-row question-row--medical-card"><span class="question-label">${escapeHtml(label)}</span><div class="question-answer-wrap medical-value-wrap">${valueHtml}</div></div>`;
}

function populateReportForm(stay) {
    const form = document.getElementById('doctorReportForm');
    const submitBtn = document.getElementById('saveReportBtn');
    if (!form || !submitBtn) {
        return;
    }
    if (!stay) {
        form.reset();
        submitBtn.disabled = true;
        return;
    }
    form.reset();
    document.getElementById('motifConsultation').value = stay.report_motif_consultation || '';
    document.getElementById('motifHospitalisation').value = stay.report_motif_hospitalisation || '';
    // Affichage en jours (API stocke en heures)
    const heures = stay.report_duree_sejour_heures;
    document.getElementById('dureeSejour').value = heures != null && heures !== '' ? (Number(heures) / 24) : '';
    document.getElementById('resumeSejour').value = stay.report_resume || '';
    document.getElementById('observationsSejour').value = stay.report_observations || '';
    document.getElementById('terminerSejour').checked = stay.status === 'completed';

    buildOptionsChecklist('actesOptions', hospitalStayOptions.actes, stay.report_actes || []);
    buildOptionsChecklist('examensOptions', hospitalStayOptions.examens, stay.report_examens || []);

    const canSubmit = stay.doctor_id === currentUserId;
    submitBtn.disabled = !canSubmit;
}

function buildOptionsChecklist(containerId, options, selectedValues) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    const selectedSet = new Set(selectedValues || []);
    container.innerHTML = options
        .map(
            (option) => `
            <label>
                <input type="checkbox" value="${escapeHtml(option)}" ${selectedSet.has(option) ? 'checked' : ''}>
                ${escapeHtml(option)}
            </label>
        `
        )
        .join('');
}

async function handleDoctorReportSubmit(event) {
    event.preventDefault();
    if (!selectedCaseId) {
        showAlert('Sélectionnez un dossier avant de soumettre un rapport.', 'warning');
        return;
    }
    const entry = doctorCases.find((item) => item.alert.id === selectedCaseId);
    const stay = entry?.sinistre?.hospital_stay;
    if (!stay) {
        showAlert('Ce dossier ne dispose pas encore de séjour hospitalier.', 'warning');
        return;
    }

    const actes = Array.from(document.querySelectorAll('#actesOptions input:checked')).map((input) => input.value);
    const examens = Array.from(document.querySelectorAll('#examensOptions input:checked')).map((input) => input.value);

    const payload = {
        motif_consultation: document.getElementById('motifConsultation').value || null,
        motif_hospitalisation: document.getElementById('motifHospitalisation').value || null,
        duree_sejour_heures: document.getElementById('dureeSejour').value
            ? Math.round(Number(document.getElementById('dureeSejour').value) * 24)
            : null,
        actes_effectues: actes,
        examens_effectues: examens,
        resume: document.getElementById('resumeSejour').value || null,
        observations: document.getElementById('observationsSejour').value || null,
        terminer_sejour: document.getElementById('terminerSejour').checked
    };

    const submitBtn = document.getElementById('saveReportBtn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Enregistrement...';

    try {
        await apiCall(`/hospital-sinistres/hospital-stays/${stay.id}/report`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        showAlert('Rapport médical enregistré.', 'success');
        const hadCloture = payload.terminer_sejour === true;
        const reportPage = isDoctorReportPage();

        if (reportPage && hadCloture) {
            window.location.href = 'hospital-doctor.html';
            return;
        }

        if (hadCloture) {
            const detailsSection = document.getElementById('caseDetailsSection');
            if (detailsSection) {
                detailsSection.hidden = true;
            }
            selectedCaseId = null;
        } else {
            await refreshSelectedCase();
        }

        if (!reportPage) {
            await loadDoctorCases();
            if (hadCloture) {
                setDoctorTab('treated');
            }
        }
    } catch (error) {
        console.error('Erreur lors de la sauvegarde du rapport:', error);
        showAlert(error.message || 'Impossible d’enregistrer le rapport.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer le rapport';
    }
}

async function refreshSelectedCase() {
    if (!selectedCaseId) {
        return;
    }
    const entry = doctorCases.find((item) => item.alert.id === selectedCaseId);
    if (!entry) {
        return;
    }
    try {
        const sinistre = await apiCall(`/sos/${entry.alert.id}/sinistre`);
        if (!sinistre?.hospital_stay || !canAccessCase(sinistre)) {
            doctorCases = doctorCases.filter((item) => item.alert.id !== entry.alert.id);
            document.getElementById('caseDetailsSection').hidden = true;
            selectedCaseId = null;
            renderDoctorCases();
            updateStats();
            return;
        }
        entry.sinistre = sinistre;
        renderSelectedCase(entry);
    } catch (error) {
        console.error('Erreur lors de la mise à jour du dossier sélectionné:', error);
    }
}

function updateStats() {
    const assigned = document.getElementById('assignedCasesCount');
    const completed = document.getElementById('completedCasesCount');
    if (assigned) {
        assigned.textContent = activeDoctorCases.length.toString();
    }
    if (completed) {
        completed.textContent = historyDoctorCases.length.toString();
    }
    const tabToTreat = document.getElementById('tabDoctorToTreat');
    const tabTreated = document.getElementById('tabDoctorTreated');
    if (tabToTreat) {
        tabToTreat.textContent = `Dossiers à traiter (${activeDoctorCases.length})`;
    }
    if (tabTreated) {
        tabTreated.textContent = `Dossiers traités (${historyDoctorCases.length})`;
    }
}

/** Bloc fiche patient (aligné présentation dossier / questionnaire médecin) */
function renderPatientDossierField(label, valueHtml, fullWidth = false) {
    const mod = fullWidth ? ' patient-dossier-field--full' : '';
    return `
        <div class="patient-dossier-field${mod}" role="listitem">
            <div class="patient-dossier-field__label">${escapeHtml(label)}</div>
            <div class="patient-dossier-field__value">${valueHtml}</div>
        </div>
    `;
}

function formatDisplayValue(value, key = null, fieldLabel = null) {
    if (key === 'date_soumission' && typeof value === 'string') {
        const d = new Date(value);
        if (!Number.isNaN(d.getTime())) {
            return escapeHtml(d.toLocaleString('fr-FR'));
        }
    }

    if (key === 'antecedents_recents' && typeof value === 'string') {
        const plain = formatPlainValue(value);
        if (!plain || plain === '—') {
            return '<span class="muted">—</span>';
        }
        return formatAntecedentsListHtml(plain);
    }

    const imageDataUrl = getMedicalImageDataUrl(value);
    if (imageDataUrl) {
        const safe = imageDataUrl.replace(/"/g, '&quot;');
        return `<img src="${safe}" alt="Photo" loading="lazy" style="max-width: 100%; max-height: 280px; border-radius: 8px; display: block; margin-top: 0.35rem;" />`;
    }
    if (Array.isArray(value)) {
        if (!value.length) {
            return '<span class="muted">—</span>';
        }
        const pills = value
            .map((entry) => `<span class="questionnaire-pill">${escapeHtml(formatPlainValue(entry))}</span>`)
            .join('');
        return `<div class="questionnaire-pill-list">${pills}</div>`;
    }
    let plain = formatPlainValue(value);
    if (!plain || plain === '—') {
        return '<span class="muted">—</span>';
    }
    if (typeof plain === 'string' && fieldLabel && plain.includes(':')) {
        const stripped = stripRedundantLabelFromPlainText(fieldLabel, plain);
        if (stripped !== plain) {
            plain = stripped;
        }
    }
    // Ne pas afficher en clair une chaîne data:image
    if (typeof value === 'string' && value.trim().startsWith('data:image')) {
        return '<span class="muted">Photo non affichable</span>';
    }
    const toneClass =
        plain === 'Oui' || plain === 'Non' || plain === 'Non concerné' || plain === 'RAS'
            ? ' medical-value--discrete'
            : '';
    return `<span class="medical-value-text${toneClass}">${escapeHtml(plain)}</span>`;
}

function formatPlainValue(value) {
    if (value === null || value === undefined) {
        return '—';
    }
    if (typeof value === 'boolean') {
        return value ? 'Oui' : 'Non';
    }
    if (typeof value === 'number') {
        return String(value);
    }
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (!trimmed) {
            return '—';
        }
        if (trimmed.toLowerCase() === 'oui') return 'Oui';
        if (trimmed.toLowerCase() === 'non') return 'Non';
        if (trimmed.toLowerCase() === 'non_concerne') return 'Non concerné';
        return trimmed;
    }
    if (typeof value === 'object') {
        try {
            return JSON.stringify(value);
        } catch (error) {
            return String(value);
        }
    }
    return String(value);
}

function formatKeyLabel(key) {
    return String(key || '')
        .replace(/_/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getPriorityLabel(priority) {
    const map = {
        critique: 'Critique',
        urgente: 'Urgente',
        elevee: 'Élevée',
        normale: 'Normale',
        faible: 'Faible'
    };
    return map[priority] || priority || 'Normale';
}

function getPriorityClass(priority) {
    const map = {
        critique: 'priority-critique',
        urgente: 'priority-urgente',
        elevee: 'priority-elevee',
        normale: 'priority-normale',
        faible: 'priority-faible'
    };
    return map[priority] || 'priority-normale';
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
        minute: '2-digit'
    });
}

function truncate(text, maxLength) {
    if (!text || text.length <= maxLength) {
        return text || '';
    }
    return `${text.slice(0, maxLength - 3)}...`;
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

window.selectDoctorCase = selectDoctorCase;

