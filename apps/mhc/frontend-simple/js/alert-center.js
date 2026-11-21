/* Centre d'alerte des urgences — liste + panneau détail latéral. */
(function () {
    'use strict';

    const API = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
    const token = () => localStorage.getItem('access_token');

    let allAlertes = [];
    let activeTab = 'toutes';

    const TABS = [
        { key: 'toutes', label: 'Toutes les alertes', match: () => true },
        { key: 'en_traitement', label: 'En traitement', match: a => a.statut === 'en_cours' },
        { key: 'a_valider', label: 'À valider', match: a => ['en_attente', 'en_cours'].includes(a.statut) },
        { key: 'validees', label: 'Validées', match: a => a.statut === 'resolue' },
        { key: 'refusees', label: 'Refusées', match: a => a.statut === 'annulee' },
        { key: 'cloturees', label: 'Clôturées', match: a => a.statut === 'cloturee' },
    ];

    // Onglet initial via ?tab= (deep-link depuis la sidebar / autres écrans).
    const urlTab = new URLSearchParams(window.location.search).get('tab');
    if (urlTab && TABS.some(t => t.key === urlTab)) activeTab = urlTab;

    const STATUT_BADGE = {
        en_attente: 'Urgente',
        en_cours: 'En traitement',
        resolue: 'Validée',
        annulee: 'Refusée',
        cloturee: 'Clôturée',
    };

    function badge(statut) {
        return '<span class="bo-badge ' + statut + '">' + (STATUT_BADGE[statut] || statut) + '</span>';
    }

    function fmt(dt) {
        if (!dt) return '—';
        const d = new Date(dt);
        return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }) + ' ' +
            d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }

    function prio(a) {
        const p = a.priorite || 'normale';
        return '<span class="bo-prio ' + p + '"></span>';
    }

    function typeUrgence(a) {
        const desc = (a.description || '').toLowerCase();
        if (desc.includes('accident')) return 'Accident';
        if (desc.includes('décès') || desc.includes('deces')) return 'Décès';
        if (desc.includes('évac') || desc.includes('evac')) return 'Évacuation sanitaire';
        return 'Maladie';
    }

    function kpis() {
        const c = s => allAlertes.filter(s).length;
        const data = [
            { label: 'Alertes reçues', v: allAlertes.length, ico: '🚨', color: 'red' },
            { label: 'En traitement', v: c(a => a.statut === 'en_cours'), ico: '⏱️', color: 'amber' },
            { label: 'Prises en charge validées', v: c(a => a.statut === 'resolue'), ico: '✅', color: 'teal' },
            { label: 'Alertes refusées', v: c(a => a.statut === 'annulee'), ico: '🚫', color: 'red' },
            { label: 'Alertes clôturées', v: c(a => a.statut === 'cloturee'), ico: '📁', color: 'slate' },
        ];
        document.getElementById('kpis').innerHTML = data.map(k =>
            '<div class="bo-kpi"><div class="bo-kpi-ico ' + k.color + '">' + k.ico + '</div>' +
            '<div><div class="l">' + k.label + '</div><div class="v">' + k.v + '</div></div></div>'
        ).join('');

        document.getElementById('filterTabs').innerHTML = TABS.map(t =>
            '<button class="bo-tab' + (t.key === activeTab ? ' active' : '') + '" data-tab="' + t.key + '">' +
            t.label + ' (' + allAlertes.filter(t.match).length + ')</button>'
        ).join('');
        document.querySelectorAll('#filterTabs .bo-tab').forEach(b =>
            b.addEventListener('click', () => {
                activeTab = b.dataset.tab;
                // Reflète l'onglet dans l'URL (deep-link partageable, état actif sidebar).
                const qs = activeTab === 'toutes' ? '' : '?tab=' + activeTab;
                history.replaceState(null, '', location.pathname + qs);
                render();
            }));
    }

    function filtered() {
        const tab = TABS.find(t => t.key === activeTab);
        const q = (document.getElementById('fSearch').value || '').toLowerCase();
        const st = document.getElementById('fStatut').value;
        const ty = document.getElementById('fType').value;
        const from = document.getElementById('fFrom').value;
        const to = document.getElementById('fTo').value;
        return allAlertes.filter(a => {
            if (!tab.match(a)) return false;
            if (st && a.statut !== st) return false;
            if (ty && typeUrgence(a).toLowerCase().indexOf(ty) < 0) return false;
            if (q) {
                const hay = ((a.numero_alerte || '') + ' ' + (a.user_full_name || '') + ' ' +
                    (a.assigned_hospital ? a.assigned_hospital.nom : '') + ' ' + (a.description || '')).toLowerCase();
                if (hay.indexOf(q) < 0) return false;
            }
            if (from && a.created_at < from) return false;
            if (to && a.created_at > to + 'T23:59') return false;
            return true;
        });
    }

    function depuis(a) {
        const t = new Date(a.created_at).getTime();
        if (!t || ['resolue', 'annulee', 'cloturee'].includes(a.statut)) return '—';
        const mins = Math.max(0, Math.floor((Date.now() - t) / 60000));
        const lbl = mins < 60 ? mins + ' min' : mins < 1440 ? Math.floor(mins / 60) + ' h ' + (mins % 60) + 'm' : Math.floor(mins / 1440) + ' j';
        return '<span class="depuis' + (mins > 30 ? ' late' : '') + '">' + lbl + '</span>';
    }

    function render() {
        kpis();
        const rows = filtered();
        document.getElementById('alertRows').innerHTML = rows.map(a =>
            '<tr onclick="openPanel(' + a.id + ')" style="cursor:pointer" title="Ouvrir le panneau de traitement">' +
            '<td>' + prio(a) + '<span class="num">' + (a.numero_alerte || 'URG-' + a.id) + '</span></td>' +
            '<td class="muted">' + fmt(a.created_at) + '</td>' +
            '<td>' + depuis(a) + '</td>' +
            '<td>' + (a.user_full_name || '—') + '</td>' +
            '<td>' + typeUrgence(a) + '</td>' +
            '<td>' + (a.assigned_hospital ? a.assigned_hospital.nom : '—') + '</td>' +
            '<td>' + (a.assigned_hospital ? (a.assigned_hospital.pays || '—') : '—') + '</td>' +
            '<td>' + badge(a.statut) + '</td>' +
            '<td class="table-actions"><select class="action-select" onclick="event.stopPropagation()">' +
            '<option value="">⚙️ Actions</option>' +
            '<option data-call="openPanel" data-arg="' + a.id + '">👁 Aperçu</option>' +
            '<option data-href="alert-detail.html?id=' + a.id + '">📄 Détails</option>' +
            '<option data-href="sos-alerts-map.html?alert_id=' + a.id + '">🗺️ Carte</option>' +
            '</select></td>' +
            '</tr>'
        ).join('') || '<tr><td colspan="9" class="muted" style="text-align:center;padding:1.4rem">Aucune alerte dans votre périmètre.</td></tr>';
        document.getElementById('countLabel').textContent = 'Affichage de ' + rows.length + ' résultat(s)';
    }

    // Détection des nouvelles alertes actives → événement consommé par
    // sos-mh-alert-modal.js (modal « Cas à prendre en charge »), même
    // mécanisme que la carte SOS — indépendant du WebSocket.
    function emitNewActiveAlertsForModal(isFirstLoad) {
        const active = (allAlertes || []).filter(a => ['en_attente', 'en_cours'].includes(a.statut));
        const idsNow = new Set(active.map(a => a.id));
        const prev = window.__mhAlertCenterActiveIds;
        window.__mhAlertCenterActiveIds = idsNow;
        if (isFirstLoad || !(prev instanceof Set)) return;
        active.forEach(a => {
            if (!prev.has(a.id)) {
                window.dispatchEvent(new CustomEvent('mh-sos-new-active-alert', {
                    detail: { alerte_id: a.id, alert: a }
                }));
            }
        });
    }

    async function load() {
        const isFirst = !load._once;
        const res = await fetch(API + '/sos/?limit=200', { headers: { Authorization: 'Bearer ' + token() } });
        if (!res.ok) { document.getElementById('alertRows').innerHTML = '<tr><td colspan="9">Erreur de chargement (HTTP ' + res.status + ')</td></tr>'; return; }
        allAlertes = await res.json();
        emitNewActiveAlertsForModal(isFirst);
        load._once = true;
        render();
    }

    // ------- Panneau détail -------
    window.openPanel = async function (id) {
        const panel = document.getElementById('detailPanel');
        panel.classList.add('open');
        const res = await fetch(API + '/alertes/' + id + '/detail-complet', {
            headers: { Authorization: 'Bearer ' + token() },
        });
        if (!res.ok) return;
        const d = await res.json();
        const a = d.alerte || {};
        const as = d.assure || {};
        const h = d.hospital_assigne || {};

        document.getElementById('dpTag').textContent = STATUT_BADGE[a.statut] || a.statut;
        document.getElementById('dpTag').className = 'dp-tag';
        if (d.sinistre_bloque) {
            const b = document.createElement('span');
            b.className = 'chip-bloque';
            b.textContent = '🔒 Bloqué' + (d.motif_blocage ? ' — ' + d.motif_blocage : '');
            document.getElementById('dpTag').after(b);
        }

        document.getElementById('dpAssure').innerHTML =
            '<h4>👤 Informations assuré</h4>' +
            '<div class="dp-row"><span class="k">Nom complet</span><span class="v">' + (as.nom || '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">N° assuré</span><span class="v">' + (as.numero_souscription || '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">Âge</span><span class="v">' + (as.age ? as.age + ' ans' : '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">Téléphone</span><span class="v">' + (as.telephone || '—') + '</span></div>';

        const sm = d.statut_medical || {};
        const descHtml = d.medical_masque
            ? '<span class="mhc-lock">🔒 Donnée réservée au pôle médical</span>'
            : (a.description || '—');
        document.getElementById('dpMedical').innerHTML =
            '<h4>📋 Informations médicales</h4>' +
            '<div class="dp-row"><span class="k">Type d\'urgence</span><span class="v">' + typeUrgence(a) + '</span></div>' +
            '<div class="dp-row"><span class="k">Description</span><span class="v" style="max-width:55%">' + descHtml + '</span></div>' +
            '<div class="dp-row"><span class="k">Établissement</span><span class="v">' + (h.nom || '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">Date et heure</span><span class="v">' + fmt(a.created_at) + '</span></div>' +
            '<div class="dp-row"><span class="k">Depuis</span><span class="v">' + depuis(a) + '</span></div>' +
            (sm.etat_patient ? '<div class="dp-row"><span class="k">État patient</span><span class="v">' + sm.etat_patient + '</span></div>' : '') +
            (d.medical_masque ? '' : (sm.motifs_symptomes ? '<div class="dp-row"><span class="k">Symptômes</span><span class="v">' + sm.motifs_symptomes + '</span></div>' : ''));

        const docs = d.documents || {};
        const docList = [...(docs.care_documents || []), ...(docs.attachments || [])];
        document.getElementById('dpDocs').innerHTML =
            '<h4>📄 Documents</h4>' +
            (docList.length ? docList.slice(0, 5).map(x =>
                '<div class="dp-row"><span class="k">📎</span><span class="v">' + (x.titre || x.filename || x.numero || 'Document') + '</span></div>'
            ).join('') : '<div class="muted" style="font-size:0.74rem">Aucun document</div>');

        const canEdit = window.MhPermissions
            ? window.MhPermissions.can('alerte_sos', 'edition')
            : true;
        const role = localStorage.getItem('user_role') || '';

        // Vérification de véracité (médecin-conseil / affaires médicales) :
        // mêmes boutons Accepter/Refuser que la fiche dossier ouverte
        // depuis le tableau de bord — sinon le choix n'apparaît pas ici.
        let verifHtml = '';
        const VERIF_ROLES = ['medecin_referent_mh', 'doctor', 'agent_medical_mhc', 'superviseur_affaires_medicales', 'admin'];
        if (d.sinistre_id && VERIF_ROLES.includes(role) && ['en_attente', 'en_cours'].includes(a.statut)) {
            const r2 = await fetch(API + '/sos/' + id, { headers: { Authorization: 'Bearer ' + token() } });
            if (r2.ok) {
                const al = await r2.json();
                const step = (al.workflow_steps || []).find(s => s.step_key === 'verification_urgence');
                if (!step || !['completed', 'cancelled'].includes(step.statut)) {
                    verifHtml =
                        '<button class="btn btn-primary" onclick="verifyAlert(' + d.sinistre_id + ',true,' + id + ')">✓ Accepter la prise en charge</button>' +
                        '<button class="btn btn-danger" onclick="verifyAlert(' + d.sinistre_id + ',false,' + id + ')">✗ Alerte non avérée</button>';
                }
            }
        }

        let blocageBtn = '';
        if (d.sinistre_id) {
            if (d.sinistre_bloque && ['admin', 'superviseur_technique'].includes(role)) {
                blocageBtn = '<button class="btn btn-outline" onclick="debloquerSinistre(' + d.sinistre_id + ',' + id + ')">🔓 Débloquer le dossier</button>';
            } else if (!d.sinistre_bloque && ['admin', 'superviseur_technique', 'agent_conformite_sinistre'].includes(role)) {
                blocageBtn = '<button class="btn btn-danger" onclick="bloquerSinistre(' + d.sinistre_id + ',' + id + ')">⛔ Bloquer le dossier</button>';
            }
        }
        document.getElementById('dpActions').innerHTML = verifHtml + (canEdit
            ? '<a class="btn btn-primary" href="alert-detail.html?id=' + id + '" style="text-decoration:none;text-align:center">✓ Traiter l\'alerte</a>' +
            '<button class="btn btn-outline" onclick="askInfo(' + id + ')">Demander des informations</button>' +
            '<button class="btn btn-danger" onclick="refuseAlert(' + id + ')">Refuser la prise en charge</button>'
            : '<a class="btn btn-outline" href="alert-detail.html?id=' + id + '" style="text-decoration:none;text-align:center">Voir le détail</a>') + blocageBtn;
    };

    window.bloquerSinistre = async function (sinistreId, alerteId) {
        const motif = prompt('Motif du blocage (obligatoire pour la conformité) :');
        if (motif === null) return;
        const res = await fetch(API + '/admin/sinistres/sinistres/' + sinistreId + '/bloquer', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token() },
            body: JSON.stringify({ motif }),
        });
        if (res.ok) { if (window.mhcToast) mhcToast('Dossier bloqué.'); openPanel(alerteId); }
        else { const e = await res.json().catch(() => ({})); if (window.mhcToast) mhcToast(e.detail || 'Blocage impossible', true); }
    };

    window.debloquerSinistre = async function (sinistreId, alerteId) {
        if (!confirm('Débloquer ce dossier ?')) return;
        const res = await fetch(API + '/admin/sinistres/sinistres/' + sinistreId + '/debloquer', {
            method: 'PUT',
            headers: { Authorization: 'Bearer ' + token() },
        });
        if (res.ok) { if (window.mhcToast) mhcToast('Dossier débloqué.'); openPanel(alerteId); }
        else { const e = await res.json().catch(() => ({})); if (window.mhcToast) mhcToast(e.detail || 'Déblocage impossible', true); }
    };

    window.closePanel = function () {
        document.getElementById('detailPanel').classList.remove('open');
    };

    window.verifyAlert = async function (sinistreId, approve, alerteId) {
        const notes = prompt(approve
            ? 'Commentaire (optionnel) — confirmer la prise en charge :'
            : 'Motif du refus — alerte non avérée :');
        if (notes === null) return;
        const res = await fetch(API + '/sos/sinistres/' + sinistreId + '/verification', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token() },
            body: JSON.stringify({ approve, notes: notes || undefined }),
        });
        if (res.ok) {
            if (window.mhcToast) mhcToast(approve ? 'Prise en charge confirmée.' : 'Alerte marquée non avérée.');
            closePanel();
            load();
        } else {
            const e = await res.json().catch(() => ({}));
            if (window.mhcToast) mhcToast(e.detail || 'Action impossible', true);
        }
    };

    window.askInfo = async function (id) {
        const note = prompt('Message de demande d\'informations :');
        if (!note) return;
        await fetch(API + '/alertes/' + id + '/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token() },
            body: JSON.stringify({ note: '[Demande d\'informations] ' + note }),
        });
        closePanel();
    };

    window.refuseAlert = async function (id) {
        if (!confirm('Refuser cette alerte / prise en charge ?')) return;
        await fetch(API + '/alertes/' + id + '/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token() },
            body: JSON.stringify({ action: 'refuser', notes: 'Refus depuis le centre d\'alerte' }),
        }).catch(() => {});
        closePanel();
        load();
    };

    // ------- Déclaration manuelle (assuré au téléphone) -------
    const DECLARE_ROLES = ['medecin_referent_mh', 'agent_medical_mhc', 'superviseur_affaires_medicales', 'admin'];
    let declareSelectedUserId = null;
    let declareSearchTimer = null;

    function initDeclaration() {
        const role = (localStorage.getItem('user_role') || '').toLowerCase();
        const btn = document.getElementById('declareBtn');
        if (!btn || !DECLARE_ROLES.includes(role)) return;
        btn.hidden = false;
        btn.addEventListener('click', () => {
            declareSelectedUserId = null;
            document.getElementById('declareSubmit').disabled = true;
            document.getElementById('declareSearch').value = '';
            document.getElementById('declareResults').innerHTML = '';
            document.getElementById('declareModal').classList.add('open');
        });
        document.getElementById('declareSearch').addEventListener('input', (e) => {
            clearTimeout(declareSearchTimer);
            const q = e.target.value.trim();
            if (q.length < 2) { document.getElementById('declareResults').innerHTML = ''; return; }
            declareSearchTimer = setTimeout(() => searchAssures(q), 300);
        });
        document.getElementById('declareSubmit').addEventListener('click', submitDeclaration);
    }

    async function searchAssures(q) {
        const box = document.getElementById('declareResults');
        box.innerHTML = '<div class="muted">Recherche…</div>';
        const res = await fetch(API + '/sos/assures/search?q=' + encodeURIComponent(q), {
            headers: { Authorization: 'Bearer ' + token() },
        });
        if (!res.ok) { box.innerHTML = '<div class="muted">Recherche impossible (HTTP ' + res.status + ')</div>'; return; }
        const users = await res.json();
        if (!users.length) { box.innerHTML = '<div class="muted">Aucun assuré trouvé.</div>'; return; }
        box.innerHTML = users.map(u =>
            '<div class="declare-item' + (u.souscription_active ? '' : ' disabled') + '" data-uid="' + u.id + '">' +
            '<strong>' + (u.nom || '—') + '</strong> <span class="muted">' + (u.email || '') + ' ' + (u.telephone || '') + '</span>' +
            (u.souscription_active
                ? ' <span class="bo-badge resolue">Couvert — ' + (u.souscription_active.numero || '') + '</span>'
                : ' <span class="bo-badge annulee">Sans souscription active</span>') +
            '</div>'
        ).join('');
        box.querySelectorAll('.declare-item:not(.disabled)').forEach(el => el.addEventListener('click', () => {
            box.querySelectorAll('.declare-item').forEach(x => x.classList.remove('selected'));
            el.classList.add('selected');
            declareSelectedUserId = Number(el.dataset.uid);
            document.getElementById('declareSubmit').disabled = false;
        }));
    }

    async function submitDeclaration() {
        if (!declareSelectedUserId) return;
        const submit = document.getElementById('declareSubmit');
        submit.disabled = true;
        const res = await fetch(API + '/sos/declaration-manuelle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token() },
            body: JSON.stringify({
                user_id: declareSelectedUserId,
                description: document.getElementById('declareDescription').value.trim() || undefined,
                priorite: document.getElementById('declarePriorite').value,
            }),
        });
        if (res.ok) {
            document.getElementById('declareModal').classList.remove('open');
            load();
        } else {
            const err = await res.json().catch(() => ({}));
            alert(err.detail || 'Déclaration impossible.');
            submit.disabled = false;
        }
    }

    document.getElementById('exportBtn').addEventListener('click', () => {
        const rows = filtered();
        const csv = 'numero;date;assure;type;etablissement;statut\n' + rows.map(a =>
            [a.numero_alerte, fmt(a.created_at), a.user_full_name, typeUrgence(a),
             (a.assigned_hospital || {}).nom || '', STATUT_BADGE[a.statut] || a.statut].join(';')
        ).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const u = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = u; link.download = 'alertes.csv'; link.click();
    });

    ['fSearch', 'fStatut', 'fType', 'fFrom', 'fTo'].forEach(id =>
        document.getElementById(id).addEventListener('input', render));

    // Quand le modal sonore « nouvelle alerte » se déclenche (WebSocket),
    // la liste se recharge pour faire apparaître le dossier immédiatement.
    window.addEventListener('mh-sos-refresh-alerts', () => { load(); });

    // Polling : nouvelles alertes détectées → modal + liste à jour.
    setInterval(() => { if (!document.hidden) load(); }, 15000);

    document.addEventListener('DOMContentLoaded', async () => {
        const isValid = await requireAuth();
        // Profils internes MHC + personnel des hôpitaux partenaires : les
        // alertes orientées vers un établissement remontent à sa réception.
        const HOSPITAL_ALERT_ROLES = ['hospital_admin', 'agent_reception_hopital', 'medecin_hopital'];
        const role = (localStorage.getItem('user_role') || '').toLowerCase();
        const allowed = isValid && (
            (window.MhPermissions && window.MhPermissions.isInternalBackoffice()) ||
            HOSPITAL_ALERT_ROLES.includes(role)
        );
        if (!allowed) {
            if (isValid) {
                alert('Accès refusé. Ce contenu est réservé aux profils internes MHC et au personnel hospitalier.');
                redirectForbidden('index.html');
            }
            return;
        }
        initDeclaration();
        await load();
        // Lien profond depuis la recherche globale : ouvrir le panneau de l'alerte.
        const focus = new URLSearchParams(location.search).get('focus');
        if (focus) openPanel(Number(focus));
    });
    if (document.readyState !== 'loading') load();
})();
