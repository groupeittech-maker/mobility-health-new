// Détails de l'alerte — centre d'alertes urgence (maquette back-office).
// Endpoints : GET /alertes/{id}/detail-complet, /etablissements-proches,
// /notes, /statut, /statut-medical, /transfer, /prevenir-hopital, /action.
(function () {
    'use strict';

    const STEPS = ['Réception', 'Évaluation', 'Orientation', 'Prise en charge', 'Suivi', 'Clôture'];
    let alerteId = null;
    let detail = null;
    let facilities = [];
    let selectedHospitalId = null;
    let map = null;
    let timerInterval = null;

    function $(id) { return document.getElementById(id); }

    function toast(msg, isError) {
        const t = $('toast');
        t.textContent = msg;
        t.className = 'toast show' + (isError ? ' error' : '');
        setTimeout(() => { t.className = 'toast'; }, 3500);
    }

    function fmtDateTime(iso) {
        if (!iso) return '—';
        const d = new Date(iso);
        return d.toLocaleDateString('fr-FR') + ' à ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }

    function fmtTime(iso) {
        if (!iso) return '—';
        return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }

    function esc(v) {
        const d = document.createElement('div');
        d.textContent = v == null ? '' : String(v);
        return d.innerHTML;
    }

    // ---------- Timer ----------
    function startTimer(createdAtIso) {
        const start = new Date(createdAtIso).getTime();
        function tick() {
            const diff = Math.max(0, Date.now() - start);
            const h = String(Math.floor(diff / 3600000)).padStart(2, '0');
            const m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, '0');
            const s = String(Math.floor((diff % 60000) / 1000)).padStart(2, '0');
            $('alertTimer').textContent = `${h}:${m}:${s}`;
        }
        tick();
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(tick, 1000);
    }

    // ---------- Stepper ----------
    function renderStepper(current) {
        const wrap = $('stepper');
        wrap.innerHTML = '';
        STEPS.forEach((label, i) => {
            const n = i + 1;
            const el = document.createElement('div');
            el.className = 'ad-step' + (n < current ? ' done' : n === current ? ' current' : '');
            el.innerHTML = `<span class="dot">${n < current ? '✓' : n}</span><span>${label}</span>`;
            wrap.appendChild(el);
            if (n < STEPS.length) {
                const sep = document.createElement('div');
                sep.className = 'ad-step-sep';
                wrap.appendChild(sep);
            }
        });
    }

    // ---------- Detail rendering ----------
    function renderDetail(d) {
        detail = d;
        const a = d.alerte;
        $('alertNumero').textContent = a.numero_alerte || `#${a.id}`;
        const pr = $('alertPriorite');
        pr.textContent = (a.priorite || 'normale').charAt(0).toUpperCase() + (a.priorite || 'normale').slice(1);
        pr.className = 'ad-badge ' + (a.priorite || 'normale');
        $('alertDate').textContent = 'Reçue le ' + fmtDateTime(a.created_at);
        $('statutSelect').value = a.statut;
        startTimer(a.created_at);
        renderStepper(d.etape_courante || 1);

        const as = d.assure || {};
        $('insuredName').textContent = as.nom || '—';
        $('insuredInitials').textContent = (as.nom || 'U').split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
        $('insuredType').textContent = as.type_contrat ? `Assuré — ${as.type_contrat}` : 'Assuré principal';
        $('kvNumeroAssure').textContent = as.numero_assure || '—';
        $('kvNaissance').textContent = as.date_naissance ? `${as.date_naissance}${as.age != null ? ` (${as.age} ans)` : ''}` : '—';
        $('kvNationalite').textContent = as.nationalite || '—';
        $('kvPasseport').textContent = as.numero_passeport || '—';
        $('kvTel').textContent = as.telephone || '—';
        $('kvEmail').textContent = as.email || '—';
        $('kvContrat').textContent = as.type_contrat || '—';
        $('kvCouverture').textContent = as.date_debut_couverture && as.date_fin_couverture
            ? `${as.date_debut_couverture} – ${as.date_fin_couverture}` : '—';

        $('kvType').textContent = 'Urgence médicale';
        $('kvDateHeure').textContent = fmtDateTime(a.created_at);
        $('kvLieu').textContent = a.adresse || '—';
        $('kvGps').textContent = `${a.latitude}, ${a.longitude}`;
        $('kvMotif').textContent = a.description ? a.description.slice(0, 80) : '—';
        $('kvDescription').textContent = a.description || '—';
        $('kvSinistre').textContent = d.numero_sinistre || 'Non créé';

        const docs = d.documents || [];
        $('docCount').textContent = docs.length;
        $('docsRow').innerHTML = docs.length
            ? docs.map(doc => `<a class="doc-chip" href="${esc(doc.url)}" target="_blank" rel="noopener">📎 ${esc(doc.file_name || doc.type)}</a>`).join('')
            : '<span style="font-size:.75rem;color:#8a8fa3">Aucun document</span>';

        $('commPhone').textContent = as.telephone || '—';

        renderStatutMedical(d.statut_medical);
        renderNotes(d.notes || []);
        renderTimeline(d.timeline || []);
        renderMap(a, d.hospital_assigne);
        $('openMapsLink').href = `https://www.google.com/maps/search/?api=1&query=${a.latitude},${a.longitude}`;
    }

    function renderStatutMedical(sm) {
        sm = sm || {};
        const etat = $('smEtat');
        etat.textContent = sm.etat_patient || 'Non renseigné';
        etat.className = 'sm-badge ' + (sm.etat_patient === 'Conscient' ? 'conscient' : 'autre');
        $('smSymptomes').textContent = sm.motifs_symptomes || 'Non renseignés';
        $('smBesoins').textContent = sm.besoins_immediats || 'Non renseignés';
        $('smAllergies').textContent = sm.allergies_connues || 'Non renseignées';
        $('smTraitements').textContent = sm.traitements_en_cours || 'Non renseignés';
        // Pré-remplir le modal
        $('smEtatInput').value = sm.etat_patient || '';
        $('smSymptomesInput').value = sm.motifs_symptomes || '';
        $('smBesoinsInput').value = sm.besoins_immediats || '';
        $('smAllergiesInput').value = sm.allergies_connues || '';
        $('smTraitementsInput').value = sm.traitements_en_cours || '';
    }

    function renderNotes(notes) {
        $('notesList').innerHTML = notes.length
            ? notes.map(n => `<div class="note-item">${esc(n.note)}<div class="meta">${esc(n.author_name || '—')} · ${fmtDateTime(n.created_at)}</div></div>`).join('')
            : '<div style="font-size:.75rem;color:#8a8fa3">Aucune note</div>';
    }

    function renderTimeline(events) {
        $('timeline').innerHTML = events.length
            ? events.map(e => `<div class="tl-item"><span class="tl-time">${fmtTime(e.created_at)}</span> · ${esc(e.label)}${e.actor_name ? ` <span class="tl-actor">· ${esc(e.actor_name)}</span>` : ''}</div>`).join('')
            : '<div style="font-size:.75rem;color:#8a8fa3">—</div>';
    }

    function renderMap(a, assigned) {
        if (typeof L === 'undefined') return;
        if (!map) {
            map = L.map('alertMap').setView([a.latitude, a.longitude], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(map);
        }
        map.eachLayer(l => { if (l instanceof L.Marker) map.removeLayer(l); });
        const pin = L.divIcon({
            className: '',
            html: '<div style="width:18px;height:18px;border-radius:50%;background:#e23d3d;border:3px solid #fff;box-shadow:0 0 0 2px #e23d3d"></div>',
            iconSize: [18, 18], iconAnchor: [9, 9],
        });
        L.marker([a.latitude, a.longitude], { icon: pin }).addTo(map).bindPopup("Position de l'assuré");
        facilities.forEach(h => {
            if (h.latitude == null || h.longitude == null) return;
            const hico = L.divIcon({
                className: '',
                html: '<div style="width:20px;height:20px;border-radius:4px;background:#2d5bd7;color:#fff;display:grid;place-items:center;font-size:11px;font-weight:700;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3)">H</div>',
                iconSize: [20, 20], iconAnchor: [10, 10],
            });
            L.marker([h.latitude, h.longitude], { icon: hico }).addTo(map)
                .bindPopup(`<b>${esc(h.nom)}</b><br>${h.distance_km} km · ~${h.temps_min} min`);
        });
    }

    function renderFacilities() {
        const body = $('facBody');
        if (!facilities.length) {
            body.innerHTML = '<tr><td colspan="6" style="color:#8a8fa3">Aucun établissement trouvé</td></tr>';
            return;
        }
        body.innerHTML = facilities.map(h => `
            <tr>
                <td><strong>${esc(h.nom)}</strong><br><span style="color:#8a8fa3;font-size:.7rem">${esc(h.ville || h.adresse || '')}</span></td>
                <td>${h.distance_km} km</td>
                <td>${h.temps_min} min</td>
                <td>${(h.specialites || []).slice(0, 2).map(esc).join('<br>') || '—'}</td>
                <td><span class="fac-status">${esc(h.disponibilite)}</span></td>
                <td><button class="fac-select ${h.id === selectedHospitalId ? 'selected' : ''}" data-hid="${h.id}" type="button">${h.id === selectedHospitalId ? 'Sélectionné' : 'Sélectionner'}</button></td>
            </tr>`).join('');
        body.querySelectorAll('.fac-select').forEach(btn => {
            btn.addEventListener('click', () => {
                selectedHospitalId = parseInt(btn.dataset.hid, 10);
                renderFacilities();
            });
        });
    }

    async function reload() {
        detail = await apiCall(`/alertes/${alerteId}/detail-complet`);
        renderDetail(detail);
    }

    // ---------- Actions ----------
    function wireActions() {
        $('statutSelect').addEventListener('change', async e => {
            try {
                await apiCall(`/alertes/${alerteId}/statut`, { method: 'PUT', body: JSON.stringify({ statut: e.target.value }) });
                toast('Statut mis à jour');
                await reload();
            } catch (err) { toast(err.message || 'Erreur', true); }
        });

        $('btnRespond').addEventListener('click', async () => {
            try {
                await apiCall(`/alertes/${alerteId}/statut`, { method: 'PUT', body: JSON.stringify({ statut: 'en_cours', commentaire: 'Prise en charge par l\'opérateur' }) });
                toast('Vous avez répondu à l\'alerte');
                await reload();
            } catch (err) { toast(err.message || 'Erreur', true); }
        });

        $('btnTransfer').addEventListener('click', () => $('transferModal').classList.add('open'));
        $('btnDoTransfer').addEventListener('click', async () => {
            try {
                await apiCall(`/alertes/${alerteId}/transfer`, {
                    method: 'POST',
                    body: JSON.stringify({ cible: $('transferTarget').value, commentaire: $('transferComment').value || null }),
                });
                $('transferModal').classList.remove('open');
                toast('Alerte transférée');
                await reload();
            } catch (err) { toast(err.message || 'Erreur', true); }
        });

        $('editStatutMedical').addEventListener('click', e => { e.preventDefault(); $('smModal').classList.add('open'); });
        $('btnSaveSm').addEventListener('click', async () => {
            try {
                await apiCall(`/alertes/${alerteId}/statut-medical`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        etat_patient: $('smEtatInput').value || null,
                        motifs_symptomes: $('smSymptomesInput').value || null,
                        besoins_immediats: $('smBesoinsInput').value || null,
                        allergies_connues: $('smAllergiesInput').value || null,
                        traitements_en_cours: $('smTraitementsInput').value || null,
                    }),
                });
                $('smModal').classList.remove('open');
                toast('Statut médical enregistré');
                await reload();
            } catch (err) { toast(err.message || 'Erreur', true); }
        });

        document.querySelectorAll('[data-close]').forEach(b =>
            b.addEventListener('click', () => b.closest('.modal-backdrop').classList.remove('open')));

        $('btnAddNote').addEventListener('click', async () => {
            const v = $('noteInput').value.trim();
            if (!v) return;
            try {
                await apiCall(`/alertes/${alerteId}/notes`, { method: 'POST', body: JSON.stringify({ note: v }) });
                $('noteInput').value = '';
                await reload();
            } catch (err) { toast(err.message || 'Erreur', true); }
        });
        $('noteInput').addEventListener('keydown', e => { if (e.key === 'Enter') $('btnAddNote').click(); });

        // Communication — liens natifs
        const phone = () => (detail?.assure?.telephone || '').replace(/\s+/g, '');
        $('commAppel').addEventListener('click', () => { window.location.href = 'tel:' + phone(); });
        $('btnCall').addEventListener('click', () => { window.location.href = 'tel:' + phone(); });
        $('commSms').addEventListener('click', () => { window.location.href = 'sms:' + phone(); });
        $('commWa').addEventListener('click', () => { window.open('https://wa.me/' + phone().replace(/^\+/, ''), '_blank'); });
        $('commEmail').addEventListener('click', () => { window.location.href = 'mailto:' + (detail?.assure?.email || ''); });

        // Bandeau d'actions
        $('btnAmbulance').addEventListener('click', () => doAction('ambulance'));
        $('btnPriseEnCharge').addEventListener('click', () => doAction('prise_en_charge'));
        $('btnHotel').addEventListener('click', openHotelModal);
        $('btnDoHotel').addEventListener('click', async () => {
            const hid = +$('hotelSelect').value;
            if (!hid) { toast('Sélectionnez un hôtel', true); return; }
            try {
                await apiCall(`/ops/alertes/${alerteId}/hebergement`, {
                    method: 'POST',
                    body: JSON.stringify({
                        hotel_id: hid,
                        nb_nuits: +$('hotelNuits').value || null,
                        notes: $('hotelNotes').value || null,
                    }),
                });
                $('hotelModal').classList.remove('open');
                toast('Hébergement réservé');
                await reload();
            } catch (err) { toast(err.message || 'Erreur', true); }
        });
        $('btnNotifyHospital').addEventListener('click', async () => {
            const hid = selectedHospitalId || (detail?.hospital_assigne?.id) || (facilities[0] && facilities[0].id);
            if (!hid) { toast('Sélectionnez un établissement', true); return; }
            try {
                await apiCall(`/alertes/${alerteId}/prevenir-hopital`, { method: 'POST', body: JSON.stringify({ hospital_id: hid }) });
                toast('Hôpital prévenu');
                await reload();
            } catch (err) { toast(err.message || 'Erreur', true); }
        });
    }

    async function openHotelModal() {
        try {
            const hotels = await apiCall('/ops/hotels');
            if (!hotels.length) {
                toast('Aucun hôtel configuré — ajoutez-en dans « Hôtels »', true);
                return;
            }
            $('hotelSelect').innerHTML = hotels.map(h =>
                `<option value="${h.id}">${esc(h.nom)}${h.ville ? ' — ' + esc(h.ville) : ''}</option>`).join('');
            $('hotelModal').classList.add('open');
        } catch (err) {
            // Repli : simple événement si le module hôtels est indisponible.
            doAction('hotel');
        }
    }

    async function doAction(action) {
        try {
            const r = await apiCall(`/alertes/${alerteId}/action`, { method: 'POST', body: JSON.stringify({ action }) });
            toast(r.label || 'Action effectuée');
            await reload();
        } catch (err) { toast(err.message || 'Erreur', true); }
    }

    // ---------- Init ----------
    document.addEventListener('DOMContentLoaded', async () => {
        const ok = await requireAuth();
        if (!ok) return;
        const params = new URLSearchParams(window.location.search);
        alerteId = params.get('id') || params.get('alerte_id');
        if (!alerteId) {
            toast('Aucune alerte spécifiée', true);
            return;
        }
        wireActions();
        try {
            await reload();
            facilities = await apiCall(`/alertes/${alerteId}/etablissements-proches?limit=6`);
            renderFacilities();
            renderMap(detail.alerte, detail.hospital_assigne);
        } catch (err) {
            toast(err.message || 'Erreur de chargement', true);
        }
    });
})();
