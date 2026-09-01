/**
 * Modal sonore « nouvelle alerte SOS » pour l’opérateur SOS et l’agent sinistre MH.
 * Temps réel : WebSocket /ws/sos + secours polling notifications.
 * Dépend de : js/api.js (apiCall, getSosWebSocketUrl), utilisateur authentifié.
 */
(function () {
    const ROLES = ['agent_sinistre_mh', 'sos_operator'];
    /** Polling rapide si WebSocket indisponible (Nginx /ws/ manquant, etc.) */
    const POLL_FAST_MS = 4000;
    const POLL_SLOW_MS = 18000;
    const STORAGE_PRESENTED = 'mh_sos_modal_presented_ids';
    const STORAGE_ALERTE_IDS = 'mh_sos_shown_alerte_ids';
    /** Préférence utilisateur : sirène uniquement si « Son des alertes : activé » (clic toolbar). */
    const STORAGE_SOUND_ON = 'mh_sos_alert_sound_on';
    /** Notifications SOS prises en compte pour le secours polling (évite d’empiler les anciennes non lues) */
    const RECENT_NOTIF_MS = 20 * 60 * 1000;

    function sleep(ms) {
        return new Promise((r) => setTimeout(r, ms));
    }

    async function fetchAlertWithRetry(alertId, attempts = 8, delayMs = 280) {
        let lastErr;
        for (let i = 0; i < attempts; i++) {
            try {
                return await apiCall(`/sos/${alertId}`);
            } catch (e) {
                lastErr = e;
                if (i < attempts - 1) await sleep(delayMs);
            }
        }
        throw lastErr;
    }

    const STATUS_LABELS = {
        en_attente: 'En attente',
        en_cours: 'En cours',
        resolue: 'Résolue',
        annulee: 'Annulée',
    };
    const PRIORITY_LABELS = {
        normale: 'Normale',
        haute: 'Haute',
        elevee: 'Élevée',
        urgence: 'Urgence',
        critique: 'Critique',
    };

    let modalQueue = [];
    let modalVisible = false;
    let currentNotification = null;
    let pollTimer = null;
    let ws = null;
    let wsReconnectTimer = null;
    let wsPingTimer = null;
    let wsReconnectDelay = 3000;
    /** Contexte Web Audio réutilisé + déverrouillé au premier clic/touche (politique navigateur). */
    let masterAudioCtx = null;

    function loadShownAlerteIdSet() {
        try {
            const raw = sessionStorage.getItem(STORAGE_ALERTE_IDS);
            const arr = raw ? JSON.parse(raw) : [];
            const list = Array.isArray(arr) ? arr : [];
            return new Set(list.map(Number).filter((x) => Number.isFinite(x)));
        } catch {
            return new Set();
        }
    }

    function saveShownAlerteIdSet(set) {
        try {
            sessionStorage.setItem(STORAGE_ALERTE_IDS, JSON.stringify([...set].slice(-200)));
        } catch (_) {
            /* ignore */
        }
    }

    let shownAlerteIds = loadShownAlerteIdSet();

    function escapeHtml(text) {
        if (typeof text !== 'string') return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function getStatusLabel(s) {
        return STATUS_LABELS[s] || s || '—';
    }

    function getPriorityLabel(p) {
        return PRIORITY_LABELS[p] || p || '—';
    }

    function getPatientInitials(fullName) {
        if (!fullName || typeof fullName !== 'string') return '?';
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

    function loadPresentedSet() {
        try {
            const raw = sessionStorage.getItem(STORAGE_PRESENTED);
            const arr = raw ? JSON.parse(raw) : [];
            return new Set(Array.isArray(arr) ? arr : []);
        } catch {
            return new Set();
        }
    }

    function savePresentedSet(set) {
        try {
            sessionStorage.setItem(STORAGE_PRESENTED, JSON.stringify([...set].slice(-200)));
        } catch (_) {
            /* ignore */
        }
    }

    function isSosAlertSoundEnabled() {
        try {
            return localStorage.getItem(STORAGE_SOUND_ON) === '1';
        } catch (_) {
            return false;
        }
    }

    function setSosAlertSoundPref(on) {
        try {
            localStorage.setItem(STORAGE_SOUND_ON, on ? '1' : '0');
        } catch (_) {}
    }

    function updateMhSosSoundToggleUi() {
        const buttons = document.querySelectorAll('#mhSosAlertSoundToggle, #receptionHospitalMapSoundToggle');
        if (!buttons.length) {
            return;
        }
        const on = isSosAlertSoundEnabled();
        buttons.forEach((btn) => {
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
            btn.classList.toggle('mh-sos-sound-toggle--on', on);
            btn.classList.toggle('mh-sos-sound-toggle--off', !on);
            btn.textContent = on ? 'Son des alertes : activé' : 'Son des alertes : désactivé';
        });
    }

    /** Déverrouillage explicite (clic bouton toolbar) : resume + buffer silencieux pour l’autoplay policy. */
    async function unlockSosAudioWithSilentBuffer() {
        const ctx = getOrCreateSosAudioContext();
        if (!ctx) {
            return false;
        }
        try {
            await ctx.resume();
        } catch {
            return false;
        }
        const ok = await waitForAudioContextRunning(ctx, 900);
        if (!ok) {
            return false;
        }
        try {
            const buffer = ctx.createBuffer(1, 1, ctx.sampleRate);
            const src = ctx.createBufferSource();
            src.buffer = buffer;
            src.connect(ctx.destination);
            src.start(0);
        } catch (_) {}
        return true;
    }

    /**
     * Bip court audible — à appeler dans la foulée du clic « activer le son » (même geste utilisateur).
     * Permet de vérifier tout de suite volume navigateur / périphérique ; la sirène seule arrive souvent sans geste.
     */
    async function playSosActivationTestBeep() {
        try {
            if (!isSosAlertSoundEnabled()) {
                return false;
            }
            const ctx = getOrCreateSosAudioContext();
            if (!ctx) {
                return false;
            }
            try {
                await ctx.resume();
            } catch {
                return false;
            }
            const ok = await waitForAudioContextRunning(ctx, 900);
            if (!ok) {
                return false;
            }
            const t0 = ctx.currentTime + 0.02;
            const osc = ctx.createOscillator();
            const g = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, t0);
            g.gain.setValueAtTime(0.0001, t0);
            g.gain.linearRampToValueAtTime(0.22, t0 + 0.025);
            g.gain.exponentialRampToValueAtTime(0.001, t0 + 0.22);
            osc.connect(g);
            g.connect(ctx.destination);
            osc.start(t0);
            osc.stop(t0 + 0.26);
            return true;
        } catch (_) {
            return false;
        }
    }

    /** Bip immédiat planifié sur le graphe (sans setTimeout) — même principe que le test d’activation. */
    function scheduleImmediateSosPing(ctx) {
        try {
            const t0 = ctx.currentTime + 0.02;
            const osc = ctx.createOscillator();
            const g = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(990, t0);
            g.gain.setValueAtTime(0.0001, t0);
            g.gain.linearRampToValueAtTime(0.2, t0 + 0.025);
            g.gain.exponentialRampToValueAtTime(0.001, t0 + 0.16);
            osc.connect(g);
            g.connect(ctx.destination);
            osc.start(t0);
            osc.stop(t0 + 0.18);
        } catch (_) {}
    }

    async function ensureSosAudioContextRunning(ctx) {
        if (!ctx) {
            return false;
        }
        try {
            await ctx.resume();
        } catch {
            return false;
        }
        let ok = await waitForAudioContextRunning(ctx, 900);
        if (ok) {
            return true;
        }
        const stuck = ctx.state === 'suspended' || ctx.state === 'interrupted';
        if (stuck) {
            await sleep(120);
            try {
                await ctx.resume();
            } catch {
                return false;
            }
            ok = await waitForAudioContextRunning(ctx, 700);
        }
        return ok;
    }

    function initMhSosSoundToggle() {
        const buttons = document.querySelectorAll('#mhSosAlertSoundToggle, #receptionHospitalMapSoundToggle');
        if (!buttons.length) {
            return;
        }
        updateMhSosSoundToggleUi();
        const onClick = async () => {
            if (isSosAlertSoundEnabled()) {
                setSosAlertSoundPref(false);
                updateMhSosSoundToggleUi();
                return;
            }
            setSosAlertSoundPref(true);
            updateMhSosSoundToggleUi();
            const ok = await unlockSosAudioWithSilentBuffer();
            if (!ok) {
                setSosAlertSoundPref(false);
                updateMhSosSoundToggleUi();
                if (typeof showAlert === 'function') {
                    showAlert(
                        'Impossible d’activer l’audio. Vérifiez que le son du navigateur n’est pas bloqué et réessayez.',
                        'warning'
                    );
                }
                return;
            }
            const heard = await playSosActivationTestBeep();
            if (!heard && typeof showAlert === 'function') {
                showAlert(
                    'Le son semble bloqué (onglet muet, volume système ou périphérique audio). Vérifiez aussi que la page n’est pas en arrière-plan.',
                    'warning'
                );
            }
        };
        buttons.forEach((btn) => btn.addEventListener('click', onClick));
    }

    function getOrCreateSosAudioContext() {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) {
            return null;
        }
        if (!masterAudioCtx) {
            masterAudioCtx = new Ctx();
        }
        return masterAudioCtx;
    }

    /**
     * Après resume(), Chrome / Safari peuvent passer à « running » un tick plus tard.
     * Sans cette attente, playAlertSound renvoyait false alors que le son aurait pu partir.
     */
    function waitForAudioContextRunning(ctx, timeoutMs = 800) {
        if (!ctx) {
            return Promise.resolve(false);
        }
        if (ctx.state === 'running') {
            return Promise.resolve(true);
        }
        return new Promise((resolve) => {
            const done = (ok) => {
                clearTimeout(tid);
                try {
                    ctx.removeEventListener('statechange', onState);
                } catch (_) {}
                resolve(ok);
            };
            const onState = () => {
                if (ctx.state === 'running') {
                    done(true);
                }
            };
            ctx.addEventListener('statechange', onState);
            const tid = setTimeout(() => done(ctx.state === 'running'), timeoutMs);
        });
    }

    /** Réveille le contexte audio dès la première interaction (sinon le navigateur coupe le son). */
    function installSosAudioUnlock() {
        const warm = () => {
            try {
                const ctx = getOrCreateSosAudioContext();
                if (!ctx) return;
                ctx.resume().then(() => {
                    try {
                        const buffer = ctx.createBuffer(1, 1, ctx.sampleRate);
                        const src = ctx.createBufferSource();
                        src.buffer = buffer;
                        src.connect(ctx.destination);
                        src.start(0);
                    } catch (_) {}
                }).catch(() => {});
            } catch (_) {}
        };
        document.addEventListener('pointerdown', warm, { capture: true, passive: true });
        document.addEventListener('keydown', warm, { capture: true, passive: true });
        document.addEventListener('touchstart', warm, { capture: true, passive: true });
    }

    function removeAudioUnlockBanner() {
        const row = document.getElementById('mhSosAudioUnlockRow');
        if (row) row.remove();
    }

    /** Affiche un bandeau + bouton si le navigateur n’a pas encore autorisé le son (pas de geste sur cette page). */
    function ensureAudioUnlockBannerInModal() {
        if (!isSosAlertSoundEnabled()) {
            return;
        }
        if (document.getElementById('mhSosAudioUnlockRow')) return;
        const body = document.getElementById('mhSosAlertModalBody');
        if (!body) return;
        body.insertAdjacentHTML(
            'afterbegin',
            `<div id="mhSosAudioUnlockRow" class="mh-sos-audio-unlock" role="region" aria-label="Son d’alerte">
                <p><strong>Pas de son ?</strong> Le navigateur exige un clic sur cette page pour l’audio. Cliquez ci-dessous pour lancer l’alarme.</p>
                <button type="button" class="btn btn-danger" id="mhSosAudioUnlockBtn">🔊 Lancer / réécouter l’alarme</button>
            </div>`
        );
        const btn = document.getElementById('mhSosAudioUnlockBtn');
        if (btn) {
            btn.addEventListener('click', async () => {
                setSosAlertSoundPref(true);
                updateMhSosSoundToggleUi();
                const ok = await playAlertSound();
                if (ok) {
                    removeAudioUnlockBanner();
                }
            });
        }
    }

    /**
     * Sirène : répétition de bips sinus, chaque chaîne osc→gain→destination comme `scheduleImmediateSosPing`
     * (pas de nœud master : sur certains navigateurs le gain maître planifié laissait toute la sirène muette).
     */
    async function playAlertSound() {
        try {
            if (!isSosAlertSoundEnabled()) {
                return false;
            }
            const ctx = getOrCreateSosAudioContext();
            if (!ctx) {
                console.warn('mh sos: Web Audio API indisponible');
                return false;
            }
            let runningOk = await ensureSosAudioContextRunning(ctx);
            if (!runningOk) {
                console.warn('mh sos: contexte audio toujours en état', ctx.state, '(cliquez sur la page ou sur le bouton dans la fenêtre)');
                return false;
            }
            /* Pas de setTimeout ici : après un await long, Chrome repasse souvent le contexte en « suspended »
             * et on sortait sans jouer la sirène (le bip d’activation, lui, reste dans le geste utilisateur). */
            runningOk = await ensureSosAudioContextRunning(ctx);
            if (!runningOk || ctx.state !== 'running') {
                console.warn('mh sos: contexte audio non running avant sirène', ctx.state);
                return false;
            }

            scheduleImmediateSosPing(ctx);
            const tAnchor = ctx.currentTime + 0.08;

            const hi = 1280;
            const lo = 820;
            const toneDur = 0.36;
            const attack = 0.028;
            const peak = 0.38;
            const gap = 0.07;
            let t = tAnchor;
            const rounds = 8;
            const beepsPerRound = 6;

            function scheduleSirenSineToneDirect(start, freq) {
                const osc = ctx.createOscillator();
                const g = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, start);
                osc.connect(g);
                g.connect(ctx.destination);
                g.gain.setValueAtTime(0.0001, start);
                g.gain.linearRampToValueAtTime(peak, start + attack);
                g.gain.exponentialRampToValueAtTime(0.001, start + toneDur);
                osc.start(start);
                osc.stop(start + toneDur + 0.06);
            }

            for (let r = 0; r < rounds; r++) {
                for (let i = 0; i < beepsPerRound; i++) {
                    scheduleSirenSineToneDirect(t, i % 2 === 0 ? hi : lo);
                    t += toneDur + gap;
                }
                t += 0.26;
            }

            return true;
        } catch (err) {
            console.warn('mh sos: alarme sonore indisponible', err);
            return false;
        }
    }

    function ensureModalDom() {
        if (document.getElementById('mhSosAlertModal')) return;
        document.body.insertAdjacentHTML(
            'beforeend',
            `
<div id="mhSosAlertModal" class="modal mh-sos-alert-modal" style="display:none;" role="dialog" aria-modal="true" aria-labelledby="mhSosAlertModalTitle">
  <div class="modal-content mh-sos-alert-modal__content">
    <div class="modal-header">
      <h3 id="mhSosAlertModalTitle" class="mh-sos-alert-modal__title">Alerte SOS — Patient assuré</h3>
      <button type="button" class="close" id="mhSosAlertModalClose" aria-label="Fermer">&times;</button>
    </div>
    <div id="mhSosAlertModalBody" class="mh-sos-alert-modal__body"></div>
    <div class="mh-sos-alert-modal__actions">
      <button type="button" class="btn btn-outline" id="mhSosAlertModalBtnDismiss">Fermer</button>
      <button type="button" class="btn btn-danger" id="mhSosAlertModalBtnOpen">Ouvrir le dossier</button>
    </div>
  </div>
</div>
        `.trim()
        );

        document.getElementById('mhSosAlertModalClose').addEventListener('click', closeModal);
        document.getElementById('mhSosAlertModalBtnDismiss').addEventListener('click', closeModal);
        document.getElementById('mhSosAlertModalBtnOpen').addEventListener('click', openDossier);
        document.getElementById('mhSosAlertModal').addEventListener('click', (e) => {
            if (e.target.id === 'mhSosAlertModal') closeModal();
        });
    }

    function buildModalBody(alert) {
        const hospital = alert.assigned_hospital;
        const distance =
            typeof alert.distance_to_hospital_km === 'number'
                ? `${alert.distance_to_hospital_km.toFixed(1)} km`
                : null;
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
            ? `<img src="${escapeHtml(photoUrl)}" alt="Photo du patient assuré" class="mh-sos-alert-modal__photo" width="104" height="104">`
            : `<span class="mh-sos-alert-modal__avatar" aria-label="Patient assuré, initiales">${escapeHtml(initials)}</span>`;
        const assurAgeLine = assurAge !== null ? ` • ${assurAge} an(s)` : '';
        const contactLine =
            contactNom || contactTel
                ? `<p><strong>Personne à contacter :</strong> ${escapeHtml(contactNom || '—')}${contactTel ? ' • ' + escapeHtml(contactTel) : ''}</p>`
                : '';
        const medecinLine =
            medecinNom || medecinTel
                ? `<p><strong>Médecin référent à contacter :</strong> ${escapeHtml(medecinNom || '—')}${medecinTel ? ' • ' + escapeHtml(medecinTel) : ''}</p>`
                : '';
        const hospLine = hospital
            ? `<p><strong>Hôpital :</strong> ${escapeHtml(hospital.nom)}${distance ? ` (${distance})` : ''}</p>`
            : '<p><strong>Hôpital :</strong> Non attribué</p>';

        return `
            <div class="mh-sos-alert-modal__badge" role="status">Cas à prendre en charge</div>
            <p class="mh-sos-alert-modal__intro">Alerte SOS — le patient assuré ci-dessous nécessite une prise en charge immédiate.</p>
            <div class="mh-sos-alert-modal__numero">${escapeHtml(numero)}</div>
            <p class="mh-sos-alert-modal__statusline muted">${escapeHtml(getStatusLabel(alert.statut))} • ${escapeHtml(getPriorityLabel(alert.priorite))}</p>
            <div class="mh-sos-alert-modal__divider"></div>
            <div class="mh-sos-alert-modal__patient" role="region" aria-label="Identité du patient assuré">
                ${photoHtml}
                <div>
                    <p class="mh-sos-alert-modal__name"><strong>Patient assuré :</strong> ${escapeHtml(assurNom)}${escapeHtml(assurAgeLine)}</p>
                    <p class="muted">N° souscription : ${escapeHtml(numeroSouscription)}</p>
                    <p class="mh-sos-alert-modal__phone">Téléphone : ${escapeHtml(assurTel)}</p>
                </div>
            </div>
            <div class="mh-sos-alert-modal__divider"></div>
            <div class="mh-sos-alert-modal__details">
            ${contactLine}
            ${medecinLine}
            ${hospLine}
            </div>
        `;
    }

    async function resolveAlertForNotification(notification) {
        if (!notification || notification.lien_relation_type !== 'sinistre' || !notification.lien_relation_id) {
            return null;
        }
        const sinistreId = Number(notification.lien_relation_id);
        if (!Number.isFinite(sinistreId)) return null;
        try {
            const sinistre = await apiCall(`/hospital-sinistres/sinistres/${sinistreId}`);
            const alertId = sinistre?.alerte_id != null ? Number(sinistre.alerte_id) : null;
            if (!Number.isFinite(alertId)) return null;
            return await apiCall(`/sos/${alertId}`);
        } catch (e) {
            console.error('mh sos modal: impossible de charger l’alerte', e);
            return null;
        }
    }

    async function markNotificationRead(id) {
        if (!id) return;
        try {
            await apiCall(`/notifications/${id}/read`, { method: 'PATCH' });
        } catch (_) {}
    }

    function showModal(alert, notification) {
        ensureModalDom();
        currentNotification = notification;
        if (notification && notification.id != null) {
            const presented = loadPresentedSet();
            presented.add(notification.id);
            savePresentedSet(presented);
        }
        const modal = document.getElementById('mhSosAlertModal');
        const body = document.getElementById('mhSosAlertModalBody');
        body.innerHTML = buildModalBody(alert);
        body.setAttribute('aria-live', 'assertive');
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        modalVisible = true;
        void (async () => {
            if (!isSosAlertSoundEnabled()) {
                return;
            }
            const ok = await playAlertSound();
            if (!ok) {
                ensureAudioUnlockBannerInModal();
            }
        })();
    }

    function closeModal() {
        const modal = document.getElementById('mhSosAlertModal');
        if (modal) modal.style.display = 'none';
        document.body.style.overflow = '';
        modalVisible = false;
        currentNotification = null;
        processQueue();
    }

    async function openDossier() {
        const n = currentNotification;
        const modal = document.getElementById('mhSosAlertModal');
        let alertId = null;
        if (n && Number.isFinite(Number(n._alertId))) {
            alertId = Number(n._alertId);
        } else if (n && n.lien_relation_type === 'sinistre' && n.lien_relation_id) {
            try {
                const sinistre = await apiCall(`/hospital-sinistres/sinistres/${Number(n.lien_relation_id)}`);
                if (sinistre?.alerte_id != null) alertId = Number(sinistre.alerte_id);
            } catch (_) {}
        }
        if (modal) modal.style.display = 'none';
        document.body.style.overflow = '';
        modalVisible = false;
        currentNotification = null;
        if (n) await markNotificationRead(n.id);
        if (Number.isFinite(alertId)) {
            window.location.href = `hospital-alert-details.html?alert_id=${alertId}`;
            return;
        }
        if (typeof showAlert === 'function') {
            showAlert('Impossible d’ouvrir le dossier (alerte introuvable).', 'error');
        }
        processQueue();
    }

    async function processQueue() {
        if (modalVisible || modalQueue.length === 0) return;
        const notification = modalQueue.shift();
        const alert = await resolveAlertForNotification(notification);
        if (!alert) {
            processQueue();
            return;
        }
        if (shownAlerteIds.has(alert.id)) {
            processQueue();
            return;
        }
        shownAlerteIds.add(alert.id);
        saveShownAlerteIdSet(shownAlerteIds);
        showModal(alert, notification);
    }

    function clearWsTimers() {
        if (wsPingTimer) {
            clearInterval(wsPingTimer);
            wsPingTimer = null;
        }
    }

    function scheduleWsReconnect() {
        if (wsReconnectTimer) return;
        const role = (localStorage.getItem('user_role') || '').toLowerCase().trim();
        if (!ROLES.includes(role)) return;
        wsReconnectTimer = setTimeout(() => {
            wsReconnectTimer = null;
            connectSosRealtime();
        }, wsReconnectDelay);
        wsReconnectDelay = Math.min(Math.round(wsReconnectDelay * 1.5), 60000);
    }

    async function handleRealtimeNewAlert(payload) {
        const alertId = Number(payload.alerte_id);
        const sinistreId = Number(payload.sinistre_id);
        if (!Number.isFinite(alertId)) return;

        if (modalVisible) {
            if (Number.isFinite(sinistreId)) {
                const queuedIds = new Set(modalQueue.map((q) => q.lien_relation_id));
                if (!queuedIds.has(sinistreId)) {
                    modalQueue.push({
                        id: null,
                        lien_relation_type: 'sinistre',
                        lien_relation_id: sinistreId,
                    });
                }
            }
            window.dispatchEvent(new CustomEvent('mh-sos-refresh-alerts'));
            return;
        }

        if (shownAlerteIds.has(alertId)) return;

        try {
            const alert = await fetchAlertWithRetry(alertId);
            if (!alert || shownAlerteIds.has(alert.id)) return;
            shownAlerteIds.add(alert.id);
            saveShownAlerteIdSet(shownAlerteIds);
            const syntheticNotif = {
                id: null,
                lien_relation_type: 'sinistre',
                lien_relation_id: Number.isFinite(sinistreId)
                    ? sinistreId
                    : Number(alert.sinistre_id) || null,
                _alertId: alertId,
            };
            showModal(alert, syntheticNotif);
            window.dispatchEvent(new CustomEvent('mh-sos-refresh-alerts'));
        } catch (e) {
            console.error('mh sos ws: chargement alerte impossible', e);
        }
    }

    function connectSosRealtime() {
        const role = (localStorage.getItem('user_role') || '').toLowerCase().trim();
        if (!ROLES.includes(role)) return;

        const token = localStorage.getItem('access_token');
        const urlFn = typeof window.getSosWebSocketUrl === 'function' ? window.getSosWebSocketUrl : null;
        if (!token || !urlFn) return;

        clearWsTimers();
        try {
            if (ws) {
                ws.onclose = null;
                ws.onerror = null;
                ws.onmessage = null;
                try {
                    ws.close();
                } catch (_) {}
                ws = null;
            }
        } catch (_) {}

        let socket;
        try {
            socket = new WebSocket(urlFn(token));
        } catch (e) {
            scheduleWsReconnect();
            return;
        }
        ws = socket;

        ws.onopen = () => {
            wsReconnectDelay = 3000;
            adjustPollInterval();
            wsPingTimer = setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    try {
                        ws.send(JSON.stringify({ type: 'ping' }));
                    } catch (_) {}
                }
            }, 25000);
        };

        ws.onmessage = (ev) => {
            let data;
            try {
                data = JSON.parse(ev.data);
            } catch {
                return;
            }
            if (data.type === 'new_alert') {
                handleRealtimeNewAlert(data);
            }
        };

        ws.onclose = () => {
            clearWsTimers();
            ws = null;
            adjustPollInterval();
            scheduleWsReconnect();
        };

        ws.onerror = () => {
            try {
                if (ws) ws.close();
            } catch (_) {}
        };
    }

    function queueKey(q) {
        if (q && q.id != null) return `n:${q.id}`;
        if (q && q.lien_relation_id != null) return `s:${q.lien_relation_id}`;
        return `u:${Math.random()}`;
    }

    function enqueueNotifications(notifications, presented) {
        const fresh = (n) => {
            if (!n.created_at) return false;
            return new Date(n.created_at).getTime() >= Date.now() - RECENT_NOTIF_MS;
        };
        const queuedKeys = new Set(modalQueue.map(queueKey));
        const list = (notifications || []).filter(
            (n) =>
                n.type_notification === 'sos_alert_received' &&
                !n.is_read &&
                fresh(n) &&
                n.lien_relation_type === 'sinistre' &&
                !presented.has(n.id) &&
                !queuedKeys.has(`n:${n.id}`)
        );
        list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
        for (const n of list) {
            modalQueue.push(n);
            queuedKeys.add(`n:${n.id}`);
        }
    }

    async function poll() {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        try {
            const response = await apiCall('/notifications?limit=80');
            const notifications = Array.isArray(response) ? response : [];
            const presented = loadPresentedSet();
            enqueueNotifications(notifications, presented);
            await processQueue();
        } catch (_) {}
    }

    function adjustPollInterval() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
        const ms = ws && ws.readyState === WebSocket.OPEN ? POLL_SLOW_MS : POLL_FAST_MS;
        pollTimer = window.setInterval(poll, ms);
    }

    /**
     * Émis par sos-dashboard.js quand une nouvelle alerte active apparaît dans le tableau (polling GET /sos/).
     * Fonctionne pour tous les opérateurs (pas seulement celui qui a la notification en base).
     */
    function handleDashboardNewAlertEvent(ev) {
        const modalEl = document.getElementById('mhSosAlertModal');
        if (modalEl && modalEl.style.display === 'block') {
            return;
        }
        const id = Number(ev.detail?.alerte_id);
        const alertObj = ev.detail?.alert;
        if (!Number.isFinite(id)) return;
        if (shownAlerteIds.has(id)) return;

        if (modalVisible) {
            if (modalQueue.some((q) => Number(q._alertId) === id)) return;
            const sid = alertObj?.sinistre_id != null ? Number(alertObj.sinistre_id) : null;
            if (Number.isFinite(sid)) {
                modalQueue.push({
                    id: null,
                    lien_relation_type: 'sinistre',
                    lien_relation_id: sid,
                    _alertId: id,
                });
            }
            return;
        }

        (async () => {
            try {
                let alert = alertObj;
                if (!alert || alert.numero_alerte == null) {
                    alert = await fetchAlertWithRetry(id);
                }
                if (!alert || shownAlerteIds.has(alert.id)) return;
                shownAlerteIds.add(alert.id);
                saveShownAlerteIdSet(shownAlerteIds);
                const sid = Number(alert.sinistre_id);
                const syntheticNotif = {
                    id: null,
                    lien_relation_type: 'sinistre',
                    lien_relation_id: Number.isFinite(sid) ? sid : null,
                    _alertId: id,
                };
                showModal(alert, syntheticNotif);
            } catch (e) {
                console.error('mh sos: événement tableau, chargement alerte impossible', e);
            }
        })();
    }

    function init() {
        const role = (localStorage.getItem('user_role') || '').toLowerCase().trim();
        initMhSosSoundToggle();
        if (!ROLES.includes(role)) {
            return;
        }
        installSosAudioUnlock();
        ensureModalDom();
        document.addEventListener('mh-sos-new-active-alert', handleDashboardNewAlertEvent);
        connectSosRealtime();
        poll();
        adjustPollInterval();
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                try {
                    masterAudioCtx?.resume?.().catch(() => {});
                } catch (_) {}
                poll();
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    wsReconnectDelay = 3000;
                    connectSosRealtime();
                }
                adjustPollInterval();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
