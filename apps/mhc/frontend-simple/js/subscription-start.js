// Script pour la page de démarrage de souscription

let currentStep = 1;
let projectData = null;
let selectedProduct = null;
let destinationCountries = [];

function normalizeCountryName(value) {
    return String(value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\s+/g, '')
        .trim()
        .toLowerCase();
}

function normalizeCountryCode(value) {
    return String(value || '').trim().toUpperCase();
}

function getResidenceCountry() {
    return (localStorage.getItem('user_pays_residence') || '').trim();
}

function hasResidenceCountry() {
    return !!getResidenceCountry();
}

function isResidenceDestinationConflict(country) {
    const residenceCountry = getResidenceCountry();
    if (!residenceCountry || !country) return false;
    const normalizedResidenceCode = normalizeCountryCode(residenceCountry);
    const normalizedCountryCode = normalizeCountryCode(country.code);
    if (normalizedResidenceCode && normalizedCountryCode && normalizedResidenceCode === normalizedCountryCode) {
        return true;
    }
    return normalizeCountryName(residenceCountry) === normalizeCountryName(country.nom);
}

// Définir showStep avant DOMContentLoaded pour qu'elle soit accessible depuis le HTML
function showStep(stepNumber) {
    console.log('🔄 showStep appelé avec:', stepNumber, 'currentStep:', currentStep);
    
    // Permettre de revenir en arrière à n'importe quelle étape déjà visitée
    // Mettre à jour currentStep pour permettre la navigation
    if (stepNumber > currentStep) {
        currentStep = stepNumber;
    } else {
        // On permet de revenir en arrière
        currentStep = stepNumber;
    }
    
    console.log('📊 currentStep mis à jour à:', currentStep);
    
    // Masquer toutes les étapes
    const allSteps = document.querySelectorAll('.subscription-step');
    console.log('📋 Nombre d\'étapes trouvées:', allSteps.length);
    allSteps.forEach(step => {
        step.style.display = 'none';
        step.classList.remove('active');
    });
    
    // Afficher l'étape courante
    const currentStepElement = document.getElementById(`step-${stepNumber}`);
    if (currentStepElement) {
        currentStepElement.style.display = 'block';
        currentStepElement.classList.add('active');
        console.log('✅ Étape', stepNumber, 'affichée avec succès');
    } else {
        console.error('❌ Élément step-', stepNumber, 'non trouvé dans le DOM');
        console.error('❌ Éléments disponibles:', Array.from(document.querySelectorAll('.subscription-step')).map(s => s.id));
    }
    
    // Mettre à jour les indicateurs
    const indicators = document.querySelectorAll('.step-indicator .step');
    console.log('📊 Nombre d\'indicateurs:', indicators.length);
    indicators.forEach((step, index) => {
        const stepNum = index + 1;
        if (stepNum < stepNumber) {
            step.classList.add('completed');
            step.classList.remove('active');
        } else if (stepNum === stepNumber) {
            step.classList.add('active');
            step.classList.remove('completed');
        } else {
            step.classList.remove('active', 'completed');
        }
    });
    
    console.log('✅ showStep terminé pour l\'étape', stepNumber);
}

// Exposer showStep globalement immédiatement
window.showStep = showStep;

function getSafeAccessToken() {
    return window.MobilityAuth?.getAccessToken
        ? window.MobilityAuth.getAccessToken()
        : localStorage.getItem('access_token');
}

document.addEventListener('DOMContentLoaded', async function() {
    await checkAuthStatus();

    setupProjectForm();
    setupStepNavigation();
    
    // Vérifier si un product_id est passé en paramètre
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('product_id');
    if (productId) {
        // Note: On ne peut pas sauter l'étape 1 car on a besoin des infos du voyage
        // Mais on peut pré-remplir certaines données si nécessaire
    }
});

async function checkAuthStatus() {
    const token = getSafeAccessToken();
    if (!token) {
        // Rediriger vers la page de connexion
        if (confirm('Vous devez être connecté pour souscrire. Voulez-vous vous connecter ?')) {
            window.location.href = 'login.html?redirect=subscription-start.html';
        } else {
            window.location.href = 'index.html';
        }
        return;
    }
    
    // Vérifier que le token est valide
    try {
        await validateAuth();
    } catch (error) {
        window.location.href = 'login.html?redirect=subscription-start.html';
    }
}

function setupProjectForm() {
    const form = document.getElementById('project-form');
    const departureInput = document.getElementById('project-departure');
    const returnInput = document.getElementById('project-return');
    const birthdateInput = document.getElementById('traveler-birthdate');
    const hasMinorsRadios = document.querySelectorAll('input[name="has-minors"]');
    const minorsDetails = document.getElementById('minors-details');
    const destinationSelect = document.getElementById('destination-country');
    const destinationCitySelect = document.getElementById('destination-city');
    
    // Définir la date minimale à aujourd'hui pour le départ
    const today = new Date().toISOString().split('T')[0];
    departureInput.min = today;
    
    // Définir la date maximale pour la date de naissance (18 ans minimum)
    const maxBirthdate = new Date();
    maxBirthdate.setFullYear(maxBirthdate.getFullYear() - 18);
    birthdateInput.max = maxBirthdate.toISOString().split('T')[0];
    
    // Charger les informations utilisateur si "Pour moi"
    loadUserInfo();
    
    loadDestinationCountries(destinationSelect, destinationCitySelect);
    if (!hasResidenceCountry()) {
        destinationSelect.disabled = true;
        if (destinationCitySelect) {
            destinationCitySelect.disabled = true;
            destinationCitySelect.innerHTML = '<option value="">Renseignez d\'abord votre pays de résidence</option>';
        }
        alert('Veuillez d\'abord renseigner votre pays de résidence dans votre profil avant de souscrire.');
    }
    destinationSelect?.addEventListener('change', function() {
        const selectedCountry = destinationCountries.find((country) => country.nom === this.value);
        if (isResidenceDestinationConflict(selectedCountry)) {
            this.value = '';
            if (destinationCitySelect) {
                destinationCitySelect.value = '';
            }
            populateDestinationCities(destinationCitySelect, null);
            alert('Le pays de destination doit être différent de votre pays de résidence.');
            return;
        }
        const selectedCountryId = this.options[this.selectedIndex]?.dataset?.countryId
            ? parseInt(this.options[this.selectedIndex].dataset.countryId, 10)
            : null;
        populateDestinationCities(destinationCitySelect, selectedCountryId);
    });
    
    // Gérer l'affichage des détails enfants mineurs
    hasMinorsRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'yes') {
                minorsDetails.style.display = 'block';
                document.getElementById('minors-count').required = true;
            } else {
                minorsDetails.style.display = 'none';
                document.getElementById('minors-count').required = false;
            }
        });
    });
    
    
    // Calcul automatique du nombre de jours
    departureInput.addEventListener('change', calculateDays);
    returnInput.addEventListener('change', calculateDays);
    
    let isSubmitting = false;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Empêcher les soumissions multiples
        if (isSubmitting) {
            console.warn('⚠️ Soumission déjà en cours, ignorée');
            return;
        }
        
        isSubmitting = true;
        const submitButton = form.querySelector('button[type="submit"]');
        const originalButtonText = submitButton ? submitButton.textContent : '';
        
        try {
            // Désactiver le bouton pendant le traitement
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Traitement en cours...';
            }
            
            const departure = new Date(document.getElementById('project-departure').value);
        const returnDate = document.getElementById('project-return').value 
            ? new Date(document.getElementById('project-return').value) 
            : null;
        
        if (returnDate && returnDate <= departure) {
            alert('La date de retour doit être postérieure à la date de départ');
            return;
        }
        
        // Calculer le nombre de jours
        const daysCount = calculateDays();
        if (daysCount === 0 && returnDate) {
            alert('Veuillez vérifier les dates de départ et de retour');
            return;
        }
        
        // Récupérer le pays de destination et son ID (nécessaire pour le calcul du tarif)
        const destSelect = document.getElementById('destination-country');
        const destinationCountry = destSelect?.value?.trim();
        const selectedOption = destSelect?.options[destSelect?.selectedIndex];
        const destination_country_id = selectedOption?.dataset?.countryId
            ? parseInt(selectedOption.dataset.countryId, 10)
            : null;
        const destination_country_code = selectedOption?.dataset?.countryCode || '';
        const destinationCity = destinationCitySelect?.value?.trim();
        const selectedCountry = destinationCountries.find((country) =>
            String(country.id) === String(destination_country_id)
                || country.nom === destinationCountry
                || country.code === destination_country_code
        );
        if (!hasResidenceCountry()) {
            alert('Veuillez d\'abord renseigner votre pays de résidence dans votre profil avant de souscrire.');
            return;
        }
        if (!destinationCountry) {
            alert('Veuillez choisir le pays de destination');
            return;
        }
        if (isResidenceDestinationConflict(selectedCountry)) {
            alert('Le pays de destination doit être différent de votre pays de résidence');
            return;
        }
        if (!destinationCity) {
            alert('Veuillez choisir la ville de destination');
            return;
        }
        
        // Compter les participants (voyageur principal + enfants mineurs si applicable)
        const hasMinors = document.querySelector('input[name="has-minors"]:checked').value === 'yes';
        const minorsCount = hasMinors ? parseInt(document.getElementById('minors-count').value) || 0 : 0;
        const totalParticipants = 1 + minorsCount; // 1 voyageur principal + enfants
        
        // Préparer les données du projet (souscription pour soi-même uniquement)
        const travelerInfo = {
            lastname: document.getElementById('traveler-lastname').value,
            firstname: document.getElementById('traveler-firstname').value,
            birthdate: document.getElementById('traveler-birthdate').value,
            isThirdParty: false
        };
        
        // Créer un titre automatique
        const title = `Voyage vers ${destinationCity}, ${destinationCountry}`;
        
        // Description avec toutes les informations supplémentaires
        const description = JSON.stringify({
            destination_country: destinationCountry,
            destination_city: destinationCity,
            has_minors: hasMinors,
            minors_count: minorsCount,
            days_count: daysCount,
            traveler: travelerInfo
        });
        
        projectData = {
            titre: title,
            destination: destinationCity,
            destination_country_id: destination_country_id,
            date_depart: departure.toISOString(),
            date_retour: returnDate ? returnDate.toISOString() : null,
            nombre_participants: totalParticipants,
            description: description,
            user_id: parseInt(localStorage.getItem('user_id')),
            // Stocker les informations supplémentaires dans notes
            notes: [
                ...(getResidenceCountry() ? [`Pays de résidence: ${getResidenceCountry()}`] : []),
                `Pays de destination: ${destinationCountry}`,
                `Ville de destination: ${destinationCity}`,
                `Has minors: ${hasMinors ? 'Oui' : 'Non'}`,
                `Minors count: ${minorsCount}`,
                `Traveler info: ${JSON.stringify(travelerInfo)}`
            ].join('\n')
        };
        
        // Créer le projet de voyage
        try {
            console.log('📤 Création du projet de voyage...', projectData);
            const project = await apiCall('/voyages', {
                method: 'POST',
                body: JSON.stringify(projectData)
            });
            
            console.log('✅ Projet créé avec succès:', project);
            
            if (!project || !project.id) {
                throw new Error('Le projet a été créé mais aucun ID n\'a été retourné');
            }
            
            projectData.id = project.id;
            // Stocker aussi les infos voyageur pour les étapes suivantes
            projectData.travelerInfo = travelerInfo;
            projectData.hasMinors = hasMinors;
            projectData.minorsCount = minorsCount;
            projectData.daysCount = daysCount;
            projectData.destination_country_id = project.destination_country_id ?? destination_country_id;
            projectData.destination_country_name = project.destination_country_name ?? destinationCountry;
            
            console.log('📝 Données du projet mises à jour:', projectData);
            console.log('🔄 Passage à l\'étape 2...');
            
            // Vérifier que l'élément step-2 existe avant de passer à l'étape 2
            const step2Element = document.getElementById('step-2');
            if (!step2Element) {
                console.error('❌ L\'élément step-2 n\'existe pas dans le DOM');
                throw new Error('Impossible de trouver l\'étape 2 dans la page');
            }
            
            // Passer à l'étape 2 (sélection du produit)
            showStep(2);
            
            // Vérifier que l'étape 2 est bien affichée
            const step2Display = window.getComputedStyle(step2Element).display;
            if (step2Display === 'none') {
                console.error('❌ L\'étape 2 n\'est pas affichée après showStep(2)');
                // Forcer l'affichage
                step2Element.style.display = 'block';
                step2Element.classList.add('active');
            }
            
            console.log('📦 Chargement des produits...');
            await loadProductsForSelection();
            
            console.log('✅ Étape 2 chargée avec succès');
        } catch (error) {
            console.error('❌ Erreur lors de la création du projet:', error);
            console.error('❌ Détails de l\'erreur:', {
                message: error.message,
                status: error.status,
                statusText: error.statusText,
                detail: error.detail,
                payload: error.payload,
                stack: error.stack
            });
            alert('Erreur lors de la création du projet: ' + (error.message || error.detail || 'Erreur inconnue'));
        } finally {
            // Réactiver le bouton
            isSubmitting = false;
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = originalButtonText;
            }
        }
    });
}

async function loadDestinationCountries(selectEl, citySelectEl) {
    if (!selectEl) return;
    try {
        const countries = await apiCall('/destinations/countries?actif_seulement=true');
        destinationCountries = Array.isArray(countries) ? countries : [];
        selectEl.innerHTML = '<option value="">Choisir un pays...</option>';
        const residenceCountry = getResidenceCountry();
        const normalizedResidence = normalizeCountryName(residenceCountry);
        destinationCountries.forEach((country) => {
            const option = document.createElement('option');
            option.value = country.nom;
            option.textContent = country.nom;
            option.dataset.countryId = country.id;
            option.dataset.countryCode = country.code || '';
            if (
                normalizedResidence &&
                (
                    normalizeCountryName(country.nom) === normalizedResidence
                    || normalizeCountryCode(country.code) === normalizeCountryCode(residenceCountry)
                )
            ) {
                option.disabled = true;
                option.textContent = `${country.nom} (pays de résidence)`;
            }
            selectEl.appendChild(option);
        });
        populateDestinationCities(citySelectEl, null);
        if (!hasResidenceCountry()) {
            selectEl.disabled = true;
            return;
        }
    } catch (error) {
        console.error('Erreur chargement des pays:', error);
        selectEl.innerHTML = '<option value="">Erreur lors du chargement</option>';
        if (citySelectEl) {
            citySelectEl.disabled = true;
            citySelectEl.innerHTML = '<option value="">Erreur lors du chargement</option>';
        }
    }
}

function populateDestinationCities(selectEl, countryId) {
    if (!selectEl) return;

    if (!countryId) {
        selectEl.disabled = true;
        selectEl.innerHTML = '<option value="">Choisir d\'abord un pays...</option>';
        return;
    }

    const country = destinationCountries.find((item) => item.id === countryId);
    const cities = Array.isArray(country?.villes) ? country.villes : [];

    selectEl.innerHTML = '<option value="">Choisir une ville...</option>';
    cities.forEach((city) => {
        const option = document.createElement('option');
        option.value = city.nom;
        option.textContent = city.nom;
        selectEl.appendChild(option);
    });

    if (cities.length === 0) {
        selectEl.disabled = true;
        selectEl.innerHTML = '<option value="">Aucune ville disponible pour ce pays</option>';
        return;
    }

    selectEl.disabled = false;
}

function loadUserInfo() {
    // Récupérer les informations utilisateur depuis localStorage ou API
    const userName = localStorage.getItem('user_name') || '';
    const userEmail = localStorage.getItem('user_email') || '';
    
    // Si on a un nom complet, essayer de le diviser
    if (userName) {
        const nameParts = userName.split(' ');
        if (nameParts.length >= 2) {
            document.getElementById('traveler-lastname').value = nameParts[nameParts.length - 1] || '';
            document.getElementById('traveler-firstname').value = nameParts.slice(0, -1).join(' ') || '';
        } else {
            document.getElementById('traveler-firstname').value = userName;
        }
    }
    
    // Essayer de récupérer la date de naissance depuis l'API si disponible
    // Pour l'instant, on laisse vide car elle n'est pas stockée par défaut
}

function calculateDays() {
    const departureInput = document.getElementById('project-departure');
    const returnInput = document.getElementById('project-return');
    const daysDisplay = document.getElementById('days-count');
    
    if (!departureInput.value) {
        daysDisplay.textContent = '--';
        return 0;
    }
    
    const departure = new Date(departureInput.value);
    
    if (!returnInput.value) {
        daysDisplay.textContent = 'Date de retour non spécifiée';
        return 0;
    }
    
    const returnDate = new Date(returnInput.value);
    
    if (returnDate <= departure) {
        daysDisplay.textContent = 'Date invalide';
        return 0;
    }
    
    // Calculer la différence en jours
    const diffTime = returnDate - departure;
    const diffDays = Math.max(1, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
    
    daysDisplay.textContent = `${diffDays} jour${diffDays > 1 ? 's' : ''}`;
    daysDisplay.className = 'days-display days-calculated';
    
    return diffDays;
}

async function loadProductsForSelection(preselectedId = null) {
    console.log('📦 loadProductsForSelection appelé');
    const container = document.getElementById('products-selection');
    
    if (!container) {
        console.error('❌ Container products-selection non trouvé');
        return;
    }
    
    try {
        console.log('📤 Chargement des produits depuis l\'API...');
        const productQs = new URLSearchParams({ est_actif: 'true', filter_by_voyage_assureur: 'true' });
        const resCountry = getResidenceCountry();
        if (resCountry) productQs.set('residence_country_name', resCountry);
        if (projectData?.destination_country_id != null) {
            productQs.set('destination_country_id', String(projectData.destination_country_id));
        }
        if (projectData?.destination_country_name) {
            productQs.set('destination_country_name', String(projectData.destination_country_name));
        }
        const products = await apiCall(`/products?${productQs.toString()}`);
        console.log('✅ Produits chargés:', products.length, 'produit(s)');
        
        if (products.length === 0) {
            container.innerHTML =
                '<p>Aucune offre pour ce voyage (assureurs partenaires / zone tarifaire). Modifiez la destination ou contactez Mobility Healthcare.</p>';
            console.warn('⚠️ Aucun produit pour ce parcours résidence-destination');
            return;
        }

        // Caractéristiques pour tarif selon durée, zone et âge (projet étape 1)
        let age = null;
        let duree_jours = projectData?.daysCount ?? null;
        if (duree_jours != null && duree_jours < 1) {
            duree_jours = 1;
        }
        const destination_country_id = projectData?.destination_country_id ?? null;
        const destination_country_name = projectData?.destination_country_name ?? null;
        if (projectData?.travelerInfo?.birthdate) {
            const birth = new Date(projectData.travelerInfo.birthdate);
            const today = new Date();
            age = Math.floor((today - birth) / (365.25 * 24 * 60 * 60 * 1000));
        }
        const quoteParams = { age, destination_country_id, duree_jours };
        if (destination_country_name) {
            quoteParams.destination_country_name = destination_country_name;
        }
        const paramsStr = new URLSearchParams(
            Object.fromEntries(
                Object.entries(quoteParams).filter(([, v]) => v != null && v !== '')
            )
        ).toString();
        const quotePromises = products.map((p) =>
            apiCall(`/products/${p.id}/quote${paramsStr ? `?${paramsStr}` : ''}`).then((q) => ({ productId: p.id, quote: q })).catch(() => ({ productId: p.id, quote: null }))
        );
        const quotes = await Promise.all(quotePromises);
        const quoteByProductId = {};
        quotes.forEach(({ productId, quote }) => { quoteByProductId[productId] = quote; });
        
        let html = '<div class="products-selection-grid">';
        products.forEach(product => {
            const quote = quoteByProductId[product.id];
            const prix = quote ? quote.prix : product.cout;
            const fromTarif = quote ? quote.from_tarif : false;
            const dureeValiditeJours = product.duree_validite_jours;
            const dureeLabel = fromTarif && quote && quote.duree_min_jours != null && quote.duree_max_jours != null
                ? `${quote.duree_min_jours} - ${quote.duree_max_jours} jours`
                : (dureeValiditeJours ? `${dureeValiditeJours} jours` : 'Durée flexible');
            const isSelected = preselectedId && product.id == preselectedId;
            html += `
                <div class="product-selection-card ${isSelected ? 'selected' : ''}" data-product-id="${product.id}">
                    <h4>${product.nom}</h4>
                    <div class="product-code">${product.code}</div>
                    <p class="product-description">${product.description || 'Protection complète'}</p>
                    <div class="product-price">${parseFloat(prix).toFixed(0)} ${product.currency || 'XAF'}${fromTarif ? ' <span class="product-price-badge">(selon profil)</span>' : ''}</div>
                    ${fromTarif ? '<p class="product-price-note text-muted small">Tarif appliqué selon l\'âge, la destination et la durée du voyage.</p>' : ''}
                    <div class="product-duration">${dureeLabel}</div>
                    <button class="btn btn-primary" onclick="selectProduct(${product.id})">Sélectionner</button>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
        
        // Si un produit est présélectionné, le sélectionner automatiquement
        if (preselectedId) {
            selectProduct(parseInt(preselectedId));
        }
    } catch (error) {
        container.innerHTML = `<div class="error-message">Erreur lors du chargement des produits: ${error.message}</div>`;
    }
}

async function selectProduct(productId) {
    try {
        const product = await apiCall(`/products/${productId}`);
        selectedProduct = product;
        
        // Mettre à jour l'affichage
        document.querySelectorAll('.product-selection-card').forEach(card => {
            card.classList.remove('selected');
            if (card.dataset.productId == productId) {
                card.classList.add('selected');
            }
        });
        
        // Créer la souscription (avec caractéristiques pour tarif selon durée/zone/âge)
        if (projectData && projectData.id) {
            let age = null;
            if (projectData.travelerInfo && projectData.travelerInfo.birthdate) {
                const birth = new Date(projectData.travelerInfo.birthdate);
                const today = new Date();
                age = Math.floor((today - birth) / (365.25 * 24 * 60 * 60 * 1000));
            }
            const subscription = await apiCall('/subscriptions/start', {
                method: 'POST',
                body: JSON.stringify({
                    produit_assurance_id: productId,
                    projet_voyage_id: projectData.id,
                    age: age,
                    duree_jours: projectData.daysCount ?? null,
                    destination_country_id: projectData.destination_country_id ?? null,
                    destination_country_name: projectData.destination_country_name ?? null,
                })
            });
            
            // Stocker l'ID de souscription pour les étapes suivantes
            localStorage.setItem('current_subscription_id', subscription.id);
            
            showStep(3);
        }
    } catch (error) {
        alert('Erreur lors de la sélection du produit: ' + (error.message || 'Erreur inconnue'));
    }
}

function setupStepNavigation() {
    // Navigation entre les étapes via les indicateurs
    document.querySelectorAll('.step-indicator .step').forEach(step => {
        step.addEventListener('click', function() {
            const stepNum = parseInt(this.dataset.step);
            // Permettre de revenir en arrière à n'importe quelle étape déjà visitée
            if (stepNum <= currentStep) {
                showStep(stepNum);
            }
        });
    });
}

async function validateAuth() {
    const token = getSafeAccessToken();
    if (!token) return false;
    
    try {
        const apiUrl = window.API_BASE_URL || 'https://api.srv1324425.hstgr.cloud/api/v1';
        const response = await fetch(`${apiUrl}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            return false;
        }
        
        const user = await response.json();
        localStorage.setItem('user_id', user.id);
        localStorage.setItem('user_role', user.role);
        localStorage.setItem('user_name', user.full_name || user.username);
        if (user.pays_residence) {
            localStorage.setItem('user_pays_residence', user.pays_residence);
        } else {
            localStorage.removeItem('user_pays_residence');
        }
        return user;
    } catch (error) {
        return false;
    }
}

// Exposer selectProduct globalement
window.selectProduct = selectProduct;
// showStep est déjà exposée au début du fichier

