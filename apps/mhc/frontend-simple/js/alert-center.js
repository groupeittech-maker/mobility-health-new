/* Centre d'alerte des urgences — liste + panneau détail latéral. */
(function () {
    'use strict';

    const API = window.API_URL || 'https://srv1324425.hstgr.cloud/api/v1';
    const token = () => localStorage.getItem('auth_token');

    let allAlertes = [];
    let activeTab = 'toutes';

    const TABS = [
        { key: 'toutes', label: 'Toutes les alertes', match: () => true },
        { key: 'en_traitement', label: 'En traitement', match: a => a.statut === 'en_cours' },
        { key: 'a_valider', label: 'À valider', match: a => a.statut === 'en_attente' },
        { key: 'validees', label: 'Validées', match: a => a.statut === 'resolue' },
        { key: 'refusees', label: 'Refusées', match: a => a.statut === 'annulee' },
        { key: 'cloturees', label: 'Clôturées', match: a => a.statut === 'cloturee' },
    ];

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
            b.addEventListener('click', () => { activeTab = b.dataset.tab; render(); }));
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

    function render() {
        kpis();
        const rows = filtered();
        document.getElementById('alertRows').innerHTML = rows.map(a =>
            '<tr>' +
            '<td>' + prio(a) + '<span class="num">' + (a.numero_alerte || 'URG-' + a.id) + '</span></td>' +
            '<td class="muted">' + fmt(a.created_at) + '</td>' +
            '<td>' + (a.user_full_name || '—') + '</td>' +
            '<td>' + typeUrgence(a) + '</td>' +
            '<td>' + (a.assigned_hospital ? a.assigned_hospital.nom : '—') + '</td>' +
            '<td>' + (a.assigned_hospital ? (a.assigned_hospital.pays || '—') : '—') + '</td>' +
            '<td>' + badge(a.statut) + '</td>' +
            '<td><a class="act-link" onclick="openPanel(' + a.id + ')">👁</a> ' +
            '<a class="act-link" href="alert-detail.html?id=' + a.id + '">Détails</a></td>' +
            '</tr>'
        ).join('') || '<tr><td colspan="8" class="muted" style="text-align:center;padding:1.4rem">Aucune alerte</td></tr>';
        document.getElementById('countLabel').textContent = 'Affichage de ' + rows.length + ' résultat(s)';
    }

    async function load() {
        const res = await fetch(API + '/alertes/?limit=200', { headers: { Authorization: 'Bearer ' + token() } });
        if (!res.ok) { document.getElementById('alertRows').innerHTML = '<tr><td colspan="8">Erreur de chargement</td></tr>'; return; }
        allAlertes = await res.json();
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

        document.getElementById('dpAssure').innerHTML =
            '<h4>👤 Informations assuré</h4>' +
            '<div class="dp-row"><span class="k">Nom complet</span><span class="v">' + (as.nom || '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">N° assuré</span><span class="v">' + (as.numero_souscription || '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">Âge</span><span class="v">' + (as.age ? as.age + ' ans' : '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">Téléphone</span><span class="v">' + (as.telephone || '—') + '</span></div>';

        const sm = d.statut_medical || {};
        document.getElementById('dpMedical').innerHTML =
            '<h4>📋 Informations médicales</h4>' +
            '<div class="dp-row"><span class="k">Type d\'urgence</span><span class="v">' + typeUrgence(a) + '</span></div>' +
            '<div class="dp-row"><span class="k">Description</span><span class="v" style="max-width:55%">' + (a.description || '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">Établissement</span><span class="v">' + (h.nom || '—') + '</span></div>' +
            '<div class="dp-row"><span class="k">Date et heure</span><span class="v">' + fmt(a.created_at) + '</span></div>' +
            (sm.etat_patient ? '<div class="dp-row"><span class="k">État patient</span><span class="v">' + sm.etat_patient + '</span></div>' : '');

        const docs = d.documents || {};
        const docList = [...(docs.care_documents || []), ...(docs.attachments || [])];
        document.getElementById('dpDocs').innerHTML =
            '<h4>📄 Documents</h4>' +
            (docList.length ? docList.slice(0, 5).map(x =>
                '<div class="dp-row"><span class="k">📎</span><span class="v">' + (x.titre || x.filename || x.numero || 'Document') + '</span></div>'
            ).join('') : '<div class="muted" style="font-size:0.74rem">Aucun document</div>');

        document.getElementById('dpActions').innerHTML =
            '<a class="btn btn-primary" href="alert-detail.html?id=' + id + '" style="text-decoration:none;text-align:center">✓ Traiter l\'alerte</a>' +
            '<button class="btn btn-outline" onclick="askInfo(' + id + ')">Demander des informations</button>' +
            '<button class="btn btn-danger" onclick="refuseAlert(' + id + ')">Refuser la prise en charge</button>';
    };

    window.closePanel = function () {
        document.getElementById('detailPanel').classList.remove('open');
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

    document.addEventListener('DOMContentLoaded', load);
    if (document.readyState !== 'loading') load();
})();
