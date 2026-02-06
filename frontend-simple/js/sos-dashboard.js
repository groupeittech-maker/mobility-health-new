const ALERTS_FETCH_LIMIT = 200;
const AUTO_REFRESH_INTERVAL = 30000;
const ACTIVE_ALERT_STATUSES = new Set(['en_attente', 'en_cours']);
const PROCESSED_ALERT_STATUSES = new Set(['resolue', 'annulee']);
const ROWS_PER_PAGE = 6;
let currentPageSosRealtime = 0;
let currentPageSosHistory = 0;
const SOS_ALLOWED_ROLES = ['sos_operator', 'agent_reception_hopital', 'agent_sinistre_mh', 'agent_sinistre_assureur'];
const MAP_DEFAULT_CENTER = [5.35, -3.99];
const MAP_DEFAULT_ZOOM = 6;
const MAP_MAX_ZOOM = 16;
const ALERT_MARKER_STYLE = {
    radius: 8,
    color: '#e63946',
    fillColor: '#e63946',
    fillOpacity: 0.85,
    weight: 1,
};
const ALERT_MARKER_HIGHLIGHT_STYLE = {
    ...ALERT_MARKER_STYLE,
    radius: ALERT_MARKER_STYLE.radius + 3,
    color: '#fb8500',
    fillColor: '#fb8500',
};
const HOSPITAL_MARKER_STYLE = {
    radius: 7,
    color: '#2a9d8f',
    fillColor: '#2a9d8f',
    fillOpacity: 0.9,
    weight: 1,
};
const HOSPITAL_LINK_STYLE = {
    color: '#6c63ff',
    weight: 2,
    dashArray: '4 4',
    opacity: 0.8,
};
const ALL_HOSPITAL_MARKER_STYLE = {
    radius: 6,
    color: '#4a5568',
    fillColor: '#718096',
    fillOpacity: 0.5,
    weight: 1,
};

const EARTH_RADIUS_KM = 6371;

function toNumber(value, fallback = null) {
    if (typeof value === 'number') {
        return Number.isFinite(value) ? value : fallback;
    }
    if (typeof value === 'string') {
        const normalized = value.replace(',', '.').trim();
        if (!normalized) {
            return fallback;
        }
        const parsed = Number(normalized);
        return Number.isFinite(parsed) ? parsed : fallback;
    }
    return fallback;
}

function hasValidCoordinates(entity) {
    return typeof entity?.latitude === 'number'
        && typeof entity?.longitude === 'number'
        && Number.isFinite(entity.latitude)
        && Number.isFinite(entity.longitude);
}

function normalizeHospital(hospital) {
    if (!hospital) {
        return null;
    }
    return {
        ...hospital,
        latitude: toNumber(hospital.latitude),
        longitude: toNumber(hospital.longitude),
    };
}

function calculateDistanceKm(lat1, lon1, lat2, lon2) {
    if ([lat1, lon1, lat2, lon2].some(value => !Number.isFinite(value))) {
        return null;
    }
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return EARTH_RADIUS_KM * c;
}

function normalizeAlert(alert) {
    const normalized = { ...alert };
    normalized.latitude = toNumber(alert.latitude);
    normalized.longitude = toNumber(alert.longitude);
    normalized.assigned_hospital = normalizeHospital(alert.assigned_hospital);
    const distance = toNumber(alert.distance_to_hospital_km);
    normalized.distance_to_hospital_km = distance;

    if (
        normalized.distance_to_hospital_km == null &&
        hasValidCoordinates(normalized) &&
        hasValidCoordinates(normalized.assigned_hospital || {})
    ) {
        const computed = calculateDistanceKm(
            normalized.latitude,
            normalized.longitude,
            normalized.assigned_hospital.latitude,
            normalized.assigned_hospital.longitude
        );
        normalized.distance_to_hospital_km = computed !== null ? Number(computed.toFixed(2)) : null;
    }

    return normalized;
}

const STATUS_LABELS = {
    en_attente: 'En attente',
    en_cours: 'En cours',
    resolue: 'Résolue',
    annulee: 'Annulée',
};

const STATUS_CLASS_MAP = {
    en_attente: 'status-pending',
    en_cours: 'status-active',
    resolue: 'status-active',
    annulee: 'status-inactive',
};

const PRIORITY_LABELS = {
    critique: 'Critique',
    urgente: 'Urgente',
    elevee: 'Élevée',
    normale: 'Normale',
    faible: 'Faible',
};

const PRIORITY_CLASS_MAP = {
    critique: 'priority-critique',
    urgente: 'priority-urgente',
    elevee: 'priority-elevee',
    normale: 'priority-normale',
    faible: 'priority-faible',
};

let alertsCache = [];
let currentStatusFilter = 'all';
let searchAlertsRealtime = '';
let searchAlertsHistory = '';
let activeSosTab = 'sosRealtimePanel';
let autoRefreshTimer = null;
let mapInstance = null;
let alertMarkersLayer = null;
let hospitalMarkersLayer = null;
let alertHospitalLinksLayer = null;
let hasFitBoundsOnce = false;
let allHospitalsCache = [];
let hasLoadedAlertsOnce = false;
let alertMarkersIndex = new Map();
let alertMarkerHighlight = null;
let highlightResetTimer = null;
let alertRowHighlightTimer = null;
let alertRowHighlightEl = null;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSosDashboard);
} else {
    initSosDashboard();
}

async function initSosDashboard() {
    const isValid = await requireAnyRole(SOS_ALLOWED_ROLES, 'index.html');
    if (!isValid) {
        return;
    }

    displayUserName();
    setupEventListeners();
    updateSosNavFacturesCount();
    await initAlertsMap();
    await loadHospitalsForMap();
    await refreshAlerts();
    initSosNotificationsModule();
    startAutoRefresh();
}

function initSosAlertsTabs() {
    const tabButtons = document.querySelectorAll('#sosAlertsTabs .tab-btn');
    const panels = document.querySelectorAll('.sos-tab-panel');
    tabButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const sectionId = button.getAttribute('data-section');
            if (!sectionId) {
                return;
            }
            activeSosTab = sectionId;
            tabButtons.forEach((btn) => btn.classList.toggle('active', btn === button));
            panels.forEach((panel) => {
                panel.hidden = panel.id !== sectionId;
            });
        });
    });
}

function displayUserName() {
    const name = localStorage.getItem('user_name') || 'Opérateur SOS';
    const role = localStorage.getItem('user_role') || 'sos_operator';
    const roleLabel = getAlertsRoleLabel(role);

    const nameEl = document.getElementById('userName');
    if (nameEl) {
        nameEl.textContent = name;
    }

    const brandLabel = document.getElementById('brandRoleLabel');
    if (brandLabel) {
        brandLabel.textContent = roleLabel;
    }

    const titleEl = document.getElementById('dashboardTitle');
    if (titleEl) {
        titleEl.textContent = `Tableau de bord ${roleLabel}`;
    }
}

function setupEventListeners() {
    initSosAlertsTabs();

    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        currentStatusFilter = statusFilter.value || 'all';
        statusFilter.addEventListener('change', () => {
            currentStatusFilter = statusFilter.value;
            renderAlerts();
        });
    }

    const searchRealtime = document.getElementById('searchAlertsRealtime');
    if (searchRealtime) {
        searchRealtime.addEventListener('input', () => {
            searchAlertsRealtime = (searchRealtime.value || '').trim().toLowerCase();
            renderAlerts();
        });
    }

    const searchHistory = document.getElementById('searchAlertsHistory');
    if (searchHistory) {
        searchHistory.addEventListener('input', () => {
            searchAlertsHistory = (searchHistory.value || '').trim().toLowerCase();
            renderTreatedAlerts();
        });
    }

    const refreshButton = document.getElementById('refreshAlertsBtn');
    if (refreshButton) {
        refreshButton.addEventListener('click', () =>
            refreshAlerts(true, { forceLoading: true })
        );
    }

    window.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
            refreshAlerts();
        }
    });

    document.addEventListener('click', handleAlertMapLinkClick);

    window.addEventListener('beforeunload', () => {
        stopAutoRefresh();
        document.removeEventListener('click', handleAlertMapLinkClick);
    });
}

async function initAlertsMap() {
    const mapContainer = document.getElementById('alertsMap');
    if (!mapContainer || mapInstance) {
        return;
    }

    if (typeof L === 'undefined' && typeof window.waitForLeaflet === 'function') {
        try {
            await window.waitForLeaflet(8000);
        } catch (error) {
            console.error('Leaflet indisponible après tentative de fallback:', error);
            showMapUnavailableMessage('Impossible de charger la carte Leaflet.');
            return;
        }
    }

    if (typeof L === 'undefined') {
        console.warn('Leaflet n\'est pas chargé, la carte SOS ne sera pas affichée.');
        showMapUnavailableMessage('Leaflet n\'a pas pu être chargé. Vérifiez votre connexion réseau.');
        return;
    }

    mapContainer.innerHTML = '';
    mapContainer.classList.remove('map-error-state');

    mapInstance = L.map(mapContainer, { zoomControl: true }).setView(MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: MAP_MAX_ZOOM,
    }).addTo(mapInstance);
    alertMarkersLayer = L.layerGroup().addTo(mapInstance);
    hospitalMarkersLayer = L.layerGroup().addTo(mapInstance);
    alertHospitalLinksLayer = L.layerGroup().addTo(mapInstance);
    hasFitBoundsOnce = false;
}

async function refreshAlerts(showToast = false, options = {}) {
    const { forceLoading = false } = options;
    const shouldShowLoading = forceLoading || !hasLoadedAlertsOnce;

    if (shouldShowLoading) {
        setAlertsLoading(true);
    }
    hideAlertsError();

    try {
        const alerts = await apiCall(`/sos/?limit=${ALERTS_FETCH_LIMIT}`);
        alertsCache = Array.isArray(alerts) ? alerts.map(normalizeAlert) : [];
        if (!hasLoadedAlertsOnce) {
            hasLoadedAlertsOnce = true;
        }
        updateStats();
        renderAlerts();
        updateLastRefresh();
        updateSosNavFacturesCount();
        if (showToast) {
            showAlert('Alertes mises à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des alertes SOS:', error);
        alertsCache = [];
        updateStats();
        renderAlerts();
        showAlertsError(error);
        updateSosNavFacturesCount();
    } finally {
        setAlertsLoading(false);
    }
}

function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = setInterval(() => refreshAlerts(), AUTO_REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}

function setAlertsLoading(isLoading) {
    const loadingEl = document.getElementById('alertsLoading');
    if (loadingEl) {
        loadingEl.hidden = !isLoading;
        loadingEl.setAttribute('aria-hidden', String(!isLoading));
        loadingEl.classList.toggle('is-visible', Boolean(isLoading));
        loadingEl.style.display = isLoading ? 'flex' : 'none';
    }
}

function updateStats() {
    const activeCountEl = document.getElementById('activeAlertsCount');
    const processedCountEl = document.getElementById('processedAlertsCount');
    const tabRealtimeBtn = document.getElementById('tabRealtimeBtn');
    const tabHistoryBtn = document.getElementById('tabHistoryBtn');
    const navTableauSos = document.getElementById('navTableauSos');

    const activeCount = alertsCache.filter(alert => ACTIVE_ALERT_STATUSES.has(alert.statut)).length;
    const processedCount = alertsCache.filter(alert => PROCESSED_ALERT_STATUSES.has(alert.statut)).length;

    if (activeCountEl) {
        activeCountEl.textContent = activeCount.toString();
    }
    if (processedCountEl) {
        processedCountEl.textContent = processedCount.toString();
    }
    if (tabRealtimeBtn) {
        tabRealtimeBtn.textContent = `Alertes en temps réel (${activeCount})`;
    }
    if (tabHistoryBtn) {
        tabHistoryBtn.textContent = `Historique des alertes (${processedCount})`;
    }
    if (navTableauSos) {
        navTableauSos.textContent = activeCount > 0 ? `Tableau SOS (${activeCount})` : 'Tableau SOS';
    }
}

async function updateSosNavFacturesCount() {
    try {
        const data = await apiCall('/invoices?stage=sinistre&limit=200');
        const n = Array.isArray(data) ? data.length : 0;
        const el = document.getElementById('navFactures');
        if (el) el.textContent = n > 0 ? `Factures (${n})` : 'Factures';
    } catch (_) {
        const el = document.getElementById('navFactures');
        if (el) el.textContent = 'Factures';
    }
}

function renderAlerts() {
    const table = document.getElementById('alertsTable');
    const tbody = document.getElementById('alertsTableBody');
    const emptyState = document.getElementById('alertsEmptyState');

    renderTreatedAlerts();

    if (!tbody) {
        return;
    }

    // Ne jamais afficher les alertes clôturées (resolue, annulee) dans l'onglet "Alertes en temps réel"
    const statutNorm = (s) => (s || '').toLowerCase();
    const activeAlerts = alertsCache.filter((alert) => {
        const s = statutNorm(alert.statut);
        return ACTIVE_ALERT_STATUSES.has(s) && !PROCESSED_ALERT_STATUSES.has(s);
    });
    let filteredAlerts = currentStatusFilter === 'all'
        ? activeAlerts
        : activeAlerts.filter((alert) => statutNorm(alert.statut) === currentStatusFilter);

    if (searchAlertsRealtime) {
        filteredAlerts = filteredAlerts.filter(alert => matchAlertSearch(alert, searchAlertsRealtime));
    }

    if (!filteredAlerts.length) {
        tbody.innerHTML = '';
        if (table) {
            table.hidden = true;
        }
        if (emptyState) {
            emptyState.hidden = false;
            emptyState.innerHTML = `
                <div class="empty-state-icon">🛰️</div>
                <p>${currentStatusFilter === 'all'
                    ? 'Aucune alerte en attente pour le moment.'
                    : 'Aucune alerte ne correspond à ce filtre.'}</p>
                <p class="muted">Les nouvelles alertes apparaîtront automatiquement ici.</p>
            `;
        }
        updateMapMarkers(filteredAlerts);
        return;
    }

    const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / ROWS_PER_PAGE));
    currentPageSosRealtime = Math.min(currentPageSosRealtime, totalPages - 1);
    const start = currentPageSosRealtime * ROWS_PER_PAGE;
    const pageData = filteredAlerts.slice(start, start + ROWS_PER_PAGE);

    const rows = pageData.map(createAlertRow).join('');
    tbody.innerHTML = rows;

    if (table) {
        table.hidden = false;
    }
    if (emptyState) {
        emptyState.hidden = true;
    }
    const pagEl = document.getElementById('sosRealtimePagination');
    if (pagEl) {
        if (filteredAlerts.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, filteredAlerts.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${filteredAlerts.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="sosPrev" ${currentPageSosRealtime <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageSosRealtime + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="sosNext" ${currentPageSosRealtime >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('sosPrev')?.addEventListener('click', () => { currentPageSosRealtime--; renderAlerts(); });
            document.getElementById('sosNext')?.addEventListener('click', () => { currentPageSosRealtime++; renderAlerts(); });
        }
    }
    updateMapMarkers(filteredAlerts);
}

function renderTreatedAlerts() {
    const table = document.getElementById('treatedAlertsTable');
    const tbody = document.getElementById('treatedAlertsTableBody');
    const emptyState = document.getElementById('treatedAlertsEmptyState');
    const countBadge = document.getElementById('treatedAlertsCount');

    if (!tbody) {
        return;
    }

    const allTreatedAlerts = alertsCache
        .filter(alert => PROCESSED_ALERT_STATUSES.has(alert.statut))
        .sort((a, b) => getAlertClosedTimestamp(b) - getAlertClosedTimestamp(a));

    if (countBadge) {
        countBadge.textContent = allTreatedAlerts.length.toString();
    }

    let treatedAlerts = allTreatedAlerts;
    if (searchAlertsHistory) {
        treatedAlerts = treatedAlerts.filter(alert => matchAlertSearch(alert, searchAlertsHistory));
    }

    if (!treatedAlerts.length) {
        tbody.innerHTML = '';
        if (table) {
            table.hidden = true;
        }
        if (emptyState) {
            emptyState.hidden = false;
        }
        return;
    }

    const totalPages = Math.max(1, Math.ceil(treatedAlerts.length / ROWS_PER_PAGE));
    currentPageSosHistory = Math.min(currentPageSosHistory, totalPages - 1);
    const start = currentPageSosHistory * ROWS_PER_PAGE;
    const pageData = treatedAlerts.slice(start, start + ROWS_PER_PAGE);

    tbody.innerHTML = pageData.map(createTreatedAlertRow).join('');
    if (table) {
        table.hidden = false;
    }
    if (emptyState) {
        emptyState.hidden = true;
    }
    const pagEl = document.getElementById('sosHistoryPagination');
    if (pagEl) {
        if (treatedAlerts.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, treatedAlerts.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${treatedAlerts.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="sosHistPrev" ${currentPageSosHistory <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageSosHistory + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="sosHistNext" ${currentPageSosHistory >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('sosHistPrev')?.addEventListener('click', () => { currentPageSosHistory--; renderTreatedAlerts(); });
            document.getElementById('sosHistNext')?.addEventListener('click', () => { currentPageSosHistory++; renderTreatedAlerts(); });
        }
    }
}

async function loadHospitalsForMap() {
    try {
        const hospitals = await apiCall('/hospitals/map/markers');
        allHospitalsCache = Array.isArray(hospitals)
            ? hospitals
                .map(normalizeHospital)
                .filter(hospital => hospital && hasValidCoordinates(hospital))
            : [];
        updateMapMarkers();
    } catch (error) {
        console.error('Erreur lors du chargement des hôpitaux pour la carte:', error);
        allHospitalsCache = [];
    }
}

function formatPriseEnChargeCell(alert) {
    const steps = alert.workflow_steps || [];
    const current = steps.find((s) => s.statut === 'in_progress');
    if (!current) {
        return '<span class="muted">—</span>';
    }
    return `<div class="prise-en-charge-cell workflow-current">${escapeHtml(current.titre)}</div>`;
}

function createAlertRow(alert) {
    const statusClass = getStatusClass(alert.statut);
    const statusLabel = getStatusLabel(alert.statut);
    const priorityClass = getPriorityClass(alert.priorite);
    const priorityLabel = getPriorityLabel(alert.priorite);
    const description = formatAlertDescription(alert.description);
    const subscriptionHtml = alert.numero_souscription
        ? escapeHtml(alert.numero_souscription)
        : (alert.souscription_id ? `Souscription #${alert.souscription_id}` : 'Non associée');
    const locationHtml = formatLocationCell(alert);
    const createdAt = formatDateTime(alert.created_at);
    const numero = alert.numero_alerte || `Alerte #${alert.id}`;
    // Afficher le nom de l'utilisateur si disponible, sinon l'ID
    const userName = alert.user_full_name || `Utilisateur #${alert.user_id}`;

    return `
        <tr data-alert-id="${alert.id}">
            <td>
                <strong>${escapeHtml(numero)}</strong>
                <div class="muted">${escapeHtml(userName)}</div>
            </td>
            <td>
                <span class="status-badge ${statusClass}">${statusLabel}</span>
            </td>
            <td>
                <span class="priority-badge ${priorityClass}">${priorityLabel}</span>
            </td>
            <td>${formatPriseEnChargeCell(alert)}</td>
            <td>${description}</td>
            <td>${formatHospitalCell(alert)}</td>
            <td>
                <div>${subscriptionHtml}</div>
            </td>
            <td>${locationHtml}</td>
            <td>${createdAt}</td>
        </tr>
    `;
}

function createTreatedAlertRow(alert) {
    const statusClass = getStatusClass(alert.statut);
    const statusLabel = getStatusLabel(alert.statut);
    const priorityClass = getPriorityClass(alert.priorite);
    const priorityLabel = getPriorityLabel(alert.priorite);
    const description = formatAlertDescription(alert.description);
    const closedAt = formatDateTime(getAlertClosedDate(alert));
    const numero = alert.numero_alerte || `Alerte #${alert.id}`;
    const userName = alert.user_full_name || `Utilisateur #${alert.user_id}`;

    return `
        <tr data-alert-id="${alert.id}">
            <td>
                <strong>${escapeHtml(numero)}</strong>
                <div class="muted">${escapeHtml(userName)}</div>
            </td>
            <td>
                <span class="status-badge ${statusClass}">${statusLabel}</span>
            </td>
            <td>
                <span class="priority-badge ${priorityClass}">${priorityLabel}</span>
            </td>
            <td>${formatPriseEnChargeCell(alert)}</td>
            <td>${description}</td>
            <td>${formatHospitalCell(alert)}</td>
            <td>${closedAt}</td>
        </tr>
    `;
}

function getAlertsRoleLabel(role) {
    if (role === 'agent_reception_hopital') {
        return 'Réception Hôpital';
    }
    return 'Opérateur SOS';
}

function formatHospitalCell(alert) {
    const hospital = alert.assigned_hospital;
    if (!hospital) {
        return '<span class="muted">Non attribué</span>';
    }
    const city = hospital.ville
        ? `${hospital.ville}${hospital.pays ? ', ' + hospital.pays : ''}`
        : hospital.pays || '';
    const distanceText = typeof alert.distance_to_hospital_km === 'number'
        ? `${alert.distance_to_hospital_km.toFixed(1)} km`
        : null;
    return `
        <div><strong>${escapeHtml(hospital.nom)}</strong></div>
        ${city ? `<div class="muted">${escapeHtml(city)}</div>` : ''}
        ${distanceText ? `<div class="map-badge">${distanceText}</div>` : ''}
    `;
}

function updateMapMarkers(alerts = alertsCache) {
    if (!mapInstance || !alertMarkersLayer || !hospitalMarkersLayer || !alertHospitalLinksLayer) {
        return;
    }

    alertMarkersLayer.clearLayers();
    hospitalMarkersLayer.clearLayers();
    alertHospitalLinksLayer.clearLayers();
    alertMarkersIndex.clear();

    const bounds = [];
    const hospitalCoordinatesMap = new Map();

    allHospitalsCache.forEach(hospital => {
        const coords = getNumericCoordinatesFromValues(hospital.latitude, hospital.longitude);
        if (!coords) {
            return;
        }
        hospitalCoordinatesMap.set(hospital.id, coords);
        const marker = L.circleMarker([coords.lat, coords.lon], ALL_HOSPITAL_MARKER_STYLE);
        marker.bindPopup(createHospitalPopupContent(hospital), {
            autoPan: true,
            autoPanPaddingTopLeft: L.point(40, 100),
            autoPanPaddingBottomRight: L.point(40, 40),
            offset: L.point(0, 40),
        });
        marker.addTo(hospitalMarkersLayer);
        bounds.push([coords.lat, coords.lon]);
    });

    (alerts || []).forEach(alert => {
        const alertCoords = getNumericCoordinatesFromValues(alert.latitude, alert.longitude);
        if (!alertCoords) {
            return;
        }
        const marker = L.circleMarker([alertCoords.lat, alertCoords.lon], ALERT_MARKER_STYLE);
        marker.bindPopup(createAlertPopupContent(alert), {
            autoPan: true,
            autoPanPaddingTopLeft: L.point(40, 100),
            autoPanPaddingBottomRight: L.point(40, 40),
            /* Pas d'offset : la pointe du popup vise le marqueur rouge d'alerte */
            offset: L.point(0, 0),
        });
        marker.addTo(alertMarkersLayer);
        alertMarkersIndex.set(alert.id, marker);
        bounds.push([alertCoords.lat, alertCoords.lon]);

        const hospital = alert.assigned_hospital;
        if (hospital) {
            const hospitalCoords =
                getNumericCoordinatesFromValues(hospital.latitude, hospital.longitude) ||
                hospitalCoordinatesMap.get(hospital.id);
            if (hospitalCoords) {
                const link = L.polyline(
                    [
                        [alertCoords.lat, alertCoords.lon],
                        [hospitalCoords.lat, hospitalCoords.lon],
                    ],
                    HOSPITAL_LINK_STYLE
                );
                link.addTo(alertHospitalLinksLayer);
                bounds.push([hospitalCoords.lat, hospitalCoords.lon]);

                const highlightMarker = L.circleMarker(
                    [hospitalCoords.lat, hospitalCoords.lon],
                    HOSPITAL_MARKER_STYLE
                );
                highlightMarker.bindPopup(createHospitalPopupContent(hospital), {
                    autoPan: true,
                    autoPanPaddingTopLeft: L.point(40, 100),
                    autoPanPaddingBottomRight: L.point(40, 40),
                    offset: L.point(0, 40),
                });
                highlightMarker.addTo(hospitalMarkersLayer);
            }
        }
    });

    if (bounds.length) {
        mapInstance.fitBounds(bounds, {
            padding: [40, 40],
            maxZoom: 13,
        });
        hasFitBoundsOnce = true;
    } else if (!hasFitBoundsOnce) {
        mapInstance.setView(MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM);
    }

    if (alertMarkerHighlight && !alertMarkersIndex.has(alertMarkerHighlight.alertId)) {
        alertMarkerHighlight = null;
    }
}

function handleAlertMapLinkClick(event) {
    let alertId = null;
    const mapLink = event.target.closest('[data-alert-map-link]');
    if (mapLink) {
        alertId = Number(mapLink.getAttribute('data-alert-id'));
    } else {
        const row = event.target.closest('tr[data-alert-id]');
        if (row) {
            const tbody = row.closest('tbody');
            if (tbody && (tbody.id === 'alertsTableBody' || tbody.id === 'treatedAlertsTableBody')) {
                alertId = Number(row.getAttribute('data-alert-id'));
            }
        }
    }
    if (alertId == null || !Number.isFinite(alertId)) {
        return;
    }
    event.preventDefault();
    const focused = focusAlertOnMap(alertId);
    if (!focused) {
        showAlert('Impossible d\'afficher cette alerte sur la carte.', 'error');
    }
}

function focusAlertOnMap(alertId) {
    if (!mapInstance || !alertMarkersIndex.has(alertId)) {
        return false;
    }
    const marker = alertMarkersIndex.get(alertId);
    if (!marker) {
        return false;
    }
    const targetLatLng = marker.getLatLng();
    const desiredZoom = Math.max(mapInstance.getZoom(), 12);
    mapInstance.flyTo(targetLatLng, desiredZoom, { duration: 0.6 });
    marker.openPopup();
    highlightAlertMarker(alertId);
    scrollMapIntoView();
    return true;
}

function highlightAlertMarker(alertId) {
    if (alertMarkerHighlight?.marker) {
        alertMarkerHighlight.marker.setStyle(ALERT_MARKER_STYLE);
    }
    const marker = alertMarkersIndex.get(alertId);
    if (!marker) {
        return;
    }
    marker.setStyle(ALERT_MARKER_HIGHLIGHT_STYLE);
    alertMarkerHighlight = { alertId, marker };
    if (highlightResetTimer) {
        clearTimeout(highlightResetTimer);
    }
    highlightResetTimer = setTimeout(() => {
        if (alertMarkerHighlight?.marker) {
            alertMarkerHighlight.marker.setStyle(ALERT_MARKER_STYLE);
        }
        alertMarkerHighlight = null;
        highlightResetTimer = null;
    }, 5000);
}

function scrollMapIntoView() {
    const mapContainer = document.getElementById('alertsMap');
    if (!mapContainer) {
        return;
    }
    mapContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
    mapContainer.classList.add('map-focus-pulse');
    window.clearTimeout(mapContainer.__mapPulseTimer);
    mapContainer.__mapPulseTimer = window.setTimeout(() => {
        mapContainer.classList.remove('map-focus-pulse');
        mapContainer.__mapPulseTimer = null;
    }, 1400);
}

/**
 * Conduit l'utilisateur vers le tableau des alertes et met en surbrillance la ligne correspondante.
 * Utilisé lorsqu'on clique sur une notification d'alerte (profil sos-operator).
 * @param {number} alertId - ID de l'alerte
 * @returns {Promise<boolean>} true si la ligne a été trouvée et mise en surbrillance
 */
async function focusAlertInTable(alertId) {
    const id = Number(alertId);
    if (!Number.isFinite(id)) {
        return false;
    }

    await refreshAlerts();

    const alert = alertsCache.find((a) => a.id === id);
    const isActive = alert && ACTIVE_ALERT_STATUSES.has(alert.statut);

    const section = document.getElementById('sosAlertsSection');
    const tabRealtimeBtn = document.getElementById('tabRealtimeBtn');
    const tabHistoryBtn = document.getElementById('tabHistoryBtn');
    const realtimePanel = document.getElementById('sosRealtimePanel');
    const historyPanel = document.getElementById('sosHistoryPanel');

    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (isActive) {
        if (tabRealtimeBtn && !tabRealtimeBtn.classList.contains('active')) {
            tabRealtimeBtn.click();
        }
        if (realtimePanel) realtimePanel.hidden = false;
        if (historyPanel) historyPanel.hidden = true;
        activeSosTab = 'sosRealtimePanel';
    } else {
        if (tabHistoryBtn && !tabHistoryBtn.classList.contains('active')) {
            tabHistoryBtn.click();
        }
        if (historyPanel) historyPanel.hidden = false;
        if (realtimePanel) realtimePanel.hidden = true;
        activeSosTab = 'sosHistoryPanel';
    }

    const tbodyRealtime = document.getElementById('alertsTableBody');
    const tbodyHistory = document.getElementById('treatedAlertsTableBody');
    const row = (tbodyRealtime && tbodyRealtime.querySelector(`tr[data-alert-id="${id}"]`))
        || (tbodyHistory && tbodyHistory.querySelector(`tr[data-alert-id="${id}"]`));

    if (alertRowHighlightEl) {
        alertRowHighlightEl.classList.remove('alert-row-highlight');
        alertRowHighlightEl = null;
    }
    if (alertRowHighlightTimer) {
        clearTimeout(alertRowHighlightTimer);
        alertRowHighlightTimer = null;
    }

    if (row) {
        row.classList.add('alert-row-highlight');
        alertRowHighlightEl = row;
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        alertRowHighlightTimer = setTimeout(() => {
            if (alertRowHighlightEl) {
                alertRowHighlightEl.classList.remove('alert-row-highlight');
                alertRowHighlightEl = null;
            }
            alertRowHighlightTimer = null;
        }, 5000);
        return true;
    }

    showAlert('L\'alerte n\'apparaît pas dans la liste actuelle (filtres ou statut).', 'info');
    return false;
}

function showMapUnavailableMessage(message) {
    const mapContainer = document.getElementById('alertsMap');
    if (!mapContainer) {
        return;
    }
    mapContainer.innerHTML = `
        <div class="map-error-message">
            <strong>${escapeHtml(message || 'Carte indisponible')}</strong>
            <p class="muted">Essayez d'actualiser la page ou vérifiez votre connexion.</p>
        </div>
    `;
    mapContainer.classList.add('map-error-state');
}

function getPatientInitials(fullName) {
    if (!fullName || typeof fullName !== 'string') {
        return '?';
    }
    const parts = fullName.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
        return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    }
    return (parts[0] || '?').charAt(0).toUpperCase();
}

function computeAgeFromIsoDate(isoDate) {
    if (!isoDate || typeof isoDate !== 'string') return null;
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return null;
    const today = new Date();
    let age = today.getFullYear() - d.getFullYear();
    const m = today.getMonth() - d.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < d.getDate())) age--;
    return age >= 0 ? age : null;
}

function createAlertPopupContent(alert) {
    const hospital = alert.assigned_hospital;
    const distance = typeof alert.distance_to_hospital_km === 'number'
        ? `${alert.distance_to_hospital_km.toFixed(1)} km`
        : null;
    const description = alert.description ? escapeHtml(truncate(alert.description, 120)) : '';
    const numero = alert.numero_alerte || `Alerte #${alert.id}`;
    const assurNom = alert.user_full_name || '—';
    const assurAge = computeAgeFromIsoDate(alert.user_date_naissance);
    const assurTel = alert.user_telephone || '—';
    const numeroSouscription = alert.numero_souscription || '—';
    const contactNom = alert.user_nom_contact_urgence || null;
    const contactTel = alert.user_contact_urgence || null;
    const medecinNom = alert.medecin_referent_nom || null;
    const medecinTel = alert.medecin_referent_telephone || null;
    const photoUrl = alert.user_photo_url || null;
    const initials = getPatientInitials(assurNom);

    const photoHtml = photoUrl
        ? `<img src="${escapeHtml(photoUrl)}" alt="" class="map-popup-photo" style="width:48px;height:48px;border-radius:50%;object-fit:cover;">`
        : `<span class="map-popup-avatar" style="display:inline-flex;align-items:center;justify-content:center;width:48px;height:48px;border-radius:50%;background:#2a9d8f;color:#fff;font-size:1rem;font-weight:600;flex-shrink:0;">${escapeHtml(initials)}</span>`;

    const assurAgeLine = assurAge !== null ? ` • ${assurAge} an(s)` : '';
    const contactLine = (contactNom || contactTel)
        ? `<div style="margin-bottom:0.35rem;"><strong>Personne à contacter :</strong> ${escapeHtml(contactNom || '—')}${contactTel ? ' • ' + escapeHtml(contactTel) : ''}</div>`
        : '';
    const medecinLine = (medecinNom || medecinTel)
        ? `<div style="margin-bottom:0.35rem;"><strong>Médecin référent à contacter :</strong> ${escapeHtml(medecinNom || '—')}${medecinTel ? ' • ' + escapeHtml(medecinTel) : ''}</div>`
        : '';

    return `
        <div class="map-popup map-popup-alert">
            <div class="map-popup-header" style="margin-bottom:0.5rem;">
                <strong>${escapeHtml(numero)}</strong>
                <div class="muted" style="font-size:0.85em;margin-top:0.2rem;">
                    ${getStatusLabel(alert.statut)} • ${getPriorityLabel(alert.priorite)}
                </div>
            </div>
            <div class="map-popup-patient" style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;padding:0.35rem 0;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;">
                ${photoHtml}
                <div style="min-width:0;">
                    <div style="font-weight:600;">Assuré : ${escapeHtml(assurNom)}${assurAgeLine}</div>
                    <div class="muted" style="font-size:0.85em;">N° souscription : ${escapeHtml(numeroSouscription)}</div>
                    <div style="font-size:0.85em;margin-top:0.2rem;">Téléphone assuré : ${escapeHtml(assurTel)}</div>
                </div>
            </div>
            ${contactLine}
            ${medecinLine}
            ${hospital
                ? `<div style="margin-bottom:0.35rem;"><strong>Hôpital :</strong> ${escapeHtml(hospital.nom)}${distance ? ` (${distance})` : ''}</div>`
                : '<div style="margin-bottom:0.35rem;"><strong>Hôpital :</strong> Non attribué</div>'
            }
            ${description ? `<div class="muted" style="font-size:0.85em;margin-top:0.35rem;">${description}</div>` : ''}
        </div>
    `;
}

function createHospitalPopupContent(hospital) {
    const cityLine = hospital.ville
        ? `${hospital.ville}${hospital.pays ? ', ' + hospital.pays : ''}`
        : hospital.pays || '';
    const contactLine = hospital.telephone || hospital.email
        ? [hospital.telephone, hospital.email].filter(Boolean).join(' • ')
        : '';
    return `
        <div class="map-popup">
            <strong>${escapeHtml(hospital.nom)}</strong>
            ${cityLine ? `<div>${escapeHtml(cityLine)}</div>` : ''}
            ${contactLine ? `<div class="muted">${escapeHtml(contactLine)}</div>` : ''}
        </div>
    `;
}

function formatAlertDescription(text) {
    if (!text) {
        return '<span class="muted">Aucune description fournie</span>';
    }
    // Limiter à 120 caractères pour éviter le débordement dans le tableau
    const safe = escapeHtml(truncate(text, 120));
    return safe.replace(/\n/g, '<br>');
}

function formatLocationCell(alert) {
    const coords = formatCoordinates(alert.latitude, alert.longitude);
    if (!coords) {
        return '<span class="muted">Non renseignée</span>';
    }
    const alertId = Number(alert.id);
    return `
        <span class="coordinates-text">${escapeHtml(coords.text)}</span>
        <div class="location-links">
            <button
                type="button"
                class="map-link-btn"
                data-alert-map-link
                data-alert-id="${alertId}"
            >
                Voir sur la carte
            </button>
        </div>
    `;
}

function getNumericCoordinatesFromValues(lat, lon) {
    if (lat === null || lat === undefined || lon === null || lon === undefined) {
        return null;
    }
    const latNum = typeof lat === 'number' ? lat : parseFloat(lat);
    const lonNum = typeof lon === 'number' ? lon : parseFloat(lon);
    if (Number.isNaN(latNum) || Number.isNaN(lonNum)) {
        return null;
    }
    return { lat: latNum, lon: lonNum };
}

function formatCoordinates(lat, lon) {
    const coords = getNumericCoordinatesFromValues(lat, lon);
    if (!coords) {
        return null;
    }
    return {
        text: `${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}`,
        link: `https://www.google.com/maps?q=${coords.lat},${coords.lon}`,
        lat: coords.lat,
        lon: coords.lon,
    };
}

function updateLastRefresh() {
    const refreshEl = document.getElementById('lastRefreshTime');
    if (!refreshEl) {
        return;
    }
    const now = new Date();
    refreshEl.textContent = `Dernière actualisation : ${now.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    })}`;
}

function showAlertsError(error) {
    const errorEl = document.getElementById('alertsError');
    if (!errorEl) {
        return;
    }

    const message = error?.message || 'Impossible de récupérer les alertes SOS.';
    errorEl.innerHTML = `
        <div class="alert alert-error">
            <h4 style="margin-bottom: 0.5rem;">Impossible de charger les alertes</h4>
            <p>${escapeHtml(message)}</p>
            <button type="button" class="btn btn-outline btn-sm" data-retry-alerts>Réessayer</button>
        </div>
    `;
    errorEl.style.display = 'block';

    const retryBtn = errorEl.querySelector('[data-retry-alerts]');
    if (retryBtn) {
        retryBtn.addEventListener('click', () =>
            refreshAlerts(true, { forceLoading: true })
        );
    }
}

function hideAlertsError() {
    const errorEl = document.getElementById('alertsError');
    if (errorEl) {
        errorEl.innerHTML = '';
        errorEl.style.display = 'none';
    }
}

function getSearchableAlertText(alert) {
    const parts = [
        alert.numero_alerte || '',
        `#${alert.id}`,
        alert.user_full_name || '',
        `user${alert.user_id || ''}`,
        getStatusLabel(alert.statut),
        getPriorityLabel(alert.priorite),
        alert.description || '',
        (alert.numero_souscription || (alert.souscription_id ? `souscription #${alert.souscription_id}` : '')),
    ];
    const hospital = alert.assigned_hospital;
    if (hospital) {
        parts.push(hospital.nom || '', hospital.ville || '', hospital.pays || '');
    }
    return parts.join(' ').toLowerCase();
}

function matchAlertSearch(alert, searchTerm) {
    if (!searchTerm) {
        return true;
    }
    const text = getSearchableAlertText(alert);
    return text.includes(searchTerm);
}

function getStatusLabel(status) {
    return STATUS_LABELS[status] || (status ? status : 'Inconnu');
}

function getStatusClass(status) {
    return STATUS_CLASS_MAP[status] || 'status-pending';
}

function getPriorityLabel(priority) {
    if (!priority) {
        return PRIORITY_LABELS.normale;
    }
    return PRIORITY_LABELS[priority] || priority.charAt(0).toUpperCase() + priority.slice(1);
}

function getPriorityClass(priority) {
    return PRIORITY_CLASS_MAP[priority] || 'priority-normale';
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

function getAlertClosedDate(alert) {
    if (!alert) {
        return null;
    }
    return alert.resolved_at
        || alert.closed_at
        || alert.completed_at
        || alert.updated_at
        || alert.created_at
        || null;
}

function getAlertClosedTimestamp(alert) {
    const closedDate = getAlertClosedDate(alert);
    if (!closedDate) {
        return 0;
    }
    const date = new Date(closedDate);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
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

// ==================== Gestion des notifications SOS ====================

const SOS_NOTIFICATION_TYPES = {
    sos_alert_received: {
        label: 'Alerte reçue',
        icon: '🚨',
        defaultMessage: 'Une nouvelle alerte SOS vient d\'être déclenchée.',
    },
    invoice_received: {
        label: 'Facture reçue',
        icon: '💼',
        defaultMessage: 'Une nouvelle facture a été créée et nécessite votre attention.',
    },
};

const SOS_NOTIFICATION_ORDER = [
    'sos_alert_received',
    'invoice_received',
];

const sosNotificationsState = {
    enabled: false,
    items: [],
    elements: {},
    caches: {
        sinistres: {},
        invoices: {},
        alertes: {},
        users: {},
    },
};

function initSosNotificationsModule() {
    const section = document.getElementById('sosNotificationsSection');
    if (!section) {
        return;
    }

    const role = (localStorage.getItem('user_role') || '').toLowerCase();
    if (role !== 'sos_operator') {
        section.style.display = 'none';
        return;
    }

    sosNotificationsState.enabled = true;
    sosNotificationsState.elements = {
        section,
        list: document.getElementById('sosNotificationsList'),
        empty: document.getElementById('sosNotificationsEmpty'),
        loading: document.getElementById('sosNotificationsLoading'),
        error: document.getElementById('sosNotificationsError'),
        count: document.getElementById('sosNotificationsCount'),
        refreshButton: document.getElementById('refreshSosNotificationsBtn'),
    };

    if (sosNotificationsState.elements.refreshButton) {
        sosNotificationsState.elements.refreshButton.addEventListener('click', () =>
            loadSosNotifications(true)
        );
    }
    if (sosNotificationsState.elements.list) {
        sosNotificationsState.elements.list.addEventListener('click', handleSosNotificationCardClick);
        sosNotificationsState.elements.list.addEventListener('keydown', handleSosNotificationCardKeyDown);
    }

    loadSosNotifications();
}

async function loadSosNotifications(showToast = false) {
    if (!sosNotificationsState.enabled) {
        return;
    }

    const { error, loading } = sosNotificationsState.elements;
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
            (item) => SOS_NOTIFICATION_TYPES[item.type_notification] && !item.is_read
        );
        sosNotificationsState.items = sortSosNotifications(filtered);
        renderSosNotifications();
        if (showToast) {
            showAlert('Notifications mises à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des notifications SOS:', error);
        if (sosNotificationsState.elements.error) {
            sosNotificationsState.elements.error.hidden = false;
            sosNotificationsState.elements.error.textContent =
                error.message || 'Impossible de charger les notifications.';
        }
        sosNotificationsState.items = [];
        renderSosNotifications();
    } finally {
        if (loading) {
            loading.hidden = true;
        }
    }
}

function sortSosNotifications(notifications) {
    return notifications
        .slice()
        .sort((a, b) => {
            const typeIndexA = SOS_NOTIFICATION_ORDER.indexOf(a.type_notification);
            const typeIndexB = SOS_NOTIFICATION_ORDER.indexOf(b.type_notification);
            if (typeIndexA !== typeIndexB) {
                const safeA = typeIndexA === -1 ? Number.MAX_SAFE_INTEGER : typeIndexA;
                const safeB = typeIndexB === -1 ? Number.MAX_SAFE_INTEGER : typeIndexB;
                return safeA - safeB;
            }
            return new Date(b.created_at || 0) - new Date(a.created_at || 0);
        });
}

function renderSosNotifications() {
    const { list, empty } = sosNotificationsState.elements;
    if (!list || !empty) {
        return;
    }

    const notifications = sosNotificationsState.items || [];
    updateSosNotificationCount(notifications.length);

    if (!notifications.length) {
        list.innerHTML = '';
        if (list) list.hidden = true;
        if (empty) empty.hidden = false;
        return;
    }

    list.innerHTML = notifications
        .map((notification, index) => buildSosNotificationCard(notification, index))
        .join('');
    if (empty) empty.hidden = true;
    if (list) list.hidden = false;
}

async function getAlertUserData(notification) {
    if (!notification || notification.lien_relation_type !== 'sinistre' || !notification.lien_relation_id) {
        return null;
    }
    
    const sinistreId = Number(notification.lien_relation_id);
    if (!Number.isFinite(sinistreId)) {
        return null;
    }
    
    // Vérifier le cache
    if (!sosNotificationsState.caches) {
        sosNotificationsState.caches = { sinistres: {}, invoices: {}, alertes: {}, users: {} };
    }
    
    const userCache = sosNotificationsState.caches.users || {};
    if (userCache[sinistreId]) {
        return userCache[sinistreId];
    }
    
    try {
        // Récupérer le sinistre pour obtenir l'alerte_id
        const sinistre = await apiCall(`/hospital-sinistres/sinistres/${sinistreId}`);
        if (!sinistre || !sinistre.alerte_id) {
            return null;
        }
        
        // Récupérer l'alerte avec les données utilisateur
        const alerte = await apiCall(`/sos/${sinistre.alerte_id}`);
        if (!alerte) {
            return null;
        }
        
        // Récupérer le téléphone depuis l'objet user si disponible
        const userTelephone = (alerte.user && alerte.user.telephone) ? alerte.user.telephone : null;
        
        const userData = {
            id: alerte.user_id,
            full_name: alerte.user_full_name || 'Non renseigné',
            email: alerte.user_email || 'Non renseigné',
            telephone: userTelephone,
            photo_url: null, // À récupérer depuis l'API si disponible dans le futur
            alerte_id: alerte.id,
            numero_alerte: alerte.numero_alerte,
            priorite: alerte.priorite || 'normale',
            adresse: alerte.adresse || 'Non renseignée',
            hospital: alerte.assigned_hospital ? alerte.assigned_hospital.nom : null,
        };
        
        // Mettre en cache
        userCache[sinistreId] = userData;
        sosNotificationsState.caches.users = userCache;
        
        return userData;
    } catch (error) {
        console.error(`Erreur lors de la récupération des données utilisateur pour le sinistre ${sinistreId}:`, error);
        return null;
    }
}

function buildSosNotificationCard(notification, index) {
    try {
        const config = SOS_NOTIFICATION_TYPES[notification.type_notification];
        if (!config) {
            return '';
        }
        const timestamp = notification.created_at
            ? new Date(notification.created_at).toLocaleString('fr-FR')
            : '—';
        const title = notification.titre || config.label;
        const body = notification.message || config.defaultMessage;
        const reference = getSosNotificationReference(notification);
        
        // Formater le message pour améliorer la lisibilité
        const formattedBody = formatSosNotificationMessage(body);
        
        // Récupérer les données utilisateur si c'est une alerte SOS
        const userDataPromise = notification.lien_relation_type === 'sinistre' 
            ? getAlertUserData(notification) 
            : Promise.resolve(null);
        
        // Créer un identifiant unique pour cette notification
        const notificationId = `notification-${notification.id}-${index}`;
        
        // Rendre la carte initialement sans les données utilisateur
        const cardHtml = `
            <div class="card notification-card notification-card--enhanced" 
                 data-notification-type="${notification.type_notification}"
                 data-notification-id="${notificationId}">
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
        
        // Charger les données utilisateur de manière asynchrone et mettre à jour la carte
        if (userDataPromise) {
            userDataPromise.then(userData => {
                if (userData) {
                    updateNotificationCardWithUserData(notificationId, userData, notification, config, timestamp, title, formattedBody, reference);
                }
            }).catch(error => {
                console.error('Erreur lors du chargement des données utilisateur:', error);
            });
        }
        
        return cardHtml;
    } catch (error) {
        console.error('Erreur lors de la construction de la carte de notification:', error);
        return '';
    }
}

function updateNotificationCardWithUserData(notificationId, userData, notification, config, timestamp, title, formattedBody, reference) {
    const cardElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
    if (!cardElement) {
        return;
    }
    
    // Créer l'URL de la photo (placeholder si pas de photo)
    const photoUrl = userData.photo_url || 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2UyZThmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iNDAiIGZpbGw9IiM5Y2EzYWYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5VPC90ZXh0Pjwvc3ZnPg==';
    
    // Déterminer la couleur de priorité
    const priorityClass = userData.priorite === 'urgente' ? 'priority-urgent' : 
                         userData.priorite === 'haute' ? 'priority-high' : 'priority-normal';
    
    // Récupérer l'index depuis l'élément original
    const originalBody = cardElement.querySelector('.notification-card__body');
    const originalIndex = originalBody ? originalBody.dataset.notificationIndex : '';
    
    // Créer le HTML amélioré avec les informations personnelles
    const enhancedCardHtml = `
        <div class="notification-card__body" role="button" tabindex="0" 
             data-notification-index="${originalIndex}"
             aria-label="Ouvrir le dossier lié à cette notification">
            <div class="notification-card__header">
                <span class="notification-pill">
                    <span aria-hidden="true">${config.icon}</span>
                    <span>${escapeHtml(config.label)}</span>
                </span>
                <span class="notification-time">${escapeHtml(timestamp)}</span>
            </div>
            
            <div class="notification-content-wrapper">
                <div class="notification-user-section">
                    <div class="notification-user-avatar">
                        <img src="${photoUrl}" 
                             alt="${escapeHtml(userData.full_name)}" 
                             class="user-avatar-img"
                             onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2UyZThmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iNDAiIGZpbGw9IiM5Y2EzYWYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5VPC90ZXh0Pjwvc3ZnPg=='">
                    </div>
                    <div class="notification-user-info">
                        <h3 class="notification-user-name">${escapeHtml(userData.full_name)}</h3>
                        <div class="notification-user-details">
                            <div class="user-detail-item">
                                <span class="user-detail-icon">📧</span>
                                <span class="user-detail-text">${escapeHtml(userData.email)}</span>
                            </div>
                            ${userData.telephone ? `
                            <div class="user-detail-item">
                                <span class="user-detail-icon">📞</span>
                                <span class="user-detail-text">${escapeHtml(userData.telephone)}</span>
                            </div>
                            ` : ''}
                            <div class="user-detail-item">
                                <span class="user-detail-icon">📍</span>
                                <span class="user-detail-text">${escapeHtml(userData.adresse)}</span>
                            </div>
                            ${userData.hospital ? `
                            <div class="user-detail-item">
                                <span class="user-detail-icon">🏥</span>
                                <span class="user-detail-text">${escapeHtml(userData.hospital)}</span>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="notification-alert-section">
                    <div class="notification-alert-header">
                        <h4 class="notification-alert-title">${escapeHtml(title)}</h4>
                        <span class="notification-priority ${priorityClass}">
                            ${userData.priorite === 'urgente' ? '🚨 Urgente' : 
                              userData.priorite === 'haute' ? '⚠️ Haute' : 'ℹ️ Normale'}
                        </span>
                    </div>
                    <div class="notification-alert-info">
                        <div class="alert-info-item">
                            <strong>Alerte:</strong> ${escapeHtml(userData.numero_alerte || 'N/A')}
                        </div>
                        ${reference ? `<div class="alert-info-item">${escapeHtml(reference)}</div>` : ''}
                    </div>
                    <div class="notification-body">${formattedBody}</div>
                </div>
            </div>
            
            <div class="notification-link muted">Cliquer pour ouvrir le dossier</div>
        </div>
    `;
    
    // Mettre à jour le contenu de la carte
    const bodyElement = cardElement.querySelector('.notification-card__body');
    if (bodyElement) {
        bodyElement.outerHTML = enhancedCardHtml;
    }
}

function formatSosNotificationMessage(message) {
    if (!message || typeof message !== 'string') {
        return '<p class="muted">Aucun message</p>';
    }
    
    // Supprimer la section "--- Extrait du questionnaire ---" si elle existe
    const excerptIndex = message.indexOf('--- Extrait du questionnaire ---');
    if (excerptIndex !== -1) {
        message = message.substring(0, excerptIndex).trim();
    }
    message = message.replace(/---\s*Extrait du questionnaire\s*---.*$/s, '').trim();
    message = message.replace(/Extrait du questionnaire.*$/s, '').trim();
    
    // Échapper le HTML d'abord
    let formatted = escapeHtml(message);
    
    // Mettre en forme les sections avec des titres
    formatted = formatted.replace(/(📋|📄|🔍|⚠️|🚨|💼)\s*([^\n]+)/g, '<strong class="notification-section-title">$1 $2</strong>');
    
    // Mettre en forme les listes à puces
    const lines = formatted.split('\n');
    let inList = false;
    let result = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (line.startsWith('•')) {
            if (!inList) {
                result.push('<ul class="notification-list">');
                inList = true;
            }
            const content = line.replace(/^•\s*/, '');
            result.push(`<li>${content}</li>`);
        } else {
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            
            if (line) {
                const enhanced = line.replace(/(Priorité|Adresse|Assuré|Dossier médical|Informations médicales|version|Alerte|Sinistre|Facture|Rapport|Hôpital|Montant TTC|Statut):/g, '<strong>$1:</strong>');
                result.push(enhanced);
            } else if (i < lines.length - 1) {
                result.push('<br>');
            }
        }
    }
    
    if (inList) {
        result.push('</ul>');
    }
    
    formatted = result.join('\n');
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

function getSosNotificationReference(notification) {
    if (!notification) {
        return '';
    }
    if (notification.lien_relation_type === 'sinistre' && notification.lien_relation_id) {
        return `Sinistre #${notification.lien_relation_id}`;
    }
    if (notification.lien_relation_type === 'invoice' && notification.lien_relation_id) {
        return `Facture #${notification.lien_relation_id}`;
    }
    return '';
}

function updateSosNotificationCount(value) {
    if (!sosNotificationsState.elements.count) {
        return;
    }
    const suffix = value > 1 ? 'notifications' : 'notification';
    sosNotificationsState.elements.count.textContent = `${value} ${suffix}`;
}

async function handleSosNotificationCardClick(event) {
    const card = event.target.closest('[data-notification-index]');
    if (!card) {
        return;
    }
    const index = Number(card.dataset.notificationIndex);
    await openSosNotificationTargetByIndex(index, card);
}

async function handleSosNotificationCardKeyDown(event) {
    if (!['Enter', ' '].includes(event.key)) {
        return;
    }
    const card = event.target.closest('[data-notification-index]');
    if (!card) {
        return;
    }
    event.preventDefault();
    const index = Number(card.dataset.notificationIndex);
    await openSosNotificationTargetByIndex(index, card);
}

async function openSosNotificationTargetByIndex(index, cardElement) {
    if (!Number.isFinite(index) || index < 0) {
        return;
    }
    const notifications = sosNotificationsState.items || [];
    const notification = notifications[index];
    if (!notification) {
        return;
    }
    if (cardElement) {
        cardElement.classList.add('notification-card--loading');
    }
    try {
        const target = await resolveSosNotificationLink(notification);
        if (!target) {
            showAlert('Impossible de trouver le dossier associé à cette notification.', 'error');
            return;
        }
        await markSosNotificationAsRead(notification.id);
        sosNotificationsState.items = sosNotificationsState.items.filter(
            (item) => item.id !== notification.id
        );
        renderSosNotifications();

        if (typeof target === 'object' && target.action === 'focusAlert' && Number.isFinite(target.alertId)) {
            const focused = await focusAlertInTable(target.alertId);
            if (!focused) {
                showAlert('Alerte introuvable dans le tableau.', 'info');
            }
        } else if (typeof target === 'string') {
            window.location.href = target;
        } else {
            showAlert('Impossible d\'ouvrir cette notification.', 'error');
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

async function markSosNotificationAsRead(notificationId) {
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

async function resolveSosNotificationLink(notification) {
    if (!notification) {
        return null;
    }
    if (notification.type_notification === 'sos_alert_received' && notification.lien_relation_type === 'sinistre' && notification.lien_relation_id) {
        const alertId = await getAlertIdFromSinistreNotification(notification.lien_relation_id);
        if (Number.isFinite(alertId)) {
            return { action: 'focusAlert', alertId };
        }
        return null;
    }
    if (notification.lien_relation_type === 'sinistre' && notification.lien_relation_id) {
        return resolveSosSinistreNotificationLink(notification.lien_relation_id);
    }
    if (notification.lien_relation_type === 'invoice' && notification.lien_relation_id) {
        return `sinistre-invoices.html?invoice_id=${notification.lien_relation_id}`;
    }
    return null;
}

async function getAlertIdFromSinistreNotification(rawId) {
    const sinistreId = Number(rawId);
    if (!Number.isFinite(sinistreId)) {
        return null;
    }
    if (!sosNotificationsState.caches) {
        sosNotificationsState.caches = { sinistres: {}, invoices: {}, alertIds: {} };
    }
    const alertIdCache = sosNotificationsState.caches.alertIds || {};
    if (alertIdCache[sinistreId] !== undefined) {
        return alertIdCache[sinistreId];
    }
    try {
        const sinistre = await apiCall(`/hospital-sinistres/sinistres/${sinistreId}`);
        const alertId = sinistre?.alerte_id != null ? Number(sinistre.alerte_id) : null;
        alertIdCache[sinistreId] = alertId;
        sosNotificationsState.caches.alertIds = alertIdCache;
        return alertId;
    } catch (error) {
        console.error(`Impossible de récupérer l'alerte pour le sinistre ${sinistreId}:`, error);
        return null;
    }
}

async function resolveSosSinistreNotificationLink(rawId) {
    const sinistreId = Number(rawId);
    if (!Number.isFinite(sinistreId)) {
        return null;
    }
    if (!sosNotificationsState.caches) {
        sosNotificationsState.caches = { sinistres: {}, invoices: {}, alertIds: {} };
    }
    const cache = sosNotificationsState.caches.sinistres || {};
    if (cache[sinistreId]) {
        return cache[sinistreId];
    }
    try {
        const sinistre = await apiCall(`/hospital-sinistres/sinistres/${sinistreId}`);
        const alertId = sinistre?.alerte_id;
        const url = alertId ? `hospital-alert-details.html?alert_id=${alertId}` : null;
        cache[sinistreId] = url;
        sosNotificationsState.caches.sinistres = cache;
        return url;
    } catch (error) {
        console.error(`Impossible de résoudre le sinistre ${sinistreId}:`, error);
        return null;
    }
}
