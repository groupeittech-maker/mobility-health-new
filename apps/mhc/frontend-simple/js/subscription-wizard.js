// Wizard "Nouvelle souscription" — calqué sur le parcours mobile Flutter.
// 5 étapes : Voyage, Produit, Médical, Paiement, Attestation.
// Endpoints identiques au mobile :
//   POST /voyages/ + /voyages/:id/documents
//   GET  /products/?filter_by_voyage_assureur=true&...
//   POST /subscriptions/quote-prices
//   POST /subscriptions/start
//   POST /subscriptions/:id/questionnaire/medical
//   POST /subscriptions/:id/evaluate
//   POST /payments/confirm
//   GET  /subscriptions/:id/attestations

(function () {
    'use strict';

    const STEPS = ['Voyage', 'Produit', 'Médical', 'Paiement', 'Attestation'];
    const PAYMENT_METHODS = ['carte_bancaire', 'mobile_money_mtn', 'mobile_money_orange', 'virement'];

    const state = {
        currentStep: 1,
        projetId: null,
        subscriptionId: null,
        montant: 0,
        primeAssurance: null,
        coutPolice: null,
        fraisServices: null,
        taxesTotal: null,
        taxes: null,
        subscriberAge: null,
        user: null,
        // Étape 1
        destinationCountries: [],
        referenceCountries: [],
        cities: [],
        pays: null,
        paysId: null,
        ville: null,
        transport: null,
        residenceCountryRaw: null,
        residenceCountryCode: null,
        mineurs: [],          // {nom, dateNaissance, numeroPasseport, validitePasseport, file}
        enfantVoyageur: null, // même structure
        documents: [],        // {file, docType, label}
        // Étape 2
        products: null,
        canalDistribution: 'assureur',
        selectedCourtierId: null,
        courtiers: [],
        devisParProduit: {},
        surprimesAge: [],
        fraisSurPrimePct: 15,
        exclusionsRead: false,
        medicalPhotoFile: null,
        medicalPhotoDataUrl: null,
        // Étape 3
        medicalAnswers: { malade_souscription: null, malade_12_mois: null, maladie_chronique: null, enceinte: null, voyage_medical: null },
        // Étape 4
        dossierState: 'to_submit', // to_submit | in_review | approved | refused
        dossierLocked: false,
        decisionReasons: [],
    };

    const $ = (id) => document.getElementById(id);

    function fmtMontant(v) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        return `${Math.round(Number(v)).toLocaleString('fr-FR')} XAF`;
    }

    function fmtDate(d) {
        if (!d) return '';
        const dt = d instanceof Date ? d : new Date(d);
        if (isNaN(dt)) return '';
        return `${String(dt.getDate()).padStart(2, '0')}/${String(dt.getMonth() + 1).padStart(2, '0')}/${dt.getFullYear()}`;
    }

    function showMessage(text, type = 'info') {
        const box = $('wizardMessage');
        if (!text) { box.innerHTML = ''; return; }
        const cls = type === 'error' ? 'alert alert-error' : type === 'success' ? 'alert alert-success' : 'alert alert-info';
        box.innerHTML = `<div class="${cls}">${text}</div>`;
    }

    function escapeHtml(s) {
        return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    function normalizeCountry(v) {
        return (v || '').toLowerCase().trim().replace(/\s+/g, '')
            .replace(/[éèêë]/g, 'e').replace(/[àâä]/g, 'a').replace(/[îï]/g, 'i')
            .replace(/[ôö]/g, 'o').replace(/[ùûü]/g, 'u').replace(/ç/g, 'c');
    }

    function isSameCountry(a, b) {
        const na = normalizeCountry(a), nb = normalizeCountry(b);
        return na !== '' && na === nb;
    }

    function isSameCode(a, b) {
        const na = (a || '').trim().toUpperCase(), nb = (b || '').trim().toUpperCase();
        return na !== '' && na === nb;
    }

    function resolveReferenceCountry(value) {
        const raw = (value || '').trim();
        if (!raw) return null;
        for (const c of state.referenceCountries) {
            if (isSameCode(c.code, raw) || isSameCountry(c.nom, raw)) return c;
        }
        for (const c of state.destinationCountries) {
            if (isSameCode(c.code, raw) || isSameCountry(c.nom, raw)) return c;
        }
        return null;
    }

    function isResidenceConflict(country) {
        if (!country) return false;
        return isSameCode(country.code, state.residenceCountryCode) || isSameCountry(country.nom, state.residenceCountryRaw);
    }

    function computeAge(dateNaissance) {
        const d = dateNaissance instanceof Date ? dateNaissance : new Date(dateNaissance);
        if (isNaN(d)) return null;
        const now = new Date();
        let a = now.getFullYear() - d.getFullYear();
        if (now.getMonth() < d.getMonth() || (now.getMonth() === d.getMonth() && now.getDate() < d.getDate())) a--;
        return a;
    }

    async function voyageurAge() {
        const voyageur = document.querySelector('input[name="voyageur"]:checked')?.value || 'adult';
        if (voyageur === 'child_only' && state.enfantVoyageur) {
            state.subscriberAge = computeAge(state.enfantVoyageur.dateNaissance);
            return state.subscriberAge;
        }
        if (state.subscriberAge == null && state.user) {
            state.subscriberAge = computeAge(state.user.date_naissance);
        }
        return state.subscriberAge;
    }

    // ---------- Stepper / navigation ----------
    function renderStepper() {
        const el = $('wizardStepper');
        let html = '';
        STEPS.forEach((label, i) => {
            const stepIndex = i + 1;
            const completed = stepIndex < state.currentStep;
            const active = stepIndex === state.currentStep;
            html += `<div class="mh-step ${completed ? 'completed' : ''} ${active ? 'active' : ''}">
                <div class="mh-step-circle">${completed ? '✓' : stepIndex}</div>
                <div class="mh-step-label">${label}</div>
            </div>`;
            if (i < STEPS.length - 1) {
                html += `<div class="mh-step-connector ${stepIndex < state.currentStep ? 'filled' : ''}"></div>`;
            }
        });
        el.innerHTML = html;
    }

    function showStep(n) {
        state.currentStep = n;
        document.querySelectorAll('.wizard-step').forEach((s) => s.classList.remove('active'));
        const ids = ['', 'step-voyage', 'step-produit', 'step-medical', 'step-paiement', 'step-attestation'];
        $(ids[n]).classList.add('active');
        $('wizardBackRow').style.display = (n > 1 && !state.dossierLocked) ? 'block' : 'none';
        renderStepper();
        showMessage('');
        if (n === 4) syncDossierState();
        if (n === 5) loadAttestations();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function lockDossier() {
        state.dossierLocked = true;
        $('wizardBackRow').style.display = 'none';
    }

    // ---------- Étape 1 : Voyage ----------
    async function loadUser() {
        try {
            state.user = await apiCall('/auth/me');
            state.residenceCountryRaw = (state.user.pays_residence || '').trim();
            syncResidenceCountry();
        } catch (e) { /* le backend garde la validation finale */ }
    }

    function syncResidenceCountry() {
        const resolved = resolveReferenceCountry(state.residenceCountryRaw);
        state.residenceCountryCode = resolved ? resolved.code : null;
        const hint = $('voyageResidenceHint');
        if (state.residenceCountryRaw) {
            const label = resolved ? (resolved.nom || resolved.name || state.residenceCountryRaw) : state.residenceCountryRaw;
            hint.textContent = `Pays de résidence: ${label}`;
            hint.className = 'mh-muted';
        } else {
            hint.textContent = 'Veuillez renseigner votre pays de résidence dans votre profil avant de souscrire.';
            hint.className = 'mh-error-text';
        }
        populatePaysSelect();
    }

    async function loadDestinations() {
        try {
            state.destinationCountries = await apiCall('/destinations/countries?actif_seulement=true&include_cities=false');
        } catch (e) {
            showMessage('Impossible de charger les destinations.', 'error');
        }
        try {
            state.referenceCountries = await apiCall('/destinations/reference-countries');
        } catch (e) { /* fallback : liste destinations */ }
        syncResidenceCountry();
    }

    function populatePaysSelect() {
        const sel = $('voyagePays');
        const options = state.destinationCountries.filter((c) => !isResidenceConflict(c));
        sel.innerHTML = '<option value="">Sélectionner</option>' + options
            .map((c) => `<option value="${c.id}">${escapeHtml(c.nom)}</option>`).join('');
        sel.disabled = !state.residenceCountryRaw;
        if (state.paysId && !options.some((c) => c.id === state.paysId)) {
            state.pays = null; state.paysId = null; state.ville = null;
            sel.value = '';
            populateVilleSelect([]);
        }
    }

    async function loadCities(countryId) {
        const sel = $('voyageVille');
        sel.innerHTML = '<option value="">Chargement des villes...</option>';
        sel.disabled = true;
        try {
            state.cities = await apiCall(`/destinations/countries/${countryId}/cities?actif_seulement=true`);
            populateVilleSelect(state.cities);
        } catch (e) {
            sel.innerHTML = '<option value="">Impossible de charger les villes</option>';
        }
    }

    function populateVilleSelect(cities) {
        const sel = $('voyageVille');
        if (!cities.length) {
            sel.innerHTML = '<option value="">Aucune ville disponible</option>';
            sel.disabled = true;
            return;
        }
        sel.innerHTML = '<option value="">Sélectionner</option>' + cities
            .map((c) => `<option value="${escapeHtml(c.nom)}">${escapeHtml(c.nom)}</option>`).join('');
        sel.disabled = false;
    }

    function updateDuree() {
        const depart = $('voyageDepart').value;
        const retour = $('voyageRetour').value;
        const el = $('voyageDuree');
        if (depart && retour) {
            const days = Math.round((new Date(retour) - new Date(depart)) / 86400000);
            el.value = days > 0 ? `${days} jours` : 'Calcul automatique';
        } else {
            el.value = 'Calcul automatique';
        }
    }

    function dureeJours() {
        const depart = $('voyageDepart').value;
        const retour = $('voyageRetour').value;
        if (!depart || !retour) return null;
        const days = Math.round((new Date(retour) - new Date(depart)) / 86400000);
        return days > 0 ? days : null;
    }

    function voyageurMode() {
        return document.querySelector('input[name="voyageur"]:checked')?.value || 'adult';
    }

    function onVoyageurChange() {
        const mode = voyageurMode();
        $('childOnlyBlock').style.display = mode === 'child_only' ? 'block' : 'none';
        $('withChildrenBlock').style.display = mode === 'with_children' ? 'block' : 'none';
        if (mode !== 'child_only' && state.enfantVoyageur) {
            state.documents = state.documents.filter((d) => d.file !== state.enfantVoyageur.file);
            state.enfantVoyageur = null;
        }
        if (mode !== 'with_children' && state.mineurs.length) {
            const files = new Set(state.mineurs.map((m) => m.file));
            state.documents = state.documents.filter((d) => !files.has(d.file));
            state.mineurs = [];
        }
        renderChildren();
        renderDocs();
    }

    function fmtDateInput(v) {
        // v = 'YYYY-MM-DD' -> 'JJ/MM/AAAA'
        if (!v) return '';
        const [y, m, d] = v.split('-');
        return `${d}/${m}/${y}`;
    }

    function renderChildren() {
        const coList = $('childOnlyList');
        const minList = $('minorsList');
        coList.innerHTML = '';
        minList.innerHTML = '';
        $('childOnlyEmpty').style.display = state.enfantVoyageur ? 'none' : 'block';
        $('minorsEmpty').style.display = state.mineurs.length ? 'none' : 'block';

        const itemHtml = (m, target) => `
            <div class="mh-list-item">
                <div class="grow">
                    <div style="font-weight:600;">${escapeHtml(m.nom)}</div>
                    <div class="mh-muted">Né(e) le ${fmtDateInput(m.dateNaissance)} · Passeport ${escapeHtml(m.numeroPasseport)} · Valide jusqu'au ${fmtDateInput(m.validitePasseport)}</div>
                </div>
                <button type="button" class="mh-icon-danger" data-remove="${target}" title="Supprimer">🗑</button>
            </div>`;
        if (state.enfantVoyageur) coList.innerHTML = itemHtml(state.enfantVoyageur, 'enfant');
        state.mineurs.forEach((m, i) => { minList.innerHTML += itemHtml(m, `mineur-${i}`); });
    }

    // Modal enfant — champ fichier conservé dans l'input jusqu'à validation
    let minorTarget = null; // 'enfant' | 'mineur'
    function openMinorModal(target) {
        minorTarget = target;
        $('minorNom').value = ''; $('minorNaissance').value = '';
        $('minorPasseport').value = ''; $('minorValidite').value = ''; $('minorPhoto').value = '';
        $('minorModal').classList.add('open');
    }
    function closeMinorModal() { $('minorModal').classList.remove('open'); }

    function saveMinor() {
        const nom = $('minorNom').value.trim();
        const naissance = $('minorNaissance').value;
        const passeport = $('minorPasseport').value.trim();
        const validite = $('minorValidite').value;
        const file = $('minorPhoto').files[0];
        if (!nom || !naissance || !passeport || !validite || !file) {
            showMessage('Tous les champs de l\'enfant sont requis (dont la photo du passeport).', 'error');
            return;
        }
        const entry = { nom, dateNaissance: naissance, numeroPasseport: passeport, validitePasseport: validite, file };
        const label = minorTarget === 'enfant'
            ? `Passeport (enfant voyageur) — ${nom}`
            : `Passeport (enfant) — ${nom}`;
        if (minorTarget === 'enfant') state.enfantVoyageur = entry;
        else state.mineurs.push(entry);
        state.documents.push({ file, docType: 'passport', label });
        closeMinorModal();
        renderChildren();
        renderDocs();
        showMessage('');
    }

    function renderDocs() {
        const list = $('docsList');
        list.innerHTML = state.documents.map((d, i) => `
            <div class="mh-list-item">
                <div class="grow">
                    <div style="font-weight:600;">${escapeHtml(d.label)}</div>
                    <div class="mh-muted">${escapeHtml(d.file.name)}</div>
                </div>
                <button type="button" class="mh-icon-danger" data-doc-remove="${i}" title="Supprimer">🗑</button>
            </div>`).join('');
    }

    async function onVoyageContinue() {
        // Validations identiques au mobile
        if (!state.residenceCountryRaw) {
            showMessage('Veuillez d\'abord renseigner votre pays de résidence dans votre profil avant de souscrire.', 'error');
            return;
        }
        const paysId = parseInt($('voyagePays').value, 10);
        const ville = $('voyageVille').value;
        const transport = $('voyageTransport').value;
        $('voyagePaysError').style.display = paysId ? 'none' : 'inline';
        $('voyageVilleError').style.display = ville ? 'none' : 'inline';
        if (!paysId || !ville) return;
        const country = state.destinationCountries.find((c) => c.id === paysId);
        if (isResidenceConflict(country)) {
            showMessage('Le pays de destination doit être différent de votre pays de résidence.', 'error');
            return;
        }
        if (!transport) { showMessage('Veuillez choisir un moyen de transport.', 'error'); return; }
        if (voyageurMode() === 'child_only' && !state.enfantVoyageur) {
            showMessage('Veuillez ajouter les informations de l\'enfant voyageur.', 'error');
            return;
        }

        const dateDepart = $('voyageDepart').value;
        const dateRetour = $('voyageRetour').value;
        const btn = $('voyageContinueBtn');
        btn.disabled = true;
        btn.textContent = 'Enregistrement en cours...';
        showMessage('');

        try {
            const mode = voyageurMode();
            const mineurs = mode === 'child_only'
                ? (state.enfantVoyageur ? [state.enfantVoyageur] : null)
                : (mode === 'with_children' && state.mineurs.length ? state.mineurs : null);

            // Notes identiques au mobile
            const residenceLabel = (resolveReferenceCountry(state.residenceCountryRaw) || {}).nom || state.residenceCountryRaw;
            const notesLines = [
                `Pays de résidence: ${residenceLabel}`,
                `Pays de destination: ${country.nom}`,
                `Ville de destination: ${ville}`,
                `Moyen de transport: ${transport}`,
            ];
            if (mineurs && mineurs.length) {
                if (mode === 'child_only') {
                    const child = mineurs[0];
                    notesLines.push(
                        'Pour un tiers: oui',
                        '=== INFORMATIONS DU TIERS (BÉNÉFICIAIRE) ===',
                        `Nom du tiers: ${child.nom}`,
                        `Date de naissance du tiers: ${fmtDateInput(child.dateNaissance)}`,
                        `Numéro de passeport du tiers: ${child.numeroPasseport}`,
                        `Date d'expiration du passeport du tiers: ${fmtDateInput(child.validitePasseport)}`,
                        '=== FIN INFORMATIONS DU TIERS ==='
                    );
                } else {
                    notesLines.push('Mineurs accompagnés: ' + mineurs
                        .map((m) => `${m.nom} (né(e) le ${fmtDateInput(m.dateNaissance)}); passeport ${m.numeroPasseport}; validité ${fmtDateInput(m.validitePasseport)}`)
                        .join('; '));
                }
            }

            state.voyageData = {
                titre: `Voyage vers ${ville}, ${country.nom}`,
                destination: ville,
                destinationCountryId: paysId,
                destinationCountryName: country.nom,
                destinationCityName: ville,
                residenceCountryName: residenceLabel,
                dateDepart: dateDepart ? new Date(dateDepart).toISOString() : new Date().toISOString(),
                dateRetour: dateRetour ? new Date(dateRetour).toISOString() : null,
                nombreParticipants: 1,
                dureeJours: dureeJours(),
                isChildOnly: mode === 'child_only',
            };

            const projet = await apiCall('/voyages/', {
                method: 'POST',
                body: JSON.stringify({
                    titre: state.voyageData.titre,
                    destination: state.voyageData.destination,
                    date_depart: state.voyageData.dateDepart,
                    date_retour: state.voyageData.dateRetour,
                    nombre_participants: 1,
                    notes: notesLines.join('\n'),
                    destination_country_id: paysId,
                }),
            });
            state.projetId = projet.id;

            // Upload séquentiel des pièces justificatives
            for (const doc of state.documents) {
                const fd = new FormData();
                fd.append('doc_type', doc.docType);
                fd.append('file', doc.file);
                try {
                    await apiCall(`/voyages/${projet.id}/documents`, { method: 'POST', body: fd });
                } catch (docErr) {
                    showMessage(`La pièce « ${doc.label} » n'a pas pu être téléversée.`, 'error');
                }
            }

            await loadProductsForVoyage();
            await fetchDevisPrices();
            showStep(2);
        } catch (e) {
            showMessage(e.message || 'Erreur lors de la création du voyage.', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Continuer vers le choix du produit';
        }
    }

    // ---------- Étape 2 : Produit ----------
    async function loadCourtiersForProducts(products) {
        const assureurIds = [...new Set(products.map((p) => p.assureur_id).filter(Boolean))].sort();
        if (!assureurIds.length) return [];
        const byId = {};
        for (const aid of assureurIds) {
            try {
                const rows = await apiCall(`/courtiers/?assureur_id=${aid}`);
                (Array.isArray(rows) ? rows : []).forEach((c) => { if (c.id != null) byId[c.id] = c; });
            } catch (e) {
                if (e.status !== 404) throw e;
            }
        }
        let list = Object.values(byId);
        if (!list.length) {
            try {
                const all = await apiCall('/courtiers/');
                list = (Array.isArray(all) ? all : []).filter((c) => c.assureur_id != null && assureurIds.includes(c.assureur_id));
            } catch (e) {
                if (e.status === 404) return [];
                throw e;
            }
        }
        list.sort((a, b) => (a.nom || '').localeCompare(b.nom || ''));
        return list;
    }

    async function loadProductsForVoyage() {
        $('productsLoading').style.display = 'block';
        $('productsList').innerHTML = '';
        try {
            const params = new URLSearchParams({
                limit: '500',
                est_actif: 'true',
                filter_by_voyage_assureur: 'true',
                canal_distribution: state.canalDistribution,
            });
            if (state.voyageData?.residenceCountryName) params.set('residence_country_name', state.voyageData.residenceCountryName);
            if (state.voyageData?.destinationCountryId) params.set('destination_country_id', state.voyageData.destinationCountryId);
            if (state.voyageData?.destinationCountryName) params.set('destination_country_name', state.voyageData.destinationCountryName);
            if (state.selectedCourtierId) params.set('courtier_id', state.selectedCourtierId);
            const rawProducts = await apiCall(`/products/?${params.toString()}`);
            state.products = Array.isArray(rawProducts) ? rawProducts : [];
            state.courtiers = await loadCourtiersForProducts(state.products);
            if (state.selectedCourtierId && !state.courtiers.some((c) => c.id === state.selectedCourtierId)) {
                state.selectedCourtierId = null;
            }
            renderCourtierSelect();
            renderProducts();
        } catch (e) {
            state.products = [];
            $('productsList').innerHTML = `<div class="alert alert-error">Impossible de charger les produits : ${escapeHtml(e.message)}</div>`;
        } finally {
            $('productsLoading').style.display = 'none';
        }
    }

    async function fetchDevisPrices() {
        if (!state.projetId || !state.products?.length) return;
        try {
            const age = await voyageurAge();
            const body = {
                projet_voyage_id: state.projetId,
                produit_assurance_ids: state.products.map((p) => p.id),
            };
            if (state.voyageData?.destinationCountryId) body.destination_country_id = state.voyageData.destinationCountryId;
            if (state.voyageData?.dureeJours) body.duree_jours = state.voyageData.dureeJours;
            if (age != null) body.age = age;
            const result = await apiCall('/subscriptions/quote-prices', { method: 'POST', body: JSON.stringify(body) });
            state.devisParProduit = {};
            (result.quotes || []).forEach((q) => { state.devisParProduit[q.produit_assurance_id] = q; });
            state.surprimesAge = result.surprimes_age_reference || [];
            state.fraisSurPrimePct = result.frais_services_sur_prime_pct ?? 15;
            renderProducts();
        } catch (e) { /* devis non bloquant */ }
    }

    function renderCourtierSelect() {
        const wrap = $('courtierSelectWrap');
        const sel = $('courtierSelect');
        if (state.canalDistribution !== 'courtier') { wrap.style.display = 'none'; return; }
        wrap.style.display = 'block';
        sel.innerHTML = '<option value="">Sélectionner un courtier</option>' + state.courtiers
            .map((c) => `<option value="${c.id}">${escapeHtml(c.nom)}</option>`).join('');
        if (state.selectedCourtierId) sel.value = state.selectedCourtierId;
    }

    function trancheLabel(q) {
        const map = { '1_7': '1 à 7 jours', '8_15': '8 à 15 jours', '16_30': '16 à 30 jours', '31_60': '31 à 60 jours', '61_90': '61 à 90 jours' };
        if (q?.tranche_duree_code && map[q.tranche_duree_code]) return map[q.tranche_duree_code];
        if (q?.duree_min_jours != null && q?.duree_max_jours != null) return `${q.duree_min_jours}–${q.duree_max_jours} jours`;
        return q?.tranche_duree_code || null;
    }

    function renderProducts() {
        const list = $('productsList');
        if (!state.products) return;
        if (!state.products.length) {
            list.innerHTML = '<div class="mh-card"><p class="mh-muted">Aucun produit disponible pour ce voyage.</p></div>';
            return;
        }
        list.innerHTML = state.products.map((p) => {
            const q = state.devisParProduit[p.id];
            const tranche = trancheLabel(q);
            const logo = p.assureur_logo_url || p.logo_url || '';
            return `<div class="mh-product-card" data-product-id="${p.id}">
                <div class="mh-product-head">
                    ${logo ? `<img class="mh-product-logo" src="${escapeHtml(logo)}" alt="">` : ''}
                    <div class="grow">
                        <div class="mh-product-name">${escapeHtml(p.nom)}</div>
                        <div class="mh-product-sub">${escapeHtml(p.assureur || '')}${tranche ? ` · ${tranche}` : ''}</div>
                    </div>
                    <span class="mh-badge">Actif</span>
                </div>
                <div style="display:flex; align-items:center; justify-content:space-between; margin-top:10px; flex-wrap:wrap; gap:8px;">
                    <div class="mh-price">${q ? fmtMontant(q.prix_applique) : fmtMontant(p.prix)}</div>
                    <div>
                        <button type="button" class="btn btn-outline btn-sm" data-details="${p.id}">Voir les détails</button>
                        <button type="button" class="btn btn-primary btn-sm" data-select="${p.id}">Sélectionner</button>
                    </div>
                </div>
            </div>`;
        }).join('');
        updateProduitContinueState();
    }

    let selectedProductId = null;

    function updateProduitContinueState() {
        const ok = selectedProductId && state.medicalPhotoDataUrl && $('consentCG').checked && $('consentExclusions').checked;
        $('produitContinueBtn').disabled = !ok;
        document.querySelectorAll('.mh-product-card').forEach((card) => {
            card.classList.toggle('selected', parseInt(card.dataset.productId, 10) === selectedProductId);
            const btn = card.querySelector('[data-select]');
            if (btn) btn.textContent = parseInt(card.dataset.productId, 10) === selectedProductId ? 'Sélectionné' : 'Sélectionner';
        });
    }

    function openProductModal(productId) {
        const p = state.products.find((x) => x.id === productId);
        const q = state.devisParProduit[productId];
        if (!p) return;
        $('productModalTitle').textContent = p.nom;
        const garanties = (p.garanties || []).map((g) =>
            `<tr><td>${escapeHtml(g.titre || g.nom || '')}</td><td>${escapeHtml(g.capitaux || g.montant || '')}</td></tr>`).join('');
        const exclusions = (p.exclusions_generales || []).map((e) =>
            `<li>${escapeHtml(e.titre || e.nom || e.libelle || e)}</li>`).join('');
        const taxesRows = (q?.taxes || []).map((t) =>
            `<tr><td>Taxe additionnelle (${escapeHtml(t.nom || t.code || '')})</td><td>${fmtMontant(t.montant)}</td></tr>`).join('');
        $('productModalBody').innerHTML = `
            <p class="mh-muted">${escapeHtml(p.assureur || '')}</p>
            ${q ? `
            <div class="mh-sub-title">Informations du devis</div>
            <table class="mh-price-table">
                ${state.subscriberAge != null ? `<tr><td>Âge du souscripteur</td><td>${state.subscriberAge} ans</td></tr>` : ''}
                ${q.zone_libelle_fr ? `<tr><td>Zone tarifaire</td><td>${escapeHtml(q.zone_libelle_fr)}</td></tr>` : ''}
                ${state.voyageData?.residenceCountryName ? `<tr><td>Pays de résidence</td><td>${escapeHtml(state.voyageData.residenceCountryName)}</td></tr>` : ''}
                ${state.voyageData?.destinationCountryName ? `<tr><td>Pays de destination</td><td>${escapeHtml(state.voyageData.destinationCountryName)}</td></tr>` : ''}
                ${state.voyageData?.dureeJours ? `<tr><td>Durée du voyage</td><td>${state.voyageData.dureeJours} jours</td></tr>` : ''}
                ${trancheLabel(q) ? `<tr><td>Tranche durée (grille)</td><td>${trancheLabel(q)}</td></tr>` : ''}
            </table>
            <div class="mh-sub-title">Décompte de la prime</div>
            <table class="mh-price-table">
                <tr><td>Prime Nette</td><td>${fmtMontant(q.prime_assurance)}</td></tr>
                <tr><td>Coût de Police</td><td>${fmtMontant(q.cout_police)}</td></tr>
                ${q.taxes_total != null ? `<tr><td>Taxe</td><td>${fmtMontant(q.taxes_total)}</td></tr>` : ''}
                ${taxesRows}
                <tr class="total"><td>Prime Nette Totale</td><td>${fmtMontant(q.prix_applique)}</td></tr>
            </table>` : ''}
            ${state.surprimesAge.length ? `
            <div class="mh-sub-title">Surprimes par âge</div>
            <table class="mh-price-table">${state.surprimesAge.map((s) => `<tr><td>${escapeHtml(s.tranche)}</td><td>+${s.pct}%</td></tr>`).join('')}</table>` : ''}
            ${garanties ? `<div class="mh-sub-title">Garanties principales</div><table class="mh-price-table">${garanties}</table>` : ''}
            ${exclusions ? `<div class="mh-sub-title">Exclusions générales</div><ul class="mh-muted">${exclusions}</ul>` : ''}
            <div class="mh-check-row" style="margin-top:12px;">
                <input type="checkbox" id="modalExclusionsRead">
                <label for="modalExclusionsRead">J'ai lu les exclusions</label>
            </div>`;
        const okBtn = $('productModalOk');
        okBtn.disabled = true;
        $('modalExclusionsRead').addEventListener('change', (e) => { okBtn.disabled = !e.target.checked; });
        okBtn.onclick = () => {
            state.exclusionsRead = true;
            $('consentExclusions').disabled = false;
            $('consentExclusions').checked = true;
            $('productModal').classList.remove('open');
            updateProduitContinueState();
        };
        $('productModal').classList.add('open');
    }

    async function onProduitContinue() {
        if (!selectedProductId || !state.projetId) return;
        const btn = $('produitContinueBtn');
        btn.disabled = true;
        btn.textContent = 'Création du dossier...';
        showMessage('');
        try {
            const age = await voyageurAge();
            let courtierId = null;
            if (state.canalDistribution === 'courtier') {
                const product = state.products.find((p) => p.id === selectedProductId);
                const aid = product?.assureur_id;
                if (state.selectedCourtierId) {
                    const sel = state.courtiers.find((c) => c.id === state.selectedCourtierId && c.assureur_id === aid);
                    if (sel) courtierId = sel.id;
                }
                if (courtierId == null && aid != null) {
                    const linked = state.courtiers.filter((c) => c.assureur_id === aid);
                    if (linked.length) courtierId = linked[0].id;
                }
                if (courtierId == null) throw new Error('Aucun courtier éligible n\'a été trouvé pour ce produit.');
            }
            const sub = await apiCall('/subscriptions/start', {
                method: 'POST',
                body: JSON.stringify({
                    produit_assurance_id: selectedProductId,
                    projet_voyage_id: state.projetId,
                    date_debut: state.voyageData?.dateDepart,
                    destination_country_id: state.voyageData?.destinationCountryId,
                    canal_distribution: state.canalDistribution,
                    courtier_id: courtierId,
                    duree_jours: state.voyageData?.dureeJours,
                    age: age,
                }),
            });
            state.subscriptionId = sub.id;
            state.montant = sub.prix_applique || 0;
            state.primeAssurance = sub.prime_assurance;
            state.coutPolice = sub.cout_police;
            state.fraisServices = sub.frais_services;
            state.taxesTotal = sub.taxes_total;
            state.taxes = sub.taxes;
            renderMedicalPhotoSummary();
            showStep(3);
        } catch (e) {
            showMessage(e.message || 'Erreur lors de la création de la souscription.', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Continuer vers les formulaires';
            updateProduitContinueState();
        }
    }

    // ---------- Étape 3 : Médical ----------
    function renderMedicalPhotoSummary() {
        const box = $('medicalPhotoSummary');
        box.innerHTML = `
            <div class="mh-sub-title">Photo e-carte</div>
            <div style="display:flex; align-items:center; gap:12px;">
                ${state.medicalPhotoDataUrl ? `<img class="mh-photo-preview" src="${state.medicalPhotoDataUrl}" alt="Photo e-carte">` : ''}
                <span class="mh-muted">${escapeHtml(state.medicalPhotoFile?.name || '')}</span>
            </div>`;
    }

    function updatePregnancyState() {
        const wrap = $('moisGrossesseWrap');
        const notice = $('pregnancyNotice');
        const enceinte = state.medicalAnswers.enceinte;
        wrap.style.display = enceinte === 'oui' ? 'block' : 'none';
        if (enceinte !== 'oui') { $('moisGrossesse').value = ''; }
        const months = parseInt($('moisGrossesse').value, 10);
        const ineligible = enceinte === 'oui' && !isNaN(months) && months > 5;
        notice.style.display = ineligible ? 'block' : 'none';
        $('medicalContinueBtn').disabled = ineligible;
    }

    async function onMedicalContinue() {
        const a = state.medicalAnswers;
        if (a.enceinte === 'oui') {
            const months = parseInt($('moisGrossesse').value, 10);
            if (isNaN(months) || months < 1) { showMessage('Veuillez indiquer le nombre de mois de grossesse.', 'error'); return; }
            if (months > 5) { showMessage('Vous n\'êtes pas éligible pour être assuré par nos services (grossesse de plus de 5 mois).', 'error'); return; }
        }
        if (Object.values(a).some((v) => v === null)) {
            showMessage('Veuillez répondre à toutes les questions médicales.', 'error');
            return;
        }
        if (!$('declarationSante').checked) {
            showMessage('Veuillez accepter la déclaration santé.', 'error');
            return;
        }
        const btn = $('medicalContinueBtn');
        btn.disabled = true;
        btn.textContent = 'Envoi en cours...';
        showMessage('');
        try {
            const mois = a.enceinte === 'oui' ? parseInt($('moisGrossesse').value, 10) : null;
            const reponses = {
                version: 'simplified_v1',
                declaration_sante: true,
                date_soumission: new Date().toISOString(),
                malade_souscription: a.malade_souscription, maladeSouscription: a.malade_souscription,
                malade_12_mois: a.malade_12_mois, malade12Mois: a.malade_12_mois,
                maladie_chronique: a.maladie_chronique, maladieChronique: a.maladie_chronique,
                enceinte: a.enceinte, pregnancy: a.enceinte,
                voyage_medical: a.voyage_medical, voyageMedical: a.voyage_medical,
            };
            if (mois != null) { reponses.mois_grossesse = mois; reponses.moisGrossesse = mois; }
            if (state.medicalPhotoDataUrl) {
                reponses.photo_medicale = state.medicalPhotoDataUrl;
                reponses.photoMedicale = state.medicalPhotoDataUrl;
                reponses.photo_identity = state.medicalPhotoDataUrl;
            }

            await apiCall(`/subscriptions/${state.subscriptionId}/questionnaire/medical`, {
                method: 'POST',
                body: JSON.stringify(reponses),
            });
            showStep(4);
        } catch (e) {
            showMessage(e.message || 'Erreur lors de l\'envoi du questionnaire.', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Continuer vers le paiement';
        }
    }

    // ---------- Étape 4 : Paiement ----------
    function renderPaiementState() {
        $('paiementLoading').style.display = 'none';
        $('paiementContent').style.display = 'block';
        $('payStateSubmit').style.display = state.dossierState === 'to_submit' ? 'block' : 'none';
        $('payStateReview').style.display = state.dossierState === 'in_review' ? 'block' : 'none';
        $('payStateApproved').style.display = state.dossierState === 'approved' ? 'block' : 'none';
        $('payStateRefused').style.display = state.dossierState === 'refused' ? 'block' : 'none';
        if (state.dossierState === 'refused') {
            $('refusedReasons').innerHTML = state.decisionReasons.map((r) => `<li>${escapeHtml(r)}</li>`).join('');
        }
        if (state.dossierState === 'in_review' && state.decisionReasons.length) {
            $('reviewReasons').innerHTML = `<ul class="mh-muted">${state.decisionReasons.map((r) => `<li>${escapeHtml(r)}</li>`).join('')}</ul>`;
        }
        if (state.dossierState === 'approved') renderPriceBreakdown();
    }

    function renderPriceBreakdown() {
        const rows = [];
        rows.push(`<tr><td>Prime Nette</td><td>${fmtMontant(state.primeAssurance)}</td></tr>`);
        rows.push(`<tr><td>Coût de Police</td><td>${fmtMontant(state.coutPolice)}</td></tr>`);
        if (state.taxesTotal != null) rows.push(`<tr><td>Taxe</td><td>${fmtMontant(state.taxesTotal)}</td></tr>`);
        (state.taxes || []).forEach((t) => {
            if ((t.montant || 0) > 0) rows.push(`<tr><td>Taxe additionnelle (${escapeHtml(t.nom || t.code || '')})</td><td>${fmtMontant(t.montant)}</td></tr>`);
        });
        rows.push(`<tr class="total"><td>Total à payer</td><td>${fmtMontant(state.montant)}</td></tr>`);
        $('priceBreakdown').innerHTML = rows.join('');
    }

    async function syncDossierState(showFeedback = false) {
        if (!state.subscriptionId) return;
        try {
            const sub = await apiCall(`/subscriptions/${state.subscriptionId}`);
            const previous = state.dossierState;
            if (sub.statut === 'en_attente_paiement') state.dossierState = 'approved';
            else if (sub.statut === 'en_attente_validation') state.dossierState = 'in_review';
            else if (sub.statut === 'refusee') state.dossierState = 'refused';
            // Mettre à jour les montants depuis le serveur
            state.montant = sub.prix_applique > 0 ? sub.prix_applique
                : (sub.prime_assurance || 0) + (sub.cout_police || 0) + (sub.frais_services || 0) + (sub.taxes_total || 0);
            state.primeAssurance = sub.prime_assurance;
            state.coutPolice = sub.cout_police;
            state.fraisServices = sub.frais_services;
            state.taxesTotal = sub.taxes_total;
            state.taxes = sub.taxes;
            if (state.dossierState !== 'to_submit') lockDossier();
            renderPaiementState();
            if (showFeedback && state.dossierState === 'in_review' && previous === 'in_review') {
                showMessage('Le dossier est toujours en cours de validation.', 'info');
            }
        } catch (e) {
            $('paiementLoading').style.display = 'none';
            if (showFeedback) showMessage('Impossible de vérifier le statut pour le moment.', 'error');
        }
    }

    async function submitDossier() {
        const btn = $('submitDossierBtn');
        btn.disabled = true;
        btn.textContent = 'Soumission en cours...';
        showMessage('');
        try {
            const age = await voyageurAge();
            const result = await apiCall(`/subscriptions/${state.subscriptionId}/evaluate`, {
                method: 'POST',
                body: JSON.stringify(age != null ? { voyageur_age: age } : {}),
            });
            const decision = (result.decision || '').toString();
            state.decisionReasons = (result.reasons || []).map((r) => r.toString());
            if (decision === 'approve') state.dossierState = 'approved';
            else if (decision === 'review') state.dossierState = 'in_review';
            else state.dossierState = 'refused';
            lockDossier();
            renderPaiementState();
        } catch (e) {
            showMessage(e.message || 'Erreur lors de la soumission.', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Soumettre le dossier';
        }
    }

    async function payNow() {
        const btn = $('payNowBtn');
        btn.disabled = true;
        btn.textContent = 'Paiement en cours...';
        showMessage('');
        try {
            const sub = await apiCall(`/subscriptions/${state.subscriptionId}`);
            let montant = sub.prix_applique > 0 ? sub.prix_applique : state.montant;
            if (montant <= 0 && sub.prime_assurance != null && sub.frais_services != null) {
                montant = sub.prime_assurance + (sub.cout_police || 0) + sub.frais_services + (sub.taxes_total || 0);
            }
            if (montant <= 0) throw new Error('Montant de paiement invalide pour cette souscription.');
            const methode = document.querySelector('input[name="payMethod"]:checked')?.value || 'carte_bancaire';
            const age = await voyageurAge();
            const body = {
                souscription_id: state.subscriptionId,
                montant: montant.toFixed(2),
                methode_paiement: methode,
            };
            if (age != null) body.age = age;
            await apiCall('/payments/confirm', { method: 'POST', body: JSON.stringify(body) });
            showStep(5);
        } catch (e) {
            showMessage(e.message || 'Erreur lors du paiement.', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Payer maintenant';
        }
    }

    // ---------- Étape 5 : Attestation ----------
    async function loadAttestations() {
        $('attestationsLoading').style.display = 'block';
        $('attestationsList').innerHTML = '';
        try {
            const list = await apiCall(`/subscriptions/${state.subscriptionId}/attestations`);
            $('attestationsList').innerHTML = list.map((att) => `
                <div class="mh-card" style="display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;">
                    <div>
                        <div style="font-weight:700;">Attestation ${escapeHtml(att.numero_attestation || att.id)}</div>
                        <div class="mh-muted">${escapeHtml(att.statut || '')} · ${att.type_attestation === 'definitive' ? 'Définitive' : escapeHtml(att.type_attestation || '')}</div>
                    </div>
                    <div>
                        <button type="button" class="btn btn-outline btn-sm" data-att-pdf="${att.id}">📄 PDF</button>
                        ${(att.carte_numerique_url || att.carte_numerique_path) ? `<button type="button" class="btn btn-outline btn-sm" data-att-ecard="${att.id}">💳 E-carte</button>` : ''}
                    </div>
                </div>`).join('') || '<div class="mh-card"><p class="mh-muted">Attestation en cours de génération…</p></div>';
            $('attestationDoneBtn').style.display = 'block';
        } catch (e) {
            $('attestationsList').innerHTML = `<div class="alert alert-error">${escapeHtml(e.message)}</div>`;
        } finally {
            $('attestationsLoading').style.display = 'none';
        }
    }

    async function downloadFile(path, filename) {
        const token = window.MobilityAuth?.getAccessToken?.() || localStorage.getItem('access_token');
        const url = `${window.API_BASE_URL}${path}`;
        const resp = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
        if (!resp.ok) throw new Error(`Téléchargement impossible (${resp.status})`);
        const blob = await resp.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
    }

    // ---------- Reprise d'un dossier ----------
    async function resumeSubscription(subscriptionId) {
        try {
            const sub = await apiCall(`/subscriptions/${subscriptionId}`);
            state.subscriptionId = sub.id;
            state.projetId = sub.projet_voyage_id;
            state.montant = sub.prix_applique > 0 ? sub.prix_applique
                : (sub.prime_assurance || 0) + (sub.cout_police || 0) + (sub.frais_services || 0) + (sub.taxes_total || 0);
            state.primeAssurance = sub.prime_assurance;
            state.coutPolice = sub.cout_police;
            state.fraisServices = sub.frais_services;
            state.taxesTotal = sub.taxes_total;
            state.taxes = sub.taxes;
            if (sub.statut !== 'en_attente') lockDossier();
            showStep(sub.statut === 'en_attente' ? 3 : 4);
        } catch (e) {
            showMessage(e.message || 'Impossible de reprendre ce dossier.', 'error');
            showStep(1);
        }
    }

    // ---------- Wiring ----------
    function bindEvents() {
        $('voyagePays').addEventListener('change', (e) => {
            const id = parseInt(e.target.value, 10);
            const country = state.destinationCountries.find((c) => c.id === id);
            if (!state.residenceCountryRaw) {
                showMessage('Veuillez d\'abord renseigner votre pays de résidence dans votre profil avant de souscrire.', 'error');
                e.target.value = '';
                return;
            }
            if (isResidenceConflict(country)) {
                showMessage('Le pays de destination doit être différent de votre pays de résidence.', 'error');
                e.target.value = '';
                return;
            }
            state.paysId = id || null;
            state.pays = country ? country.nom : null;
            state.ville = null;
            $('voyagePaysError').style.display = 'none';
            if (id) loadCities(id); else populateVilleSelect([]);
        });
        $('voyageVille').addEventListener('change', (e) => {
            state.ville = e.target.value || null;
            $('voyageVilleError').style.display = 'none';
        });
        $('voyageTransport').addEventListener('change', (e) => { state.transport = e.target.value; });
        $('voyageDepart').addEventListener('change', updateDuree);
        $('voyageRetour').addEventListener('change', updateDuree);
        document.querySelectorAll('input[name="voyageur"]').forEach((r) => r.addEventListener('change', onVoyageurChange));
        $('addChildOnlyBtn').addEventListener('click', () => openMinorModal('enfant'));
        $('addMinorBtn').addEventListener('click', () => openMinorModal('mineur'));
        $('closeMinorModal').addEventListener('click', closeMinorModal);
        $('cancelMinorBtn').addEventListener('click', closeMinorModal);
        $('saveMinorBtn').addEventListener('click', saveMinor);

        document.querySelectorAll('.mh-doc-chip').forEach((chip) => {
            chip.addEventListener('click', () => {
                const input = $('docFileInput');
                input.dataset.docType = chip.dataset.doctype;
                input.dataset.docLabel = chip.dataset.doclabel;
                input.value = '';
                input.click();
            });
        });
        $('docFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            state.documents.push({ file, docType: e.target.dataset.docType, label: e.target.dataset.docLabel });
            renderDocs();
        });

        $('docsList').addEventListener('click', (e) => {
            const idx = e.target.dataset?.docRemove;
            if (idx !== undefined) { state.documents.splice(parseInt(idx, 10), 1); renderDocs(); }
        });
        $('minorsList').addEventListener('click', (e) => {
            const key = e.target.dataset?.remove;
            if (key?.startsWith('mineur-')) {
                const i = parseInt(key.split('-')[1], 10);
                const m = state.mineurs[i];
                state.documents = state.documents.filter((d) => d.file !== m.file);
                state.mineurs.splice(i, 1);
                renderChildren(); renderDocs();
            }
        });
        $('childOnlyList').addEventListener('click', (e) => {
            if (e.target.dataset?.remove === 'enfant') {
                state.documents = state.documents.filter((d) => d.file !== state.enfantVoyageur.file);
                state.enfantVoyageur = null;
                renderChildren(); renderDocs();
            }
        });

        $('voyageContinueBtn').addEventListener('click', onVoyageContinue);

        // Étape 2
        document.querySelectorAll('input[name="canal"]').forEach((r) => {
            r.addEventListener('change', async (e) => {
                state.canalDistribution = e.target.value;
                renderCourtierSelect();
                if (state.voyageData) { await loadProductsForVoyage(); await fetchDevisPrices(); }
            });
        });
        $('courtierSelect').addEventListener('change', async (e) => {
            state.selectedCourtierId = parseInt(e.target.value, 10) || null;
            if (state.voyageData && state.canalDistribution === 'courtier') { await loadProductsForVoyage(); await fetchDevisPrices(); }
        });
        $('productsList').addEventListener('click', (e) => {
            const selId = e.target.dataset?.select;
            const detId = e.target.dataset?.details;
            if (selId) { selectedProductId = parseInt(selId, 10); updateProduitContinueState(); }
            if (detId) openProductModal(parseInt(detId, 10));
        });
        $('closeProductModal').addEventListener('click', () => $('productModal').classList.remove('open'));
        $('ecardPhotoInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) { state.medicalPhotoFile = null; state.medicalPhotoDataUrl = null; $('ecardPhotoPreview').innerHTML = ''; updateProduitContinueState(); return; }
            if (file.size > 5 * 1024 * 1024) {
                showMessage('Photo trop volumineuse (max. 5 Mo).', 'error');
                e.target.value = '';
                return;
            }
            state.medicalPhotoFile = file;
            const reader = new FileReader();
            reader.onload = () => {
                state.medicalPhotoDataUrl = reader.result;
                $('ecardPhotoPreview').innerHTML = `<img class="mh-photo-preview" src="${state.medicalPhotoDataUrl}" alt="Photo e-carte">`;
                updateProduitContinueState();
            };
            reader.readAsDataURL(file);
        });
        $('consentCG').addEventListener('change', updateProduitContinueState);
        $('consentExclusions').addEventListener('change', updateProduitContinueState);
        $('produitContinueBtn').addEventListener('click', onProduitContinue);

        // Étape 3
        document.querySelectorAll('.mh-yesno').forEach((group) => {
            group.addEventListener('click', (e) => {
                const v = e.target.dataset?.v;
                if (!v) return;
                const q = group.dataset.q;
                state.medicalAnswers[q] = v;
                group.querySelectorAll('.mh-chip').forEach((c) => c.classList.toggle('selected', c.dataset.v === v));
                updatePregnancyState();
            });
        });
        $('moisGrossesse').addEventListener('input', updatePregnancyState);
        $('medicalContinueBtn').addEventListener('click', onMedicalContinue);

        // Étape 4
        $('submitDossierBtn').addEventListener('click', submitDossier);
        $('checkStatusBtn').addEventListener('click', () => syncDossierState(true));
        $('payNowBtn').addEventListener('click', payNow);

        // Étape 5
        $('attestationsList').addEventListener('click', (e) => {
            const pdf = e.target.dataset?.attPdf;
            const ecard = e.target.dataset?.attEcard;
            if (pdf) downloadFile(`/attestations/${pdf}/download`, `attestation-${pdf}.pdf`).catch((err) => showMessage(err.message, 'error'));
            if (ecard) downloadFile(`/attestations/${ecard}/ecard/download`, `ecarte-${ecard}.png`).catch((err) => showMessage(err.message, 'error'));
        });
        $('attestationDoneBtn').addEventListener('click', () => { window.location.href = 'user-dashboard.html'; });

        // Navigation
        $('wizardBackBtn').addEventListener('click', () => {
            if (state.dossierLocked || state.currentStep <= 1) { window.location.href = 'user-dashboard.html'; return; }
            showStep(state.currentStep - 1);
        });
    }

    // ---------- Init ----------
    async function init() {
        if (typeof requireAuth === 'function' && !(await requireAuth())) return;
        bindEvents();
        renderStepper();
        const resumeId = new URLSearchParams(window.location.search).get('subscription_id');
        await loadUser();
        await loadDestinations();
        if (resumeId) {
            await resumeSubscription(parseInt(resumeId, 10));
        } else {
            showStep(1);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
