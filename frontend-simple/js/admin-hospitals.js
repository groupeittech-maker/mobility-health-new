const MAP_DEFAULT_CENTER = [5.35, -3.99];
const MAP_DEFAULT_ZOOM = 6;

const state = {
    hospitals: [],
    medecins: [],
    receptionists: [],
    hospitalDoctorsChoices: [],
    accountants: [],
    editingHospitalId: null,
    hospitalsMap: null,
    hospitalsMarkersLayer: null,
    selectionMap: null,
    selectionMarker: null,
};

let formEl;
let submitBtnEl;
let cancelEditBtnEl;
let medecinSelectEl;
let receptionistSelectEl;
let doctorsSelectEl;
let accountantsSelectEl;
let latitudeInputEl;
let longitudeInputEl;
let hospitalsTableBodyEl;
let hospitalsEmptyStateEl;
let searchHospitalsInputEl;
let searchHospitalsTerm = '';
const ROWS_PER_PAGE = 6;
let currentPageHospitals = 0;

document.addEventListener('DOMContentLoaded', initAdminHospitals);

async function initAdminHospitals() {
    const allowed = await requireRole('admin', 'login.html');
    if (!allowed) {
        return;
    }
    cacheDomElements();
    setupEventListeners();
    await Promise.all([
        loadMedecins(),
        loadReceptionists(),
        loadAccountants(),
        loadHospitalDoctorsChoices(),
        loadHospitals(),
    ]);
    populateUserSelects();
    await initMaps();
}

function cacheDomElements() {
    formEl = document.getElementById('hospitalForm');
    submitBtnEl = document.getElementById('submitBtn');
    cancelEditBtnEl = document.getElementById('cancelEditBtn');
    medecinSelectEl = document.getElementById('medecinReferentSelect');
    receptionistSelectEl = document.getElementById('receptionistsSelect');
    doctorsSelectEl = document.getElementById('doctorsSelect');
    accountantsSelectEl = document.getElementById('accountantsSelect');
    latitudeInputEl = document.getElementById('latitude');
    longitudeInputEl = document.getElementById('longitude');
    hospitalsTableBodyEl = document.getElementById('hospitalsTableBody');
    hospitalsEmptyStateEl = document.getElementById('hospitalsEmptyState');
    searchHospitalsInputEl = document.getElementById('searchHospitals');
}

function setupEventListeners() {
    document.getElementById('refreshHospitalsBtn')?.addEventListener('click', () => loadHospitals(true));
    document.getElementById('resetFormBtn')?.addEventListener('click', resetForm);
    if (searchHospitalsInputEl) {
        searchHospitalsInputEl.addEventListener('input', () => {
            searchHospitalsTerm = (searchHospitalsInputEl.value || '').trim().toLowerCase();
            renderHospitalsTable();
        });
    }
    cancelEditBtnEl?.addEventListener('click', resetForm);
    if (formEl) {
        formEl.addEventListener('submit', handleSubmit);
    }
}

async function initMaps() {
    try {
        await window.waitForLeaflet?.(8000);
    } catch (error) {
        console.error('Leaflet indisponible', error);
        showAlert('Impossible de charger Leaflet. Vérifiez votre connexion.', 'error');
        return;
    }

    if (!window.L) {
        return;
    }

    state.hospitalsMap = L.map('hospitalsMap').setView(MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 16,
    }).addTo(state.hospitalsMap);
    state.hospitalsMarkersLayer = L.layerGroup().addTo(state.hospitalsMap);
    plotHospitalsOnMap();

    state.selectionMap = L.map('hospitalCreateMap').setView(MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 16,
    }).addTo(state.selectionMap);
    state.selectionMap.on('click', handleSelectionMapClick);
}

function handleSelectionMapClick(event) {
    const { lat, lng } = event.latlng;
    latitudeInputEl.value = lat.toFixed(6);
    longitudeInputEl.value = lng.toFixed(6);
    if (state.selectionMarker) {
        state.selectionMarker.setLatLng([lat, lng]);
    } else if (window.L) {
        state.selectionMarker = L.marker([lat, lng], { draggable: true }).addTo(state.selectionMap);
        state.selectionMarker.on('dragend', evt => {
            const coords = evt.target.getLatLng();
            latitudeInputEl.value = coords.lat.toFixed(6);
            longitudeInputEl.value = coords.lng.toFixed(6);
        });
    }
}

async function loadHospitals(showToast = false) {
    try {
        const hospitals = await apiCall('/hospitals/');
        state.hospitals = Array.isArray(hospitals) ? hospitals : [];
        renderHospitalsTable();
        plotHospitalsOnMap();
        if (showToast) {
            showAlert('Liste des hôpitaux actualisée.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des hôpitaux:', error);
        showAlert(error.message || 'Impossible de charger les hôpitaux.', 'error');
    }
}

async function loadMedecins() {
    try {
        const medReferents = await apiCall('/users?role=medecin_referent_mh&limit=500');
        let doctors = medReferents;
        if (!medReferents?.length) {
            doctors = await apiCall('/users?role=doctor&limit=500');
        }
        state.medecins = Array.isArray(doctors) ? doctors : [];
    } catch (error) {
        console.error('Erreur lors du chargement des médecins référents:', error);
        state.medecins = [];
    }
}

async function loadReceptionists() {
    try {
        const receptionists = await apiCall('/users?role=agent_reception_hopital&limit=500');
        state.receptionists = Array.isArray(receptionists) ? receptionists : [];
    } catch (error) {
        console.error('Erreur lors du chargement des réceptionnistes:', error);
        state.receptionists = [];
    }
}

async function loadAccountants() {
    try {
        const accountants = await apiCall('/users?role=agent_comptable_hopital&limit=500');
        state.accountants = Array.isArray(accountants) ? accountants : [];
    } catch (error) {
        console.error('Erreur lors du chargement des agents comptables:', error);
        state.accountants = [];
    }
}

async function loadHospitalDoctorsChoices() {
    try {
        // Uniquement les médecins hospitaliers (pas les médecins génériques ni les médecins référents MH)
        const medecinsHopital = await apiCall('/users?role=medecin_hopital&limit=500');
        state.hospitalDoctorsChoices = Array.isArray(medecinsHopital) ? medecinsHopital : [];
    } catch (error) {
        console.error('Erreur lors du chargement des médecins hospitaliers:', error);
        state.hospitalDoctorsChoices = [];
    }
}

function populateUserSelects() {
    if (medecinSelectEl) {
        medecinSelectEl.innerHTML = '<option value="">-- Sélectionner --</option>';
        state.medecins.forEach(doctor => {
            const option = document.createElement('option');
            option.value = doctor.id;
            option.textContent = doctor.full_name || doctor.email || doctor.username;
            medecinSelectEl.appendChild(option);
        });
    }
    if (receptionistSelectEl) {
        receptionistSelectEl.innerHTML = '';
        state.receptionists.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.full_name || user.email || user.username;
            receptionistSelectEl.appendChild(option);
        });
    }
    if (doctorsSelectEl) {
        doctorsSelectEl.innerHTML = '';
        state.hospitalDoctorsChoices.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.full_name || user.email || user.username;
            doctorsSelectEl.appendChild(option);
        });
    }
    if (accountantsSelectEl) {
        accountantsSelectEl.innerHTML = '';
        state.accountants.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.full_name || user.email || user.username;
            accountantsSelectEl.appendChild(option);
        });
    }
}

function renderHospitalsTable() {
    if (!hospitalsTableBodyEl) {
        return;
    }
    const filtered = searchHospitalsTerm
        ? state.hospitals.filter((h) => {
            const nom = (h.nom || '').toLowerCase();
            const ville = (h.ville || '').toLowerCase();
            const pays = (h.pays || '').toLowerCase();
            const adresse = (h.adresse || '').toLowerCase();
            const email = (h.email || '').toLowerCase();
            const telephone = (h.telephone || '').toLowerCase();
            const medecin = ((h.medecin_referent?.full_name || h.medecin_referent?.email) || '').toLowerCase();
            return nom.includes(searchHospitalsTerm) || ville.includes(searchHospitalsTerm) ||
                pays.includes(searchHospitalsTerm) || adresse.includes(searchHospitalsTerm) ||
                email.includes(searchHospitalsTerm) || telephone.includes(searchHospitalsTerm) ||
                medecin.includes(searchHospitalsTerm);
        })
        : state.hospitals;
    if (!filtered.length) {
        hospitalsTableBodyEl.innerHTML = '';
        if (hospitalsEmptyStateEl) {
            hospitalsEmptyStateEl.hidden = false;
            hospitalsEmptyStateEl.querySelector('p').textContent = state.hospitals.length
                ? 'Aucun hôpital ne correspond à la recherche.'
                : 'Aucun hôpital enregistré pour le moment.';
        }
        return;
    }
    hospitalsEmptyStateEl && (hospitalsEmptyStateEl.hidden = true);
    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    currentPageHospitals = Math.min(currentPageHospitals, totalPages - 1);
    const start = currentPageHospitals * ROWS_PER_PAGE;
    const pageData = filtered.slice(start, start + ROWS_PER_PAGE);
    const rows = pageData.map(hospital => {
        const medecinName = hospital.medecin_referent?.full_name || hospital.medecin_referent?.email || 'Non défini';
        const contactLines = [
            hospital.telephone || '',
            hospital.email || ''
        ].filter(Boolean).join(' • ');
        const location = [hospital.ville, hospital.pays].filter(Boolean).join(', ');
        const coords = hospital.latitude && hospital.longitude
            ? `${Number(hospital.latitude).toFixed(4)}, ${Number(hospital.longitude).toFixed(4)}`
            : '—';
        const receptionSummary = `${hospital.receptionists_count || 0} agent(s)`;
        const accountantSummary = hospital.accountants_count
            ? `${hospital.accountants_count} agent(s)`
            : 'Aucun agent';
        return `
            <tr>
                <td>
                    <strong>${escapeHtml(hospital.nom)}</strong>
                    <div class="muted">${escapeHtml(hospital.adresse || '')}</div>
                </td>
                <td>${escapeHtml(medecinName)}</td>
                <td>${escapeHtml(receptionSummary)}</td>
                <td>${escapeHtml(accountantSummary)}</td>
                <td>${escapeHtml(contactLines || '—')}</td>
                <td>
                    <div>${escapeHtml(location || '—')}</div>
                    <div class="muted">${coords}</div>
                </td>
                <td class="table-actions">
                    <select class="action-select" data-hospital-id="${hospital.id}">
                        <option value="">Actions</option>
                        <option value="edit">Modifier</option>
                    </select>
                </td>
            </tr>
        `;
    }).join('');
    hospitalsTableBodyEl.innerHTML = rows;
    setupHospitalsTableActions();
    const pagEl = document.getElementById('hospitalsPagination');
    if (pagEl) {
        if (filtered.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, filtered.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${filtered.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="hospPrev" ${currentPageHospitals <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageHospitals + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="hospNext" ${currentPageHospitals >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('hospPrev')?.addEventListener('click', () => { currentPageHospitals--; renderHospitalsTable(); });
            document.getElementById('hospNext')?.addEventListener('click', () => { currentPageHospitals++; renderHospitalsTable(); });
        }
    }
}

function setupHospitalsTableActions() {
    if (!hospitalsTableBodyEl) {
        return;
    }
    
    hospitalsTableBodyEl.addEventListener('change', (event) => {
        const select = event.target.closest('.action-select');
        if (!select) {
            return;
        }
        
        const action = select.value;
        if (!action) {
            return;
        }
        
        const hospitalId = parseInt(select.dataset.hospitalId, 10);
        if (Number.isNaN(hospitalId)) {
            return;
        }
        
        switch (action) {
            case 'edit':
                startEditHospital(hospitalId);
                break;
        }
        
        // Réinitialiser le select
        select.value = '';
    });
}

async function startEditHospital(hospitalId) {
    try {
        const detail = await apiCall(`/hospitals/${hospitalId}/details`);
        state.editingHospitalId = hospitalId;
        document.getElementById('formTitle').textContent = `Modifier l'hôpital #${hospitalId}`;
        cancelEditBtnEl.hidden = false;
        submitBtnEl.textContent = 'Mettre à jour';

        formEl.nom.value = detail.nom || '';
        formEl.adresse.value = detail.adresse || '';
        formEl.ville.value = detail.ville || '';
        formEl.pays.value = detail.pays || '';
        formEl.telephone.value = detail.telephone || '';
        formEl.email.value = detail.email || '';
        formEl.specialites.value = detail.specialites || '';
        formEl.capacite_lits.value = detail.capacite_lits || '';
        formEl.latitude.value = Number(detail.latitude || 0).toFixed(6);
        formEl.longitude.value = Number(detail.longitude || 0).toFixed(6);
        if (medecinSelectEl) {
            medecinSelectEl.value = detail.medecin_referent_id || '';
        }
        if (receptionistSelectEl) {
            Array.from(receptionistSelectEl.options).forEach(option => {
                option.selected = detail.receptionists?.some(user => user.id === Number(option.value));
            });
        }
        if (doctorsSelectEl) {
            Array.from(doctorsSelectEl.options).forEach(option => {
                option.selected = detail.doctors?.some(user => user.id === Number(option.value));
            });
        }
        if (accountantsSelectEl) {
            Array.from(accountantsSelectEl.options).forEach(option => {
                option.selected = detail.accountants?.some(user => user.id === Number(option.value));
            });
        }
        if (state.selectionMap && state.selectionMarker && detail.latitude && detail.longitude) {
            const coords = [Number(detail.latitude), Number(detail.longitude)];
            state.selectionMarker.setLatLng(coords);
            state.selectionMap.setView(coords, 12);
        }
    } catch (error) {
        console.error('Impossible de charger le détail de l’hôpital:', error);
        showAlert(error.message || 'Impossible de charger le détail de l’hôpital.', 'error');
    }
}

function resetForm() {
    state.editingHospitalId = null;
    formEl.reset();
    document.getElementById('formTitle').textContent = 'Créer un nouvel hôpital';
    submitBtnEl.textContent = 'Enregistrer';
    cancelEditBtnEl.hidden = true;
    if (medecinSelectEl) {
        medecinSelectEl.value = '';
    }
    if (receptionistSelectEl) {
        Array.from(receptionistSelectEl.options).forEach(option => option.selected = false);
    }
    if (doctorsSelectEl) {
        Array.from(doctorsSelectEl.options).forEach(option => option.selected = false);
    }
    if (accountantsSelectEl) {
        Array.from(accountantsSelectEl.options).forEach(option => option.selected = false);
    }
}

async function handleSubmit(event) {
    event.preventDefault();
    const payload = {
        nom: formEl.nom.value.trim(),
        adresse: formEl.adresse.value.trim() || null,
        ville: formEl.ville.value.trim() || null,
        pays: formEl.pays.value.trim() || null,
        telephone: formEl.telephone.value.trim() || null,
        email: formEl.email.value.trim() || null,
        specialites: formEl.specialites.value.trim() || null,
        capacite_lits: formEl.capacite_lits.value ? Number(formEl.capacite_lits.value) : null,
        latitude: Number(formEl.latitude.value),
        longitude: Number(formEl.longitude.value),
        est_actif: true,
        medecin_referent_id: medecinSelectEl.value ? Number(medecinSelectEl.value) : null,
        receptionist_ids: receptionistSelectEl
            ? Array.from(receptionistSelectEl.selectedOptions || []).map(option => Number(option.value))
            : [],
        doctor_ids: doctorsSelectEl
            ? Array.from(doctorsSelectEl.selectedOptions || []).map(option => Number(option.value))
            : [],
        accountant_ids: accountantsSelectEl
            ? Array.from(accountantsSelectEl.selectedOptions || []).map(option => Number(option.value))
            : [],
    };

    if (!payload.nom || Number.isNaN(payload.latitude) || Number.isNaN(payload.longitude)) {
        showAlert('Veuillez renseigner un nom et une position géographique.', 'error');
        return;
    }

    submitBtnEl.disabled = true;
    submitBtnEl.textContent = 'Enregistrement...';
    try {
        if (state.editingHospitalId) {
            await apiCall(`/hospitals/${state.editingHospitalId}`, {
                method: 'PUT',
                body: JSON.stringify(payload),
            });
            showAlert('Hôpital mis à jour avec succès.', 'success');
        } else {
            await apiCall('/hospitals/', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            showAlert('Hôpital enregistré avec succès.', 'success');
        }
        resetForm();
        await loadHospitals();
    } catch (error) {
        console.error('Erreur lors de l’enregistrement:', error);
        showAlert(error.message || 'Échec de l’enregistrement de l’hôpital.', 'error');
    } finally {
        submitBtnEl.disabled = false;
        submitBtnEl.textContent = state.editingHospitalId ? 'Mettre à jour' : 'Enregistrer';
    }
}

function plotHospitalsOnMap() {
    if (!state.hospitalsMap || !state.hospitalsMarkersLayer || !window.L) {
        return;
    }
    state.hospitalsMarkersLayer.clearLayers();
    const bounds = [];
    state.hospitals.forEach(hospital => {
        const lat = Number(hospital.latitude);
        const lon = Number(hospital.longitude);
        if (Number.isNaN(lat) || Number.isNaN(lon)) {
            return;
        }
        const popupContent = `
            <div class="map-popup">
                <strong>${escapeHtml(hospital.nom)}</strong>
                <div>${escapeHtml(hospital.ville || '')}</div>
                <div class="muted">${escapeHtml(hospital.medecin_referent?.full_name || 'Médecin référent non défini')}</div>
            </div>
        `;
        const marker = L.circleMarker([lat, lon], {
            radius: 7,
            color: '#2a9d8f',
            fillColor: '#2a9d8f',
            fillOpacity: 0.85,
            weight: 1,
        });
        marker.bindPopup(popupContent);
        marker.addTo(state.hospitalsMarkersLayer);
        bounds.push([lat, lon]);
    });
    if (bounds.length) {
        state.hospitalsMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
    }
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

