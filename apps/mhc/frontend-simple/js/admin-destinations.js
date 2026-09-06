// Gestion des destinations (pays et villes)
let currentSelectedCountryId = null;
let countriesData = [];
let medecinConseilOptions = [];
let searchCountriesTerm = '';
let searchCitiesTerm = '';
let citiesListData = [];
const ROWS_PER_PAGE = 6;
let currentPageCountries = 0;
let currentPageCities = 0;

document.addEventListener('DOMContentLoaded', async () => {
    const authenticated = await requireAuth();
    if (!authenticated) {
        window.location.href = 'login.html';
        return;
    }

    // Vérifier que l'utilisateur est admin
    const userRole = localStorage.getItem('user_role');
    if (userRole !== 'admin') {
        alert('Accès réservé aux administrateurs');
        window.location.href = 'user-dashboard.html';
        return;
    }

    await loadMedecinConseilOptions();
    await loadDestinations();
});

async function loadMedecinConseilOptions() {
    try {
        const medReferents = await apiCall('/users?role=medecin_referent_mh&limit=500');
        let doctors = Array.isArray(medReferents) ? medReferents : [];
        if (!doctors.length) {
            const fallback = await apiCall('/users?role=doctor&limit=500');
            doctors = Array.isArray(fallback) ? fallback : [];
        }
        medecinConseilOptions = doctors;
    } catch (error) {
        console.error('Erreur lors du chargement des médecins-conseils:', error);
        medecinConseilOptions = [];
    }
    populateMedecinConseilSelect();
}

function populateMedecinConseilSelect(selectedId = '') {
    const select = document.getElementById('countryMedecinConseil');
    if (!select) return;
    select.innerHTML = '<option value="">-- Aucun médecin-conseil --</option>';
    medecinConseilOptions.forEach((doctor) => {
        const option = document.createElement('option');
        option.value = doctor.id;
        const phone = doctor.telephone ? ` — ${doctor.telephone}` : '';
        option.textContent = `${doctor.full_name || doctor.email || doctor.username}${phone}`;
        select.appendChild(option);
    });
    select.value = selectedId ? String(selectedId) : '';
}

function medecinConseilLabel(country) {
    const contact = country.medecin_conseil;
    if (contact && (contact.nom || contact.telephone)) {
        return contact.nom || contact.telephone;
    }
    return null;
}

async function loadDestinations() {
    const statusFilter = document.getElementById('statusFilter').value;
    const actifSeulement = statusFilter === 'true' ? true : (statusFilter === 'false' ? false : null);
    
    try {
        const params = {};
        if (actifSeulement !== null) {
            params.actif_seulement = actifSeulement;
        }
        
        const queryString = new URLSearchParams(params).toString();
        const url = `/destinations/admin/countries${queryString ? '?' + queryString : ''}`;
        
        console.log('🔍 Chargement des destinations, URL:', url);
        const response = await apiCall(url);
        console.log('📊 Réponse API brute:', response);
        
        // S'assurer que countriesData est un tableau
        if (Array.isArray(response)) {
            countriesData = response;
        } else if (response && Array.isArray(response.data)) {
            countriesData = response.data;
        } else {
            console.error('❌ Format de réponse inattendu:', response);
            countriesData = [];
        }
        
        console.log('📊 Pays chargés (après traitement):', countriesData.length, countriesData);
        
        // Vérifier le conteneur avant le rendu
        const containerCheck = document.getElementById('countriesList');
        console.log('🔍 Conteneur countriesList trouvé:', !!containerCheck);
        
        if (containerCheck) {
            renderCountries();
            bindDestinationsSearch();
        } else {
            console.error('❌ Le conteneur countriesList n\'existe pas dans le DOM');
            showAlert('Erreur: conteneur non trouvé', 'error');
        }
        
        if (currentSelectedCountryId) {
            loadCitiesForCountry(currentSelectedCountryId);
        }
    } catch (error) {
        console.error('Erreur lors du chargement des destinations:', error);
        showAlert('Impossible de charger les destinations', 'error');
    }
}

function bindDestinationsSearch() {
    const searchCountriesEl = document.getElementById('searchCountries');
    if (searchCountriesEl) {
        searchCountriesEl.addEventListener('input', () => {
            searchCountriesTerm = (searchCountriesEl.value || '').trim().toLowerCase();
            renderCountries();
        });
    }
    const searchCitiesEl = document.getElementById('searchCities');
    if (searchCitiesEl) {
        searchCitiesEl.addEventListener('input', () => {
            searchCitiesTerm = (searchCitiesEl.value || '').trim().toLowerCase();
            renderCitiesList();
        });
    }
}

function renderCountries() {
    const container = document.getElementById('countriesList');
    
    if (!container) {
        console.error('❌ Conteneur countriesList non trouvé');
        return;
    }
    
    container.classList.remove('loading');
    
    if (!countriesData || countriesData.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>Aucun pays trouvé</p></div>';
        return;
    }
    
    const filtered = searchCountriesTerm
        ? countriesData.filter((c) => {
            const nom = (c.nom || '').toLowerCase();
            const code = (c.code || '').toLowerCase();
            return nom.includes(searchCountriesTerm) || code.includes(searchCountriesTerm);
        })
        : countriesData;
    
    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>Aucun pays ne correspond à la recherche.</p></div>';
        document.getElementById('countriesPagination') && (document.getElementById('countriesPagination').innerHTML = '');
        return;
    }
    
    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    currentPageCountries = Math.min(currentPageCountries, totalPages - 1);
    const start = currentPageCountries * ROWS_PER_PAGE;
    const pageData = filtered.slice(start, start + ROWS_PER_PAGE);
    
    try {
        let htmlContent = '';
        pageData.forEach((country, index) => {
            try {
                const countryId = country.id;
                const countryName = escapeHtml(country.nom || 'Sans nom');
                const countryNameAttr = escapeForAttribute(country.nom || 'Sans nom');
                const countryCode = escapeHtml(country.code || 'N/A');
                const isInactive = !country.est_actif ? 'inactive' : '';
                
                const countryHtml = `
                <div class="country-item ${isInactive}" 
                     onclick="selectCountry(${countryId}, '${countryNameAttr}')"
                     style="cursor: pointer;">
                    <div class="country-info">
                        <div class="country-name">${countryName}</div>
                        <div class="country-code">Code: ${countryCode}${medecinConseilLabel(country) ? ` · Médecin-conseil: ${escapeHtml(medecinConseilLabel(country))}` : ''}</div>
                    </div>
                    <div class="item-actions" onclick="event.stopPropagation()">
                        <button class="btn-icon edit" onclick="editCountry(${countryId})" title="Modifier">
                            ✏️
                        </button>
                        <button class="btn-icon delete" onclick="deleteCountry(${countryId}, '${countryNameAttr}')" title="Supprimer">
                            🗑️
                        </button>
                    </div>
                </div>
                `;
                htmlContent += countryHtml;
            } catch (countryError) {
                console.error(`❌ Erreur lors du traitement du pays ${index}:`, countryError, country);
            }
        });
        
        console.log('📝 HTML généré, longueur:', htmlContent.length);
        console.log('📝 Aperçu HTML (premiers 200 caractères):', htmlContent.substring(0, 200));
        
        container.innerHTML = htmlContent;
        
        // Pagination pour les pays
        const pagEl = document.getElementById('countriesPagination');
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
                            <button type="button" class="btn btn-outline btn-sm" id="countriesPrev" ${currentPageCountries <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                            <span>Page ${currentPageCountries + 1} / ${totalPages}</span>
                            <button type="button" class="btn btn-outline btn-sm" id="countriesNext" ${currentPageCountries >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                        </div>
                    </div>
                `;
                document.getElementById('countriesPrev')?.addEventListener('click', () => { currentPageCountries--; renderCountries(); });
                document.getElementById('countriesNext')?.addEventListener('click', () => { currentPageCountries++; renderCountries(); });
            }
        }
        
        // S'assurer que la classe loading est retirée
        container.classList.remove('loading');
        
        // Vérifier que le contenu a été inséré
        const insertedItems = container.querySelectorAll('.country-item');
        console.log('✅ Pays rendus avec succès, éléments dans le DOM:', insertedItems.length);
        console.log('📦 Conteneur après rendu:', container.className, container.innerHTML.length, 'caractères');
        
        if (insertedItems.length === 0) {
            console.error('❌ Aucun élément .country-item trouvé dans le DOM après insertion');
            console.error('❌ Contenu HTML inséré:', container.innerHTML.substring(0, 500));
            container.innerHTML = '<div class="empty-state"><p>Erreur: les pays n\'ont pas pu être affichés. Vérifiez la console pour plus de détails.</p></div>';
        } else {
            console.log('✅ Rendu réussi!', insertedItems.length, 'pays affichés');
        }
    } catch (error) {
        console.error('❌ Erreur lors du rendu des pays:', error);
        console.error('❌ Stack trace:', error.stack);
        container.innerHTML = '<div class="empty-state"><p>Erreur lors de l\'affichage des pays: ' + error.message + '</p></div>';
    }
}

function selectCountry(countryId, countryName) {
    currentSelectedCountryId = countryId;
    searchCitiesTerm = '';
    currentPageCities = 0;
    const searchCitiesEl = document.getElementById('searchCities');
    if (searchCitiesEl) {
        searchCitiesEl.value = '';
        searchCitiesEl.style.display = 'block';
    }
    document.getElementById('selectedCountryInfo').style.display = 'block';
    document.getElementById('selectedCountryName').textContent = `Pays sélectionné: ${countryName}`;
    document.getElementById('addCityBtn').disabled = false;
    loadCitiesForCountry(countryId);
}

async function loadCitiesForCountry(countryId) {
    const container = document.getElementById('citiesList');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        const country = countriesData.find(c => c.id === countryId);
        if (!country || !country.villes) {
            citiesListData = [];
            container.innerHTML = '<div class="empty-state"><p>Aucune ville trouvée</p></div>';
            return;
        }
        
        citiesListData = country.villes;
        if (citiesListData.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>Aucune ville pour ce pays</p></div>';
            return;
        }
        
        renderCitiesList();
    } catch (error) {
        console.error('Erreur lors du chargement des villes:', error);
        citiesListData = [];
        container.innerHTML = '<div class="empty-state"><p>Erreur lors du chargement</p></div>';
    }
}

function renderCitiesList() {
    const container = document.getElementById('citiesList');
    if (!container) {
        return;
    }
    if (!citiesListData.length) {
        container.innerHTML = '<div class="empty-state"><p>Aucune ville pour ce pays</p></div>';
        document.getElementById('citiesPagination') && (document.getElementById('citiesPagination').innerHTML = '');
        return;
    }
    const filtered = searchCitiesTerm
        ? citiesListData.filter((v) => (v.nom || '').toLowerCase().includes(searchCitiesTerm))
        : citiesListData;
    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>Aucune ville ne correspond à la recherche.</p></div>';
        document.getElementById('citiesPagination') && (document.getElementById('citiesPagination').innerHTML = '');
        return;
    }
    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    currentPageCities = Math.min(currentPageCities, totalPages - 1);
    const start = currentPageCities * ROWS_PER_PAGE;
    const pageData = filtered.slice(start, start + ROWS_PER_PAGE);
    container.innerHTML = pageData.map(ville => `
        <div class="city-item ${!ville.est_actif ? 'inactive' : ''}">
            <div class="city-info">
                <div class="city-name">${escapeHtml(ville.nom)}</div>
            </div>
            <div class="item-actions">
                <button class="btn-icon edit" onclick="editCity(${ville.id})" title="Modifier">
                    ✏️
                </button>
                <button class="btn-icon delete" onclick="deleteCity(${ville.id}, '${(ville.nom || '').replace(/'/g, "\\'")}')" title="Supprimer">
                    🗑️
                </button>
            </div>
        </div>
    `).join('');
    const pagEl = document.getElementById('citiesPagination');
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
                        <button type="button" class="btn btn-outline btn-sm" id="citiesPrev" ${currentPageCities <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageCities + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="citiesNext" ${currentPageCities >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('citiesPrev')?.addEventListener('click', () => { currentPageCities--; renderCitiesList(); });
            document.getElementById('citiesNext')?.addEventListener('click', () => { currentPageCities++; renderCitiesList(); });
        }
    }
}

function showCountryModal(countryId = null) {
    const modal = document.getElementById('countryModal');
    const form = document.getElementById('countryForm');
    const title = document.getElementById('countryModalTitle');
    
    if (countryId) {
        title.textContent = 'Modifier un pays';
        const country = countriesData.find(c => c.id === countryId);
        if (country) {
            document.getElementById('countryId').value = country.id;
            document.getElementById('countryCode').value = country.code;
            document.getElementById('countryName').value = country.nom;
            document.getElementById('countryOrder').value = country.ordre_affichage || 0;
            document.getElementById('countryActive').checked = country.est_actif;
            document.getElementById('countryNotes').value = country.notes || '';
            document.getElementById('countryCode').disabled = true; // Ne pas modifier le code
            populateMedecinConseilSelect(country.medecin_conseil_id || country.medecin_conseil?.id || '');
        }
    } else {
        title.textContent = 'Ajouter un pays';
        form.reset();
        document.getElementById('countryId').value = '';
        document.getElementById('countryCode').disabled = false;
        document.getElementById('countryActive').checked = true;
        document.getElementById('countryOrder').value = 0;
        populateMedecinConseilSelect('');
    }
    
    modal.style.display = 'flex';
}

function closeCountryModal() {
    document.getElementById('countryModal').style.display = 'none';
    document.getElementById('countryForm').reset();
}

async function saveCountry(event) {
    event.preventDefault();
    
    const countryId = document.getElementById('countryId').value;
    const code = document.getElementById('countryCode').value.trim().toUpperCase();
    const nom = document.getElementById('countryName').value.trim();
    
    // Validation côté client
    if (!code || !nom) {
        showAlert('Le code et le nom sont requis', 'error');
        return;
    }
    
    // Vérifier si le code existe déjà (uniquement pour la création)
    if (!countryId) {
        const existingCountry = countriesData.find(c => c.code.toUpperCase() === code);
        if (existingCountry) {
            showAlert(`Un pays avec le code '${code}' existe déjà (${existingCountry.nom})`, 'error');
            return;
        }
    }
    
    const data = {
        code: code,
        nom: nom,
        ordre_affichage: parseInt(document.getElementById('countryOrder').value) || 0,
        est_actif: document.getElementById('countryActive').checked,
        notes: document.getElementById('countryNotes').value.trim() || null,
        medecin_conseil_id: document.getElementById('countryMedecinConseil').value
            ? Number(document.getElementById('countryMedecinConseil').value)
            : null,
    };
    
    let createdCountry = null;
    
    try {
        if (countryId) {
            // Mise à jour
            await apiCall(`/destinations/admin/countries/${countryId}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            showAlert('Pays mis à jour avec succès', 'success');
        } else {
            // Création
            createdCountry = await apiCall('/destinations/admin/countries', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            console.log('✅ Pays créé:', createdCountry);
            showAlert('Pays créé avec succès', 'success');
        }
        
        closeCountryModal();
        // Réinitialiser le filtre pour afficher tous les pays après création
        document.getElementById('statusFilter').value = '';
        // Attendre un peu pour s'assurer que la base de données est à jour
        await new Promise(resolve => setTimeout(resolve, 300));
        await loadDestinations();
        
        // Si c'était une création, sélectionner automatiquement le nouveau pays
        if (createdCountry && createdCountry.id) {
            setTimeout(() => {
                selectCountry(createdCountry.id, createdCountry.nom);
            }, 500);
        }
    } catch (error) {
        console.error('Erreur lors de la sauvegarde:', error);
        // Extraire le message d'erreur détaillé depuis la réponse API
        let errorMessage = error.message || 'Erreur lors de la sauvegarde';
        if (error.payload && error.payload.detail) {
            errorMessage = error.payload.detail;
        }
        showAlert(errorMessage, 'error');
    }
}

function editCountry(countryId) {
    showCountryModal(countryId);
}

async function deleteCountry(countryId, countryName) {
    if (!confirm(`Êtes-vous sûr de vouloir supprimer le pays "${countryName}" ?\n\nCette action supprimera également toutes les villes associées.`)) {
        return;
    }
    
    try {
        await apiCall(`/destinations/admin/countries/${countryId}`, {
            method: 'DELETE'
        });
        showAlert('Pays supprimé avec succès', 'success');
        
        if (currentSelectedCountryId === countryId) {
            currentSelectedCountryId = null;
            document.getElementById('selectedCountryInfo').style.display = 'none';
            document.getElementById('addCityBtn').disabled = true;
            document.getElementById('citiesList').innerHTML = '<div class="empty-state"><p>Sélectionnez un pays pour voir ses villes</p></div>';
        }
        
        await loadDestinations();
    } catch (error) {
        console.error('Erreur lors de la suppression:', error);
        showAlert(error.message || 'Erreur lors de la suppression', 'error');
    }
}

function showCityModal(cityId = null) {
    if (!currentSelectedCountryId) {
        showAlert('Veuillez d\'abord sélectionner un pays', 'error');
        return;
    }
    
    const modal = document.getElementById('cityModal');
    const form = document.getElementById('cityForm');
    const title = document.getElementById('cityModalTitle');
    
    if (cityId) {
        title.textContent = 'Modifier une ville';
        const country = countriesData.find(c => c.id === currentSelectedCountryId);
        const city = country?.villes?.find(v => v.id === cityId);
        if (city) {
            document.getElementById('cityId').value = city.id;
            document.getElementById('cityName').value = city.nom;
            document.getElementById('cityOrder').value = city.ordre_affichage || 0;
            document.getElementById('cityActive').checked = city.est_actif;
            document.getElementById('cityNotes').value = city.notes || '';
        }
    } else {
        title.textContent = 'Ajouter une ville';
        form.reset();
        document.getElementById('cityId').value = '';
        document.getElementById('cityActive').checked = true;
        document.getElementById('cityOrder').value = 0;
    }
    
    document.getElementById('cityCountryId').value = currentSelectedCountryId;
    modal.style.display = 'flex';
}

function closeCityModal() {
    document.getElementById('cityModal').style.display = 'none';
    document.getElementById('cityForm').reset();
}

async function saveCity(event) {
    event.preventDefault();
    
    const cityId = document.getElementById('cityId').value;
    const paysId = parseInt(document.getElementById('cityCountryId').value);
    const data = {
        nom: document.getElementById('cityName').value.trim(),
        ordre_affichage: parseInt(document.getElementById('cityOrder').value) || 0,
        est_actif: document.getElementById('cityActive').checked,
        notes: document.getElementById('cityNotes').value.trim() || null,
    };
    
    try {
        if (cityId) {
            // Mise à jour
            await apiCall(`/destinations/admin/cities/${cityId}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            showAlert('Ville mise à jour avec succès', 'success');
        } else {
            // Création
            const createData = {
                ...data,
                pays_id: paysId
            };
            await apiCall('/destinations/admin/cities', {
                method: 'POST',
                body: JSON.stringify(createData)
            });
            showAlert('Ville créée avec succès', 'success');
        }
        
        closeCityModal();
        await loadDestinations();
    } catch (error) {
        console.error('Erreur lors de la sauvegarde:', error);
        showAlert(error.message || 'Erreur lors de la sauvegarde', 'error');
    }
}

function editCity(cityId) {
    showCityModal(cityId);
}

async function deleteCity(cityId, cityName) {
    if (!confirm(`Êtes-vous sûr de vouloir supprimer la ville "${cityName}" ?`)) {
        return;
    }
    
    try {
        await apiCall(`/destinations/admin/cities/${cityId}`, {
            method: 'DELETE'
        });
        showAlert('Ville supprimée avec succès', 'success');
        await loadDestinations();
    } catch (error) {
        console.error('Erreur lors de la suppression:', error);
        showAlert(error.message || 'Erreur lors de la suppression', 'error');
    }
}

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function escapeForAttribute(text) {
    if (text === null || text === undefined) {
        return '';
    }
    return String(text)
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r');
}

// showAlert est déjà défini dans api.js

