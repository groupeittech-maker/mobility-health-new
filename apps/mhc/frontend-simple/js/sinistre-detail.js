/* Détail du sinistre — infos, statut, matrice parcours, onglets. */
(function () {
    'use strict';

    const API = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
    const token = () => localStorage.getItem('access_token');
    const id = new URLSearchParams(location.search).get('id');

    let detail = null;
    let parcours = null;
    let activeTab = 'details';

    const STATUT_LABELS = { en_cours: 'En cours', resolu: 'Réglé', annule: 'Annulé', cloture: 'Clôturé' };
    const TIMELINE_STEPS = [
        { key: 'declare', label: 'Déclaration du sinistre' },
        { key: 'valide', label: "Validation de l'urgence" },
        { key: 'pc', label: 'Prise en charge en cours' },
        { key: 'reglement', label: 'Règlement en attente' },
        { key: 'cloture', label: 'Clôture du sinistre' },
    ];

    function fmt(dt) {
        if (!dt) return '—';
        const d = new Date(dt);
        return d.toLocaleDateString('fr-FR') + ' - ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }

    function initials(n) { return (n || '?').split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase(); }

    async function load() {
        if (!id) { document.querySelector('main').innerHTML = '<p style="padding:2rem">Paramètre ?id= manquant.</p>'; return; }
        const [dRes, pRes] = await Promise.all([
            fetch(API + '/sinistre-detail/sinistres/' + id + '/detail-complet', { headers: { Authorization: 'Bearer ' + token() } }),
            fetch(API + '/sinistre-detail/sinistres/' + id + '/parcours', { headers: { Authorization: 'Bearer ' + token() } }),
        ]);
        if (!dRes.ok) { document.querySelector('main').innerHTML = '<p style="padding:2rem">Sinistre introuvable ou accès refusé.</p>'; return; }
        detail = await dRes.json();
        parcours = pRes.ok ? await pRes.json() : null;
        renderAll();
    }

    function renderAll() {
        const s = detail.sinistre || {};
        const a = detail.alerte || {};
        const sub = detail.souscription || {};
        const as = detail.assure || {};
        const stay = detail.stay || {};

        // Header
        const badge = document.getElementById('sinStatut');
        badge.textContent = STATUT_LABELS[s.statut] || s.statut || '—';
        badge.className = 'bo-badge ' + s.statut;
        document.getElementById('sinMaj').textContent = 'Dernière mise à jour : ' + fmt(s.created_at);

        // Générales
        document.getElementById('fNumero').textContent = s.numero || '—';
        document.getElementById('fPolice').textContent = sub.numero || '—';
        document.getElementById('fAssure').textContent = as.nom || '—';
        document.getElementById('fAssureMeta').textContent =
            (as.date_naissance ? 'Né(e) le ' + as.date_naissance + '  |  ' : '') + (sub.numero || '');
        document.getElementById('fDate').textContent = fmt(a.created_at);
        const adresse = a.adresse || '';
        const parts = adresse.split(',').map(x => x.trim());
        document.getElementById('fPays').textContent = parts.length > 1 ? parts[parts.length - 1] : '—';
        document.getElementById('fVille').textContent = parts.length > 1 ? parts[parts.length - 2] : (parts[0] || '—');
        document.getElementById('fLieu').textContent = adresse || '—';

        // Photos
        const atts = detail.attachments || [];
        document.getElementById('photos').innerHTML =
            atts.filter(x => (x.type || '').includes('photo') || /jpe?g|png/i.test(x.filename || '')).slice(0, 4).map(x =>
                '<div class="ph" title="' + (x.filename || '') + '" style="display:grid;place-items:center;font-size:0.6rem;color:#8a8fa3">📷</div>'
            ).join('') + '<div class="add">+ Ajouter<br>des photos</div>';

        // Médicales
        if (a.description && a.description.toLowerCase().includes('accident')) document.getElementById('mType').value = 'Accident';
        document.getElementById('mMedecin').textContent = (s.medecin_referent || {}).nom || '—';
        document.getElementById('mDiagnostic').value = a.description || stay.report_motif_consultation || '';
        document.getElementById('mCommentaires').value = stay.report_observations || '';

        // Timeline statut
        const st = s.statut;
        let currentIdx = 1;
        if (st === 'resolu' || st === 'cloture') currentIdx = 4;
        else if (detail.care_documents && detail.care_documents.length) currentIdx = 2;
        document.getElementById('statusTimeline').innerHTML = TIMELINE_STEPS.map((t, i) =>
            '<div class="bo-tl-item ' + (i < currentIdx ? 'done' : i === currentIdx ? 'active' : '') + '">' +
            '<span class="lbl">' + t.label + '</span></div>'
        ).join('');

        renderParcours();
        renderTabs();
    }

    // ---------- Matrice parcours ----------
    function renderParcours() {
        if (!parcours) { document.getElementById('parcours').innerHTML = '<tbody><tr><td>Données indisponibles</td></tr></tbody>'; return; }
        const editable = window.MhPermissions && MhPermissions.can('sinistres', 'edition');
        let html = '<thead><tr><th>Parties prenantes /<br>Étapes</th>' +
            parcours.etapes.map(e => '<th>' + e.label + '</th>').join('') + '</tr></thead><tbody>';
        parcours.parties.forEach(p => {
            html += '<tr><td><span class="pm-avatar">' + initials(p.label) + '</span>' + p.label + '</td>';
            parcours.etapes.forEach(e => {
                const v = (parcours.cells[p.key] || {})[e.key] || '—';
                const cls = v === 'A' ? 'a' : v === 'R' ? 'r' : '';
                const ed = editable ? ' editable' : '';
                const sym = v === '—' ? '— ▾' : v + ' ▾';
                html += '<td><span class="bo-cell ' + cls + ed + '" data-p="' + p.key + '" data-e="' + e.key + '">' + sym + '</span></td>';
            });
            html += '</tr>';
        });
        html += '</tbody>';
        document.getElementById('parcours').innerHTML = html;

        if (editable) {
            document.querySelectorAll('.bo-cell.editable').forEach(cell => {
                cell.addEventListener('click', () => cycleCell(cell));
            });
        }
    }

    function cycleCell(cell) {
        // Rotation locale : — → A → R → —  (indicateur décisionnel, persisté via les documents)
        const cur = cell.textContent.trim()[0];
        const next = cur === 'A' ? 'R' : cur === 'R' ? '—' : 'A';
        cell.className = 'bo-cell editable ' + (next === 'A' ? 'a' : next === 'R' ? 'r' : '');
        cell.textContent = next + ' ▾';
    }

    // ---------- Onglets ----------
    function renderTabs() {
        const docs = detail.care_documents || [];
        const atts = detail.attachments || [];
        const tabs = [
            { key: 'details', label: 'Détails' },
            { key: 'documents', label: 'Documents', cnt: docs.length + atts.length },
            { key: 'echanges', label: 'Échanges', cnt: (detail.historique || []).length },
            { key: 'factures', label: 'Factures', cnt: detail.invoice ? 1 : 0 },
            { key: 'remboursement', label: 'Remboursement' },
            { key: 'historique', label: 'Historique' },
        ];
        document.getElementById('bottomTabs').innerHTML = tabs.map(t =>
            '<button class="bo-tab' + (t.key === activeTab ? ' active' : '') + '" data-t="' + t.key + '">' +
            t.label + (t.cnt !== undefined ? ' <span class="cnt">' + t.cnt + '</span>' : '') + '</button>'
        ).join('');
        document.querySelectorAll('#bottomTabs .bo-tab').forEach(b =>
            b.addEventListener('click', () => { activeTab = b.dataset.t; renderTabs(); }));
        renderTabBody();
    }

    function renderTabBody() {
        const el = document.getElementById('tabBody');
        const docs = detail.care_documents || [];
        const atts = detail.attachments || [];
        const hist = detail.historique || [];

        if (activeTab === 'details') {
            const stay = detail.stay || {};
            el.innerHTML =
                '<div class="bo-info-list">' +
                '<div class="ir"><span class="k">Statut séjour</span><span class="v">' + (stay.status || '—') + '</span></div>' +
                '<div class="ir"><span class="k">Service</span><span class="v">' + (stay.service || '—') + '</span></div>' +
                '<div class="ir"><span class="k">Entrée</span><span class="v">' + fmt(stay.started_at) + '</span></div>' +
                '<div class="ir"><span class="k">Sortie</span><span class="v">' + fmt(stay.ended_at) + '</span></div>' +
                '<div class="ir"><span class="k">Motif hospitalisation</span><span class="v">' + (stay.report_motif_hospitalisation || '—') + '</span></div>' +
                '</div>';
        } else if (activeTab === 'documents') {
            el.innerHTML = (docs.length || atts.length) ?
                docs.map(d =>
                    '<div class="ir" style="display:flex;justify-content:space-between;padding:0.45rem 0;border-bottom:1px dashed #f1f2f8">' +
                    '<span>' + (d.titre || d.type) + ' — <b>' + d.numero + '</b></span>' +
                    '<span class="bo-badge ' + d.validation_status + '">' + (d.validation_status || '') + '</span></div>'
                ).join('') +
                atts.map(x => '<div style="padding:0.45rem 0;border-bottom:1px dashed #f1f2f8">📎 ' + (x.filename || 'Pièce jointe') + '</div>').join('')
                : '<p class="muted">Aucun document.</p>';
        } else if (activeTab === 'echanges' || activeTab === 'historique') {
            el.innerHTML = hist.length ?
                '<div class="bo-timeline">' + hist.map(h =>
                    '<div class="bo-tl-item done"><span class="t">' + fmt(h.at) + '</span>' +
                    '<span class="lbl">' + (h.label || h.type) + '</span>' +
                    (h.actor ? '<div class="sub">' + h.actor + '</div>' : '') + '</div>'
                ).join('') + '</div>'
                : '<p class="muted">Aucun événement.</p>';
        } else if (activeTab === 'factures') {
            const inv = detail.invoice;
            el.innerHTML = inv ?
                '<div class="bo-info-list"><div class="ir"><span class="k">N° facture</span><span class="v">' + (inv.numero || inv.id) + '</span></div>' +
                '<div class="ir"><span class="k">Montant TTC</span><span class="v">' + Number(inv.montant_ttc).toLocaleString('fr-FR') + ' FCFA</span></div>' +
                '<div class="ir"><span class="k">Statut</span><span class="v"><span class="bo-badge ' + inv.statut + '">' + inv.statut + '</span></span></div></div>'
                : '<p class="muted">Aucune facture hospitalière liée.</p>';
        } else if (activeTab === 'remboursement') {
            el.innerHTML = '<p class="muted">Aucun remboursement associé à ce sinistre.</p>';
        }
    }

    // Sauvegarde infos médicales → note sur l'alerte liée
    document.getElementById('saveMedical').addEventListener('click', async () => {
        if (!detail || !detail.alerte) return;
        const note = 'Diagnostic: ' + document.getElementById('mDiagnostic').value +
            '\nCommentaires: ' + document.getElementById('mCommentaires').value;
        await fetch(API + '/alertes/' + detail.alerte.id + '/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token() },
            body: JSON.stringify({ note: note }),
        });
        alert('Informations médicales enregistrées.');
    });

    document.addEventListener('DOMContentLoaded', load);
    if (document.readyState !== 'loading') load();
})();
