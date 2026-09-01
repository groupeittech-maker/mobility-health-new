const ALLOWED_RECEPTION_ROLES = ['agent_reception_hopital', 'hospital_admin'];
const ACTIVE_ALERT_STATUSES = new Set(['en_attente', 'en_cours']);
const ALERT_REFRESH_INTERVAL = 60000;

let assignedAlerts = [];
let currentReceptionTab = 'to_treat'; // 'to_treat' | 'orientations'
let searchAlertsReception = '';
const ROWS_PER_PAGE = 6;
let currentPageReception = 0;
let selectedAlert = null;
let selectedSinistre = null;
let hospitalDoctors = [];
let autoRefreshTimer = null;

const currentHospitalId = Number(localStorage.getItem('hospital_id') || 0);
const currentUserRole = localStorage.getItem('user_role') || '';

document.addEventListener('DOMContentLoaded', () => {
    initHospitalReception();
});

async function initHospitalReception() {
    const allowed = await requireAnyRole(ALLOWED_RECEPTION_ROLES, 'index.html');
    if (!allowed) {
        return;
    }
    displayUserContext();
    bindReceptionEvents();

    if (!currentHospitalId) {
        showAlert('Aucun hôpital n’est associé à votre compte. Contactez un administrateur.', 'error');
        toggleGlobalState({ table: false, empty: true });
        return;
    }

    await loadHospitalDoctors();
    await refreshReceptionAlerts();
    initReceptionNotificationsModule();
    startAutoRefresh();

    const deepAlert = new URLSearchParams(window.location.search).get('alert_id');
    const deepTrim = deepAlert != null ? String(deepAlert).trim() : '';
    if (deepTrim && /^\d+$/.test(deepTrim)) {
        const mapUrl = `hospital-reception-map.html?alert_id=${encodeURIComponent(deepTrim)}`;
        window.requestAnimationFrame(() => {
            const w = window.open(mapUrl, '_blank', 'noopener,noreferrer');
            if (!w) {
                window.location.href = mapUrl;
            }
        });
    }
}

function displayUserContext() {
    const userName = localStorage.getItem('user_name') || 'Réceptionniste';
    const welcome = document.getElementById('userName');
    if (welcome) {
        welcome.textContent = userName;
    }
    const badge = document.getElementById('hospitalBadge');
    if (badge) {
        const hospitalName = localStorage.getItem('hospital_name');
        badge.textContent = currentHospitalId
            ? (hospitalName || `Hôpital #${currentHospitalId}`)
            : 'Hôpital non défini';
    }
}

function bindReceptionEvents() {
    const refreshBtn = document.getElementById('refreshAlertsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => refreshReceptionAlerts(true));
    }
    const tabToTreat = document.getElementById('tabReceptionToTreat');
    const tabOrientations = document.getElementById('tabReceptionOrientations');
    const searchInput = document.getElementById('searchAlertsReception');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            searchAlertsReception = (searchInput.value || '').trim().toLowerCase();
            currentPageReception = 0;
            renderAlertsTable();
        });
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchInput.value = '';
                searchAlertsReception = '';
                renderAlertsTable();
            }
        });
    }

    [tabToTreat, tabOrientations].forEach((btn) => {
        if (!btn) return;
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-reception-tab');
            if (tab !== 'to_treat' && tab !== 'orientations') return;
            currentReceptionTab = tab;
            currentPageReception = 0;
            tabToTreat.classList.toggle('active', tab === 'to_treat');
            tabToTreat.setAttribute('aria-selected', tab === 'to_treat' ? 'true' : 'false');
            tabOrientations.classList.toggle('active', tab === 'orientations');
            tabOrientations.setAttribute('aria-selected', tab === 'orientations' ? 'true' : 'false');
            renderAlertsTable();
        });
    });
}

function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = window.setInterval(() => refreshReceptionAlerts(), ALERT_REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}

async function refreshReceptionAlerts(forceLoading = false) {
    if (!currentHospitalId) {
        return;
    }
    setAlertsLoading(forceLoading);
    const errorEl = document.getElementById('alertsError');
    if (errorEl) {
        errorEl.hidden = true;
    }
    try {
        const alerts = await apiCall(`/sos/?limit=200`);
        assignedAlerts = filterReceptionAlerts(alerts);
        renderAlertsTable();
        updateReceptionStats();
    } catch (error) {
        assignedAlerts = [];
        renderAlertsTable();
        if (errorEl) {
            errorEl.hidden = false;
            errorEl.textContent = error.message || 'Impossible de charger les dossiers assignés.';
        }
        showAlert('Erreur lors du chargement des dossiers assignés.', 'error');
    } finally {
        setAlertsLoading(false);
    }
}

function filterReceptionAlerts(alerts = []) {
    if (!Array.isArray(alerts)) {
        return [];
    }
    return alerts
        .filter(alert =>
            alert?.assigned_hospital?.id === currentHospitalId &&
            ACTIVE_ALERT_STATUSES.has(alert?.statut)
        )
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
}

function setAlertsLoading(state) {
    const loading = document.getElementById('alertsLoading');
    if (loading) {
        loading.hidden = !state;
    }
}

function toggleGlobalState({ table, empty }) {
    const cardList = document.getElementById('alertsCardList');
    const emptyState = document.getElementById('alertsEmpty');
    if (cardList) {
        cardList.hidden = !table;
    }
    if (emptyState) {
        emptyState.hidden = !empty;
    }
}

function getAlertsForCurrentTab() {
    const toTreat = assignedAlerts.filter((a) => !a.is_oriented);
    const orientations = assignedAlerts.filter((a) => a.is_oriented);
    return currentReceptionTab === 'orientations' ? orientations : toTreat;
}

function matchReceptionAlertSearch(alert, term) {
    if (!term) return true;
    const t = term.toLowerCase();
    const numero = (alert.numero_alerte || `Dossier #${alert.id}`).toLowerCase();
    const patient = (alert.user_full_name || `Utilisateur #${alert.user_id}`).toLowerCase();
    const description = (alert.description || '').toLowerCase();
    const hospital = (alert.assigned_hospital?.nom || '').toLowerCase();
    const souscription = (alert.numero_souscription || '').toLowerCase();
    return numero.includes(t) || patient.includes(t) || description.includes(t) || hospital.includes(t) || souscription.includes(t);
}

function renderAlertsTable() {
    const list = document.getElementById('alertsCardList');
    const emptyState = document.getElementById('alertsEmpty');
    const emptyMessage = document.getElementById('alertsEmptyMessage');
    if (!list || !emptyState) {
        return;
    }

    let alertsToShow = getAlertsForCurrentTab();
    if (searchAlertsReception) {
        alertsToShow = alertsToShow.filter((alert) => matchReceptionAlertSearch(alert, searchAlertsReception));
    }

    if (emptyMessage) {
        emptyMessage.textContent = currentReceptionTab === 'orientations'
            ? 'Aucune orientation envoyée pour le moment.'
            : 'Aucun dossier à traiter pour le moment.';
    }

    if (!alertsToShow.length) {
        list.innerHTML = '';
        list.hidden = true;
        emptyState.hidden = false;
        const pagEl = document.getElementById('receptionAlertsPagination');
        if (pagEl) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        }
        if (currentReceptionTab === 'orientations') {
            resetAlertDetails();
        }
        return;
    }

    emptyState.hidden = true;
    list.hidden = false;

    const totalPages = Math.max(1, Math.ceil(alertsToShow.length / ROWS_PER_PAGE));
    currentPageReception = Math.min(currentPageReception, totalPages - 1);
    const start = currentPageReception * ROWS_PER_PAGE;
    const pageData = alertsToShow.slice(start, start + ROWS_PER_PAGE);

    list.innerHTML = pageData.map((alert) => buildAlertCard(alert)).join('');

    const pagEl = document.getElementById('receptionAlertsPagination');
    if (pagEl) {
        if (alertsToShow.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, alertsToShow.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Dossiers ${start + 1}-${end} sur ${alertsToShow.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="recPrev" ${currentPageReception <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageReception + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="recNext" ${currentPageReception >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('recPrev')?.addEventListener('click', () => { currentPageReception--; renderAlertsTable(); });
            document.getElementById('recNext')?.addEventListener('click', () => { currentPageReception++; renderAlertsTable(); });
        }
    }

    list.querySelectorAll('.reception-alert-card[data-row-alert-id]').forEach((card) => {
        card.addEventListener('click', (event) => {
            if (
                event.target.closest('.reception-dossier-full-link') ||
                event.target.closest('[data-open-alert]')
            ) {
                return;
            }
            list.querySelectorAll('.reception-alert-card[data-row-alert-id]').forEach((c) => c.classList.remove('selected'));
            card.classList.add('selected');
            const alertId = Number(card.getAttribute('data-row-alert-id'));
            selectAlert(alertId);
        });
        card.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }
            if (event.target.closest('a') || event.target.closest('button')) {
                return;
            }
            event.preventDefault();
            list.querySelectorAll('.reception-alert-card[data-row-alert-id]').forEach((c) => c.classList.remove('selected'));
            card.classList.add('selected');
            selectAlert(Number(card.getAttribute('data-row-alert-id')));
        });
    });

    list.querySelectorAll('[data-open-alert]').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            event.stopPropagation();
            const id = Number(btn.getAttribute('data-alert-id'));
            list.querySelectorAll('.reception-alert-card[data-row-alert-id]').forEach((c) => c.classList.remove('selected'));
            const card = btn.closest('.reception-alert-card');
            if (card) {
                card.classList.add('selected');
            }
            selectAlert(id);
        });
    });

}

function hospitalAlertDetailsPageUrl(alertId) {
    const from = encodeURIComponent('hospital-reception.html');
    return `hospital-alert-details.html?alert_id=${alertId}&from=${from}`;
}

function buildAlertCard(alert) {
    const numero = escapeHtml(alert.numero_alerte || `Dossier #${alert.id}`);
    const patient = escapeHtml(alert.user_full_name || `Utilisateur #${alert.user_id}`);
    const priority = renderPriorityBadge(alert.priorite);
    const created = formatDateTime(alert.created_at);
    const isSelected = selectedAlert && selectedAlert.id === alert.id;
    const dossierUrl = hospitalAlertDetailsPageUrl(alert.id);
    return `
        <li class="card reception-alert-card${isSelected ? ' selected' : ''}" data-row-alert-id="${alert.id}" tabindex="0" role="group" aria-label="Dossier ${escapeHtml(alert.numero_alerte || '#' + alert.id)}">
            <div class="reception-alert-card__body">
                <div class="reception-alert-card__main">
                    <div class="reception-alert-card__head">
                        <strong class="reception-alert-card__numero">${numero}</strong>
                        <span class="reception-alert-card__priority">${priority}</span>
                    </div>
                    <p class="reception-alert-card__patient">${patient}</p>
                    <p class="muted small reception-alert-card__date">Assigné le ${created}</p>
                </div>
                <div class="reception-alert-card__actions">
                    <a class="btn btn-primary btn-sm reception-dossier-full-link" href="${dossierUrl}">Voir le dossier</a>
                    <button type="button" class="btn btn-outline btn-sm" data-open-alert data-alert-id="${alert.id}">Aperçu</button>
                </div>
            </div>
        </li>
    `;
}

async function selectAlert(alertId) {
    console.log('🔍 selectAlert appelé avec alertId:', alertId);
    if (!alertId) {
        console.warn('⚠️ alertId manquant');
        return;
    }
    try {
        setAlertDetailsLoading(true);
        selectedAlert = assignedAlerts.find(alert => alert.id === alertId) || null;
        if (!selectedAlert) {
            console.error('❌ Alerte introuvable dans assignedAlerts');
            showAlert('Dossier introuvable.', 'error');
            return;
        }
        console.log('✅ Alerte trouvée, chargement du sinistre...');
        const sinistre = await apiCall(`/sos/${alertId}/sinistre`);
        selectedSinistre = sinistre;
        console.log('✅ Sinistre chargé, rendu de l\'alerte...');
        renderSelectedAlert();
        
        const cardList = document.getElementById('alertsCardList');
        if (cardList) {
            cardList.querySelectorAll('.reception-alert-card[data-row-alert-id]').forEach((card) => {
                const rowAlertId = Number(card.getAttribute('data-row-alert-id'));
                card.classList.toggle('selected', rowAlertId === alertId);
            });
        }
        console.log('✅ Sélection terminée');
    } catch (error) {
        console.error('❌ Erreur lors du chargement du dossier:', error);
        showAlert(error.message || 'Impossible de charger le dossier.', 'error');
    } finally {
        setAlertDetailsLoading(false);
    }
}

/** Même modèle visuel que la fiche patient médecin hospitalier (patient-dossier-grid). */
function renderReceptionDossierField(label, valueHtml, opts = {}) {
    const { fullWidth = false, multiline = false } = opts;
    const mod = `${fullWidth ? ' patient-dossier-field--full' : ''}${multiline ? ' patient-dossier-field--multiline' : ''}`;
    return `
        <div class="patient-dossier-field${mod}" role="listitem">
            <div class="patient-dossier-field__label">${escapeHtml(label)}</div>
            <div class="patient-dossier-field__value">${valueHtml}</div>
        </div>
    `;
}

function renderSelectedAlert() {
    const section = document.getElementById('alertDetailsSection');
    if (!section || !selectedAlert || !selectedSinistre) {
        resetAlertDetails();
        return;
    }
    
    // Afficher les sections d'informations et d'actions
    section.hidden = false;
    section.style.display = 'block';
    section.style.visibility = 'visible';
    
    // Forcer un reflow pour s'assurer que la section est rendue
    section.offsetHeight;

    const meta = document.getElementById('selectedAlertMeta');
    if (meta) {
        meta.textContent = `${selectedAlert.numero_alerte || `Dossier #${selectedAlert.id}`} • Assigné le ${formatDateTime(selectedAlert.created_at)}`;
    }

    const patientDetails = document.getElementById('patientDetails');
    if (patientDetails) {
        const patient = selectedSinistre.patient || {};
        const name = patient.full_name || selectedAlert.user_full_name || `Utilisateur #${selectedAlert.user_id}`;
        const email = patient.email || selectedAlert.user_email || '—';
        const numSinistre = selectedSinistre.numero_sinistre || '—';
        const numAlerte = selectedAlert.numero_alerte || `#${selectedAlert.id}`;
        const souscription =
            selectedSinistre.numero_souscription != null && String(selectedSinistre.numero_souscription).trim() !== ''
                ? escapeHtml(String(selectedSinistre.numero_souscription))
                : selectedSinistre.souscription_id
                  ? `Souscription #${selectedSinistre.souscription_id}`
                  : '—';
        const adresse = selectedAlert.adresse || '—';
        const gpsRaw = formatCoordinates(selectedAlert);
        const gpsHtml = gpsRaw === '—' ? '<span class="muted">—</span>' : escapeHtml(gpsRaw);

        const prioriteText = escapeHtml(getPriorityLabel(selectedAlert.priorite));
        const civilHtml = [
            renderReceptionDossierField('Patient', escapeHtml(name)),
            renderReceptionDossierField('Email', email === '—' ? '<span class="muted">—</span>' : escapeHtml(email)),
            renderReceptionDossierField(
                'Numéro de sinistre',
                numSinistre === '—' ? '<span class="muted">—</span>' : escapeHtml(String(numSinistre))
            ),
            renderReceptionDossierField('Numéro d’alerte', escapeHtml(String(numAlerte))),
            renderReceptionDossierField(
                'Souscription',
                souscription === '—' ? '<span class="muted">—</span>' : souscription
            ),
            renderReceptionDossierField('Priorité', `<span class="medical-value-text">${prioriteText}</span>`),
            renderReceptionDossierField(
                'Adresse',
                adresse === '—' ? '<span class="muted">—</span>' : escapeHtml(String(adresse))
            ),
            renderReceptionDossierField('Coordonnées GPS', gpsHtml, { fullWidth: true })
        ].join('');

        patientDetails.innerHTML = `<div class="patient-dossier-grid" role="list">${civilHtml}</div>`;
    }

    const notesPreview = document.getElementById('receptionStayNotesPreview');
    if (notesPreview) {
        const raw = selectedSinistre?.hospital_stay?.orientation_notes;
        const n = raw != null ? String(raw).trim() : '';
        notesPreview.textContent = n ? n : 'Aucune note partagée.';
    }

    const alertDetails = document.getElementById('alertDetails');
    if (alertDetails) {
        const desc = (selectedAlert.description || '').trim();
        const descHtml = desc
            ? escapeHtml(desc)
            : '<span class="muted">Aucune description</span>';
        const dossierHtml = [
            renderReceptionDossierField('Statut du dossier', renderStatusBadge(selectedAlert.statut)),
            renderReceptionDossierField('Description', descHtml, { fullWidth: true, multiline: true })
        ].join('');

        alertDetails.innerHTML = `<div class="patient-dossier-grid" role="list">${dossierHtml}</div>`;
    }

    const openBtn = document.getElementById('openFullFileBtn');
    if (openBtn) {
        openBtn.href = `hospital-alert-details.html?alert_id=${selectedAlert.id}`;
    }

    renderReceptionActions();
    
    // Faire défiler vers la section de traitement (informations et actions)
    // Approche simple : défiler vers le haut puis vers la section
    const scrollToTreatmentSection = () => {
        const targetSection = document.getElementById('alertDetailsSection');
        if (!targetSection) {
            return;
        }
        
        // S'assurer que la section est visible
        targetSection.hidden = false;
        targetSection.style.display = 'block';
        targetSection.style.visibility = 'visible';
        
        // Forcer un reflow pour que le navigateur calcule les positions
        void targetSection.offsetHeight;
        
        // Méthode 1: scrollIntoView (le plus simple)
        targetSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start'
        });
        
        // Méthode 2: Calcul manuel avec scrollTo (fallback)
        setTimeout(() => {
            const navbar = document.querySelector('.navbar');
            const navbarHeight = (navbar ? navbar.offsetHeight : 80) + 20;
            const rect = targetSection.getBoundingClientRect();
            const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
            const targetScroll = currentScroll + rect.top - navbarHeight;
            
            if (targetScroll >= 0 && Math.abs(currentScroll - targetScroll) > 5) {
                window.scrollTo({
                    top: targetScroll,
                    behavior: 'smooth'
                });
            }
        }, 100);
    };
    
    // Défiler après un court délai pour laisser le temps au DOM de se mettre à jour
    setTimeout(scrollToTreatmentSection, 50);
    setTimeout(scrollToTreatmentSection, 200);
    setTimeout(scrollToTreatmentSection, 400);
}

function resetAlertDetails() {
    const section = document.getElementById('alertDetailsSection');
    if (section) {
        section.hidden = true;
        section.style.display = 'none';
    }
    const actions = document.getElementById('receptionActionsSection');
    if (actions) {
        actions.hidden = true;
        actions.style.display = 'none';
    }
    const patientDetails = document.getElementById('patientDetails');
    if (patientDetails) {
        patientDetails.innerHTML = '';
    }
    const alertDetails = document.getElementById('alertDetails');
    if (alertDetails) {
        alertDetails.innerHTML = '';
    }
    const notesPreview = document.getElementById('receptionStayNotesPreview');
    if (notesPreview) {
        notesPreview.textContent = '—';
    }
    selectedAlert = null;
    selectedSinistre = null;
}

function closeAlertDetails() {
    resetAlertDetails();
    const cardList = document.getElementById('alertsCardList');
    if (cardList) {
        cardList.querySelectorAll('.reception-alert-card[data-row-alert-id]').forEach((card) => {
            card.classList.remove('selected');
        });
    }
    // Faire défiler vers la liste des alertes
    const alertsSection = document.getElementById('alertsListSection');
    if (alertsSection) {
        const navbar = document.querySelector('.navbar');
        const navbarHeight = navbar ? navbar.offsetHeight : 80;
        const targetPosition = alertsSection.getBoundingClientRect().top + window.pageYOffset - navbarHeight - 20;
        window.scrollTo({
            top: Math.max(0, targetPosition),
            behavior: 'smooth'
        });
    }
}

function renderWorkflowTimeline(steps) {
    const container = document.getElementById('workflowTimeline');
    const workflowSection = document.getElementById('workflowSection');
    
    if (!container) {
        return;
    }
    
    if (!Array.isArray(steps) || !steps.length) {
        container.innerHTML = '<div class="workflow-empty">Aucun workflow disponible.</div>';
        if (workflowSection) {
            workflowSection.hidden = true;
        }
        return;
    }
    
    // Afficher la section workflow
    if (workflowSection) {
        workflowSection.hidden = false;
        workflowSection.style.display = 'block';
    }
    
    // Créer les cartes du workflow en ligne horizontale
    container.innerHTML = steps
        .map(step => {
            const status = step.statut || 'pending';
            const isCompleted = status === 'completed' || status === 'terminé';
            const statusClass = isCompleted ? 'workflow-card--completed' : 
                               status === 'in_progress' || status === 'en_cours' ? 'workflow-card--in-progress' : 
                               'workflow-card--pending';
            
            return `
                <div class="workflow-card ${statusClass}">
                    <div class="workflow-card-header">
                        <h5 class="workflow-card-title">${escapeHtml(step.titre || step.step_key || 'Étape')}</h5>
                        ${renderStatusBadge(status)}
                    </div>
                    <div class="workflow-card-body">
                        <p class="workflow-card-description">${escapeHtml(step.description || '')}</p>
                    </div>
                    ${step.completed_at ? `
                        <div class="workflow-card-footer">
                            <span class="workflow-card-date">${formatDateTime(step.completed_at)}</span>
                        </div>
                    ` : ''}
                </div>
            `;
        })
        .join('');
}

function renderReceptionActions() {
    const section = document.getElementById('receptionActionsSection');
    if (!section || !selectedSinistre?.hospital) {
        if (section) section.hidden = true;
        return;
    }
    const sameHospital = selectedSinistre.hospital?.id === currentHospitalId;
    if (!sameHospital) {
        section.hidden = true;
        return;
    }
    section.hidden = false;

    updateAmbulanceButton();
    populateDoctorsSelect();

    const form = document.getElementById('orientationForm');
    if (form) {
        form.addEventListener('submit', handleOrientationSubmit, { once: true });
    }
}

function updateAmbulanceButton() {
    const button = document.getElementById('dispatchAmbulanceBtn');
    const status = document.getElementById('ambulanceStatus');
    if (!button) {
        return;
    }
    const workflow = (selectedSinistre.workflow_steps || []).find(step => step.step_key === 'ambulance_en_route');
    const alreadyDispatched = workflow?.statut === 'completed';
    button.disabled = alreadyDispatched;
    button.textContent = alreadyDispatched ? '🚑 Ambulance envoyée' : '🚑 Envoyer une ambulance';
    button.onclick = () => handleDispatchAmbulance(button);
    if (status) {
        status.textContent = alreadyDispatched
            ? `Ambulance déclenchée le ${formatDateTime(workflow.completed_at)}`
            : 'Aucune ambulance envoyée pour le moment.';
    }
}

async function handleDispatchAmbulance(button) {
    if (!selectedSinistre) {
        return;
    }
    button.disabled = true;
    button.textContent = 'Envoi en cours...';
    try {
        await apiCall(`/hospital-sinistres/sinistres/${selectedSinistre.id}/dispatch-ambulance`, {
            method: 'POST',
            body: JSON.stringify({ notes: 'Action déclenchée depuis le portail réception' }),
        });
        showAlert('Ambulance envoyée.', 'success');
        await selectAlert(selectedAlert.id);
    } catch (error) {
        showAlert(error.message || 'Impossible d\'envoyer l\'ambulance.', 'error');
        button.disabled = false;
        button.textContent = '🚑 Envoyer une ambulance';
    }
}

async function handleOrientationSubmit(event) {
    event.preventDefault();
    if (!selectedSinistre) {
        return;
    }
    const doctorId = Number(document.getElementById('doctorSelect').value);
    const notes = document.getElementById('orientationNotes').value || null;
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Orientation en cours...';
    try {
        await apiCall(`/hospital-sinistres/sinistres/${selectedSinistre.id}/stays`, {
            method: 'POST',
            body: JSON.stringify({ doctor_id: doctorId, orientation_notes: notes }),
        });
        showAlert('Patient orienté vers le médecin sélectionné.', 'success');
        document.getElementById('orientationNotes').value = '';
        await refreshReceptionAlerts();
        currentReceptionTab = 'orientations';
        const tabToTreat = document.getElementById('tabReceptionToTreat');
        const tabOrientations = document.getElementById('tabReceptionOrientations');
        if (tabToTreat) tabToTreat.classList.remove('active');
        if (tabOrientations) {
            tabOrientations.classList.add('active');
            tabOrientations.setAttribute('aria-selected', 'true');
        }
        if (tabToTreat) tabToTreat.setAttribute('aria-selected', 'false');
        renderAlertsTable();
        updateReceptionStats();
        resetAlertDetails();
    } catch (error) {
        showAlert(error.message || 'Impossible de créer le séjour.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Orienter le patient';
        event.target.addEventListener('submit', handleOrientationSubmit, { once: true });
    }
}

async function loadHospitalDoctors() {
    if (!currentHospitalId) {
        hospitalDoctors = [];
        return;
    }
    try {
        const doctors = await apiCall(`/hospital-sinistres/hospitals/${currentHospitalId}/doctors`);
        hospitalDoctors = Array.isArray(doctors) ? doctors : [];
    } catch (error) {
        console.error('Impossible de charger les médecins:', error);
        hospitalDoctors = [];
    }
}

function populateDoctorsSelect() {
    const select = document.getElementById('doctorSelect');
    if (!select) {
        return;
    }
    select.innerHTML = hospitalDoctors.length
        ? hospitalDoctors
            .map(doc => `<option value="${doc.id}">${escapeHtml(doc.full_name || doc.email || doc.username)}</option>`)
            .join('')
        : '<option value="">Aucun médecin disponible</option>';
    select.disabled = !hospitalDoctors.length;
}

function updateReceptionStats() {
    const assigned = document.getElementById('assignedAlertsCount');
    if (assigned) {
        assigned.textContent = assignedAlerts.length.toString();
    }
    const ambulance = document.getElementById('ambulanceCount');
    if (ambulance) {
        const dispatched = assignedAlerts.filter(alert => alert.workflow_status === 'ambulance_en_route').length;
        ambulance.textContent = dispatched.toString();
    }
    const orientation = document.getElementById('orientationCount');
    if (orientation) {
        const oriented = assignedAlerts.filter(alert => alert.is_oriented === true).length;
        orientation.textContent = oriented.toString();
    }
    const toTreatCount = assignedAlerts.filter((a) => !a.is_oriented).length;
    const orientationsCount = assignedAlerts.filter((a) => a.is_oriented).length;
    const tabToTreat = document.getElementById('tabReceptionToTreat');
    const tabOrientations = document.getElementById('tabReceptionOrientations');
    if (tabToTreat) {
        tabToTreat.textContent = `Dossiers à traiter (${toTreatCount})`;
    }
    if (tabOrientations) {
        tabOrientations.textContent = `Orientations envoyées (${orientationsCount})`;
    }
}

function renderPriorityBadge(priority) {
    return `<span class="priority-badge ${getPriorityClass(priority)}">${getPriorityLabel(priority)}</span>`;
}

function renderStatusBadge(status) {
    return `<span class="status-badge ${getStatusClass(status)}">${getStatusLabel(status)}</span>`;
}

function formatCoordinates(alert) {
    const lat = alert.latitude != null ? Number(alert.latitude) : NaN;
    const lon = alert.longitude != null ? Number(alert.longitude) : NaN;
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
        return '—';
    }
    return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

function setAlertDetailsLoading(state) {
    const section = document.getElementById('alertDetailsSection');
    if (!section) {
        return;
    }
    section.classList.toggle('is-loading', state);
}

function getStatusLabel(status) {
    return {
        en_attente: 'En attente',
        en_cours: 'En cours',
        resolue: 'Résolue',
        annulee: 'Annulée',
        completed: 'Terminé',
    }[status] || status || 'Inconnu';
}

function getStatusClass(status) {
    return {
        en_attente: 'status-pending',
        en_cours: 'status-active',
        resolue: 'status-active',
        annulee: 'status-inactive',
        completed: 'status-active',
    }[status] || 'status-pending';
}

function getPriorityLabel(priority) {
    return {
        critique: 'Critique',
        urgente: 'Urgente',
        elevee: 'Élevée',
        normale: 'Normale',
        faible: 'Faible'
    }[priority] || priority || '—';
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

// ==================== Gestion des notifications de réception ====================

const RECEPTION_NOTIFICATION_TYPES = {
    sos_alert_hospital: {
        label: 'Dossier assigné',
        icon: '🚨',
        defaultMessage: 'Un nouveau dossier SOS vous a été assigné.',
    },
    alert_validated_by_referent: {
        label: 'Dossier validé',
        icon: '✅',
        defaultMessage: 'Le médecin référent MH a validé le dossier. Vous pouvez orienter l\'assuré vers un médecin hospitalier.',
    },
};

const RECEPTION_NOTIFICATION_ORDER = [
    'sos_alert_hospital',
    'alert_validated_by_referent',
];

const receptionNotificationsState = {
    enabled: false,
    items: [],
    elements: {},
    caches: {
        sinistres: {},
    },
};

function initReceptionNotificationsModule() {
    const section = document.getElementById('receptionNotificationsSection');
    if (!section) {
        return;
    }

    const role = (localStorage.getItem('user_role') || '').toLowerCase();
    if (!ALLOWED_RECEPTION_ROLES.includes(role)) {
        section.style.display = 'none';
        return;
    }
    // Ne pas afficher les notifications pour l'agent réception hôpital
    if (role === 'agent_reception_hopital') {
        section.style.display = 'none';
        return;
    }

    receptionNotificationsState.enabled = true;
    receptionNotificationsState.elements = {
        section,
        list: document.getElementById('receptionNotificationsList'),
        empty: document.getElementById('receptionNotificationsEmpty'),
        loading: document.getElementById('receptionNotificationsLoading'),
        error: document.getElementById('receptionNotificationsError'),
        count: document.getElementById('receptionNotificationsCount'),
        refreshButton: document.getElementById('refreshReceptionNotificationsBtn'),
    };

    if (receptionNotificationsState.elements.refreshButton) {
        receptionNotificationsState.elements.refreshButton.addEventListener('click', () =>
            loadReceptionNotifications(true)
        );
    }
    if (receptionNotificationsState.elements.list) {
        receptionNotificationsState.elements.list.addEventListener('click', handleReceptionNotificationCardClick);
        receptionNotificationsState.elements.list.addEventListener('keydown', handleReceptionNotificationCardKeyDown);
    }

    loadReceptionNotifications();
}

async function loadReceptionNotifications(showToast = false) {
    if (!receptionNotificationsState.enabled) {
        return;
    }

    const { error, loading } = receptionNotificationsState.elements;
    if (error) {
        error.hidden = true;
        error.textContent = '';
    }
    if (loading) {
        loading.hidden = false;
    }

    try {
        const response = await apiCall('/notifications?limit=50');
        const notifications = Array.isArray(response) ? response : [];
        const filtered = notifications.filter(
            (item) => RECEPTION_NOTIFICATION_TYPES[item.type_notification] && !item.is_read
        );
        receptionNotificationsState.items = sortReceptionNotifications(filtered);
        renderReceptionNotifications();
        if (showToast) {
            showAlert('Notifications mises à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des notifications de réception:', error);
        if (receptionNotificationsState.elements.error) {
            receptionNotificationsState.elements.error.hidden = false;
            receptionNotificationsState.elements.error.textContent =
                error.message || 'Impossible de charger les notifications.';
        }
        receptionNotificationsState.items = [];
        renderReceptionNotifications();
    } finally {
        if (loading) {
            loading.hidden = true;
        }
    }
}

function sortReceptionNotifications(notifications) {
    return notifications
        .slice()
        .sort((a, b) => {
            const typeIndexA = RECEPTION_NOTIFICATION_ORDER.indexOf(a.type_notification);
            const typeIndexB = RECEPTION_NOTIFICATION_ORDER.indexOf(b.type_notification);
            if (typeIndexA !== typeIndexB) {
                const safeA = typeIndexA === -1 ? Number.MAX_SAFE_INTEGER : typeIndexA;
                const safeB = typeIndexB === -1 ? Number.MAX_SAFE_INTEGER : typeIndexB;
                return safeA - safeB;
            }
            return new Date(b.created_at || 0) - new Date(a.created_at || 0);
        });
}

function renderReceptionNotifications() {
    const { list, empty } = receptionNotificationsState.elements;
    if (!list || !empty) {
        return;
    }

    const notifications = receptionNotificationsState.items || [];
    updateReceptionNotificationCount(notifications.length);

    if (!notifications.length) {
        list.innerHTML = '';
        if (list) list.hidden = true;
        if (empty) empty.hidden = false;
        return;
    }

    list.innerHTML = notifications
        .map((notification, index) => buildReceptionNotificationCard(notification, index))
        .join('');
    if (empty) empty.hidden = true;
    if (list) list.hidden = false;
}

function buildReceptionNotificationCard(notification, index) {
    try {
        const config = RECEPTION_NOTIFICATION_TYPES[notification.type_notification];
        if (!config) {
            return '';
        }
        const timestamp = notification.created_at
            ? new Date(notification.created_at).toLocaleString('fr-FR')
            : '—';
        const title = notification.titre || config.label;
        const body = notification.message || config.defaultMessage;
        const reference = getReceptionNotificationReference(notification);
        
        // Formater le message pour améliorer la lisibilité
        const formattedBody = formatNotificationMessage(body);

        return `
            <div class="card notification-card" data-notification-type="${notification.type_notification}">
                <div
                    class="notification-card__body"
                    role="button"
                    tabindex="0"
                    data-notification-index="${index}"
                    aria-label="Ouvrir le dossier lié à cette notification"
                >
                <div class="notification-card__header">
                    <span class="notification-pill">
                        <span aria-hidden="true">${config.icon}</span>
                        <span>${escapeHtml(config.label)}</span>
                    </span>
                    <span class="notification-time">${escapeHtml(timestamp)}</span>
                </div>
                <h4>${escapeHtml(title)}</h4>
                <div class="notification-body">${formattedBody}</div>
                ${reference ? `<div class="notification-meta">${escapeHtml(reference)}</div>` : ''}
                <div class="notification-link muted">Cliquer pour ouvrir le dossier</div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur lors de la construction de la carte de notification:', error);
        return '';
    }
}

function formatNotificationMessage(message) {
    if (!message || typeof message !== 'string') {
        return '<p class="muted">Aucun message</p>';
    }
    
    // Supprimer la section "--- Extrait du questionnaire ---" et tout ce qui suit
    const excerptIndex = message.indexOf('--- Extrait du questionnaire ---');
    if (excerptIndex !== -1) {
        message = message.substring(0, excerptIndex).trim();
    }
    
    // Supprimer aussi les variantes possibles
    message = message.replace(/---\s*Extrait du questionnaire\s*---.*$/s, '').trim();
    message = message.replace(/Extrait du questionnaire.*$/s, '').trim();
    
    // Échapper le HTML d'abord
    let formatted = escapeHtml(message);
    
    // Mettre en forme les sections avec des titres (doit être fait avant les sauts de ligne)
    formatted = formatted.replace(/(📋|📄|🔍|⚠️)\s*([^\n]+)/g, '<strong class="notification-section-title">$1 $2</strong>');
    
    // Mettre en forme les listes à puces (doit être fait avant les sauts de ligne)
    const lines = formatted.split('\n');
    let inList = false;
    let result = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // Détecter le début d'une liste
        if (line.startsWith('•')) {
            if (!inList) {
                result.push('<ul class="notification-list">');
                inList = true;
            }
            const content = line.replace(/^•\s*/, '');
            result.push(`<li>${content}</li>`);
        } else {
            // Fermer la liste si nécessaire
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            
            // Traiter les lignes normales
            if (line) {
                // Mettre en évidence les labels importants
                const enhanced = line.replace(/(Priorité|Adresse|Assuré|Dossier médical|Informations médicales|version):/g, '<strong>$1:</strong>');
                result.push(enhanced);
            } else if (i < lines.length - 1) {
                // Ligne vide entre sections
                result.push('<br>');
            }
        }
    }
    
    // Fermer la liste si elle est encore ouverte
    if (inList) {
        result.push('</ul>');
    }
    
    formatted = result.join('\n');
    
    // Convertir les sauts de ligne restants en <br>
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

function getReceptionNotificationReference(notification) {
    if (!notification) {
        return '';
    }
    if (notification.lien_relation_type === 'sinistre' && notification.lien_relation_id) {
        return `Sinistre #${notification.lien_relation_id}`;
    }
    return '';
}

function updateReceptionNotificationCount(value) {
    if (!receptionNotificationsState.elements.count) {
        return;
    }
    const suffix = value > 1 ? 'notifications' : 'notification';
    receptionNotificationsState.elements.count.textContent = `${value} ${suffix}`;
}

async function handleReceptionNotificationCardClick(event) {
    const card = event.target.closest('[data-notification-index]');
    if (!card) {
        return;
    }
    const index = Number(card.dataset.notificationIndex);
    await openReceptionNotificationTargetByIndex(index, card);
}

async function handleReceptionNotificationCardKeyDown(event) {
    if (!['Enter', ' '].includes(event.key)) {
        return;
    }
    const card = event.target.closest('[data-notification-index]');
    if (!card) {
        return;
    }
    event.preventDefault();
    const index = Number(card.dataset.notificationIndex);
    await openReceptionNotificationTargetByIndex(index, card);
}

async function openReceptionNotificationTargetByIndex(index, cardElement) {
    if (!Number.isFinite(index) || index < 0) {
        return;
    }
    const notifications = receptionNotificationsState.items || [];
    const notification = notifications[index];
    if (!notification) {
        return;
    }
    if (cardElement) {
        cardElement.classList.add('notification-card--loading');
    }
    try {
        const targetUrl = await resolveReceptionNotificationLink(notification);
        if (targetUrl) {
            await markNotificationAsRead(notification.id);
            receptionNotificationsState.items = receptionNotificationsState.items.filter(
                (item) => item.id !== notification.id
            );
            renderReceptionNotifications();
            window.location.href = targetUrl;
        } else {
            showAlert('Impossible de trouver le dossier associé à cette notification.', 'error');
        }
    } catch (error) {
        console.error('Erreur lors de l\'ouverture du dossier notification:', error);
        showAlert(error.message || 'Ouverture du dossier impossible.', 'error');
    } finally {
        if (cardElement) {
            cardElement.classList.remove('notification-card--loading');
        }
    }
}

async function markNotificationAsRead(notificationId) {
    if (!notificationId) {
        return;
    }
    try {
        await apiCall(`/notifications/${notificationId}/read`, {
            method: 'PATCH',
        });
    } catch (error) {
        console.error(`Erreur lors du marquage de la notification ${notificationId} comme lue:`, error);
    }
}

async function resolveReceptionNotificationLink(notification) {
    if (!notification) {
        return null;
    }
    if (notification.lien_relation_type === 'sinistre' && notification.lien_relation_id) {
        return resolveReceptionSinistreNotificationLink(notification.lien_relation_id);
    }
    return null;
}

async function resolveReceptionSinistreNotificationLink(rawId) {
    const sinistreId = Number(rawId);
    if (!Number.isFinite(sinistreId)) {
        return null;
    }
    if (!receptionNotificationsState.caches) {
        receptionNotificationsState.caches = { sinistres: {} };
    }
    const cache = receptionNotificationsState.caches.sinistres || {};
    if (cache[sinistreId]) {
        return cache[sinistreId];
    }
    try {
        const sinistre = await apiCall(`/hospital-sinistres/sinistres/${sinistreId}`);
        const alertId = sinistre?.alerte_id;
        const url = alertId ? `hospital-alert-details.html?alert_id=${alertId}` : null;
        cache[sinistreId] = url;
        receptionNotificationsState.caches.sinistres = cache;
        return url;
    } catch (error) {
        console.error(`Impossible de résoudre le sinistre ${sinistreId}:`, error);
        return null;
    }
}

function formatDateTime(value) {
    if (!value) {
        return '—';
    }
    return new Date(value).toLocaleString('fr-FR');
}

function setHidden(element, hidden) {
    if (!element) {
        return;
    }
    element.hidden = hidden;
}

// Exposer les fonctions globalement pour les boutons HTML
window.closeAlertDetails = closeAlertDetails;
window.selectAlert = selectAlert;

