/* Tableau de bord back-office — données par profil. */
(function () {
    'use strict';

    const API = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
    const role = localStorage.getItem('user_role') || 'user';
    const name = localStorage.getItem('user_name') || '';

    // Chaque KPI porte la feature requise : filtrage par prérogatives dans load().
    const KPIS_BY_ROLE = {
        medical: [
            { key: 'demandes_medicales.total_mois', label: 'Demandes médicales', ico: '📋', color: 'purple', feature: 'prise_en_charge' },
            { key: 'demandes_medicales.prises_en_charge_emises', label: 'Prises en charge émises', ico: '✅', color: 'teal', feature: 'prise_en_charge' },
            { key: 'demandes_medicales.refus_emis', label: 'Refus émis', ico: '🚫', color: 'red', feature: 'prise_en_charge' },
            { key: 'demandes_medicales.hospitalisations', label: 'Hospitalisations', ico: '🛏️', color: 'blue', feature: 'hospitalisation' },
            { key: 'demandes_medicales.rapatriements', label: 'Rapatriements', ico: '✈️', color: 'slate', feature: 'rapatriement' },
        ],
        production: [
            { key: 'production.comptes_crees', label: 'Nouveaux comptes créés', ico: '👤', color: 'purple', feature: 'comptes_utilisateurs' },
            { key: 'production.souscriptions', label: 'Souscriptions coordonnées', ico: '📄', color: 'teal', feature: 'production' },
            { key: 'production.avenants', label: 'Avenants traités', ico: '📝', color: 'blue', feature: 'production' },
            { key: 'production.primes_encaissees', label: 'Primes encaissées', ico: '💰', color: 'teal', fmt: v => (v || 0).toLocaleString('fr-FR') + ' FCFA', feature: 'encaissement_prime' },
            { key: 'production.remboursements', label: 'Remboursements / annulations', ico: '🔄', color: 'red', feature: 'remboursement' },
        ],
        sinistre: [
            { key: 'sinistres.total', label: 'Sinistres total', ico: '📁', color: 'purple', feature: 'sinistres' },
            { key: 'sinistres.en_cours', label: 'En cours', ico: '⏳', color: 'amber', feature: 'sinistres' },
            { key: 'sinistres.resolus', label: 'Réglés', ico: '✅', color: 'teal', feature: 'sinistres' },
            { key: 'alertes.en_traitement', label: 'Alertes en traitement', ico: '🚨', color: 'red', feature: 'alerte_sos' },
        ],
        alertes: [
            { key: 'alertes.recues', label: 'Alertes reçues', ico: '🚨', color: 'red', feature: 'alerte_sos' },
            { key: 'alertes.en_traitement', label: 'En traitement', ico: '⏱️', color: 'amber', feature: 'alerte_sos' },
            { key: 'alertes.valides', label: 'Prises en charge validées', ico: '✅', color: 'teal', feature: 'prise_en_charge' },
            { key: 'alertes.refusees', label: 'Alertes refusées', ico: '🚫', color: 'red', feature: 'alerte_sos' },
            { key: 'alertes.cloturees', label: 'Alertes clôturées', ico: '📁', color: 'slate', feature: 'alerte_sos' },
        ],
        finance: [
            { key: 'finance.encaissements_attente', label: 'Encaissements en attente', ico: '⏳', color: 'amber', feature: 'encaissement_prime' },
            { key: 'finance.primes_mois', label: 'Primes encaissées (mois)', ico: '💰', color: 'teal', fmt: v => (v || 0).toLocaleString('fr-FR') + ' FCFA', feature: 'encaissement_prime' },
            { key: 'finance.remboursements_attente', label: 'Remboursements à valider', ico: '🔄', color: 'red', feature: 'remboursement' },
            { key: 'finance.factures_attente', label: 'Factures en attente', ico: '📄', color: 'blue', feature: 'facturation_medicale' },
            { key: 'finance.paiements_mois', label: 'Paiements du mois', ico: '💳', color: 'purple', feature: 'paiement_sinistre' },
        ],
        admin: [
            { key: 'production.comptes_crees', label: 'Nouveaux comptes', ico: '👤', color: 'purple', feature: 'comptes_utilisateurs' },
            { key: 'production.souscriptions', label: 'Souscriptions (mois)', ico: '📄', color: 'teal', feature: 'production' },
            { key: 'production.primes_encaissees', label: 'Primes encaissées (mois)', ico: '💰', color: 'teal', fmt: v => (v || 0).toLocaleString('fr-FR') + ' FCFA', feature: 'encaissement_prime' },
            { key: 'alertes.en_traitement', label: 'Alertes actives', ico: '🚨', color: 'red', feature: 'alerte_sos' },
            { key: 'sinistres.en_cours', label: 'Sinistres en cours', ico: '📁', color: 'amber', feature: 'sinistres' },
            { key: 'taches.comptes_en_attente', label: 'Inscriptions en attente', ico: '⏳', color: 'blue', feature: 'comptes_utilisateurs' },
        ],
    };

    function roleGroup(r) {
        if (['admin', 'superviseur_technique'].includes(r)) return 'admin';
        if (['medecin_referent_mh', 'superviseur_affaires_medicales', 'agent_medical_mhc', 'agent_conformite_medical', 'agent_medical_assureur', 'medecin_conseil', 'medical_advisor'].includes(r)) return 'medical';
        if (['agent_comptable_mh', 'agent_conformite_comptable', 'superviseur_comptable', 'agent_comptable_assureur', 'agent_comptable_courtier'].includes(r)) return 'finance';
        if (['agent_sinistre_mh', 'agent_sinistre_assureur', 'agent_sinistre_courtier'].includes(r)) return 'alertes';
        if (['agent_conformite_sinistre'].includes(r)) return 'sinistre';
        return 'production';
    }

    const actSel = (href, label) =>
        '<td class="table-actions"><select class="action-select"><option value="">⚙️ Actions</option>' +
        '<option data-href="' + href + '">' + (label || '👁 Voir') + '</option></select></td>';

    const LIST_BY_ROLE = {
        production: {
            title: '📋 Souscriptions récentes', link: 'admin-subscriptions.html', feature: 'production',
            headers: ['N° souscription', 'Date', 'Assuré', 'Prix', 'Statut', 'Actions'],
            rows: d => (d.souscriptions_recentes || []).map(s =>
                '<tr><td class="num">' + s.numero + '</td><td class="muted">' + s.date + '</td><td>' + s.assure +
                '</td><td>' + s.prix.toLocaleString('fr-FR') + ' FCFA</td><td>' + badge(s.statut) + '</td>' +
                actSel('admin-subscriptions.html') + '</tr>'
            ).join(''),
        },
        finance: {
            title: '💳 Paiements récents', link: 'finance-outbound.html', feature: 'encaissement_prime',
            headers: ['Référence', 'Date', 'Montant', 'Dossier', 'Statut', 'Actions'],
            rows: d => (d.paiements_recents || []).map(p =>
                '<tr><td class="num">' + p.reference + '</td><td class="muted">' + p.date + '</td><td>' +
                p.montant.toLocaleString('fr-FR') + ' FCFA</td><td>SUB-' + (p.souscription_id || '—') + '</td><td>' + badge(p.statut) + '</td>' +
                actSel('finance-outbound.html') + '</tr>'
            ).join(''),
        },
        admin: {
            title: '📋 Souscriptions récentes', link: 'admin-subscriptions.html', feature: 'production',
            headers: ['N° souscription', 'Date', 'Assuré', 'Prix', 'Statut', 'Actions'],
            rows: d => (d.souscriptions_recentes || []).map(s =>
                '<tr><td class="num">' + s.numero + '</td><td class="muted">' + s.date + '</td><td>' + s.assure +
                '</td><td>' + s.prix.toLocaleString('fr-FR') + ' FCFA</td><td>' + badge(s.statut) + '</td>' +
                actSel('admin-subscriptions.html') + '</tr>'
            ).join(''),
        },
        default: {
            title: '📋 Demandes récentes', link: 'medical-validations.html', feature: 'prise_en_charge',
            headers: ['N° demande', 'Date et heure', 'Assuré', 'Type de demande', 'Statut', 'Actions'],
            rows: d => (d.demandes_recentes || []).map(s =>
                '<tr><td class="num">' + s.numero + '</td><td class="muted">' + s.date + '</td><td>' + s.assure +
                '</td><td>' + s.type + '</td><td>' + badge(s.statut) + '</td>' +
                actSel('medical-validations.html') + '</tr>'
            ).join(''),
        },
    };

    const QUICK_BY_ROLE = {
        medical: [
            { href: 'alert-center.html', ico: '🚨', label: "Traiter les alertes", feature: 'alerte_sos' },
            { href: 'medical-validations.html', ico: '✔️', label: 'Validations en attente', feature: 'prise_en_charge' },
            { href: 'sinistre-invoices.html', ico: '📄', label: 'Factures à valider', feature: 'facturation_medicale' },
            { href: 'admin-ops.html', ico: '🏨', label: 'Hôtels & transport', feature: 'alerte_sos' },
        ],
        production: [
            { href: 'admin-users.html', ico: '👤', label: 'Créer un compte utilisateur', feature: 'comptes_utilisateurs', minLevel: 'edition' },
            { href: 'admin-subscriptions.html', ico: '📋', label: 'Coordonner une souscription', feature: 'production' },
            { href: 'admin-attestations.html', ico: '📄', label: 'Attestations', feature: 'comptes_produits' },
            { href: 'admin-products.html', ico: '💠', label: 'Produits', feature: 'comptes_produits' },
        ],
        sinistre: [
            { href: 'sinistre-invoices.html', ico: '📁', label: 'Suivi des sinistres', feature: 'sinistres' },
            { href: 'alert-center.html', ico: '🚨', label: "Alertes", feature: 'alerte_sos' },
            { href: 'finance-outbound.html', ico: '💰', label: 'Paiements', feature: 'paiement_sinistre' },
        ],
        alertes: [
            { href: 'alert-center.html?tab=a_valider', ico: '✔️', label: 'Alertes à valider', feature: 'alerte_sos' },
            { href: 'alert-center.html', ico: '🚨', label: 'Centre d\'alertes', feature: 'alerte_sos' },
            { href: 'sos-alerts-map.html', ico: '🗺️', label: 'Carte des alertes', feature: 'alerte_sos' },
            { href: 'medical-validations.html', ico: '🩺', label: 'Validations médicales', feature: 'prise_en_charge' },
        ],
        finance: [
            { href: 'finance-dashboard.html', ico: '💰', label: 'Tableau financier', feature: 'encaissement_prime' },
            { href: 'finance-outbound.html', ico: '💳', label: 'Encaissements & paiements', feature: 'encaissement_prime' },
            { href: 'accounting-portal.html', ico: '📒', label: 'Portail comptable', feature: 'encaissement_prime' },
            { href: 'mh-invoices.html', ico: '📄', label: 'Factures médicales', feature: 'facturation_medicale' },
        ],
        admin: [
            { href: 'admin-users.html', ico: '👤', label: 'Comptes & utilisateurs', feature: 'comptes_utilisateurs' },
            { href: 'admin-subscriptions.html', ico: '📋', label: 'Souscriptions', feature: 'production' },
            { href: 'alert-center.html', ico: '🚨', label: 'Centre d\'alertes', feature: 'alerte_sos' },
            { href: 'statistics-portal.html', ico: '📊', label: 'Reporting global', feature: 'encaissement_prime' },
        ],
        default: [
            { href: 'alert-center.html', ico: '🚨', label: 'Centre d\'alertes', feature: 'alerte_sos' },
            { href: 'admin-users.html', ico: '👤', label: 'Utilisateurs', feature: 'comptes_utilisateurs' },
            { href: 'statistics-portal.html', ico: '📊', label: 'Reporting', feature: 'encaissement_prime' },
        ],
    };

    const ROLE_LABELS = {
        admin: 'Vue d\'ensemble — direction & administration.',
        production: 'Pôle production — inscriptions, souscriptions, avenants.',
        medical: 'Pôle affaires médicales — validations & documents médicaux.',
        sinistre: 'Pôle sinistres — suivi & règlement des dossiers.',
        alertes: 'Pôle sinistres — traitement des alertes & urgences.',
        finance: 'Pôle comptabilité & finances — encaissements, paiements, remboursements.',
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

        const token = localStorage.getItem('access_token');
        const res = await fetch(API + '/admin/dashboard/summary', {
            headers: { Authorization: 'Bearer ' + token },
        });
        if (!res.ok) { document.getElementById('kpis').innerHTML = '<p style="color:#c81e1e">Impossible de charger les données.</p>'; return; }
        const d = await res.json();
        const perms = window.MhPermissions;
        const can = (f, lvl) => !f || (perms && perms.can && perms.can(f, lvl || 'consultation'));

        // KPIs par groupe de profil, filtrés par prérogatives de la feature
        const grpKey = roleGroup(role);
        let grp = (KPIS_BY_ROLE[grpKey] || KPIS_BY_ROLE.production)
            .filter(k => can(k.feature) && get(d, k.key) !== undefined);
        if (!grp.length) {
            grp = [
                { key: 'taches.comptes_en_attente', label: 'Inscriptions en attente', ico: '⏳', color: 'blue', feature: 'comptes_utilisateurs' },
                { key: 'taches.souscriptions_en_cours', label: 'Souscriptions en cours', ico: '📄', color: 'teal', feature: 'production' },
                { key: 'taches.remboursements_a_valider', label: 'Remboursements à valider', ico: '🔄', color: 'red', feature: 'remboursement' },
            ].filter(k => can(k.feature) && get(d, k.key) !== undefined);
        }
        const sub = document.querySelector('.bo-page-head .sub');
        if (sub && ROLE_LABELS[grpKey]) sub.textContent = ROLE_LABELS[grpKey];
        document.getElementById('kpis').innerHTML = grp.map(k => {
            const raw = get(d, k.key);
            const val = k.fmt ? k.fmt(raw) : raw;
            return '<div class="bo-kpi"><div class="bo-kpi-ico ' + k.color + '">' + k.ico + '</div>' +
                '<div><div class="l">' + k.label + '</div><div class="v">' + (val ?? '—') + '</div></div></div>';
        }).join('') || '<div class="bo-card" style="padding:1rem 1.2rem;color:#7c7590">Aucun indicateur dans votre périmètre.</div>';

        // Donut répartition + statut global — uniquement si le périmètre médical est accessible
        const donutCard = document.getElementById('donutCard');
        const statusCard = document.getElementById('statusCard');
        if (d.repartition_demandes) {
            const parts = d.repartition_demandes || [];
            const total = parts.reduce((s, p) => s + p.value, 0);
            let acc = 0;
            const segs = parts.filter(p => p.value > 0).map(p => {
                const from = acc / Math.max(total, 1) * 360;
                acc += p.value;
                return p.color + ' ' + from + 'deg ' + (acc / Math.max(total, 1) * 360) + 'deg';
            });
            document.getElementById('donut').style.background =
                'conic-gradient(' + (segs.length ? segs.join(',') : '#eeedf2 0 360deg') + ')';
            document.getElementById('donutCenter').innerHTML = total + '<small>demandes</small>';
            document.getElementById('donutLegend').innerHTML = parts.map(p =>
                '<li><span class="dot" style="background:' + p.color + '"></span>' + p.label +
                '<span class="pct">' + (total ? Math.round(p.value / total * 100) : 0) + '%</span></li>'
            ).join('');
        } else if (donutCard) { donutCard.style.display = 'none'; }

        if (d.statut_global) {
            const sg = d.statut_global;
            const sgTotal = Math.max((sg.validees || 0) + (sg.en_analyse || 0) + (sg.refusees || 0) + (sg.en_attente || 0) + (sg.cloturees || 0), 1);
            const rows = [
                ['Validées', sg.validees, '#1f9d55'],
                ['En analyse', sg.en_analyse, '#d98a10'],
                ['Refusées', sg.refusees, '#d64545'],
                ['En attente', sg.en_attente, '#2f6fd6'],
                ['Clôturées', sg.cloturees, '#7c7590'],
            ];
            document.getElementById('globalStatus').innerHTML = rows.map(r =>
                '<li><span class="dot" style="background:' + r[2] + '"></span>' + r[0] +
                '<span class="pct">' + (r[1] || 0) + ' <span class="muted">' + Math.round((r[1] || 0) / sgTotal * 100) + '%</span></span></li>'
            ).join('');
        } else if (statusCard) { statusCard.style.display = 'none'; }

        // Première liste : adaptée au profil et à ses prérogatives
        // (sinon repli sur la liste demandes médicales, sinon carte masquée).
        const listCard = document.getElementById('recentCard');
        const candidates = [LIST_BY_ROLE[grpKey], LIST_BY_ROLE.default].filter(Boolean);
        const listCfg = candidates.find(l => can(l.feature));
        if (listCard && !listCfg) {
            listCard.style.display = 'none';
        } else if (listCard) {
            listCard.querySelector('.bo-card-title').textContent = listCfg.title;
            const link = listCard.querySelector('.bo-link-all');
            if (link) link.href = listCfg.link;
            listCard.querySelector('thead tr').innerHTML = listCfg.headers.map(h => '<th>' + h + '</th>').join('');
            document.getElementById('recentRows').innerHTML = listCfg.rows(d) ||
                '<tr><td colspan="6" class="muted" style="text-align:center;padding:1rem">Aucun élément dans votre périmètre</td></tr>';
        }

        // Alertes urgences — masquée si le périmètre alertes n'est pas accessible
        const alertsCard = document.getElementById('alertsCard');
        if (alertsCard && !d.alertes_urgences) {
            alertsCard.style.display = 'none';
        } else {
            document.getElementById('alertRows').innerHTML = (d.alertes_urgences || []).map(a =>
                '<tr><td><span class="bo-prio ' + a.priorite + '"></span><span class="num">' + a.numero + '</span></td>' +
                '<td class="muted">' + a.date + '</td><td>' + a.assure + '</td><td>' + (a.motif || '—') + '</td>' +
                '<td>' + badge(a.statut) + '</td>' +
                actSel('alert-center.html?focus=' + a.id) + '</tr>'
            ).join('') || '<tr><td colspan="6" class="muted" style="text-align:center;padding:1rem">Aucune alerte active</td></tr>';
        }

        // À traiter en priorité — notifications non lues (top 5)
        loadPriority();

        // Actions rapides — filtrées par prérogatives ; carte masquée si vide
        const qa = (QUICK_BY_ROLE[grpKey] || QUICK_BY_ROLE.default).filter(q =>
            !q.feature || can(q.feature, q.minLevel));
        const quickCard = document.getElementById('quickCard');
        if (quickCard && !qa.length) {
            quickCard.style.display = 'none';
        } else {
            document.getElementById('quickActions').innerHTML = qa.map(q =>
                '<a href="' + q.href + '"><span class="qi" style="background:#efe9f6">' + q.ico + '</span>' + q.label + '</a>'
            ).join('');
        }
    }

    async function loadPriority() {
        const el = document.getElementById('priorityCard');
        if (!el || typeof apiCall !== 'function') return;
        try {
            const list = await apiCall('/notifications/?is_read=false&limit=5');
            if (!list || !list.length) { el.innerHTML = ''; return; }
            el.innerHTML =
                '<div class="bo-card" style="margin-bottom:1rem">' +
                '<div class="bo-card-h"><span class="bo-card-title">🔔 À traiter en priorité (' + list.length + ')</span>' +
                '<a class="bo-link-all" href="bo-notifications.html">Tout voir →</a></div>' +
                '<div class="bo-card-b" style="padding:0;">' +
                list.map(n =>
                    '<a class="bo-notif" href="bo-notifications.html" style="text-decoration:none;color:inherit">' +
                    '<span class="dot"></span><div><b>' + (n.titre || 'Notification') + '</b>' +
                    '<br><small>' + (n.created_at || '').slice(0, 16).replace('T', ' ') + '</small></div></a>'
                ).join('') +
                '</div></div>';
        } catch (e) { el.innerHTML = ''; }
    }

    document.addEventListener('DOMContentLoaded', async () => {
        if (!(await requireBackoffice('index.html'))) return;
        load();
    });
    if (document.readyState !== 'loading') load();
})();
