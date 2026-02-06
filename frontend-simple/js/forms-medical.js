let questionnaireMode = 'long';

document.addEventListener('DOMContentLoaded', async () => {
    const authenticated = await requireAuth();
    if (!authenticated) {
        return;
    }

    // Vérifier si on arrive depuis une notification avec subscription_id dans l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const subscriptionIdFromUrl = urlParams.get('subscription_id');
    
    let draft = null;
    
    if (subscriptionIdFromUrl) {
        // Si on a un subscription_id dans l'URL, récupérer les informations de la souscription
        try {
            const subscription = await apiCall(`/subscriptions/${subscriptionIdFromUrl}`);
            if (subscription) {
                // Récupérer le projet (voyage) et le produit associés
                const voyage = subscription.voyage_id ? await apiCall(`/voyages/${subscription.voyage_id}`) : null;
                const produit = subscription.produit_assurance_id ? await apiCall(`/products/${subscription.produit_assurance_id}`) : null;
                
                if (voyage && produit) {
                    draft = {
                        projectId: voyage.id,
                        projectTitle: voyage.titre,
                        productId: produit.id,
                        productName: produit.nom,
                        assureur: produit.assureur || 'Mobility Health',
                        questionnaireType: 'long',
                        subscriptionId: subscription.id
                    };
                    // Sauvegarder dans sessionStorage pour la cohérence
                    sessionStorage.setItem('subscription_draft', JSON.stringify(draft));
                } else {
                    showMessage('Impossible de récupérer les informations de la souscription.', 'error');
                    setTimeout(() => window.location.href = 'user-dashboard.html', 1500);
                    return;
                }
            }
        } catch (error) {
            console.error('Erreur lors de la récupération de la souscription:', error);
            showMessage('Impossible de charger les informations de la souscription.', 'error');
            setTimeout(() => window.location.href = 'user-dashboard.html', 1500);
            return;
        }
    } else {
        // Comportement normal : récupérer depuis sessionStorage
        const draftRaw = sessionStorage.getItem('subscription_draft');
        if (!draftRaw) {
            showMessage('Veuillez sélectionner un voyage et un produit avant de remplir les formulaires.', 'error');
            setTimeout(() => window.location.href = 'project-wizard.html', 1500);
            return;
        }
        draft = JSON.parse(draftRaw);
    }

    questionnaireMode = 'long';
    populateSummary(draft);
    populateCheckboxes();
    setupSymptomOtherField();
    setupSurgeryDetailsField();
    setupYesNoConditionalFields();
    applyQuestionnaireMode(questionnaireMode);

    const form = document.getElementById('questionnaireForm');
    const submitBtn = document.getElementById('submitFormsBtn');

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        submitBtn.disabled = true;
        submitBtn.textContent = 'Enregistrement...';

        try {
            const administrative = collectAdministrativeData();
            if (draft.tierInfo) {
                administrative.personal = buildPersonalFromTierInfo(draft.tierInfo);
            }
            const medical = collectMedicalData();
            const payload = {
                projectId: draft.projectId,
                productId: draft.productId,
                questionnaireMode,
                administrative,
                medical,
                timestamp: new Date().toISOString()
            };

            sessionStorage.setItem('forms_payload', JSON.stringify(payload));
            showMessage('Questionnaires enregistrés. Passage à l’étape de paiement...', 'success');

            setTimeout(() => {
                window.location.href = `payment-checkout.html?projectId=${draft.projectId}&productId=${draft.productId}`;
            }, 900);
        } catch (error) {
            console.error('Erreur questionnaire', error);
            showMessage(error.message || 'Impossible d’enregistrer les réponses.', 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Continuer vers le paiement';
        }
    });
});

function goBack() {
    // Récupérer le projectId depuis le draft ou l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const projectIdFromUrl = urlParams.get('projectId');
    
    let projectId = projectIdFromUrl;
    
    if (!projectId) {
        // Essayer de récupérer depuis sessionStorage
        const draftRaw = sessionStorage.getItem('subscription_draft');
        if (draftRaw) {
            try {
                const draft = JSON.parse(draftRaw);
                projectId = draft.projectId;
            } catch (e) {
                console.error('Erreur parsing draft:', e);
            }
        }
    }
    
    // Si on a un projectId, rediriger vers la sélection de produit
    if (projectId) {
        window.location.href = `product-selection.html?projectId=${projectId}`;
    } else {
        // Sinon, utiliser l'historique du navigateur
        window.history.back();
    }
}

// Exposer goBack globalement
window.goBack = goBack;

function populateSummary(draft) {
    const container = document.getElementById('subscriptionSummary');
    if (!container) return;
    container.innerHTML = `
        <p><strong>Voyage :</strong> ${draft.projectTitle || '—'}</p>
        <p><strong>Produit :</strong> ${draft.productName || '—'}</p>
        <p><strong>Assureur :</strong> ${draft.assureur || 'Mobility Health'}</p>
        <p><strong>Mode questionnaire :</strong> Questionnaire long</p>
    `;
}

function populateCheckboxes() {
    const symptomOptions = [
        'Paludisme',
        'Tuberculose',
        'Fièvre typhoïde',
        'Choléra',
        'Dengue',
        'Hépatite',
        'Infections respiratoires sévères',
        'Fièvre persistante',
        'Douleurs thoraciques',
        'Essoufflement inhabituel',
        'Vertiges fréquents',
        'Perte de connaissance',
        'Saignements anormaux',
        'Réactions allergiques sévères',
        'Autre'
    ];
    renderCheckboxGroup('symptomsList', symptomOptions, 'symptom');
}

function setupSymptomOtherField() {
    const container = document.getElementById('symptomsList');
    const otherGroup = document.getElementById('symptomOtherGroup');
    const otherInput = document.getElementById('symptomOther');
    if (!container || !otherGroup || !otherInput) {
        return;
    }
    const otherCheckbox = container.querySelector('input[value="Autre"]');
    if (!otherCheckbox) {
        return;
    }
    const toggle = () => {
        if (otherCheckbox.checked) {
            otherGroup.style.display = 'block';
            otherInput.required = true;
        } else {
            otherGroup.style.display = 'none';
            otherInput.required = false;
            otherInput.value = '';
        }
    };
    otherCheckbox.addEventListener('change', toggle);
    toggle();
}

function setupSurgeryDetailsField() {
    const selectEl = document.getElementById('surgeryLast6Months');
    const detailsGroup = document.getElementById('surgeryDetailsGroup');
    const detailsInput = document.getElementById('surgeryLast6MonthsDetails');
    if (!selectEl || !detailsGroup || !detailsInput) {
        return;
    }
    const toggle = () => {
        if (selectEl.value === 'oui') {
            detailsGroup.style.display = 'block';
            detailsInput.required = true;
        } else {
            detailsGroup.style.display = 'none';
            detailsInput.required = false;
            detailsInput.value = '';
        }
    };
    selectEl.addEventListener('change', toggle);
    toggle();
}

function setupYesNoConditionalFields() {
    const pairs = [
        ['malade_souscription', 'malade_souscription_detail'],
        ['symptomes_persistants', 'symptomes_persistants_detail'],
        ['medecin_traitant', 'medecin_traitant_detail'],
        ['traitement_regulier', 'traitement_regulier_detail'],
        ['hospitalise_12_mois', 'hospitalise_12_mois_detail'],
        ['fumeur', 'fumeur_detail'],
        ['alcool', 'alcool_detail'],
        ['activite_physique', 'activite_physique_detail'],
        ['allergies', 'allergies_detail'],
        ['sante_mentale', 'sante_mentale_detail']
    ];
    pairs.forEach(([radioName, detailId]) => {
        const radios = document.querySelectorAll(`input[name="${radioName}"]`);
        const detail = document.getElementById(detailId);
        if (!detail || !radios.length) return;
        function update() {
            const checked = document.querySelector(`input[name="${radioName}"]:checked`);
            detail.style.display = checked && checked.value === 'oui' ? 'block' : 'none';
        }
        radios.forEach(r => r.addEventListener('change', update));
        update();
    });
}

function renderCheckboxGroup(containerId, options, prefix) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    options.forEach((label, index) => {
        const id = `${prefix}-${index}`;
        const wrapper = document.createElement('label');
        wrapper.innerHTML = `
            <input type="checkbox" id="${id}" value="${label}">
            ${label}
        `;
        container.appendChild(wrapper);
    });
}

function collectAdministrativeData() {
    return {
        technical: {
            acceptCG: consentValue('acceptCG'),
            acceptExclusions: consentValue('acceptExclusions'),
            acceptData: consentValue('acceptData'),
            honesty1: consentValue('honesty1'),
            honesty2: consentValue('honesty2')
        }
    };
}

/**
 * Construit l'objet personal attendu par le backend (attestation, PDF) à partir des infos tiers.
 * Quand on souscrit pour un tiers, les documents produits concernent le tiers.
 */
function buildPersonalFromTierInfo(tier) {
    const first = (tier.firstname || '').trim();
    const last = (tier.lastname || '').trim();
    const fullName = [first, last].filter(Boolean).join(' ') || last || first;
    return {
        fullName,
        birthDate: tier.birthdate || '',
        gender: '',
        nationality: '',
        passportNumber: (tier.passportNumber || '').trim(),
        passportExpiryDate: tier.passportExpiryDate || '',
        address: '',
        phone: (tier.emergencyPhone || '').trim(),
        email: ''
    };
}

function collectMedicalData() {
    return collectLongMedicalData();
}

function collectLongMedicalData() {
    const maladeSouscription = document.querySelector('input[name="malade_souscription"]:checked')?.value;
    const symptomesPersistants = document.querySelector('input[name="symptomes_persistants"]:checked')?.value;
    const medecinTraitant = document.querySelector('input[name="medecin_traitant"]:checked')?.value;
    const traitementRegulier = document.querySelector('input[name="traitement_regulier"]:checked')?.value;
    const hospitalise12 = document.querySelector('input[name="hospitalise_12_mois"]:checked')?.value;
    const fumeur = document.querySelector('input[name="fumeur"]:checked')?.value;
    const alcool = document.querySelector('input[name="alcool"]:checked')?.value;
    const activitePhysique = document.querySelector('input[name="activite_physique"]:checked')?.value;
    const allergies = document.querySelector('input[name="allergies"]:checked')?.value;
    const santeMentale = document.querySelector('input[name="sante_mentale"]:checked')?.value;
    return {
        mode: 'long',
        maladeSouscription: maladeSouscription || null,
        maladeSouscriptionPrecision: valueOf('malade_souscription_precision'),
        symptomesPersistants: symptomesPersistants || null,
        symptomesPersistantsPrecision: valueOf('symptomes_persistants_precision'),
        medecinTraitant: medecinTraitant || null,
        medecinTraitantNom: valueOf('medecin_traitant_nom'),
        medecinTraitantSpecialite: valueOf('medecin_traitant_specialite'),
        medecinTraitantTelephone: valueOf('medecin_traitant_telephone'),
        symptoms: selectedValues('symptomsList'),
        symptomOther: valueOf('symptomOther'),
        pregnancy: valueOf('pregnancy'),
        surgeryLast6Months: valueOf('surgeryLast6Months'),
        surgeryLast6MonthsDetails: valueOf('surgeryLast6MonthsDetails'),
        traitementRegulier: traitementRegulier || null,
        traitementRegulierPrecision: valueOf('traitement_regulier_precision'),
        hospitalise12Mois: hospitalise12 || null,
        hospitalise12MoisRaison: valueOf('hospitalise_12_mois_raison'),
        fumeur: fumeur || null,
        fumeurCigarettes: valueOf('fumeur_cigarettes'),
        alcool: alcool || null,
        alcoolFrequence: valueOf('alcool_frequence'),
        activitePhysique: activitePhysique || null,
        activitePhysiquePrecision: valueOf('activite_physique_precision'),
        allergies: allergies || null,
        allergiesPrecision: valueOf('allergies_precision'),
        santeMentale: santeMentale || null,
        santeMentalePrecision: valueOf('sante_mentale_precision'),
        photoMedicale: getStoredMedicalPhoto(),
        honourDeclaration: {
            medicalHonesty1: checked('medicalHonesty1'),
            medicalHonesty2: checked('medicalHonesty2')
        }
    };
}

function applyQuestionnaireMode(mode) {
    const longSection = document.getElementById('medicalLongSection');
    const longRequiredEls = document.querySelectorAll('[data-long-required]');
    if (!longSection) {
        return;
    }
    longSection.style.display = 'block';
    longRequiredEls.forEach((el) => {
        el.required = true;
    });
}

function selectedValues(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return [];
    return Array.from(container.querySelectorAll('input[type="checkbox"]:checked'))
        .map((input) => input.value);
}

function valueOf(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
}

function checked(id) {
    const el = document.getElementById(id);
    return !!el?.checked;
}

function getStoredConsents() {
    const raw = sessionStorage.getItem('consents_payload');
    if (!raw) return {};
    try {
        return JSON.parse(raw) || {};
    } catch (e) {
        console.warn('Consents payload invalid', e);
        return {};
    }
}

function consentValue(id) {
    const el = document.getElementById(id);
    if (el) {
        return !!el.checked;
    }
    const stored = getStoredConsents();
    return !!stored?.[id];
}

function getStoredMedicalPhoto() {
    const raw = sessionStorage.getItem('medical_photo');
    if (!raw) return null;
    try {
        const payload = JSON.parse(raw);
        return payload?.dataUrl || null;
    } catch (e) {
        console.warn('Medical photo payload invalid', e);
        return null;
    }
}

function showMessage(message, type) {
    const box = document.getElementById('formsMessage');
    if (!box) return;
    box.textContent = message;
    box.className = `message ${type}`;
    box.style.display = 'block';
}

/**
 * Récupère la relation depuis les notes du voyage et pré-remplit les champs
 * si "Je suis le voyageur" est sélectionné
 */
async function populateUserInfoIfSelf(projectId) {
    try {
        // Récupérer le voyage pour extraire la relation
        const voyage = await apiCall(`/voyages/${projectId}`);
        if (!voyage || !voyage.notes) {
            return;
        }
        
        // Extraire la relation depuis les notes
        const notes = voyage.notes;
        const isSelf = notes.includes('Souscription: Je suis le voyageur');
        
        if (!isSelf) {
            // Si "Pour un tiers", laisser les champs libres
            return;
        }
        
        // Récupérer les informations de l'utilisateur connecté
<<<<<<< HEAD
        const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
=======
        const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
        const token = window.MobilityAuth?.getAccessToken ? window.MobilityAuth.getAccessToken() : localStorage.getItem('access_token');
        
        if (!token) {
            console.warn('Token non disponible pour récupérer les informations utilisateur');
            return;
        }
        
        const response = await fetch(`${apiUrl}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            console.warn('Impossible de récupérer les informations utilisateur');
            return;
        }
        
        const user = await response.json();
        
        // Pré-remplir les champs disponibles
        const fullNameInput = document.getElementById('fullName');
        const emailInput = document.getElementById('email');
        const birthDateInput = document.getElementById('birthDate');
        const phoneInput = document.getElementById('phone');
        const genderSelect = document.getElementById('gender');
        
        if (fullNameInput && user.full_name) {
            fullNameInput.value = user.full_name;
            fullNameInput.disabled = true;
            fullNameInput.style.backgroundColor = '#f5f5f5';
            fullNameInput.style.cursor = 'not-allowed';
        }
        
        if (emailInput && user.email) {
            emailInput.value = user.email;
            emailInput.disabled = true;
            emailInput.style.backgroundColor = '#f5f5f5';
            emailInput.style.cursor = 'not-allowed';
        }
        
        if (birthDateInput && user.date_naissance) {
            birthDateInput.value = user.date_naissance;
            birthDateInput.disabled = true;
            birthDateInput.style.backgroundColor = '#f5f5f5';
            birthDateInput.style.cursor = 'not-allowed';
        }
        
        if (phoneInput && user.telephone) {
            phoneInput.value = user.telephone;
            phoneInput.disabled = true;
            phoneInput.style.backgroundColor = '#f5f5f5';
            phoneInput.style.cursor = 'not-allowed';
        }
        
        if (genderSelect && user.sexe) {
            genderSelect.value = user.sexe;
            genderSelect.disabled = true;
            genderSelect.style.backgroundColor = '#f5f5f5';
            genderSelect.style.cursor = 'not-allowed';
        }
        
    } catch (error) {
        console.error('Erreur lors de la récupération des informations utilisateur:', error);
    }
}

/**
 * Liste complète des pays du monde (en français)
 */
const ALL_COUNTRIES = [
    'Afghanistan', 'Afrique du Sud', 'Albanie', 'Algérie', 'Allemagne', 'Andorre', 'Angola', 'Antigua-et-Barbuda',
    'Arabie saoudite', 'Argentine', 'Arménie', 'Australie', 'Autriche', 'Azerbaïdjan', 'Bahamas', 'Bahreïn',
    'Bangladesh', 'Barbade', 'Belgique', 'Belize', 'Bénin', 'Bhoutan', 'Biélorussie', 'Birmanie', 'Bolivie',
    'Bosnie-Herzégovine', 'Botswana', 'Brésil', 'Brunei', 'Bulgarie', 'Burkina Faso', 'Burundi', 'Cambodge',
    'Cameroun', 'Canada', 'Cap-Vert', 'Chili', 'Chine', 'Chypre', 'Colombie', 'Comores', 'Congo', 'Corée du Nord',
    'Corée du Sud', 'Costa Rica', 'Côte d\'Ivoire', 'Croatie', 'Cuba', 'Danemark', 'Djibouti', 'Dominique',
    'Égypte', 'Émirats arabes unis', 'Équateur', 'Érythrée', 'Espagne', 'Estonie', 'Eswatini', 'États-Unis',
    'Éthiopie', 'Fidji', 'Finlande', 'France', 'Gabon', 'Gambie', 'Géorgie', 'Ghana', 'Grèce', 'Grenade',
    'Guatemala', 'Guinée', 'Guinée-Bissau', 'Guinée équatoriale', 'Guyana', 'Haïti', 'Honduras', 'Hongrie',
    'Inde', 'Indonésie', 'Irak', 'Iran', 'Irlande', 'Islande', 'Israël', 'Italie', 'Jamaïque', 'Japon', 'Jordanie',
    'Kazakhstan', 'Kenya', 'Kirghizistan', 'Kiribati', 'Koweït', 'Laos', 'Lesotho', 'Lettonie', 'Liban',
    'Liberia', 'Libye', 'Liechtenstein', 'Lituanie', 'Luxembourg', 'Macédoine du Nord', 'Madagascar', 'Malaisie',
    'Malawi', 'Maldives', 'Mali', 'Malte', 'Maroc', 'Marshall', 'Maurice', 'Mauritanie', 'Mexique', 'Micronésie',
    'Moldavie', 'Monaco', 'Mongolie', 'Monténégro', 'Mozambique', 'Namibie', 'Nauru', 'Népal', 'Nicaragua',
    'Niger', 'Nigeria', 'Norvège', 'Nouvelle-Zélande', 'Oman', 'Ouganda', 'Ouzbékistan', 'Pakistan', 'Palaos',
    'Palestine', 'Panama', 'Papouasie-Nouvelle-Guinée', 'Paraguay', 'Pays-Bas', 'Pérou', 'Philippines', 'Pologne',
    'Portugal', 'Qatar', 'République centrafricaine', 'République démocratique du Congo', 'République dominicaine',
    'République tchèque', 'Roumanie', 'Royaume-Uni', 'Russie', 'Rwanda', 'Saint-Christophe-et-Niévès',
    'Saint-Marin', 'Saint-Vincent-et-les-Grenadines', 'Sainte-Lucie', 'Salomon', 'Salvador', 'Samoa', 'São Tomé-et-Príncipe',
    'Sénégal', 'Serbie', 'Seychelles', 'Sierra Leone', 'Singapour', 'Slovaquie', 'Slovénie', 'Somalie', 'Soudan',
    'Soudan du Sud', 'Sri Lanka', 'Suède', 'Suisse', 'Suriname', 'Syrie', 'Tadjikistan', 'Tanzanie', 'Tchad',
    'Thaïlande', 'Timor oriental', 'Togo', 'Tonga', 'Trinité-et-Tobago', 'Tunisie', 'Turkménistan', 'Turquie',
    'Tuvalu', 'Ukraine', 'Uruguay', 'Vanuatu', 'Vatican', 'Venezuela', 'Viêt Nam', 'Yémen', 'Zambie', 'Zimbabwe'
];

/**
 * Charge la liste complète des pays du monde et remplit le select de nationalité
 */
function loadNationalityCountries() {
    const nationalitySelect = document.getElementById('nationality');
    if (!nationalitySelect) {
        return;
    }
    
    // Trier les pays par ordre alphabétique
    const sortedCountries = [...ALL_COUNTRIES].sort((a, b) => {
        return a.localeCompare(b, 'fr', { sensitivity: 'base' });
    });
    
    // Ajouter chaque pays au select
    sortedCountries.forEach(country => {
        const option = document.createElement('option');
        option.value = country;
        option.textContent = country;
        nationalitySelect.appendChild(option);
    });
}

