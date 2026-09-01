const fallbackCurrencyHelper = {
    getLocale: () => 'fr-FR',
    getCurrency: () => 'XOF',
    format: (value, options = {}) => {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return '—';
        }
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'XOF',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
            ...options,
        }).format(numeric);
    },
};

const currencyHelper = window.CurrencyHelper || fallbackCurrencyHelper;

/** Photo e-carte : même stockage que forms-medical / checkout (`medical_photo`). */
function hasStoredMedicalPhoto() {
    const raw = sessionStorage.getItem('medical_photo');
    if (!raw) return false;
    try {
        const payload = JSON.parse(raw);
        const url = payload?.dataUrl;
        return typeof url === 'string' && url.length >= 50;
    } catch {
        return false;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const authenticated = await requireAuth();
    if (!authenticated) {
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const projectId = params.get('projectId');
    if (!projectId) {
        showMessage('Identifiant du voyage manquant. Veuillez reprendre la déclaration.', 'error');
        return;
    }

    const projectSummaryEl = document.getElementById('projectSummary');
    const productsContainer = document.getElementById('productsContainer');
    const assureurSelect = document.getElementById('assureurFilter');
    const searchInput = document.getElementById('searchInput');
    const continueBtn = document.getElementById('continueBtn');
    const modal = document.getElementById('productModal');
    const modalBody = document.getElementById('productModalBody');
    const modalCloseBtn = document.getElementById('modalCloseBtn');
    const consentInputs = {
        acceptCG: document.getElementById('acceptCG'),
        acceptExclusions: document.getElementById('acceptExclusions'),
    };
    const medicalPhoto = {
        input: document.getElementById('medicalPhotoInput'),
        preview: document.getElementById('medicalPhotoPreview'),
        status: document.getElementById('medicalPhotoStatus'),
        openCamera: document.getElementById('medicalOpenCameraBtn'),
        capture: document.getElementById('medicalCapturePhotoBtn'),
        closeCamera: document.getElementById('medicalCloseCameraBtn'),
        clear: document.getElementById('medicalClearPhotoBtn'),
        cameraContainer: document.getElementById('medicalCameraContainer'),
        video: document.getElementById('medicalPhotoVideo'),
        canvas: document.getElementById('medicalPhotoCanvas'),
    };
    let medicalPhotoData = null;
    let activeMedicalStream = null;

    let allProducts = [];
    let selectedProduct = null;
    let currentProject = null;
    const locale = currencyHelper.getLocale();
    const currency = currencyHelper.getCurrency();

    try {
        const [project, userResponse] = await Promise.all([
            apiCall(`/voyages/${projectId}`),
            apiCall('/auth/me').catch(() => null)
        ]);

        currentProject = project;
        renderProjectSummary(projectSummaryEl, project);

        const productQs = new URLSearchParams({ limit: '1000', filter_by_voyage_assureur: 'true' });
        const resName =
            (userResponse && userResponse.pays_residence && String(userResponse.pays_residence).trim()) ||
            (typeof localStorage !== 'undefined' && (localStorage.getItem('user_pays_residence') || '').trim()) ||
            '';
        if (resName) productQs.set('residence_country_name', resName);
        if (project.destination_country_id != null) {
            productQs.set('destination_country_id', String(project.destination_country_id));
        }
        if (project.destination_country_name) {
            productQs.set('destination_country_name', String(project.destination_country_name));
        }
        const productsResponse = await apiCall(`/products?${productQs.toString()}`);

        allProducts = (productsResponse || []).filter((p) => p.est_actif !== false);
        if (!allProducts.length) {
            productsContainer.innerHTML =
                '<p class="empty-state">Aucune offre ne correspond à votre voyage (pays de résidence / destination et assureurs partenaires sur ce parcours). Modifiez le projet de voyage ou contactez Mobility Healthcare.</p>';
            showMessage(
                'Aucun produit disponible pour ce parcours. Vérifiez la destination ou la configuration assureur / zone tarifaire.',
                'error',
            );
        } else {

        // Caractéristiques pour tarif selon durée, zone et âge
        let age = null;
        if (userResponse && userResponse.date_naissance) {
            const birth = new Date(userResponse.date_naissance);
            const today = new Date();
            age = Math.floor((today - birth) / (365.25 * 24 * 60 * 60 * 1000));
        }
        let duree_jours = null;
        if (project.date_depart && project.date_retour) {
            const dep = new Date(project.date_depart);
            const ret = new Date(project.date_retour);
            duree_jours = Math.max(1, Math.ceil((ret - dep) / (24 * 60 * 60 * 1000)));
        }
        const destination_country_id = project.destination_country_id ?? null;
        const destination_country_name = project.destination_country_name ?? null;
        const residence_country_name =
            (userResponse && userResponse.pays_residence && String(userResponse.pays_residence).trim()) || null;

        // Devis par produit : résidence + destination, durée et âge → tarif (grille voyage)
        const quoteParams = { age, destination_country_id, duree_jours };
        if (destination_country_name) {
            quoteParams.destination_country_name = destination_country_name;
        }
        if (residence_country_name) {
            quoteParams.residence_country_name = residence_country_name;
        }
        const paramsStr = new URLSearchParams(
            Object.fromEntries(
                Object.entries(quoteParams).filter(([, v]) => v != null && v !== '')
            )
        ).toString();
        const quotePromises = allProducts.map((p) =>
            apiCall(`/products/${p.id}/quote${paramsStr ? `?${paramsStr}` : ''}`).then((q) => ({ productId: p.id, quote: q })).catch(() => ({ productId: p.id, quote: null }))
        );
        const quotes = await Promise.all(quotePromises);
        const quoteByProductId = {};
        quotes.forEach(({ productId, quote }) => { quoteByProductId[productId] = quote; });
        allProducts.forEach((p) => {
            p._quote = quoteByProductId[p.id];
        });

        populateAssureurs(assureurSelect, allProducts);
        renderProducts(allProducts);
        }
    } catch (error) {
        console.error('Erreur chargement produits/projet', error);
        showMessage(error.message || 'Impossible de charger les données.', 'error');
        return;
    }

    hydrateConsents();
    bindConsentListeners();
    setupMedicalPhotoCapture();
    updateContinueState();

    assureurSelect.addEventListener('change', handleFilters);
    searchInput.addEventListener('input', handleFilters);

    continueBtn.addEventListener('click', () => {
        if (!selectedProduct) {
            return;
        }
        if (!hasStoredMedicalPhoto()) {
            showMessage(
                'La photo pour la carte d’assurance numérique est obligatoire. Ajoutez une image ci-dessus (fichier ou caméra).',
                'error',
            );
            return;
        }
        let tierInfo = null;
        try {
            const raw = sessionStorage.getItem('tier_info');
            if (raw) tierInfo = JSON.parse(raw);
        } catch (e) {}
        const draft = {
            projectId: currentProject.id,
            projectTitle: currentProject.titre,
            productId: selectedProduct.id,
            productName: selectedProduct.nom,
            assureur: selectedProduct.assureur,
            questionnaireType: currentProject.questionnaire_type || 'long',
        };
        if (tierInfo) draft.tierInfo = tierInfo;
        sessionStorage.setItem('subscription_draft', JSON.stringify(draft));
        persistConsents();
        showMessage('Produit sélectionné ! Passage aux formulaires...', 'success');
        setTimeout(() => {
            window.location.href = `forms-medical.html?projectId=${currentProject.id}&productId=${selectedProduct.id}`;
        }, 600);
    });

    function handleFilters() {
        const assureur = assureurSelect.value;
        const query = searchInput.value?.toLowerCase().trim();

        const filtered = allProducts.filter((product) => {
            const matchAssureur = assureur ? product.assureur === assureur : true;
            const matchText = query
                ? (product.nom?.toLowerCase().includes(query) ||
                    product.description?.toLowerCase().includes(query) ||
                    product.code?.toLowerCase().includes(query))
                : true;
            return matchAssureur && matchText;
        });
        renderProducts(filtered);
    }

    modalCloseBtn?.addEventListener('click', closeModal);
    modal?.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    function renderProducts(list) {
        if (!productsContainer) return;
        productsContainer.innerHTML = '';
        if (!list.length) {
            productsContainer.innerHTML = '<p class="empty-state">Aucun produit ne correspond à vos filtres.</p>';
            return;
        }

        const apiBase = window.API_BASE_URL || '/api/v1';
        function productLogoSrc(product) {
            const ad = product.assureur_details;
            if (!ad || !ad.logo_url) return '';
            return ad.logo_url.startsWith('http') ? ad.logo_url : `${apiBase}/assureurs/${ad.id}/logo`;
        }
        list.forEach((product) => {
            const quote = product._quote;
            const prixHtml = voyageTarifPriceHtml(quote, product.cout);
            const fromTarif = quote ? quote.from_tarif : false;
            const dureeValiditeJours = product.duree_validite_jours;
            const dureeLabel = fromTarif && quote && quote.duree_min_jours != null && quote.duree_max_jours != null
                ? `${quote.duree_min_jours} - ${quote.duree_max_jours} jours`
                : (dureeValiditeJours ? `${dureeValiditeJours} jours` : 'Durée flexible');
            const logoSrc = productLogoSrc(product);
            const card = document.createElement('div');
            card.className = 'product-card';
            card.dataset.productId = product.id;
            card.innerHTML = `
                <div class="product-meta">
                    <div class="product-assureur-brand">
                        ${logoSrc ? `<img src="${logoSrc}" alt="" class="product-assureur-logo" onerror="this.style.display='none'">` : ''}
                        <strong class="product-assureur-name">${product.assureur || 'Assureur MH'}</strong>
                    </div>
                    <span class="product-duration">${dureeLabel}</span>
                </div>
                <div class="product-header">
                    <h4>${product.nom}</h4>
                    <div class="product-price">${prixHtml}${fromTarif ? ' <span class="product-price-badge">(selon profil)</span>' : ' <span class="product-price-badge product-price-default">(prix par défaut)</span>'}</div>
                    ${fromTarif ? '<p class="product-price-note text-muted small">Prime d’assurance + frais de services selon résidence, destination, âge et durée.</p>' : '<p class="product-price-note text-muted small">Aucun tarif spécifique ne correspond à votre profil ; le prix par défaut du produit est facturé.</p>'}
                </div>
                <div class="product-badges">
                    ${product.zones_geographiques?.zones?.length
                        ? `<span class="product-badge">${product.zones_geographiques.zones.length} zones couvertes</span>`
                        : ''}
                    ${product.couverture_multi_entrees
                        ? `<span class="product-badge">Entrées multiples</span>`
                        : ''}
                </div>
                <p>${product.description || 'Couverture complète pour vos déplacements internationaux.'}</p>
                <div class="status-pill">${product.est_actif ? 'Actif' : 'Suspendu'}</div>
                <button class="detail-link" type="button">Voir les détails</button>
            `;
            card.addEventListener('click', () => selectProduct(card, product));
            const detailBtn = card.querySelector('.detail-link');
            detailBtn?.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                showProductDetails(product);
            });
            productsContainer.appendChild(card);
        });
    }

    function selectProduct(cardElement, product) {
        document.querySelectorAll('.product-card').forEach((card) => card.classList.remove('selected'));
        cardElement.classList.add('selected');
        selectedProduct = product;
        updateContinueState();
        showMessage(`Produit « ${product.nom} » sélectionné.`, 'success');
    }

    function renderProjectSummary(container, project) {
        if (!container) return;
        const depart = formatDate(project.date_depart);
        const retour = project.date_retour ? formatDate(project.date_retour) : '—';
        const questionnaireLabel = project.questionnaire_type === 'short'
            ? 'Questionnaire court'
            : 'Questionnaire long';
        container.innerHTML = `
            <div class="project-summary-item">
                <span>Voyage</span>
                <strong>${project.titre}</strong>
            </div>
            <div class="project-summary-item">
                <span>Destination</span>
                <strong>${project.destination_display || project.destination || '—'}</strong>
            </div>
            <div class="project-summary-item">
                <span>Période</span>
                <strong>${depart} → ${retour}</strong>
            </div>
            <div class="project-summary-item">
                <span>Participants</span>
                <strong>${project.nombre_participants}</strong>
            </div>
            <div class="project-summary-item">
                <span>Mode questionnaire</span>
                <strong>${questionnaireLabel}</strong>
            </div>
        `;
    }

    function populateAssureurs(select, products) {
        const assureurs = [...new Set(products.map((p) => p.assureur).filter(Boolean))].sort();
        assureurs.forEach((assureur) => {
            select.appendChild(new Option(assureur, assureur));
        });
    }

    function formatPrice(value) {
        if (value == null) return '—';
        try {
            return currencyHelper.format(value, {
                locale,
                currency,
                maximumFractionDigits: 0,
            });
        } catch {
            return `${value} ${currency}`;
        }
    }

    /** Affiche prime + frais + total lorsque l’API les renvoie (grille voyage). */
    function voyageTarifPriceHtml(quote, fallbackCout) {
        if (!quote || quote.prix == null) {
            return formatPrice(fallbackCout);
        }
        const frais = quote.frais_services;
        const prime = quote.prime_assurance;
        if (frais != null && Number(frais) > 0 && prime != null) {
            return `${formatPrice(prime)} <span class="product-price-plus">+ frais</span> ${formatPrice(frais)} <span class="product-price-plus">=</span> ${formatPrice(quote.prix)}`;
        }
        return formatPrice(quote.prix);
    }

    function formatDate(value) {
        if (!value) return '-';
        return new Date(value).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    }
    function modalAssureurLogoSrc(product) {
        const apiBase = window.API_BASE_URL || '/api/v1';
        const ad = product.assureur_details;
        if (!ad || !ad.logo_url) return '';
        return ad.logo_url.startsWith('http') ? ad.logo_url : `${apiBase}/assureurs/${ad.id}/logo`;
    }
    function showProductDetails(product) {
        if (!modal || !modalBody) {
            showMessage('Module de détails indisponible.', 'error');
            return;
        }
        const quote = product._quote;
        const prixModalHtml = voyageTarifPriceHtml(quote, product.cout);
        const dureeModal = quote && quote.from_tarif && quote.duree_min_jours != null && quote.duree_max_jours != null
            ? `${quote.duree_min_jours} - ${quote.duree_max_jours} jours`
            : (product.duree_validite_jours ? `${product.duree_validite_jours} jours` : 'Durée flexible');
        const assureurLogoSrc = modalAssureurLogoSrc(product);
        const assureurBlock = assureurLogoSrc
            ? `<div class="product-modal-assureur">
                <img src="${assureurLogoSrc}" alt="" class="product-modal-assureur-logo" onerror="this.style.display='none'">
                <span class="product-modal-assureur-name">${escapeHtml(product.assureur || 'Assureur MH')}</span>
               </div>`
            : (product.assureur ? `<div class="product-modal-assureur"><span class="product-modal-assureur-name">${escapeHtml(product.assureur)}</span></div>` : '');
        modalBody.innerHTML = `
            <div class="product-modal-header">
                <div>
                    ${assureurBlock}
                    <div class="product-code-badge">${escapeHtml(product.code || 'N/A')}</div>
                    <h3 id="modalTitle">${escapeHtml(product.nom)}</h3>
                    <div class="product-duration-modal">${escapeHtml(dureeModal)}</div>
                    <div class="product-price-modal">${prixModalHtml}${quote && quote.from_tarif ? ' <span class="product-price-badge">(selon profil)</span>' : ' <span class="product-price-badge product-price-default">(prix par défaut)</span>'}</div>
                    ${quote && quote.from_tarif ? '<p class="product-price-note text-muted small">Prime d’assurance + frais de services selon résidence, destination, âge et durée.</p>' : '<p class="product-price-note text-muted small">Aucun tarif spécifique ne correspond à votre profil ; le prix par défaut du produit est facturé.</p>'}
                </div>
            </div>
            <div class="product-modal-content">
                ${product.description ? `<div class="product-description-section">
                    <p>${escapeHtml(product.description)}</p>
                </div>` : ''}
                ${renderProductCharacteristicsTable(product, quote)}
                ${renderGuaranteesTable(product.garanties)}
                ${renderPrimesGenerees(product.primes_generees)}
                ${renderExclusions(product.exclusions_generales)}
            </div>
        `;
        modal.classList.add('show');
    }

    function consentsAccepted() {
        return Object.values(consentInputs).every((input) => input?.checked);
    }

    function updateContinueState() {
        if (!continueBtn) return;
        const hasProduct = !!selectedProduct;
        const hasProductsAvailable = allProducts.length > 0;
        const consentsOk = consentsAccepted();
        const photoOk = hasStoredMedicalPhoto();
        const ready = hasProduct && consentsOk && photoOk;
        continueBtn.disabled = !ready;
        const hintEl = document.getElementById('continueHint');
        if (hintEl) {
            if (ready) {
                hintEl.textContent = 'Vous pouvez continuer vers les formulaires.';
            } else if (!hasProductsAvailable) {
                hintEl.textContent = 'Aucun produit disponible. Contactez l\'administrateur pour en ajouter.';
            } else if (!hasProduct) {
                hintEl.textContent = 'Pour continuer : sélectionnez un produit, ajoutez votre photo e-carte, puis cochez les deux cases.';
            } else if (!photoOk) {
                hintEl.textContent = 'Pour continuer : ajoutez votre photo pour la e-carte (fichier ou caméra) dans le bloc ci-dessus.';
            } else if (!consentsOk) {
                hintEl.textContent = 'Pour continuer : cochez les deux cases de consentement ci-dessus.';
            } else {
                hintEl.textContent = 'Pour continuer : sélectionnez un produit, une photo e-carte et les deux consentements.';
            }
        }
    }

    function persistConsents() {
        if (!Object.values(consentInputs).some(Boolean)) return;
        const payload = Object.fromEntries(
            Object.entries(consentInputs).map(([key, input]) => [key, !!input?.checked])
        );
        sessionStorage.setItem('consents_payload', JSON.stringify(payload));
    }

    function setupMedicalPhotoCapture() {
        if (!medicalPhoto.input || !medicalPhoto.preview) {
            return;
        }

        medicalPhoto.input.addEventListener('change', (event) => handleMedicalPhotoUpload(event));
        medicalPhoto.clear?.addEventListener('click', clearMedicalPhoto);

        const hasMediaDevices = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
        const isSecureContext = window.isSecureContext;
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const cameraSupported = hasMediaDevices && isSecureContext && isMobile;
        if (cameraSupported) {
            medicalPhoto.openCamera?.addEventListener('click', openMedicalCamera);
            medicalPhoto.capture?.addEventListener('click', captureMedicalPhoto);
            medicalPhoto.closeCamera?.addEventListener('click', closeMedicalCamera);
        } else {
            medicalPhoto.openCamera?.style.setProperty('display', 'none');
            medicalPhoto.capture?.style.setProperty('display', 'none');
            medicalPhoto.closeCamera?.style.setProperty('display', 'none');
        }
        // Délégation d'événements : capter le clic même si le bouton était absent à l'init
        document.body.addEventListener('click', function cameraClickDelegation(e) {
            const btn = e.target.closest ? e.target.closest('#medicalOpenCameraBtn') : null;
            if (btn && !btn.disabled) {
                e.preventDefault();
                openMedicalCamera();
                return;
            }
            const captureBtn = e.target.closest ? e.target.closest('#medicalCapturePhotoBtn') : null;
            if (captureBtn && !captureBtn.disabled) {
                e.preventDefault();
                captureMedicalPhoto();
                return;
            }
            const closeBtn = e.target.closest ? e.target.closest('#medicalCloseCameraBtn') : null;
            if (closeBtn) {
                e.preventDefault();
                closeMedicalCamera();
            }
        });
        hydrateMedicalPhoto();
    }

    async function handleMedicalPhotoUpload(event) {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }
        if (!file.type.startsWith('image/')) {
            updateMedicalPhotoStatus("Merci de sélectionner un fichier image (JPG ou PNG).", 'error');
            return;
        }
        const maxBytes = 5 * 1024 * 1024;
        if (file.size > maxBytes) {
            updateMedicalPhotoStatus("Photo trop volumineuse (5 Mo max).", 'error');
            return;
        }
        const dataUrl = await readMedicalFileAsDataURL(file);
        setMedicalPhoto(dataUrl, 'upload');
    }

    async function readMedicalFileAsDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    function setMedicalPhoto(dataUrl, source) {
        medicalPhotoData = dataUrl;
        sessionStorage.setItem('medical_photo', JSON.stringify({ dataUrl, source }));
        if (medicalPhoto.preview) {
            medicalPhoto.preview.innerHTML = `<img src="${dataUrl}" alt="Photo médicale">`;
        }
        if (medicalPhoto.status) {
            medicalPhoto.status.textContent = 'Photo ajoutée.';
        }
        if (medicalPhoto.clear) {
            medicalPhoto.clear.disabled = false;
        }
        updateContinueState();
    }

    function clearMedicalPhoto() {
        medicalPhotoData = null;
        sessionStorage.removeItem('medical_photo');
        if (medicalPhoto.preview) {
            medicalPhoto.preview.innerHTML = '<span style="text-align:center;color:#7d8fb3;">Aucune photo</span>';
        }
        if (medicalPhoto.status) {
            medicalPhoto.status.textContent = 'Photo obligatoire pour continuer.';
        }
        if (medicalPhoto.clear) {
            medicalPhoto.clear.disabled = true;
        }
        if (medicalPhoto.input) {
            medicalPhoto.input.value = '';
        }
        updateContinueState();
    }

    function updateMedicalPhotoStatus(message, type) {
        const statusEl = document.getElementById('medicalPhotoStatus') || medicalPhoto.status;
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.style.color = type === 'error' ? '#c0392b' : '#4d618f';
        }
        if (!statusEl && (type === 'error' || message.startsWith('Ouverture'))) {
            showMessage(message, type === 'error' ? 'error' : 'info');
        }
    }

    async function openMedicalCamera() {
        const videoEl = document.getElementById('medicalPhotoVideo');
        const containerEl = document.getElementById('medicalCameraContainer');
        const captureBtn = document.getElementById('medicalCapturePhotoBtn');
        const closeBtn = document.getElementById('medicalCloseCameraBtn');

        updateMedicalPhotoStatus('Ouverture de la caméra…', 'info');

        if (!videoEl || !containerEl) {
            updateMedicalPhotoStatus('Éléments caméra introuvables. Rechargez la page.', 'error');
            return;
        }
        if (!window.isSecureContext) {
            updateMedicalPhotoStatus('La caméra nécessite une connexion HTTPS.', 'error');
            return;
        }
        if (!navigator.mediaDevices?.getUserMedia) {
            updateMedicalPhotoStatus('Votre navigateur ne supporte pas l\'accès à la caméra.', 'error');
            return;
        }
        try {
            medicalPhoto.video = videoEl;
            medicalPhoto.cameraContainer = containerEl;
            containerEl.style.display = 'block';
            containerEl.style.visibility = 'visible';

            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
            } catch (_) {
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
            }
            activeMedicalStream = stream;
            videoEl.srcObject = stream;
            videoEl.muted = true;
            videoEl.playsInline = true;
            videoEl.setAttribute('playsinline', '');
            await videoEl.play().catch(function (playErr) {
                console.warn('video.play error', playErr);
            });

            if (captureBtn) captureBtn.disabled = false;
            if (closeBtn) closeBtn.style.display = 'inline-flex';
            updateMedicalPhotoStatus('Cadrez puis cliquez sur Capturer.', 'info');
        } catch (e) {
            if (containerEl) containerEl.style.display = 'none';
            const name = e?.name || '';
            const msg = name === 'NotAllowedError' || name === 'PermissionDeniedError'
                ? 'Accès à la caméra refusé. Autorisez-la dans les paramètres du navigateur (icône cadenas dans la barre d\'adresse). Si le blocage persiste, le serveur doit envoyer l\'en-tête Permissions-Policy: camera=(self).'
                : name === 'NotFoundError'
                    ? 'Aucune caméra détectée.'
                    : name === 'SecurityError'
                        ? 'La caméra nécessite HTTPS et l\'en-tête Permissions-Policy: camera=(self) côté serveur.'
                        : 'Caméra indisponible. Utilisez « Choisir un fichier » pour ajouter une photo.';
            updateMedicalPhotoStatus(msg, 'error');
            console.warn('getUserMedia error', e);
        }
    }

    function closeMedicalCamera() {
        if (activeMedicalStream) {
            activeMedicalStream.getTracks().forEach((track) => track.stop());
            activeMedicalStream = null;
        }
        if (medicalPhoto.cameraContainer) {
            medicalPhoto.cameraContainer.style.display = 'none';
        }
        if (medicalPhoto.capture) medicalPhoto.capture.disabled = true;
        if (medicalPhoto.closeCamera) medicalPhoto.closeCamera.style.display = 'none';
    }

    function captureMedicalPhoto() {
        if (!medicalPhoto.video || !medicalPhoto.canvas) return;
        const canvas = medicalPhoto.canvas;
        canvas.width = medicalPhoto.video.videoWidth;
        canvas.height = medicalPhoto.video.videoHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.drawImage(medicalPhoto.video, 0, 0);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
        setMedicalPhoto(dataUrl, 'camera');
        closeMedicalCamera();
    }

    function hydrateMedicalPhoto() {
        const raw = sessionStorage.getItem('medical_photo');
        if (!raw) return;
        try {
            const payload = JSON.parse(raw);
            if (payload?.dataUrl) {
                setMedicalPhoto(payload.dataUrl, payload.source || 'saved');
            }
        } catch (e) {
            console.warn('Medical photo payload invalid', e);
        }
    }

    window.addEventListener('beforeunload', () => {
        if (activeMedicalStream) {
            activeMedicalStream.getTracks().forEach((track) => track.stop());
            activeMedicalStream = null;
        }
    });

    function hydrateConsents() {
        const raw = sessionStorage.getItem('consents_payload');
        if (!raw) return;
        try {
            const payload = JSON.parse(raw);
            Object.entries(consentInputs).forEach(([key, input]) => {
                if (input && typeof payload?.[key] === 'boolean') {
                    input.checked = payload[key];
                }
            });
        } catch (e) {
            console.warn('Consents payload invalid', e);
        }
        updateContinueState();
    }

    function bindConsentListeners() {
        Object.values(consentInputs).forEach((input) => {
            if (!input) return;
            input.addEventListener('change', () => {
                persistConsents();
                updateContinueState();
            });
        });
    }

    function renderGuaranteesTable(list) {
        if (!Array.isArray(list) || !list.length) return '';
        const rows = list.map((g) => {
            const libelle = g.titre || g.nom || g.libelle || g.garantie || 'Garantie';
            const obligatoire = g.obligatoire ? '<span class="obligatoire-badge">Obligatoire</span>' : '';
            const gForCap = { ...g };
            if (
                (gForCap.capitaux == null || gForCap.capitaux === '') &&
                gForCap.description
            ) {
                gForCap.capitaux = gForCap.description;
            }
            const capitaux = formatGuaranteeCapitauxCell(gForCap);
            return `
                <tr>
                    <td>
                        <div class="guarantee-name">${escapeHtml(libelle)} ${obligatoire}</div>
                    </td>
                    <td class="guarantee-capitaux">${capitaux}</td>
                </tr>`;
        }).join('');
        return `
            <div class="product-detail-block">
                <h4>C — Garanties incluses</h4>
                <table class="product-detail-table guarantees-table">
                    <thead>
                        <tr>
                            <th>Garanties</th>
                            <th style="text-align: left;">Capitaux</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>`;
    }

    function renderPrimesGenerees(pg) {
        if (!pg || typeof pg !== 'object') return '';
        const a = (v) => (v != null && v !== '') ? formatPrice(Number(v)) : '—';
        const hasAny = [pg.prime_nette, pg.accessoire, pg.taxes, pg.prime_total].some((v) => v != null && v !== '');
        if (!hasAny) return '';
        return `
            <div class="product-detail-block">
                <h4>Primes générées</h4>
                <table class="product-detail-table primes-table">
                    <tbody>
                        <tr>
                            <td class="char-label">Prime nette</td>
                            <td class="char-value primes-value">${a(pg.prime_nette)}</td>
                        </tr>
                        <tr>
                            <td class="char-label">Accessoire</td>
                            <td class="char-value primes-value">${a(pg.accessoire)}</td>
                        </tr>
                        <tr>
                            <td class="char-label">Taxes</td>
                            <td class="char-value primes-value">${a(pg.taxes)}</td>
                        </tr>
                        <tr class="primes-total-row">
                            <td class="char-label"><strong>Prime total</strong></td>
                            <td class="char-value primes-value"><strong>${a(pg.prime_total)}</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>`;
    }

    function renderProductCharacteristicsTable(product, quote) {
        const zones = (product.zones_geographiques && product.zones_geographiques.zones)
            ? product.zones_geographiques.zones.join(', ') : 'Non précisé';
        
        const rows = [];
        
        if (product.assureur) {
            rows.push(['Assureur', escapeHtml(product.assureur)]);
        }
        if (product.code) {
            rows.push(['Code produit', escapeHtml(product.code)]);
        }
        
        if (product.duree_validite_jours) {
            rows.push(['Durée de validité', `${product.duree_validite_jours} jours`]);
        }
        if (product.duree_min_jours || product.duree_max_jours) {
            const duree = [];
            if (product.duree_min_jours) duree.push(`Min: ${product.duree_min_jours} jours`);
            if (product.duree_max_jours) duree.push(`Max: ${product.duree_max_jours} jours`);
            rows.push(['Durée du séjour', duree.join(' - ')]);
        }
        
        if (product.couverture_multi_entrees !== undefined) {
            rows.push(['Entrées multiples', product.couverture_multi_entrees ? 'Oui' : 'Non']);
        }
        if (product.reconduction_possible !== undefined) {
            rows.push(['Reconduction possible', product.reconduction_possible ? 'Oui' : 'Non']);
        }
        
        if (product.age_minimum || product.age_maximum) {
            const age = [];
            if (product.age_minimum) age.push(`Min: ${product.age_minimum} ans`);
            if (product.age_maximum) age.push(`Max: ${product.age_maximum} ans`);
            rows.push(['Âge', age.length ? age.join(' - ') : 'Non spécifié']);
        }
        if (product.categories_assures && Array.isArray(product.categories_assures) && product.categories_assures.length > 0) {
            rows.push(['Catégories d\'assurés', escapeHtml(product.categories_assures.join(', '))]);
        }
        
        rows.push(['Zones couvertes', escapeHtml(zones)]);
        if (product.zones_geographiques?.pays_eligibles && product.zones_geographiques.pays_eligibles.length > 0) {
            rows.push(['Pays éligibles', escapeHtml(product.zones_geographiques.pays_eligibles.join(', '))]);
        }
        
        if (product.conditions_sante) {
            rows.push(['Conditions de santé', escapeHtml(product.conditions_sante)]);
        }

        if (quote && quote.from_tarif && quote.prix != null) {
            if (quote.prime_assurance != null && quote.frais_services != null && Number(quote.frais_services) > 0) {
                rows.push(['Prime d’assurance (hors frais)', formatPrice(quote.prime_assurance)]);
                rows.push(['Frais de services', formatPrice(quote.frais_services)]);
                rows.push(['Total à payer', formatPrice(quote.prix)]);
            } else {
                rows.push(['Montant estimé (votre profil)', formatPrice(quote.prix)]);
            }
            if (quote.zone_geographique_code) {
                rows.push(['Zone tarifaire (parcours)', escapeHtml(String(quote.zone_geographique_code))]);
            }
            if (quote.tranche_duree_code) {
                rows.push(['Tranche de durée (grille)', escapeHtml(String(quote.tranche_duree_code))]);
            }
            if (quote.tarif_base != null && Number(quote.montant_surprime || 0) > 0) {
                rows.push(['Prime grille avant surprime', formatPrice(quote.tarif_base)]);
            }
            if (quote.montant_surprime != null && Number(quote.montant_surprime) > 0) {
                rows.push(['Surprime âge (sur la prime)', formatPrice(quote.montant_surprime)]);
            }
            if (quote.pct_surprime_applique != null && Number(quote.pct_surprime_applique) > 0) {
                rows.push(['Taux de surprime', `${quote.pct_surprime_applique} %`]);
            }
        } else {
            rows.push(['Prix catalogue', formatPrice(product.cout)]);
        }
        
        rows.push(['Statut', product.est_actif ? '<span class="status-active-badge">Actif</span>' : '<span class="status-inactive-badge">Inactif</span>']);
        
        const tbody = rows.map(([k, v]) => `<tr><td class="char-label">${escapeHtml(k)}</td><td class="char-value">${v}</td></tr>`).join('');
        return `
            <div class="product-detail-block">
                <h4>A — Informations générales</h4>
                <table class="product-detail-table">
                    <tbody>${tbody}</tbody>
                </table>
            </div>`;
    }

    function escapeHtml(s) {
        if (s == null) return '';
        const div = document.createElement('div');
        div.textContent = String(s);
        return div.innerHTML;
    }

    function formatGuaranteeCapitauxCell(g) {
        const raw = g.capitaux ?? g.plafond ?? g.limite;
        if (raw == null || raw === '') return '—';
        if (typeof raw === 'number' && Number.isFinite(raw)) {
            return formatPrice(raw);
        }
        const str = String(raw).trim();
        if (!str) return '—';
        const compact = str.replace(/[\s\u00a0\u202f]/g, '').replace(/,/g, '');
        if (/^\d+$/.test(compact)) {
            return formatPrice(Number(compact));
        }
        return escapeHtml(str);
    }

    function renderExclusions(list) {
        if (!Array.isArray(list) || !list.length) return '';
        const items = list.map((item) => {
            let text;
            if (item && typeof item === 'object') {
                const ref = String(
                    item.reference ?? item.cle ?? item.libelle ?? item.titre ?? ''
                ).trim();
                const exc = String(
                    item.exclusion ?? item.valeur ?? item.description ?? ''
                ).trim();
                if (ref && exc) {
                    text = `${ref} — ${exc}`;
                } else {
                    text = ref || exc || '';
                }
            } else {
                text = String(item);
            }
            return `<li>${escapeHtml(text)}</li>`;
        }).join('');
        return `
            <div class="product-detail-block">
                <h4>C' — Exclusions générales</h4>
                <p class="text-muted small" style="margin:0 0 0.5rem 0;">Renseignements repris pour l’attestation définitive.</p>
                <ul class="exclusions-list">${items}</ul>
            </div>`;
    }

    function closeModal() {
        modal?.classList.remove('show');
    }

});

function showMessage(message, type) {
    const box = document.getElementById('messageBox');
    if (!box) return;
    if (!message) {
        box.style.display = 'none';
        box.textContent = '';
        return;
    }
    box.textContent = message;
    box.className = `message ${type === 'error' ? 'error' : 'success'}`;
    box.style.display = 'block';
}

function goBackToStep1() {
    // Récupérer le projectId depuis l'URL ou sessionStorage
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
    
    // Si on a un projectId, rediriger vers project-wizard.html
    // Sinon, utiliser l'historique du navigateur
    if (projectId) {
        window.location.href = `project-wizard.html?projectId=${projectId}`;
    } else {
        window.location.href = 'project-wizard.html';
    }
}

// Exposer goBackToStep1 globalement
window.goBackToStep1 = goBackToStep1;

