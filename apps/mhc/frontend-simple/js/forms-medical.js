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
    setupPregnancyEligibilityCheck();
    applyQuestionnaireMode(questionnaireMode);
    setupFormsMedicalPhotoUploader();

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
            validateMedicalEligibility(medical);
            const pm = medical.photoMedicale;
            if (!pm || typeof pm !== 'string' || pm.length < 50) {
                showMessage(
                    'La photo pour la carte d’assurance numérique est obligatoire. Ajoutez une image dans le bloc photo ci-dessus ou revenez à l’étape choix du produit.',
                    'error',
                );
                submitBtn.disabled = false;
                submitBtn.textContent = 'Continuer vers le paiement';
                return;
            }
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
        <p><strong>Mode questionnaire :</strong> Questionnaire médical simplifié (5 questions)</p>
    `;
}

function setupPregnancyEligibilityCheck() {
    const radios = document.querySelectorAll('input[name="enceinte"]');
    const detail = document.getElementById('enceinte_detail');
    const monthsInput = document.getElementById('mois_grossesse');
    const ineligibleBanner = document.getElementById('enceinteIneligible');
    const submitBtn = document.getElementById('submitFormsBtn');

    function update() {
        const checked = document.querySelector('input[name="enceinte"]:checked');
        const isPregnant = checked && checked.value === 'oui';
        if (detail) {
            detail.style.display = isPregnant ? 'block' : 'none';
        }
        if (monthsInput) {
            monthsInput.required = isPregnant;
            if (!isPregnant) {
                monthsInput.value = '';
            }
        }
        refreshPregnancyEligibility(ineligibleBanner, submitBtn);
    }

    radios.forEach((radio) => radio.addEventListener('change', update));
    if (monthsInput) {
        monthsInput.addEventListener('input', () => refreshPregnancyEligibility(ineligibleBanner, submitBtn));
    }
    update();
}

function refreshPregnancyEligibility(ineligibleBanner, submitBtn) {
    const checked = document.querySelector('input[name="enceinte"]:checked');
    const monthsRaw = document.getElementById('mois_grossesse')?.value?.trim();
    const months = monthsRaw ? Number.parseInt(monthsRaw, 10) : NaN;
    const ineligible = checked?.value === 'oui' && Number.isFinite(months) && months > 5;

    if (ineligibleBanner) {
        ineligibleBanner.style.display = ineligible ? 'block' : 'none';
    }
    if (submitBtn) {
        submitBtn.disabled = ineligible;
    }
    return !ineligible;
}

function validateMedicalEligibility(medical) {
    const requiredFields = [
        ['maladeSouscription', '1. Êtes-vous malade au moment de la souscription ?'],
        ['malade12Mois', '2. Avez-vous été malade au cours des 12 derniers mois ?'],
        ['maladieChronique', '3. Souffrez-vous d\'une maladie chronique ?'],
        ['enceinte', '4. Êtes-vous enceinte au moment de la souscription ?'],
        ['voyageMedical', '5. Faites-vous un voyage à but médical ?'],
    ];
    for (const [key, label] of requiredFields) {
        if (!medical[key]) {
            throw new Error(`Veuillez répondre : ${label}`);
        }
    }
    if (medical.enceinte === 'oui') {
        const months = Number.parseInt(String(medical.moisGrossesse ?? ''), 10);
        if (!Number.isFinite(months) || months < 1) {
            throw new Error('Veuillez indiquer le nombre de mois de grossesse.');
        }
        if (months > 5) {
            throw new Error('Vous n\'êtes pas éligible pour être assuré par nos services (grossesse de plus de 5 mois).');
        }
    }
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
    const malade12Mois = document.querySelector('input[name="malade_12_mois"]:checked')?.value;
    const maladieChronique = document.querySelector('input[name="maladie_chronique"]:checked')?.value;
    const enceinte = document.querySelector('input[name="enceinte"]:checked')?.value;
    const voyageMedical = document.querySelector('input[name="voyage_medical"]:checked')?.value;
    const moisGrossesseRaw = valueOf('mois_grossesse');
    const moisGrossesse = moisGrossesseRaw ? Number.parseInt(moisGrossesseRaw, 10) : null;

    return {
        mode: 'long',
        version: 'simplified_v1',
        maladeSouscription: maladeSouscription || null,
        malade_souscription: maladeSouscription || null,
        malade12Mois: malade12Mois || null,
        malade_12_mois: malade12Mois || null,
        maladieChronique: maladieChronique || null,
        maladie_chronique: maladieChronique || null,
        enceinte: enceinte || null,
        pregnancy: enceinte || null,
        moisGrossesse: Number.isFinite(moisGrossesse) ? moisGrossesse : null,
        mois_grossesse: Number.isFinite(moisGrossesse) ? moisGrossesse : null,
        voyageMedical: voyageMedical || null,
        voyage_medical: voyageMedical || null,
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
        el.required = false;
    });
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

/** Photo e-carte : même clé sessionStorage que product-selection.js (`medical_photo`). */
function setupFormsMedicalPhotoUploader() {
    const input = document.getElementById('formsMedicalPhotoInput');
    const preview = document.getElementById('formsMedicalPhotoPreview');
    const clearBtn = document.getElementById('formsMedicalPhotoClearBtn');
    const statusEl = document.getElementById('formsMedicalPhotoStatus');
    if (!input || !preview) {
        return;
    }

    function setStatus(text, isError) {
        if (statusEl) {
            statusEl.textContent = text || '';
            statusEl.style.color = isError ? '#c0392b' : '#4d618f';
        }
    }

    function showPreview(dataUrl) {
        preview.innerHTML = `<img src="${dataUrl}" alt="Aperçu photo e-carte" style="max-height:140px;object-fit:contain;border-radius:8px;">`;
        if (clearBtn) clearBtn.disabled = false;
        setStatus('Photo enregistrée pour le paiement et la e-carte.', false);
    }

    function clearPhoto() {
        sessionStorage.removeItem('medical_photo');
        preview.innerHTML = '<span style="text-align:center;color:#7d8fb3;">Aucune photo</span>';
        if (clearBtn) clearBtn.disabled = true;
        input.value = '';
        setStatus('Photo obligatoire pour passer au paiement.', true);
    }

    function hydrateFromStorage() {
        const dataUrl = getStoredMedicalPhoto();
        if (dataUrl) {
            showPreview(dataUrl);
        }
    }

    input.addEventListener('change', async (event) => {
        const file = event.target.files?.[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            setStatus('Merci de choisir une image (JPG ou PNG).', true);
            return;
        }
        const maxBytes = 5 * 1024 * 1024;
        if (file.size > maxBytes) {
            setStatus('Photo trop volumineuse (5 Mo max).', true);
            return;
        }
        try {
            const dataUrl = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
            sessionStorage.setItem('medical_photo', JSON.stringify({ dataUrl, source: 'forms-medical' }));
            showPreview(dataUrl);
        } catch (e) {
            console.error(e);
            setStatus('Lecture du fichier impossible.', true);
        }
    });

    if (clearBtn) {
        clearBtn.addEventListener('click', () => clearPhoto());
    }

    hydrateFromStorage();
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
        const apiUrl = window.API_BASE_URL || 'https://api.srv1324425.hstgr.cloud/api/v1';
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

