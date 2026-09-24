/* Tableau de bord back-office — données par profil. */
(function () {
    'use strict';

    const API = window.API_URL || 'https://srv1324425.hstgr.cloud/api/v1';
    const role = localStorage.getItem('user_role') || 'user';
    const name = localStorage.getItem('user_name') || '';

    const KPIS_BY_ROLE = {
        medical: [
            { key: 'demandes_medicales.total_mois', label: 'Demandes médicales', ico: '📋', color: 'purple' },
            { key: 'demandes_medicales.prises_en_charge_emises', label: 'Prises en charge émises', ico: '✅', color: 'teal' },
            { key: 'demandes_medicales.refus_emis', label: 'Refus émis', ico: '🚫', color: 'red' },
            { key: 'demandes_medicales.hospitalisations', label: 'Hospitalisations', ico: '🛏️', color: 'blue' },
            { key: 'demandes_medicales.rapatriements', label: 'Rapatriements', ico: '✈️', color: 'slate' },
        ],
        production: [
            { key: 'production.comptes_crees', label: 'Nouveaux comptes créés', ico: '👤', color: 'purple' },
            { key: 'production.souscriptions', label: 'Souscriptions coordonnées', ico: '📄', color: 'teal' },
            { key: 'production.avenants', label: 'Avenants traités', ico: '📝', color: 'blue' },
            { key: 'production.primes_encaissees', label: 'Primes encaissées', ico: '💰', color: 'teal', fmt: v => (v || 0).toLocaleString('fr-FR') + ' FCFA' },
            { key: 'production.remboursements', label: 'Remboursements / annulations', ico: '🔄', color: 'red' },
        ],
        sinistre: [
            { key: 'sinistres.total', label: 'Sinistres total', ico: '📁', color: 'purple' },
            { key: 'sinistres.en_cours', label: 'En cours', ico: '⏳', color: 'amber' },
            { key: 'sinistres.resolus', label: 'Réglés', ico: '✅', color: 'teal' },
            { key: 'alertes.en_traitement', label: 'Alertes en traitement', ico: '🚨', color: 'red' },
        ],
        alertes: [
            { key: 'alertes.recues', label: 'Alertes reçues', ico: '🚨', color: 'red' },
            { key: 'alertes.en_traitement', label: 'En traitement', ico: '⏱️', color: 'amber' },
            { key: 'alertes.valides', label: 'Prises en charge validées', ico: '✅', color: 'teal' },
            { key: 'alertes.refusees', label: 'Alertes refusées', ico: '🚫', color: 'red' },
            { key: 'alertes.cloturees', label: 'Alertes clôturées', ico: '📁', color: 'slate' },
        ],
    };

    function roleGroup(r) {
        if (['medecin_referent_mh', 'medical_reviewer', 'superviseur_affaires_medicales', 'agent_medical_mhc', 'agent_conformite_medical', 'agent_medical_assureur'].includes(r)) return 'medical';
        if (['production_agent', 'agent_conformite_production', 'superviseur_technique', 'assistant_souscription', 'agent_production_assureur', 'agent_production_courtier'].includes(r)) return 'production';
        if (['agent_sinistre_mh', 'agent_sinistre_assureur', 'agent_sinistre_courtier', 'agent_conformite_sinistre'].includes(r)) return 'sinistre';
        if (['sos_operator'].includes(r)) return 'alertes';
        return 'production';
    }

    const QUICK_BY_ROLE = {
        medical: [
            { href: 'alert-center.html', ico: '🚨', label: "Traiter les alertes" },
            { href: 'medical-validations.html', ico: '✔️', label: 'Validations en attente' },
            { href: 'sinistre-invoices.html', ico: '📄', label: 'Factures à valider' },
            { href: 'admin-ops.html', ico: '🏨', label: 'Hôtels & transport' },
        ],
        production: [
            { href: 'admin-users.html', ico: '👤', label: 'Créer un compte utilisateur' },
            { href: 'admin-subscriptions.html', ico: '📋', label: 'Coordonner une souscription' },
            { href: 'admin-attestations.html', ico: '📄', label: 'Attestations' },
            { href: 'admin-products.html', ico: '💠', label: 'Produits' },
        ],
        sinistre: [
            { href: 'sinistre-invoices.html', ico: '📁', label: 'Suivi des sinistres' },
            { href: 'alert-center.html', ico: '🚨', label: "Alertes" },
            { href: 'finance-outbound.html', ico: '💰', label: 'Paiements' },
        ],
        default: [
            { href: 'alert-center.html', ico: '🚨', label: 'Centre d\'alertes' },
            { href: 'admin-users.html', ico: '👤', label: 'Utilisateurs' },
            { href: 'statistics-portal.html', ico: '📊', label: 'Reporting' },
        ],
    };

    function get(obj, path) {
        return path.split('.').reduce((o, k) => (o || {})[k], obj);
    }

    function fmtDate() {
        const d = new Date();
        const days = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
        const months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
        return days[d.getDay()] + ' ' + d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
    }

    function badge(statut) {
        const s = (statut || '').toString().toLowerCase().replace(/\s+/g, '_');
        const lbl = (statut || '—').toString().replace(/_/g, ' ');
        return '<span class="bo-badge ' + s + '">' + lbl + '</span>';
    }

    async function load() {
        document.getElementById('greeting').textContent = 'Bonjour ' + (name.split(' ')[0] || '') + ',';
        document.getElementById('todayLabel').textContent = "Aujourd'hui : " + fmtDate();

        const token = localStorage.getItem('auth_token');
        const res = await fetch(API + '/admin/dashboard/summary', {
            headers: { Authorization: 'Bearer ' + token },
        });
        if (!res.ok) { document.getElementById('kpis').innerHTML = '<p style="color:#c81e1e">Impossible de charger les données.</p>'; return; }
        const d = await res.json();

        // KPIs par groupe de profil
        const grp = KPIS_BY_ROLE[roleGroup(role)] || KPIS_BY_ROLE.production;
        document.getElementById('kpis').innerHTML = grp.map(k => {
            const raw = get(d, k.key);
            const val = k.fmt ? k.fmt(raw) : raw;
            return '<div class="bo-kpi"><div class="bo-kpi-ico ' + k.color + '">' + k.ico + '</div>' +
                '<div><div class="l">' + k.label + '</div><div class="v">' + (val ?? '—') + '</div></div></div>';
        }).join('');

        // Donut répartition
        const parts = d.repartition_demandes || [];
        const total = parts.reduce((s, p) => s + p.value, 0);
        let acc = 0;
        const segs = parts.filter(p => p.value > 0).map(p => {
            const from = acc / Math.max(total, 1) * 360;
            acc += p.value;
            return p.color + ' ' + from + 'deg ' + (acc / Math.max(total, 1) * 360) + 'deg';
        });
        document.getElementById('donut').style.background =
            'conic-gradient(' + (segs.length ? segs.join(',') : '#eceef6 0 360deg') + ')';
        document.getElementById('donutCenter').innerHTML = total + '<small>demandes</small>';
        document.getElementById('donutLegend').innerHTML = parts.map(p =>
            '<li><span class="dot" style="background:' + p.color + '"></span>' + p.label +
            '<span class="pct">' + (total ? Math.round(p.value / total * 100) : 0) + '%</span></li>'
        ).join('');

        // Statut global
        const sg = d.statut_global || {};
        const sgTotal = Math.max((sg.validees || 0) + (sg.en_analyse || 0) + (sg.refusees || 0) + (sg.en_attente || 0) + (sg.cloturees || 0), 1);
        const rows = [
            ['Validées', sg.validees, '#0a9b6c'],
            ['En analyse', sg.en_analyse, '#e8a13a'],
            ['Refusées', sg.refusees, '#e23d3d'],
            ['En attente', sg.en_attente, '#2d5bd7'],
            ['Clôturées', sg.cloturees, '#64748b'],
        ];
        document.getElementById('globalStatus').innerHTML = rows.map(r =>
            '<li><span class="dot" style="background:' + r[2] + '"></span>' + r[0] +
            '<span class="pct">' + (r[1] || 0) + ' <span class="muted">' + Math.round((r[1] || 0) / sgTotal * 100) + '%</span></span></li>'
        ).join('');

        // Demandes récentes
        document.getElementById('recentRows').innerHTML = (d.demandes_recentes || []).map(s =>
            '<tr><td class="num">' + s.numero + '</td><td class="muted">' + s.date + '</td><td>' + s.assure +
            '</td><td>' + s.type + '</td><td>' + badge(s.statut) + '</td>' +
            '<td><a class="act-link" href="admin-subscriptions.html">Voir</a></td></tr>'
        ).join('') || '<tr><td colspan="6" class="muted" style="text-align:center;padding:1rem">Aucune demande</td></tr>';

        // Alertes urgences
        document.getElementById('alertRows').innerHTML = (d.alertes_urgences || []).map(a =>
            '<tr><td><span class="bo-prio ' + a.priorite + '"></span><span class="num">' + a.numero + '</span></td>' +
            '<td class="muted">' + a.date + '</td><td>' + a.assure + '</td><td>' + (a.motif || '—') + '</td>' +
            '<td>' + badge(a.statut) + '</td>' +
            '<td><a class="act-link" href="alert-detail.html?id=' + a.id + '">Voir</a></td></tr>'
        ).join('') || '<tr><td colspan="6" class="muted" style="text-align:center;padding:1rem">Aucune alerte active</td></tr>';

        // Actions rapides
        const grpKey = KPIS_BY_ROLE[roleGroup(role)] ? roleGroup(role) : 'default';
        const qa = QUICK_BY_ROLE[grpKey] || QUICK_BY_ROLE.default;
        document.getElementById('quickActions').innerHTML = qa.map(q =>
            '<a href="' + q.href + '"><span class="qi" style="background:#efeaf9">' + q.ico + '</span>' + q.label + '</a>'
        ).join('');
    }

    document.addEventListener('DOMContentLoaded', load);
    if (document.readyState !== 'loading') load();
})();
