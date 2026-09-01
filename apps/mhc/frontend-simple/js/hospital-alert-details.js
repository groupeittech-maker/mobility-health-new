const ALLOWED_HOSPITAL_ROLES = [
    'hospital_admin',
    'agent_reception_hopital',
    'medecin_referent_mh',
    'medecin_hopital',
    'doctor',
    'agent_comptable_hopital'
];
const ACTIVE_ALERT_STATUSES = new Set(['en_attente', 'en_cours']);
const ALERTS_FETCH_LIMIT = 200;

const MEDICAL_ACTION_ROLES = ['medecin_referent_mh'];
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
    honourDeclaration: 'Déclaration sur l’honneur',
    maladies_chroniques: 'Maladies chroniques',
    traitements_en_cours: 'Traitement médical régulier',
    antecedents_recents:
        'Hospitalisation (12 mois), tabac, alcool, activité physique, allergies, santé mentale',
    declaration_sante: 'Je déclare que les informations fournies sont exactes et complètes',
    date_soumission: 'Date de soumission du questionnaire',
    enceinte: 'Êtes-vous enceinte ? (si concerné)',
    photo_medicale: 'Photo',
    photo_identity: 'Photo',
    photoMedicale: 'Photo'
};
/** Champs retirés du questionnaire médical (risques particuliers, voyage avec équipement) — non affichés. */
const REMOVED_MEDICAL_KEYS = new Set(['riskySports', 'medicalEquipment', 'equipmentDetails']);
/** Clés de déclarations/consentements — masquées dans le dossier patient pour le médecin référent. */
const CONSENT_KEYS = new Set(['honourDeclaration', 'technicalConsents']);
const SHORT_MEDICAL_FIELD_LABELS = {
    health: 'Santé générale',
    allergies: 'Allergies déclarées',
    medications: 'Traitements en cours',
    conditions: 'Conditions notables',
    insurance: 'Autre assurance santé'
};

/** Libellés courts en grille dossier (évite titres trop longs et doublons avec le texte mobile). */
const MEDICAL_FIELD_DISPLAY_LABELS = {
    antecedents_recents: 'Antécédents et habitudes de vie',
};

const RECEPTION_ACTION_ROLES = ['hospital_admin', 'agent_reception_hopital'];
const REPORT_VALIDATION_ROLES = ['medecin_referent_mh'];
const ACCOUNTING_ROLES = ['agent_comptable_hopital'];

let alertId = null;
let previousUrl = null;
let currentAlerte = null;
let currentSinistre = null;
let currentStay = null;
let currentUserRole = null;
let decisionControlsInitialized = false;
let hospitalStayOptions = { actes: [], examens: [] };
let hospitalDoctors = [];
const currentHospitalId = Number(localStorage.getItem('hospital_id') || 0);
const currentUserId = Number(localStorage.getItem('user_id') || 0);
let assignedAlerts = [];
const ROWS_PER_PAGE = 6;
let currentPageAssignedAlerts = 0;

function isMedicalDecisionLocked() {
    const status = currentAlerte?.statut || currentSinistre?.statut;
    if (!status) {
        return false;
    }
    return !ACTIVE_ALERT_STATUSES.has(status);
}

function isReferentForCurrentCase() {
    if (currentUserRole !== 'medecin_referent_mh') {
        return false;
    }
    const referentIds = [];
    if (currentSinistre?.medecin_referent_id) {
        referentIds.push(currentSinistre.medecin_referent_id);
    }
    if (currentSinistre?.hospital?.medecin_referent_id) {
        referentIds.push(currentSinistre.hospital.medecin_referent_id);
    }
    return referentIds.includes(currentUserId);
}

document.addEventListener('DOMContentLoaded', () => {
    initHospitalAlertDetails();
});

async function initHospitalAlertDetails() {
    const allowed = await requireAnyRole(ALLOWED_HOSPITAL_ROLES, 'hospital-dashboard.html');
    if (!allowed) {
        return;
    }
    const params = new URLSearchParams(window.location.search);
    const rawAlertParam = (params.get('alert_id') || params.get('id') || '').trim();
    alertId = rawAlertParam || null;
    previousUrl = params.get('from') || document.referrer || '';
    currentUserRole = localStorage.getItem('user_role');
    configureBackLink();
    bindAssignedAlertsEvents();
    toggleMedicalDecisionSection();
    toggleAssignedAlertsSection();
    await loadHospitalStayOptions();
    if (!alertId) {
        await handleLandingWithoutAlert();
        return;
    }
    await loadAlertDetails();
}

async function loadAlertDetails() {
    try {
        const alerte = await apiCall(`/sos/${alertId}`);
        hideReceptionLanding();
        renderAlertInfo(alerte);
        const sinistre = await apiCall(`/sos/${alertId}/sinistre`);
        renderSinistreInfo(sinistre, alerte);
    } catch (error) {
        console.error('Erreur lors du chargement du dossier:', error);
        showAlert(error.message || 'Impossible de charger le dossier.', 'error');
    }
}

async function handleLandingWithoutAlert() {
    const isReception = RECEPTION_ACTION_ROLES.includes(currentUserRole || '');
    const isDoctor = ['doctor', 'medecin_hopital'].includes(currentUserRole || '');
    if (!isReception && !isDoctor) {
        showReceptionLanding('Ouvrez cette page depuis le tableau des alertes ou un dossier existant.');
        showAlert('Identifiant d’alerte manquant.', 'error');
        await loadAssignedAlerts(false);
        return;
    }
    if (isDoctor) {
        showReceptionLanding('Ouvrez un dossier depuis l\'onglet « Dossiers traités » de la page Traitement.');
        const landingActions = document.querySelector('.landing-actions');
        if (landingActions) {
            const link = document.createElement('a');
            link.href = 'hospital-doctor.html';
            link.className = 'btn btn-outline';
            link.textContent = 'Retour à la prise en charge';
            landingActions.innerHTML = '';
            landingActions.appendChild(link);
        }
        return;
    }
    if (!currentHospitalId) {
        showReceptionLanding('Aucun hôpital n’est associé à votre compte. Contactez un administrateur pour finaliser votre profil.');
        return;
    }
    showReceptionLanding('Sélectionnez ci-dessous une alerte assignée pour afficher son dossier.');
    await loadAssignedAlerts();
}

async function loadHospitalStayOptions() {
    try {
        hospitalStayOptions = await apiCall('/hospital-sinistres/hospital-stays/options');
    } catch (error) {
        console.warn('Impossible de charger les options de séjour:', error);
        hospitalStayOptions = { actes: [], examens: [] };
    }
}

function configureBackLink() {
    const backLink = document.getElementById('backLink');
    if (!backLink) {
        return;
    }
    backLink.addEventListener('click', (event) => {
        event.preventDefault();
        if (previousUrl) {
            window.location.href = previousUrl;
            return;
        }
        const defaultTarget = getDefaultBackTarget();
        window.location.href = defaultTarget;
    });
}

function getDefaultBackTarget() {
    if (!currentUserRole) {
        return 'index.html';
    }
    if (['doctor', 'medecin_hopital'].includes(currentUserRole)) {
        return 'hospital-doctor.html';
    }
    if (currentUserRole === 'medecin_referent_mh') {
        return 'medical-review.html';
    }
    if (RECEPTION_ACTION_ROLES.includes(currentUserRole)) {
        return 'hospital-reception.html';
    }
    if (currentUserRole === 'agent_comptable_hopital') {
        return 'hospital-invoices.html';
    }
    if (currentUserRole === 'agent_sinistre_mh' || currentUserRole === 'agent_sinistre_assureur') {
        return 'sinistre-invoices.html';
    }
    if (currentUserRole === 'sos_operator') {
        return 'sos-dashboard.html';
    }
    return 'hospital-dashboard.html';
}

function renderAlertInfo(alerte) {
    currentAlerte = alerte;
    document.getElementById('alertNumber').textContent = alerte.numero_alerte || `#${alerte.id}`;
    const userName = alerte.user_full_name || (alerte.user_email ? alerte.user_email.split('@')[0] : null) || `Utilisateur #${alerte.user_id}`;
    document.getElementById('alertMeta').textContent = `Créée le ${formatDateTime(alerte.created_at)} • ${userName}`;
    document.getElementById('alertStatus').innerHTML = `<span class="status-badge ${getStatusClass(alerte.statut)}">${getStatusLabel(alerte.statut)}</span>`;
    document.getElementById('alertPriority').innerHTML = `<span class="priority-badge ${getPriorityClass(alerte.priorite)}">${getPriorityLabel(alerte.priorite)}</span>`;
    const coords = alerte.latitude && alerte.longitude ? `${Number(alerte.latitude).toFixed(4)}, ${Number(alerte.longitude).toFixed(4)}` : '—';
    document.getElementById('alertLocation').textContent = coords;
    document.getElementById('alertDescription').textContent = alerte.description || 'Aucune description';
}

function renderSinistreInfo(sinistre, alerte) {
    currentSinistre = sinistre;
    currentStay = sinistre.hospital_stay || null;

    const patientInfo = document.getElementById('patientInfo');
    if (patientInfo) {
        const patient = sinistre.patient || {
            id: alerte.user_id,
            full_name: alerte.user_full_name,
            email: alerte.user_email
        };
        const name = patient.full_name || `Utilisateur #${patient.id}`;
        const email = patient.email || '—';
        const sous =
            sinistre.numero_souscription != null && String(sinistre.numero_souscription).trim() !== ''
                ? escapeHtml(String(sinistre.numero_souscription))
                : sinistre.souscription_id
                  ? `Souscription #${sinistre.souscription_id}`
                  : '—';
        patientInfo.innerHTML = `<div class="patient-dossier-grid" role="list">
            ${renderCivilDossierField('Patient', escapeHtml(name))}
            ${renderCivilDossierField('Email', email === '—' ? '<span class="muted">—</span>' : escapeHtml(email))}
            ${renderCivilDossierField('Souscription', sous === '—' ? '<span class="muted">—</span>' : sous)}
        </div>`;
    }

    const hospitalInfo = document.getElementById('hospitalInfo');
    if (hospitalInfo) {
        const hospital = sinistre.hospital;
        hospitalInfo.innerHTML = hospital ? `
            <div>
                <strong>Hôpital</strong>
                <div>${escapeHtml(hospital.nom)}</div>
                <div class="muted">${escapeHtml([hospital.ville, hospital.pays].filter(Boolean).join(', '))}</div>
            </div>
            <div>
                <strong>Médecin référent</strong>
                <div>${escapeHtml(sinistre.medecin_referent_nom || 'Non défini')}</div>
            </div>
            <div>
                <strong>Agent sinistre</strong>
                <div>${escapeHtml(sinistre.agent_sinistre_nom || 'Non défini')}</div>
            </div>
        ` : '<p class="muted">Aucun hôpital assigné.</p>';
    }

    const workflowList = document.getElementById('workflowList');
    if (workflowList) {
        workflowList.innerHTML = (sinistre.workflow_steps || []).map(step => `
            <li>
                <strong>${escapeHtml(step.titre)}</strong>
                <div class="muted">${escapeHtml(step.description || '')}</div>
                <div style="margin-top: 0.5rem; display: flex; flex-direction: column; gap: 0.25rem;">
                    <span class="status-badge ${getWorkflowStepStatusClass(step.statut)}">${getWorkflowStepStatusLabel(step.statut)}</span>
                    ${step.completed_at ? `<span class="map-badge" style="font-size: 0.75rem;">${formatDateTime(step.completed_at)}</span>` : ''}
                </div>
            </li>
        `).join('') || '<li class="muted">Aucune étape disponible.</li>';
    }

    renderPatientDossier(sinistre.patient, sinistre, alerte);
    updateMedicalDecisionStatus(sinistre.workflow_steps || []);
    renderReceptionActions();
    renderDoctorReport();
    renderReportValidationSection();
    renderInvoiceSection();
}

function showReceptionLanding(message) {
    const section = document.getElementById('receptionLandingSection');
    const messageEl = document.getElementById('receptionLandingMessage');
    if (messageEl) {
        messageEl.textContent = message;
    }
    if (section) {
        section.hidden = false;
    }
}

function hideReceptionLanding() {
    const section = document.getElementById('receptionLandingSection');
    if (section) {
        section.hidden = true;
    }
}

function bindAssignedAlertsEvents() {
    const refreshBtn = document.getElementById('refreshAssignedAlertsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadAssignedAlerts());
    }
}

async function loadAssignedAlerts(showLoading = true) {
    if (alertId) {
        return;
    }
    const errorEl = document.getElementById('assignedAlertsError');
    if (errorEl) {
        errorEl.hidden = true;
        errorEl.textContent = '';
    }

    if (!currentHospitalId || !RECEPTION_ACTION_ROLES.includes(currentUserRole || '')) {
        assignedAlerts = [];
        renderAssignedAlerts();
        if (!alertId) {
            const message = currentHospitalId
                ? 'Aucune alerte disponible pour votre profil.'
                : 'Aucun hôpital associé à votre compte.';
            showReceptionLanding(message);
        }
        return;
    }

    if (showLoading) {
        setAssignedAlertsLoading(true);
    }

    try {
        const alerts = await apiCall(`/sos/?limit=${ALERTS_FETCH_LIMIT}`);
        assignedAlerts = Array.isArray(alerts) ? filterAlertsForReception(alerts) : [];
        renderAssignedAlerts();
        if (!alertId) {
            if (assignedAlerts.length) {
                showReceptionLanding('Sélectionnez l’une des alertes ci-dessous pour ouvrir le dossier.');
            } else {
                showReceptionLanding('Aucune alerte active assignée pour le moment. Surveillez le tableau SOS.');
            }
        }
    } catch (error) {
        console.error('Erreur lors du chargement des alertes assignées:', error);
        assignedAlerts = [];
        renderAssignedAlerts();
        if (errorEl) {
            errorEl.hidden = false;
            errorEl.textContent = error.message || 'Impossible de charger les alertes assignées.';
        }
        if (!alertId) {
            showReceptionLanding('Impossible de charger les alertes. Utilisez le tableau SOS comme alternative.');
        }
    } finally {
        if (showLoading) {
            setAssignedAlertsLoading(false);
        }
    }
}

function filterAlertsForReception(alerts) {
    if (!Array.isArray(alerts)) {
        return [];
    }
    return alerts
        .map(normalizeAlertEntry)
        .filter(alert =>
            alert.assigned_hospital?.id === currentHospitalId &&
            ACTIVE_ALERT_STATUSES.has(alert.statut) &&
            !alert.is_oriented
        )
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
}

function normalizeAlertEntry(alert) {
    return {
        ...alert,
        numero_alerte: alert.numero_alerte || null,
        user_full_name: alert.user_full_name || alert.user?.full_name || null,
        created_at: alert.created_at || alert.updated_at || null,
    };
}

function renderAssignedAlerts() {
    const table = document.getElementById('assignedAlertsTable');
    const body = document.getElementById('assignedAlertsBody');
    const empty = document.getElementById('assignedAlertsEmpty');
    if (!table || !body || !empty) {
        return;
    }

    if (!assignedAlerts.length) {
        body.innerHTML = '';
        table.hidden = true;
        empty.hidden = false;
        return;
    }

    empty.hidden = true;
    table.hidden = false;

    const totalPages = Math.max(1, Math.ceil(assignedAlerts.length / ROWS_PER_PAGE));
    currentPageAssignedAlerts = Math.min(currentPageAssignedAlerts, totalPages - 1);
    const start = currentPageAssignedAlerts * ROWS_PER_PAGE;
    const pageData = assignedAlerts.slice(start, start + ROWS_PER_PAGE);
    body.innerHTML = pageData.map(buildAssignedAlertRow).join('');

    const pagEl = document.getElementById('assignedAlertsPagination');
    if (pagEl) {
        if (assignedAlerts.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, assignedAlerts.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${assignedAlerts.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="assignedPrev" ${currentPageAssignedAlerts <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageAssignedAlerts + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="assignedNext" ${currentPageAssignedAlerts >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('assignedPrev')?.addEventListener('click', () => { currentPageAssignedAlerts--; renderAssignedAlerts(); });
            document.getElementById('assignedNext')?.addEventListener('click', () => { currentPageAssignedAlerts++; renderAssignedAlerts(); });
        }
    }
}

function buildAssignedAlertRow(alert) {
    const numero = escapeHtml(alert.numero_alerte || `Alerte #${alert.id}`);
    const patient = escapeHtml(alert.user_full_name || `Utilisateur #${alert.user_id}` || '—');
    const priority = renderPriorityBadge(alert.priorite);
    const status = renderStatusBadge(alert.statut);
    const created = formatDateTime(alert.created_at);
    const link = `hospital-alert-details.html?alert_id=${alert.id}`;
    return `
        <tr>
            <td>${numero}</td>
            <td>${patient}</td>
            <td>${priority}</td>
            <td>${status}</td>
            <td>${created}</td>
            <td>
                <a class="btn btn-outline btn-sm" href="${link}">
                    Ouvrir
                </a>
            </td>
        </tr>
    `;
}

function renderPriorityBadge(priority) {
    return `<span class="priority-badge ${getPriorityClass(priority)}">${getPriorityLabel(priority)}</span>`;
}

function renderStatusBadge(status) {
    return `<span class="status-badge ${getStatusClass(status)}">${getStatusLabel(status)}</span>`;
}

function setAssignedAlertsLoading(state) {
    const loadingEl = document.getElementById('assignedAlertsLoading');
    if (loadingEl) {
        loadingEl.hidden = !state;
    }
}

function renderPatientDossier(patient, sinistre, alerte) {
    const section = document.getElementById('questionnaireSection');
    const civilContainer = document.getElementById('civilDataContent');
    const medicalContainer = document.getElementById('medicalDataContent');
    const versionBadge = document.getElementById('medicalQuestionnaireVersion');

    if (!section || !civilContainer || !medicalContainer) {
        return;
    }

    const civilRows = buildCivilRows(patient, sinistre, alerte);
    civilContainer.innerHTML = civilRows || '<p class="muted">Aucune donnée civile disponible.</p>';

    const medicalHtml = renderMedicalQuestionnaireBlock(sinistre.medical_questionnaire, { excludeConsent: true });
    medicalContainer.innerHTML = medicalHtml || '<p class="muted">Données médicales non disponibles.</p>';

    if (sinistre.medical_questionnaire?.version && versionBadge) {
        versionBadge.hidden = false;
        versionBadge.textContent = `v${sinistre.medical_questionnaire.version}`;
    } else if (versionBadge) {
        versionBadge.hidden = true;
    }

    section.hidden = !civilRows && !medicalHtml;
}

/** Grille identique à la fiche médecin hospitalier (patient-dossier-field). */
function renderCivilDossierField(label, valueHtml, opts = {}) {
    const { fullWidth = false, multiline = false } = opts;
    const mod = `${fullWidth ? ' patient-dossier-field--full' : ''}${multiline ? ' patient-dossier-field--multiline' : ''}`;
    return `
        <div class="patient-dossier-field${mod}" role="listitem">
            <div class="patient-dossier-field__label">${escapeHtml(label)}</div>
            <div class="patient-dossier-field__value">${valueHtml}</div>
        </div>
    `;
}

function buildCivilRows(patient = {}, sinistre, alerte) {
    if (!sinistre && !alerte) {
        return '';
    }
    const name = patient.full_name || `Utilisateur #${patient.id || alerte?.user_id || '—'}`;
    const email = patient.email || alerte?.user_email || '—';
    const numSin = sinistre?.numero_sinistre || '—';
    const numAlert = alerte?.numero_alerte || `#${alerte?.id || '—'}`;
    const sous =
        sinistre?.numero_souscription != null && String(sinistre.numero_souscription).trim() !== ''
            ? escapeHtml(String(sinistre.numero_souscription))
            : sinistre?.souscription_id
              ? `Souscription #${sinistre.souscription_id}`
              : '—';
    const prioriteText = escapeHtml(getPriorityLabel(alerte?.priorite));
    const adresse = alerte?.adresse || '—';
    const gpsRaw =
        alerte?.latitude != null && alerte?.longitude != null
            ? `${Number(alerte.latitude).toFixed(4)}, ${Number(alerte.longitude).toFixed(4)}`
            : '—';
    const gpsHtml = gpsRaw === '—' ? '<span class="muted">—</span>' : escapeHtml(gpsRaw);

    const cells = [
        renderCivilDossierField('Patient', escapeHtml(String(name || '—'))),
        renderCivilDossierField('Email', email === '—' ? '<span class="muted">—</span>' : escapeHtml(String(email))),
        renderCivilDossierField(
            'Numéro de sinistre',
            numSin === '—' ? '<span class="muted">—</span>' : escapeHtml(String(numSin))
        ),
        renderCivilDossierField('Numéro d’alerte', escapeHtml(String(numAlert))),
        renderCivilDossierField('Souscription', sous === '—' ? '<span class="muted">—</span>' : sous),
        renderCivilDossierField('Priorité', `<span class="medical-value-text">${prioriteText}</span>`),
        renderCivilDossierField(
            'Adresse',
            adresse === '—' ? '<span class="muted">—</span>' : escapeHtml(String(adresse))
        ),
        renderCivilDossierField('Coordonnées GPS', gpsHtml, { fullWidth: true })
    ];

    return `<div class="patient-dossier-grid" role="list">${cells.join('')}</div>`;
}

function normalizeMedicalLabelMatch(s) {
    return String(s || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

/** Si la valeur commence par « même libellé : … », n’afficher que la partie droite. */
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

function renderMedicalQuestionnaireBlock(questionnaire, options = {}) {
    if (!questionnaire || !questionnaire.reponses) {
        return '';
    }
    const responses = questionnaire.reponses;
    const questionnaireMode = String(
        responses.mode || questionnaire.type_questionnaire || ''
    ).toLowerCase();
    const excludeConsent = options.excludeConsent === true;
    if (questionnaireMode === 'short') {
        return renderShortMedicalQuestionnaire(responses, questionnaireMode, excludeConsent);
    }
    return renderLongMedicalQuestionnaire(responses, excludeConsent);
}

function renderLongMedicalQuestionnaire(responses, excludeConsent = false) {
    const entries = Object.entries(responses || {}).filter(
        ([key]) => key !== 'mode' && !REMOVED_MEDICAL_KEYS.has(key) && !(excludeConsent && CONSENT_KEYS.has(key))
    );
    if (!entries.length) {
        return '';
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
    const declarationsSection = [];
    const otherEntries = [];

    entries.forEach(([key, value]) => {
        if (used.has(key)) {
            return;
        }
        if (['symptoms', 'symptomOther', 'pregnancy'].includes(key)) {
            symptomsSection.push([key, value]);
        } else if (['surgeryLast6Months', 'surgeryLast6MonthsDetails'].includes(key)) {
            surgerySection.push([key, value]);
        } else if (!excludeConsent && CONSENT_KEYS.has(key)) {
            declarationsSection.push([key, value]);
        } else if (!CONSENT_KEYS.has(key)) {
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
    if (declarationsSection.length > 0) {
        html += subsection('Déclarations et consentements', '', declarationsSection);
    }
    return html;
}

function renderShortMedicalQuestionnaire(responses = {}, questionnaireMode = '', excludeConsent = false) {
    const overviewEntries = Object.entries(responses.overview || {}).filter(
        ([key]) => !excludeConsent || !CONSENT_KEYS.has(key)
    );
    const additionalEntries = Object.entries(responses)
        .filter(([key]) => !['mode', 'overview'].includes(key) && !REMOVED_MEDICAL_KEYS.has(key) && !(excludeConsent && CONSENT_KEYS.has(key)));
    const overviewContent = overviewEntries.length
        ? `<div class="medical-short-overview-card__grid">
                ${overviewEntries
                    .map(([key, value]) => renderShortOverviewChip(key, value))
                    .join('')}
           </div>`
        : '<p class="medical-short-empty">Aucune information fournie.</p>';
    const additionalHtml = additionalEntries.length
        ? `<div class="questionnaire-subsection questionnaire-subsection--medical" style="margin-top: 1rem;">
                <div class="questionnaire-subsection__header">
                    <h6>Informations complémentaires</h6>
                </div>
                <div class="questionnaire-content questionnaire-content--medical-dossier">
                ${additionalEntries
                    .map(([key, value]) => {
                        const label =
                            MEDICAL_FIELD_DISPLAY_LABELS[key] ||
                            SHORT_MEDICAL_FIELD_LABELS[key] ||
                            MEDICAL_FIELD_LABELS[key] ||
                            formatKeyLabel(key);
                        return renderQuestionRowMedicalCard(label, formatDisplayValue(value, key, label));
                    })
                    .join('')}
                </div>
           </div>`
        : '';
    const modeLabel = formatQuestionnaireModeLabel(questionnaireMode || responses.mode);
    return `
        <div class="medical-short-summary">
            <div class="medical-short-meta">
                <span class="medical-short-meta__label">Mode</span>
                <span class="medical-short-meta__value">${escapeHtml(modeLabel)}</span>
            </div>
            <div class="medical-short-overview-card">
                <div class="medical-short-overview-card__header">
                    <span>Vue d’ensemble</span>
                    <small>Synthèse rapide</small>
                </div>
                ${overviewContent}
            </div>
            ${additionalHtml}
        </div>
    `;
}

function renderDataPair(label, valueHtml) {
    return `
        <div class="data-pair">
            <div class="data-label">${escapeHtml(label)}</div>
            <div class="data-value">${valueHtml}</div>
        </div>
    `;
}

function renderShortOverviewChip(key, rawValue) {
    const label = SHORT_MEDICAL_FIELD_LABELS[key] || formatKeyLabel(key);
    const normalizedValue = normalizeShortValue(formatPlainValue(rawValue));
    const valueContent = normalizedValue
        ? escapeHtml(normalizedValue)
        : '<span class="muted">—</span>';
    return `
        <div class="medical-short-chip">
            <span class="medical-short-chip__label">${escapeHtml(label)}</span>
            <span class="medical-short-chip__value">${valueContent}</span>
        </div>
    `;
}

function formatQuestionnaireModeLabel(mode) {
    if (!mode) {
        return 'Mode non précisé';
    }
    const normalized = String(mode).toLowerCase();
    if (normalized === 'short') {
        return 'Questionnaire court';
    }
    if (normalized === 'long') {
        return 'Questionnaire long';
    }
    return formatKeyLabel(mode);
}

function normalizeShortValue(value) {
    if (!value || value === '—') {
        return '';
    }
    const normalized = String(value).trim();
    if (!normalized) {
        return '';
    }
    if (normalized.toLowerCase() === 'ras') {
        return 'RAS';
    }
    return normalized;
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

function formatDisplayValue(value, key = null, fieldLabel = null) {
    // Traitement spécial pour les objets de déclaration et consentements
    if (key === 'honourDeclaration' && typeof value === 'object' && value !== null) {
        return formatHonourDeclaration(value);
    }
    if (key === 'technicalConsents' && typeof value === 'object' && value !== null) {
        return formatTechnicalConsents(value);
    }

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

    // Photo : afficher l'image, ne pas afficher le lien data:image
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
    // Ne pas afficher en clair une chaîne data:image (reste affiché si pas reconnue comme image ci-dessus)
    if (typeof value === 'string' && value.trim().startsWith('data:image')) {
        return '<span class="muted">Photo non affichable</span>';
    }
    const toneClass =
        plain === 'Oui' || plain === 'Non' || plain === 'Non concerné' || plain === 'RAS'
            ? ' medical-value--discrete'
            : '';
    return `<span class="medical-value-text${toneClass}">${escapeHtml(plain)}</span>`;
}

function formatHonourDeclaration(value) {
    if (!value || typeof value !== 'object') {
        return '<span class="muted">—</span>';
    }
    
    const items = [];
    if (value.medicalHonesty1 !== undefined) {
        items.push({
            label: 'Je déclare n\'avoir rien omis dans ce questionnaire',
            checked: value.medicalHonesty1
        });
    }
    if (value.medicalHonesty2 !== undefined) {
        items.push({
            label: 'Je reconnais qu\'une fausse déclaration entraîne la nullité des garanties',
            checked: value.medicalHonesty2
        });
    }
    
    if (items.length === 0) {
        return '<span class="muted">—</span>';
    }
    
    return `
        <div class="declaration-list">
            ${items.map(item => `
                <div class="declaration-item">
                    <span class="declaration-check ${item.checked ? 'declaration-check--checked' : 'declaration-check--unchecked'}">
                        ${item.checked ? '✓' : '✗'}
                    </span>
                    <span class="declaration-text">${escapeHtml(item.label)}</span>
                </div>
            `).join('')}
        </div>
    `;
}

function formatTechnicalConsents(value) {
    if (!value || typeof value !== 'object') {
        return '<span class="muted">—</span>';
    }
    
    const items = [];
    if (value.acceptData !== undefined) {
        items.push({
            label: 'J\'accepte le traitement de mes données personnelles',
            checked: value.acceptData
        });
    }
    if (value.honesty1 !== undefined) {
        items.push({
            label: 'Je certifie que toutes les informations fournies sont exactes',
            checked: value.honesty1
        });
    }
    if (value.honesty2 !== undefined) {
        items.push({
            label: 'Je reconnais qu\'une fausse déclaration peut annuler la garantie',
            checked: value.honesty2
        });
    }
    if (value.acceptCG !== undefined) {
        items.push({
            label: 'J\'accepte les conditions générales',
            checked: value.acceptCG
        });
    }
    if (value.acceptExclusions !== undefined) {
        items.push({
            label: 'J\'accepte les clauses d\'exclusion',
            checked: value.acceptExclusions
        });
    }
    
    if (items.length === 0) {
        return '<span class="muted">—</span>';
    }
    
    return `
        <div class="declaration-list">
            ${items.map(item => `
                <div class="declaration-item">
                    <span class="declaration-check ${item.checked ? 'declaration-check--checked' : 'declaration-check--unchecked'}">
                        ${item.checked ? '✓' : '✗'}
                    </span>
                    <span class="declaration-text">${escapeHtml(item.label)}</span>
                </div>
            `).join('')}
        </div>
    `;
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
    if (Array.isArray(value)) {
        return value.map((entry) => formatPlainValue(entry)).join(', ');
    }
    if (typeof value === 'object') {
        try {
            return JSON.stringify(value, null, 2);
        } catch (error) {
            return String(value);
        }
    }
    return String(value);
}

function toggleMedicalDecisionSection() {
    const section = document.getElementById('medicalDecisionSection');
    if (!section) {
        return;
    }
    if (!MEDICAL_ACTION_ROLES.includes(currentUserRole)) {
        section.style.display = 'none';
        return;
    }
    section.style.display = '';
    setupMedicalDecisionControls();
}

function toggleAssignedAlertsSection() {
    const section = document.getElementById('assignedAlertsSection');
    if (!section) {
        return;
    }
    // Dossier ciblé : liste réservée à la page sans identifiant (voir aussi .mh-dossier-detail-view dans le CSS)
    if (alertId) {
        section.hidden = true;
        section.style.display = 'none';
        return;
    }
    section.style.display = '';
    // Masquer cette section pour tous les rôles sauf ceux de réception
    if (!RECEPTION_ACTION_ROLES.includes(currentUserRole)) {
        section.hidden = true;
        return;
    }
    section.hidden = false;
}

function setupMedicalDecisionControls() {
    if (decisionControlsInitialized) {
        return;
    }
    const approveBtn = document.getElementById('medicalApproveBtn');
    const rejectBtn = document.getElementById('medicalRejectBtn');
    if (!approveBtn || !rejectBtn) {
        return;
    }
    approveBtn.addEventListener('click', () => submitMedicalDecision(true));
    rejectBtn.addEventListener('click', () => submitMedicalDecision(false));
    decisionControlsInitialized = true;
}

function setMedicalDecisionButtonsDisabled(state) {
    const approveBtn = document.getElementById('medicalApproveBtn');
    const rejectBtn = document.getElementById('medicalRejectBtn');
    if (approveBtn) approveBtn.disabled = state;
    if (rejectBtn) rejectBtn.disabled = state;
}

function setMedicalDecisionNotesDisabled(state, placeholderText) {
    const notesField = document.getElementById('medicalDecisionNotes');
    if (!notesField) {
        return;
    }
    if (!notesField.dataset.defaultPlaceholder) {
        notesField.dataset.defaultPlaceholder = notesField.placeholder || 'Précisez votre décision...';
    }
    notesField.disabled = state;
    if (state && placeholderText) {
        notesField.placeholder = placeholderText;
        return;
    }
    notesField.placeholder = notesField.dataset.defaultPlaceholder;
}

async function submitMedicalDecision(approve) {
    if (!currentSinistre) {
        return;
    }
    const notesField = document.getElementById('medicalDecisionNotes');
    const notes = notesField ? notesField.value.trim() : '';
    setMedicalDecisionButtonsDisabled(true);
    try {
        await apiCall(`/sos/sinistres/${currentSinistre.id}/verification`, {
            method: 'POST',
            body: JSON.stringify({
                approve,
                notes: notes || undefined,
            }),
        });
        if (notesField) {
            notesField.value = '';
        }
        showAlert(
            approve
                ? 'Prise en charge confirmée. Le dossier passe dans l\'onglet « Sinistre validé ». Redirection...'
                : 'Alerte marquée comme non avérée. Redirection vers la liste des alertes...',
            approve ? 'success' : 'warning'
        );
        
        // Rediriger vers la liste des alertes après un court délai pour permettre de voir le message
        setTimeout(() => {
            let targetUrl = getDefaultBackTarget();
            // Médecin référent : ouvrir directement l'onglet « Sinistre validé » après validation
            if (approve && (currentUserRole === 'medecin_referent_mh' || currentUserRole === 'doctor')) {
                const sep = targetUrl.includes('?') ? '&' : '?';
                targetUrl = `${targetUrl}${sep}tab=sinistre_valide`;
            }
            window.location.href = targetUrl;
        }, 1500);
    } catch (error) {
        showAlert(error.message || 'Impossible d’enregistrer la décision.', 'error');
    } finally {
        setMedicalDecisionButtonsDisabled(false);
    }
}

function updateMedicalDecisionStatus(workflowSteps) {
    const statusEl = document.getElementById('medicalDecisionStatus');
    const section = document.getElementById('medicalDecisionSection');
    if (!statusEl || !section || section.style.display === 'none') {
        return;
    }
    if (isMedicalDecisionLocked()) {
        statusEl.textContent = 'Décision médicale verrouillée : alerte clôturée.';
        setMedicalDecisionButtonsDisabled(true);
        setMedicalDecisionNotesDisabled(true, 'Alerte clôturée, décision non modifiable.');
        return;
    }
    const step = workflowSteps.find((s) => s.step_key === 'verification_urgence');
    if (!step) {
        statusEl.textContent = 'Étape de vérification indisponible pour ce sinistre.';
        setMedicalDecisionButtonsDisabled(true);
        setMedicalDecisionNotesDisabled(true, 'Étape de vérification indisponible.');
        return;
    }
    const notes = step.details?.notes ? ` • ${step.details.notes}` : '';
    if (step.statut === 'completed') {
        statusEl.textContent = `Alerte confirmée par un médecin${notes}`;
        setMedicalDecisionButtonsDisabled(true);
        setMedicalDecisionNotesDisabled(true, 'Décision déjà confirmée.');
    } else if (step.statut === 'cancelled') {
        statusEl.textContent = `Alerte refusée${notes}`;
        setMedicalDecisionButtonsDisabled(true);
        setMedicalDecisionNotesDisabled(true, 'Décision déjà refusée.');
    } else {
        statusEl.textContent = 'Décision médicale attendue : confirmez ou refusez la véracité.';
        setMedicalDecisionButtonsDisabled(false);
        setMedicalDecisionNotesDisabled(false);
    }
}

function getWorkflowStep(stepKey) {
    return (currentSinistre?.workflow_steps || []).find(step => step.step_key === stepKey);
}

async function renderReceptionActions() {
    const section = document.getElementById('receptionActionsSection');
    if (!section) {
        return;
    }
    const isReception = RECEPTION_ACTION_ROLES.includes(currentUserRole || '');
    const sameHospital = currentHospitalId && currentSinistre?.hospital?.id && currentHospitalId === currentSinistre.hospital.id;
    if (!isReception || !sameHospital) {
        section.hidden = true;
        return;
    }
    section.hidden = false;

    const dispatchBtn = document.getElementById('dispatchAmbulanceBtn');
    const ambulanceStep = getWorkflowStep('ambulance_en_route');
    const dispatched = ambulanceStep && ambulanceStep.statut === 'completed';
    dispatchBtn.disabled = dispatched;
    dispatchBtn.textContent = dispatched ? '🚑 Ambulance déployée' : '🚑 Envoyer une ambulance';
    dispatchBtn.onclick = () => handleDispatchAmbulance(dispatchBtn);

    const formContainer = document.getElementById('orientationFormContainer');
    if (currentStay) {
        const stayInfo = buildReceptionStayAlert(currentStay);
        formContainer.innerHTML = `
            <div class="alert alert-${stayInfo.tone}">
                ${escapeHtml(stayInfo.message)}
            </div>
        `;
        return;
    }
    if (!currentSinistre?.numero_sinistre) {
        formContainer.innerHTML = '<p class="muted">Attente de validation médicale avant orientation.</p>';
        return;
    }

    await ensureHospitalDoctors();
    if (!hospitalDoctors.length) {
        formContainer.innerHTML = '<p class="muted">Aucun médecin hospitalier configuré pour cet établissement.</p>';
        return;
    }

    formContainer.innerHTML = `
        <form id="orientationForm" class="orientation-form">
            <div class="form-grid">
                <div class="form-group">
                    <label for="doctorSelect">Médecin assigné</label>
                    <select id="doctorSelect" required>
                        ${hospitalDoctors.map(doc => `<option value="${doc.id}">${escapeHtml(doc.full_name || doc.email || doc.username)}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label for="orientationNotes">Notes pour l'équipe médicale</label>
                    <textarea id="orientationNotes" rows="2" placeholder="Précisions pour l'accueil ou le médecin"></textarea>
                </div>
            </div>
            <button type="submit" class="btn btn-primary">Orienter le patient</button>
        </form>
    `;
    document.getElementById('orientationForm').addEventListener('submit', handleOrientationSubmit);
}

async function handleDispatchAmbulance(button) {
    button.disabled = true;
    button.textContent = 'Envoi en cours...';
    try {
        await apiCall(`/hospital-sinistres/sinistres/${currentSinistre.id}/dispatch-ambulance`, {
            method: 'POST',
            body: JSON.stringify({ notes: 'Action déclenchée par la réception' }),
        });
        showAlert('Ambulance envoyée.', 'success');
        await loadAlertDetails();
    } catch (error) {
        console.error('Erreur ambulance:', error);
        showAlert(error.message || 'Impossible d’envoyer l’ambulance.', 'error');
    } finally {
        button.disabled = false;
        button.textContent = '🚑 Envoyer une ambulance';
    }
}

async function ensureHospitalDoctors() {
    if (hospitalDoctors.length || !currentSinistre?.hospital?.id) {
        return;
    }
    try {
        const doctors = await apiCall(`/hospital-sinistres/hospitals/${currentSinistre.hospital.id}/doctors`);
        hospitalDoctors = Array.isArray(doctors) ? doctors : [];
    } catch (error) {
        console.error('Erreur lors du chargement des médecins:', error);
    }
}

function buildReceptionStayAlert(stay) {
    const doctorName = stay.assigned_doctor?.full_name || `Dr #${stay.doctor_id}`;
    switch (stay.status) {
        case 'in_progress':
            return {
                tone: 'info',
                message: `Séjour en cours avec ${doctorName}.`,
            };
        case 'awaiting_validation':
            return {
                tone: 'warning',
                message: `Rapport transmis par ${doctorName}. Attente de validation du médecin référent.`,
            };
        case 'validated':
            return {
                tone: 'success',
                message: 'Rapport validé. Le service comptable peut maintenant établir la facture.',
            };
        case 'rejected':
            return {
                tone: 'warning',
                message: 'Rapport rejeté par le médecin référent. Merci de contacter l’équipe médicale.',
            };
        case 'invoiced':
            return {
                tone: 'success',
                message: 'Facture émise et transmise au comptable Mobility Health.',
            };
        default:
            return {
                tone: 'info',
                message: `Séjour suivi par ${doctorName}.`,
            };
    }
}

async function handleOrientationSubmit(event) {
    event.preventDefault();
    const doctorId = Number(document.getElementById('doctorSelect').value);
    const notes = document.getElementById('orientationNotes').value || null;
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Orientation en cours...';
    try {
        await apiCall(`/hospital-sinistres/sinistres/${currentSinistre.id}/stays`, {
            method: 'POST',
            body: JSON.stringify({ doctor_id: doctorId, orientation_notes: notes }),
        });
        showAlert('Patient orienté vers le médecin sélectionné.', 'success');
        await loadAlertDetails();
        if (!alertId) {
            await loadAssignedAlerts(false);
        }
    } catch (error) {
        console.error('Erreur orientation:', error);
        showAlert(error.message || 'Impossible de créer le séjour.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Orienter le patient';
    }
}

function renderDoctorReport() {
    const section = document.getElementById('doctorReportSection');
    if (!section || !currentStay) {
        if (section) section.hidden = true;
        return;
    }
    const isAssignedDoctor = currentStay.doctor_id === currentUserId;
    const isReferent = isReferentForCurrentCase();
    if (!isAssignedDoctor && !isReferent) {
        section.hidden = true;
        return;
    }
    section.hidden = false;

    const form = document.getElementById('doctorReportForm');
    form.reset();
    const canEdit = isAssignedDoctor && !['validated', 'invoiced'].includes(currentStay.status);

    setFieldValue('motifConsultation', currentStay.report_motif_consultation);
    setFieldValue('motifHospitalisation', currentStay.report_motif_hospitalisation);
    // Affichage en jours (API stocke en heures)
    setFieldValue('dureeSejour', currentStay.report_duree_sejour_heures != null ? (currentStay.report_duree_sejour_heures / 24) : '');
    setFieldValue('resumeSejour', currentStay.report_resume);
    setFieldValue('observationsSejour', currentStay.report_observations);
    const terminerInput = document.getElementById('terminerSejour');
    if (terminerInput) {
        terminerInput.checked = currentStay.status !== 'in_progress';
        terminerInput.disabled = !canEdit;
    }

    buildOptionsChecklist('actesOptions', hospitalStayOptions.actes, currentStay.report_actes || []);
    buildOptionsChecklist('examensOptions', hospitalStayOptions.examens, currentStay.report_examens || []);
    setChecklistDisabled('actesOptions', !canEdit);
    setChecklistDisabled('examensOptions', !canEdit);

    toggleFieldsetDisabled(
        ['motifConsultation', 'motifHospitalisation', 'dureeSejour', 'resumeSejour', 'observationsSejour'],
        !canEdit
    );

    const formActions = form.querySelector('.form-actions');
    if (formActions) {
        formActions.style.display = canEdit ? '' : 'none';
    }

    const submitHandler = async (event) => {
        event.preventDefault();
        form.removeEventListener('submit', submitHandler);
        await handleDoctorReportSubmit(event);
    };
    if (canEdit) {
        form.addEventListener('submit', submitHandler, { once: true });
    }
}

function renderReportValidationSection() {
    const section = document.getElementById('reportValidationSection');
    if (!section || !currentStay) {
        if (section) section.hidden = true;
        return;
    }
    const canValidate =
        REPORT_VALIDATION_ROLES.includes(currentUserRole || '') &&
        currentStay.status === 'awaiting_validation';
    if (!canValidate) {
        section.hidden = true;
        return;
    }
    section.hidden = false;
    const approveBtn = document.getElementById('approveReportBtn');
    const rejectBtn = document.getElementById('rejectReportBtn');
    if (approveBtn) {
        approveBtn.onclick = () => handleReportValidation(true);
    }
    if (rejectBtn) {
        rejectBtn.onclick = () => handleReportValidation(false);
    }
}

async function handleReportValidation(approve) {
    if (!currentStay) {
        return;
    }
    const notes = document.getElementById('reportValidationNotes')?.value || null;
    const approveBtn = document.getElementById('approveReportBtn');
    const rejectBtn = document.getElementById('rejectReportBtn');
    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;
    try {
        await apiCall(`/hospital-sinistres/hospital-stays/${currentStay.id}/validation`, {
            method: 'POST',
            body: JSON.stringify({ approve, notes }),
        });
        showAlert(approve ? 'Rapport validé.' : 'Rapport rejeté.', approve ? 'success' : 'warning');
        await loadAlertDetails();
    } catch (error) {
        showAlert(error.message || 'Impossible de traiter la validation.', 'error');
    } finally {
        if (approveBtn) approveBtn.disabled = false;
        if (rejectBtn) rejectBtn.disabled = false;
    }
}

function renderInvoiceSection() {
    const section = document.getElementById('invoiceSection');
    const approvalCard = document.getElementById('invoiceMedicalApproval');
    const approvalStatus = document.getElementById('invoiceApprovalStatus');
    const notesField = document.getElementById('invoiceMedicalNotes');
    const approveInvoiceBtn = document.getElementById('invoiceApproveBtn');
    const rejectInvoiceBtn = document.getElementById('invoiceRejectBtn');
    if (approvalCard) {
        approvalCard.hidden = true;
    }
    if (approvalStatus) {
        approvalStatus.hidden = true;
        approvalStatus.textContent = '';
    }
    if (approveInvoiceBtn) {
        approveInvoiceBtn.onclick = null;
    }
    if (rejectInvoiceBtn) {
        rejectInvoiceBtn.onclick = null;
    }
    if (!section || !currentStay) {
        if (section) section.hidden = true;
        return;
    }
    const invoice = currentStay.invoice;
    const userIsAccountant =
        ACCOUNTING_ROLES.includes(currentUserRole || '') &&
        currentHospitalId &&
        currentSinistre?.hospital?.id === currentHospitalId;
    const canCreateInvoice = userIsAccountant && currentStay.status === 'validated' && !invoice;

    if (!invoice && !canCreateInvoice) {
        section.hidden = true;
        return;
    }

    section.hidden = false;
    const summary = document.getElementById('invoiceSummary');
    const actionBtn = document.getElementById('createInvoiceBtn');
    const invoiceContentBlock = document.getElementById('invoiceContentBlock');
    if (invoiceContentBlock) {
        invoiceContentBlock.hidden = true;
    }
    const sinistreApprovalCardEl = document.getElementById('invoiceSinistreApproval');
    if (sinistreApprovalCardEl) {
        sinistreApprovalCardEl.hidden = true;
    }

    if (invoice) {
        summary.innerHTML = `
            <div>
                <strong>Numéro</strong>
                <div>${escapeHtml(invoice.numero_facture || `Facture #${invoice.id}`)}</div>
            </div>
            <div>
                <strong>Montant TTC</strong>
                <div>${formatCurrency(invoice.montant_ttc)}</div>
            </div>
            <div>
                <strong>Statut</strong>
                <div><span class="badge">${escapeHtml(getInvoiceStatusLabel(invoice.statut))}</span></div>
            </div>
        `;
        loadAndRenderInvoiceContent(invoice.id);
        if (approvalStatus) {
            const message = getInvoiceApprovalStatusMessage(invoice);
            if (message) {
                approvalStatus.hidden = false;
                approvalStatus.textContent = message;
            }
        }
        const canMedicalApprove = canCurrentUserApproveInvoice(invoice);
        if (approvalCard) {
            if (canMedicalApprove) {
                approvalCard.hidden = false;
                if (notesField) {
                    notesField.value = '';
                    notesField.disabled = false;
                }
                if (approveInvoiceBtn) {
                    approveInvoiceBtn.disabled = false;
                    approveInvoiceBtn.onclick = () => handleInvoiceMedicalDecision(true);
                }
                if (rejectInvoiceBtn) {
                    rejectInvoiceBtn.disabled = false;
                    rejectInvoiceBtn.onclick = () => handleInvoiceMedicalDecision(false);
                }
            } else {
                approvalCard.hidden = true;
                setInvoiceMedicalButtonsDisabled(true);
                if (notesField) {
                    notesField.disabled = true;
                }
            }
        }
        const sinistreApprovalCard = document.getElementById('invoiceSinistreApproval');
        const canSinistreApprove = canCurrentUserApproveInvoiceSinistre(invoice);
        if (sinistreApprovalCard) {
            if (canSinistreApprove) {
                sinistreApprovalCard.hidden = false;
                const sinistreNotes = document.getElementById('invoiceSinistreNotes');
                if (sinistreNotes) {
                    sinistreNotes.value = '';
                    sinistreNotes.disabled = false;
                }
                const sinistreApproveBtn = document.getElementById('invoiceSinistreApproveBtn');
                const sinistreRejectBtn = document.getElementById('invoiceSinistreRejectBtn');
                if (sinistreApproveBtn) {
                    sinistreApproveBtn.disabled = false;
                    sinistreApproveBtn.onclick = () => handleInvoiceSinistreDecision(true);
                }
                if (sinistreRejectBtn) {
                    sinistreRejectBtn.disabled = false;
                    sinistreRejectBtn.onclick = () => handleInvoiceSinistreDecision(false);
                }
            } else {
                sinistreApprovalCard.hidden = true;
            }
        }
        if (actionBtn) {
            actionBtn.textContent = 'Facture envoyée';
            actionBtn.disabled = true;
        }
    } else if (canCreateInvoice) {
        summary.innerHTML = `
            <p class="muted">
                Utilisez les informations du séjour pour générer une facture. Elle sera transmise au comptable Mobility Health.
            </p>
        `;
        if (actionBtn) {
            actionBtn.disabled = false;
            actionBtn.onclick = () => handleInvoiceCreation(actionBtn);
            actionBtn.textContent = 'Créer et envoyer la facture';
        }
    } else if (actionBtn) {
        actionBtn.disabled = true;
    }
}

async function handleInvoiceCreation(button) {
    if (!currentStay) {
        return;
    }
    button.disabled = true;
    button.textContent = 'Création en cours...';
    try {
        await apiCall(`/hospital-sinistres/hospital-stays/${currentStay.id}/invoice`, {
            method: 'POST',
            body: JSON.stringify({ taux_tva: 0.18 }),
        });
        showAlert('Facture générée et transmise.', 'success');
        await loadAlertDetails();
    } catch (error) {
        showAlert(error.message || 'Impossible de créer la facture.', 'error');
    } finally {
        button.disabled = false;
        button.textContent = 'Créer et envoyer la facture';
    }
}

function buildOptionsChecklist(containerId, options, selectedValues) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const selectedSet = new Set(selectedValues || []);
    container.innerHTML = options.map(option => `
        <label>
            <input type="checkbox" value="${escapeHtml(option)}" ${selectedSet.has(option) ? 'checked' : ''}>
            ${escapeHtml(option)}
        </label>
    `).join('');
}

function setChecklistDisabled(containerId, disabled) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    container.querySelectorAll('input[type="checkbox"]').forEach((input) => {
        input.disabled = disabled;
    });
}

function setFieldValue(id, value) {
    const input = document.getElementById(id);
    if (!input) {
        return;
    }
    if (typeof value === 'number' && Number.isFinite(value)) {
        input.value = String(value);
    } else {
        input.value = value || '';
    }
}

function toggleFieldsetDisabled(ids, disabled) {
    ids.forEach((id) => {
        const input = document.getElementById(id);
        if (input) {
            input.disabled = disabled;
        }
    });
}

async function handleDoctorReportSubmit(event) {
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Enregistrement...';

    const actes = Array.from(document.querySelectorAll('#actesOptions input:checked')).map(input => input.value);
    const examens = Array.from(document.querySelectorAll('#examensOptions input:checked')).map(input => input.value);

    const payload = {
        motif_consultation: document.getElementById('motifConsultation').value || null,
        motif_hospitalisation: document.getElementById('motifHospitalisation').value || null,
        duree_sejour_heures: document.getElementById('dureeSejour').value ? Math.round(Number(document.getElementById('dureeSejour').value) * 24) : null,
        actes_effectues: actes,
        examens_effectues: examens,
        resume: document.getElementById('resumeSejour').value || null,
        observations: document.getElementById('observationsSejour').value || null,
        terminer_sejour: document.getElementById('terminerSejour').checked,
    };

    try {
        await apiCall(`/hospital-sinistres/hospital-stays/${currentStay.id}/report`, {
            method: 'PUT',
            body: JSON.stringify(payload),
        });
        showAlert('Rapport médical enregistré.', 'success');
        await loadAlertDetails();
    } catch (error) {
        console.error('Erreur rapport médical:', error);
        showAlert(error.message || 'Impossible d’enregistrer le rapport.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer le rapport';
    }
}

function getStatusLabel(status) {
    return {
        en_attente: 'En attente',
        en_cours: 'En cours',
        resolue: 'Résolue',
        annulee: 'Annulée'
    }[status] || status || 'Inconnu';
}

function getStatusClass(status) {
    return {
        en_attente: 'status-pending',
        en_cours: 'status-active',
        resolue: 'status-active',
        annulee: 'status-inactive'
    }[status] || 'status-pending';
}

function getWorkflowStepStatusLabel(status) {
    return {
        pending: 'En attente',
        in_progress: 'En cours',
        completed: 'Terminé',
        cancelled: 'Annulé'
    }[status] || status || 'Inconnu';
}

function getWorkflowStepStatusClass(status) {
    return {
        pending: 'status-pending',
        in_progress: 'status-active',
        completed: 'status-active',
        cancelled: 'status-inactive'
    }[status] || 'status-pending';
}

function getPriorityLabel(priority) {
    return {
        critique: 'Critique',
        urgente: 'Urgente',
        elevee: 'Élevée',
        normale: 'Normale',
        faible: 'Faible'
    }[priority] || priority || 'Normale';
}

function getPriorityClass(priority) {
    return {
        critique: 'priority-critique',
        urgente: 'priority-urgente',
        elevee: 'priority-elevee',
        normale: 'priority-normale',
        faible: 'priority-faible'
    }[priority] || 'priority-normale';
}

/** Médecin référent MH ou médecin MH (medical_reviewer) peut valider médicalement la facture. */
function canCurrentUserApproveInvoice(invoice) {
    if (!invoice) return false;
    const canMedical = isReferentForCurrentCase() || (currentUserRole === 'medical_reviewer');
    if (!canMedical) return false;
    const alreadyProcessed = ['approved', 'rejected'].includes(invoice.validation_medicale || '');
    return invoice.statut === 'pending_medical' && !alreadyProcessed;
}

/** SOS operator ou agent sinistre MH peut valider la facture (étape sinistre). */
function canCurrentUserApproveInvoiceSinistre(invoice) {
    if (!invoice) return false;
    const canSinistre = ['sos_operator', 'agent_sinistre_mh'].includes(currentUserRole || '');
    if (!canSinistre) return false;
    const alreadyProcessed = ['approved', 'rejected'].includes(invoice.validation_sinistre || '');
    return invoice.statut === 'pending_sinistre' && !alreadyProcessed;
}

function getInvoiceApprovalStatusMessage(invoice) {
    if (!invoice) {
        return '';
    }
    if (invoice.validation_medicale === 'approved') {
        return 'Accord médical donné. La facture poursuit son circuit.';
    }
    if (invoice.validation_medicale === 'rejected') {
        return 'Facture rejetée par le médecin référent.';
    }
    if (invoice.statut === 'pending_medical') {
        return 'En attente de validation médicale (médecin référent MH / médecin MH).';
    }
    if (invoice.statut === 'pending_sinistre') {
        return 'En attente de validation du pôle sinistre (SOS / agent sinistre MH).';
    }
    return '';
}

async function loadAndRenderInvoiceContent(invoiceId) {
    const block = document.getElementById('invoiceContentBlock');
    const table = document.getElementById('invoiceLinesTable');
    const body = document.getElementById('invoiceLinesBody');
    const emptyEl = document.getElementById('invoiceLinesEmpty');
    if (!block || !body) return;
    block.hidden = false;
    body.innerHTML = '';
    if (emptyEl) emptyEl.hidden = true;
    if (table) table.hidden = false;
    try {
        const full = await apiCall(`/invoices/${invoiceId}`);
        const items = full.items || [];
        if (!items.length) {
            if (emptyEl) {
                emptyEl.hidden = false;
                emptyEl.textContent = 'Aucune ligne.';
            }
            if (table) table.hidden = true;
            return;
        }
        body.innerHTML = items
            .map(
                (line) => `
            <tr>
                <td>${escapeHtml(line.libelle || '—')}</td>
                <td>${escapeHtml(String(line.quantite ?? '—'))}</td>
                <td>${formatCurrency(line.prix_unitaire)}</td>
                <td>${formatCurrency(line.montant_ttc)}</td>
            </tr>
        `
            )
            .join('');
    } catch (err) {
        console.warn('Impossible de charger le détail de la facture:', err);
        if (emptyEl) {
            emptyEl.hidden = false;
            emptyEl.textContent = 'Impossible d\'afficher le détail des lignes.';
        }
        if (table) table.hidden = true;
    }
}

async function handleInvoiceSinistreDecision(approve) {
    if (!currentStay?.invoice) return;
    const notesEl = document.getElementById('invoiceSinistreNotes');
    const notes = notesEl ? notesEl.value.trim() : '';
    const approveBtn = document.getElementById('invoiceSinistreApproveBtn');
    const rejectBtn = document.getElementById('invoiceSinistreRejectBtn');
    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;
    try {
        await apiCall(`/invoices/${currentStay.invoice.id}/validate_sinistre`, {
            method: 'POST',
            body: JSON.stringify({ approve, notes: notes || undefined }),
        });
        if (notesEl) notesEl.value = '';
        showAlert(
            approve ? 'Facture validée par le pôle sinistre.' : 'Facture refusée par le pôle sinistre.',
            approve ? 'success' : 'warning'
        );
        await loadAlertDetails();
    } catch (error) {
        showAlert(error.message || 'Impossible de traiter la validation sinistre.', 'error');
    } finally {
        if (approveBtn) approveBtn.disabled = false;
        if (rejectBtn) rejectBtn.disabled = false;
    }
}

async function handleInvoiceMedicalDecision(approve) {
    if (!currentStay?.invoice) {
        return;
    }
    const notesField = document.getElementById('invoiceMedicalNotes');
    const notes = notesField ? notesField.value.trim() : '';
    setInvoiceMedicalButtonsDisabled(true);
    try {
        await apiCall(`/invoices/${currentStay.invoice.id}/validate_medical`, {
            method: 'POST',
            body: JSON.stringify({
                approve,
                notes: notes || undefined,
            }),
        });
        if (notesField) {
            notesField.value = '';
        }
        showAlert(
            approve ? 'Facture approuvée par le médecin référent.' : 'Facture rejetée par le médecin référent.',
            approve ? 'success' : 'warning'
        );
        await loadAlertDetails();
    } catch (error) {
        showAlert(error.message || 'Impossible de traiter la validation médicale de la facture.', 'error');
    } finally {
        setInvoiceMedicalButtonsDisabled(false);
    }
}

function setInvoiceMedicalButtonsDisabled(state) {
    const approveBtn = document.getElementById('invoiceApproveBtn');
    const rejectBtn = document.getElementById('invoiceRejectBtn');
    if (approveBtn) {
        approveBtn.disabled = state;
    }
    if (rejectBtn) {
        rejectBtn.disabled = state;
    }
}

function getInvoiceStatusLabel(status) {
    const map = {
        pending_medical: 'En attente accord médical',
        pending_sinistre: 'En attente pôle sinistre',
        pending_compta: 'En attente comptabilité MH',
        validated: 'Validée',
        rejected: 'Refusée'
    };
    return map[status] || (status ? status : 'Inconnu');
}

function formatKeyLabel(key) {
    return String(key || '')
        .replace(/_/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDateTime(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    if (typeof text !== 'string') return '';
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
    const amount = Number(value);
    if (Number.isNaN(amount)) {
        return value;
    }
    return amount.toLocaleString('fr-FR', { style: 'currency', currency: 'XAF' });
}

