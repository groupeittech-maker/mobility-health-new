// Shell d'accueil assuré — calqué sur l'écran d'accueil mobile (home_screen).
// 3 onglets : Souscription / Alerte SOS / Historique.
//   - Souscription : métriques (user-dashboard.js) + partenaires + nouvelle souscription.
//   - Alerte SOS   : même écran que SosScreen mobile (éligibilité, bouton SOS,
//                    médecin-conseil, liste « Mes alertes »).
//   - Historique   : Souscriptions (user-dashboard.js) / Alertes / Prestations.

(function () {
    'use strict';

    const homeState = {
        sosEligible: null,
        sosLoading: false,
        histLoaded: { alertes: false, prestations: false },
    };

    const el = (id) => document.getElementById(id);

    // ==================== Onglets principaux ====================
    function switchHomeTab(name) {
        document.querySelectorAll('.home-tab').forEach((t) =>
            t.classList.toggle('active', t.dataset.homeTab === name));
        document.querySelectorAll('.home-tab-content').forEach((c) => c.classList.remove('active'));
        const target = { souscription: 'homeTabSouscription', sos: 'homeTabSos', historique: 'homeTabHistorique' }[name];
        if (target) el(target)?.classList.add('active');
        if (name === 'sos') initSosTab();
        if (name === 'historique') initHistoriqueTab();
    }

    function initHomeTabs() {
        document.querySelectorAll('.home-tab').forEach((t) =>
            t.addEventListener('click', () => switchHomeTab(t.dataset.homeTab)));
        const requested = new URLSearchParams(window.location.search).get('tab');
        if (requested === 'sos' || requested === 'historique') switchHomeTab(requested);
    }

    // ==================== Partenaires (carrousel mobile) ====================
    async function loadPartners() {
        const strip = el('partnersStrip');
        if (!strip) return;
        try {
            const assureurs = await apiCall('/assureurs');
            const list = Array.isArray(assureurs) && assureurs.length
                ? assureurs
                : [{ id: null, nom: 'ARC' }, { id: null, nom: 'AXA afrique' }, { id: null, nom: 'NSIA' }];
            strip.innerHTML = list.map((a) => {
                const logo = a.id ? `${window.API_BASE_URL}/assureurs/${a.id}/logo` : '';
                return `<div class="partner-card">
                    ${logo ? `<img src="${logo}" alt="${escapeHtmlHome(a.nom || '')}" onerror="this.style.display='none'">` : ''}
                    <span>${escapeHtmlHome(a.nom || 'Partenaire')}</span>
                </div>`;
            }).join('');
        } catch (_) {
            strip.innerHTML = '';
        }
    }

    // ==================== Compteur attestations (4e métrique mobile) ====================
    async function loadAttestationsCount() {
        try {
            const atts = await apiCall('/users/me/attestations');
            const target = el('attestationsCount');
            if (target) target.textContent = Array.isArray(atts) ? atts.length : 0;
        } catch (_) {
            const target = el('attestationsCount');
            if (target) target.textContent = '0';
        }
    }

    // ==================== Onglet SOS ====================
    let sosTabInitialized = false;
    async function initSosTab() {
        if (sosTabInitialized) return;
        sosTabInitialized = true;
        el('sosBtn')?.addEventListener('click', triggerSos);
        await Promise.all([refreshSosEligibility(), loadSosMedecinConseil(), loadSosAlertes('sosAlertesList')]);
    }

    /// Même règle que SosEligibilityService mobile : dernière souscription active
    /// + attestation définitive valide rattachée à cette souscription.
    async function canTriggerSos() {
        const [subs, atts] = await Promise.all([
            apiCall('/subscriptions/?limit=500'),
            apiCall('/users/me/attestations'),
        ]);
        const activeSubs = (Array.isArray(subs) ? subs : [])
            .filter((s) => s.statut === 'active')
            .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
        if (!activeSubs.length) return false;
        const targetId = activeSubs[0].id;
        return (Array.isArray(atts) ? atts : []).some((a) => {
            const type = (a.type_attestation || '').toString().toLowerCase().trim();
            if (type !== 'definitive') return false;
            if (a.est_valide === false) return false;
            return parseInt(a.souscription_id, 10) === targetId;
        });
    }

    async function refreshSosEligibility() {
        const btn = el('sosBtn');
        const note = el('sosEligibilityNote');
        if (!btn) return;
        btn.disabled = true;
        btn.textContent = 'Vérification de l\'éligibilité…';
        try {
            homeState.sosEligible = await canTriggerSos();
        } catch (_) {
            homeState.sosEligible = false;
        }
        if (homeState.sosEligible) {
            btn.disabled = false;
            btn.textContent = '🚨 Déclarer une alerte SOS';
            if (note) note.textContent = 'En cas d\'urgence vitale, appelez d\'abord les services d\'urgence locaux (112).';
        } else {
            btn.disabled = true;
            btn.textContent = 'SOS non disponible';
            if (note) note.textContent = 'Le bouton SOS nécessite une souscription active avec attestation définitive valide.';
        }
    }

    function showSosStatus(message, type) {
        const box = el('sosStatus');
        if (box) box.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    }

    function triggerSos() {
        if (!homeState.sosEligible) {
            showSosStatus('Le bouton SOS nécessite une souscription active avec attestation définitive valide.', 'error');
            return;
        }
        if (!navigator.geolocation) {
            showSosStatus('La géolocalisation n\'est pas supportée par votre navigateur.', 'error');
            return;
        }
        const btn = el('sosBtn');
        homeState.sosLoading = true;
        if (btn) { btn.disabled = true; btn.textContent = '⏳ Envoi en cours…'; }
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const latitude = parseFloat(position.coords.latitude.toFixed(6));
                const longitude = parseFloat(position.coords.longitude.toFixed(6));
                try {
                    const response = await apiCall('/sos/trigger', {
                        method: 'POST',
                        body: JSON.stringify({ latitude, longitude, priorite: 'normale', description: null }),
                    });
                    showSosStatus(`Alerte SOS envoyée (${response.numero_alerte || 'Alerte #' + response.id}). Un agent va vous contacter rapidement.`, 'success');
                    await loadSosAlertes('sosAlertesList');
                    histLoadedReset();
                } catch (error) {
                    showSosStatus(`Erreur : ${error.message || 'Impossible d\'envoyer l\'alerte'}`, 'error');
                } finally {
                    homeState.sosLoading = false;
                    if (btn) { btn.disabled = false; btn.textContent = '🚨 Déclarer une alerte SOS'; }
                }
            },
            () => {
                homeState.sosLoading = false;
                if (btn) { btn.disabled = false; btn.textContent = '🚨 Déclarer une alerte SOS'; }
                showSosStatus('Impossible d\'obtenir votre position. Vérifiez les autorisations de localisation et réessayez.', 'error');
            },
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
    }

    async function loadSosMedecinConseil() {
        const container = el('medecinConseilContainer');
        if (!container || typeof renderMedecinConseilSection !== 'function') return;
        const cached = typeof readMedecinConseilCache === 'function' ? readMedecinConseilCache() : [];
        if (cached.length) container.innerHTML = renderMedecinConseilSection(cached, { fromCache: true });
        try {
            const result = await loadMedecinConseilAssignments({ souscriptionId: null });
            container.innerHTML = renderMedecinConseilSection(result.items, { fromCache: result.fromCache });
        } catch (_) { /* silencieux comme sur mobile */ }
    }

    function renderSosAlertes(alertes, showHeader = true) {
        if (!alertes.length) {
            return showHeader ? '<h3>Mes alertes</h3><p class="sos-note">Aucune alerte déclarée.</p>' : '<p class="sos-note">Aucune alerte.</p>';
        }
        const items = alertes.map((a) => {
            const numero = a.numero_alerte || `Alerte #${a.id}`;
            const statut = a.statut || 'en_attente';
            const created = a.created_at ? new Date(a.created_at).toLocaleString('fr-FR') : '';
            return `<div class="hist-item"><strong>${escapeHtmlHome(numero)}</strong>
                <span class="muted" style="text-transform:capitalize;"> · ${escapeHtmlHome(statut)}</span>
                ${created ? `<div class="muted">${created}</div>` : ''}</div>`;
        }).join('');
        return (showHeader ? '<h3>Mes alertes</h3>' : '') + items;
    }

    async function loadSosAlertes(containerId) {
        const container = el(containerId);
        if (!container) return;
        try {
            const alertes = await apiCall('/sos/?skip=0&limit=100');
            container.innerHTML = renderSosAlertes(alertes || [], containerId === 'sosAlertesList');
        } catch (_) {
            container.innerHTML = '';
        }
    }

    // ==================== Onglet Historique ====================
    let histTabInitialized = false;
    function initHistoriqueTab() {
        if (histTabInitialized) return;
        histTabInitialized = true;
        document.querySelectorAll('.hist-tab').forEach((t) =>
            t.addEventListener('click', () => switchHistTab(t.dataset.histTab)));
    }

    function switchHistTab(name) {
        document.querySelectorAll('.hist-tab').forEach((t) =>
            t.classList.toggle('active', t.dataset.histTab === name));
        document.querySelectorAll('.hist-content').forEach((c) => c.classList.remove('active'));
        const target = { souscriptions: 'histSouscriptions', alertes: 'histAlertes', prestations: 'histPrestations' }[name];
        if (target) el(target)?.classList.add('active');
        if (name === 'alertes' && !homeState.histLoaded.alertes) {
            homeState.histLoaded.alertes = true;
            loadHistAlertes();
        }
        if (name === 'prestations' && !homeState.histLoaded.prestations) {
            homeState.histLoaded.prestations = true;
            loadHistPrestations();
        }
    }

    function histLoadedReset() {
        homeState.histLoaded.alertes = false;
        if (el('histAlertes')?.classList.contains('active')) {
            homeState.histLoaded.alertes = true;
            loadHistAlertes();
        }
    }

    async function loadHistAlertes() {
        const container = el('histAlertesList');
        if (!container) return;
        container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        try {
            const alertes = await apiCall('/sos/?skip=0&limit=100');
            container.innerHTML = (alertes || []).map((a) => {
                const numero = a.numero_alerte || `Alerte #${a.id}`;
                const statut = a.statut || 'en_attente';
                const created = a.created_at ? new Date(a.created_at).toLocaleString('fr-FR') : '';
                const type = a.type_alerte === 'urgence' ? 'Urgence' : 'Alerte';
                return `<div class="hist-item"><strong>${escapeHtmlHome(numero)}</strong>
                    <span class="muted"> · ${escapeHtmlHome(statut)}</span>
                    <div class="muted">${created}${type ? ' · ' + type : ''}</div></div>`;
            }).join('') || '<div class="empty-state"><p>Aucune alerte.</p></div>';
        } catch (e) {
            container.innerHTML = `<div class="alert alert-error">${escapeHtmlHome(e.message)}</div>`;
        }
    }

    async function loadHistPrestations() {
        const container = el('histPrestationsList');
        if (!container) return;
        container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        try {
            const stays = await apiCall('/hospital-sinistres/hospital-stays?skip=0&limit=50');
            container.innerHTML = (stays || []).map((s) => {
                const created = s.created_at ? new Date(s.created_at).toLocaleString('fr-FR') : '';
                const statut = s.status || s.report_status || '';
                const lieu = s.city || s.lieu || '';
                const hopital = s.hospital_name || s.hopital || '';
                return `<div class="hist-item"><strong>Séjour #${s.id}</strong>
                    <span class="muted"> · ${escapeHtmlHome(statut)}</span>
                    <div class="muted">${[created, lieu, hopital].filter(Boolean).map(escapeHtmlHome).join(' · ')}</div></div>`;
            }).join('') || '<div class="empty-state"><p>Aucune prestation.</p></div>';
        } catch (e) {
            container.innerHTML = `<div class="alert alert-error">${escapeHtmlHome(e.message)}</div>`;
        }
    }

    function escapeHtmlHome(s) {
        return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    // ==================== Init ====================
    function init() {
        initHomeTabs();
        loadPartners();
        loadAttestationsCount();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
