// Shell back-office MHC — sidebar unifiée filtrée par la matrice de permissions.
// Activé sur les pages dont <body data-backoffice>. Charge js/permissions.js avant.
//
// Chaque entrée : { id, label, icon, href?, feature?, minLevel?, children?, roles? }
// - feature + minLevel : visible si MhPermissions.can(feature, minLevel)
// - roles : restreint à une liste de rôles (sinon visible pour tous les profils back-office)
// - href : page cible ; children : sous-menu dépliable
(function () {
    'use strict';

    const ICO = {
        dashboard: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>',
        alert: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        production: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        claim: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>',
        users: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
        shield: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
        partners: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>',
        medical: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
        stetho: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6 6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/><path d="M8 15v1a6 6 0 0 0 6 6 6 6 0 0 0 6-6v-4"/><circle cx="20" cy="10" r="2"/></svg>',
        money: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
        chart: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
        gear: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
        tag: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
        globe: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
        doc: '<svg class="bo-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    };

    // Tableau de bord d'atterrissage par profil.
    const DASHBOARD_BY_ROLE = {
        admin: 'bo-dashboard.html',
        superviseur_technique: 'bo-dashboard.html',
        production_agent: 'bo-dashboard.html',
        agent_conformite_production: 'bo-dashboard.html',
        agent_sinistre_mh: 'bo-dashboard.html',
        agent_conformite_sinistre: 'bo-dashboard.html',
        superviseur_affaires_medicales: 'bo-dashboard.html',
        agent_medical_mhc: 'bo-dashboard.html',
        agent_conformite_medical: 'bo-dashboard.html',
        medecin_conseil: 'bo-dashboard.html',
        superviseur_comptable: 'bo-dashboard.html',
        agent_comptable_mh: 'bo-dashboard.html',
        agent_conformite_comptable: 'bo-dashboard.html',
        medecin_referent_mh: 'bo-dashboard.html',
        doctor: 'doctor-dashboard.html',
        hospital_admin: 'hospital-dashboard.html',
        medecin_hopital: 'hospital-doctor.html',
        agent_reception_hopital: 'hospital-reception.html',
        agent_comptable_hopital: 'hospital-invoices.html',
        agent_production_assureur: 'assureur-production.html',
        agent_sinistre_assureur: 'assureur-sinistres.html',
        agent_comptable_assureur: 'assureur-accounting.html',
        agent_medical_assureur: 'assureur-production.html',
        agent_production_courtier: 'courtier-production.html',
        agent_sinistre_courtier: 'courtier-sinistres.html',
        agent_comptable_courtier: 'accounting-portal.html',
        assistant_souscription: 'courtier-production.html',
        agent_verificateur_reassureur: 'reassureur-portal.html',
    };

    const MENU = [
        { id: 'dashboard', label: 'Tableau de bord', icon: 'dashboard', href: 'bo-dashboard.html', dynamicDashboard: true },
        {
            id: 'pole_pilotage',
            label: 'Pilotage',
            icon: 'dashboard',
            internalOnly: true,
            children: [
                { label: 'Notifications', href: 'bo-notifications.html', feature: 'alerte_sos' },
                { label: 'Journal des actions', href: 'bo-journal.html', roles: ['admin', 'superviseur_technique', 'superviseur_comptable', 'superviseur_affaires_medicales', 'agent_conformite_production', 'agent_conformite_sinistre', 'agent_conformite_medical', 'agent_conformite_comptable'] },
            ],
        },
        {
            id: 'pole_inscriptions',
            label: 'Gestion des inscriptions',
            icon: 'users',
            internalOnly: true,
            children: [
                { label: 'Liste des assurés', href: 'admin-users.html?role=user', feature: 'comptes_utilisateurs', badge: 'inscriptions_attente' },
                { label: 'Modifications de profil', href: 'admin-profile-changes.html', feature: 'comptes_utilisateurs', badge: 'profils_attente' },
            ],
        },
        {
            id: 'pole_souscriptions',
            label: 'Gestion des souscriptions',
            icon: 'production',
            internalOnly: true,
            children: [
                { label: 'Validation des souscriptions', href: 'admin-subscriptions.html', feature: 'production', badge: 'souscriptions_attente,avenants_en_cours' },
                { label: 'Réclamations', href: 'admin-reclamations.html', feature: 'production', badge: 'reclamations_ouvertes' },
            ],
        },
        {
            id: 'pole_sinistres',
            label: 'Gestion des sinistres',
            icon: 'medical',
            internalOnly: true,
            children: [
                { label: 'Validation des alertes', href: 'alert-center.html?tab=a_valider', feature: 'alerte_sos', badge: 'alertes_actives' },
                { label: 'Carte des alertes', href: 'sos-alerts-map.html', feature: 'alerte_sos' },
                { label: 'Validation des rapports médicaux', href: 'medical-validations.html', feature: 'prise_en_charge', badge: 'validations_medicales' },
                { label: 'Validation des factures hospitalières', href: 'sinistre-invoices.html', feature: 'facturation_medicale', badge: 'factures_attente' },
            ],
        },
        {
            id: 'pole_finance',
            label: 'Comptabilité & Finances',
            icon: 'money',
            feature: 'encaissement_prime',
            internalOnly: true,
            children: [
                { label: 'Tableau financier', href: 'finance-dashboard.html', feature: 'encaissement_prime' },
                { label: 'Encaissements, paiements & remboursements', href: 'finance-outbound.html', anyFeatures: ['encaissement_prime', 'paiement_sinistre', 'remboursement'], badge: 'encaissements_attente,remboursements_attente' },
                { label: 'Factures médicales', href: 'mh-invoices.html', feature: 'facturation_medicale' },
                { label: 'Grand livre', href: 'accounting-ledger.html', feature: 'retrocession_mhc' },
                { label: 'Portail comptable', href: 'accounting-portal.html', feature: 'encaissement_prime' },
            ],
        },
        {
            id: 'gestion_comptes',
            label: 'Comptes & Partenaires',
            icon: 'partners',
            internalOnly: true,
            children: [
                { label: 'Utilisateurs MHC', href: 'admin-users.html', feature: 'comptes_utilisateurs', minLevel: 'edition' },
                { label: 'Médecins-conseil', href: 'admin-users.html?role=medecin_referent_mh', feature: 'comptes_medecins_conseil' },
                { label: 'Assureurs', href: 'admin-assureurs.html', feature: 'comptes_assureurs' },
                { label: 'Courtiers & intermédiaires', href: 'admin-courtiers.html', feature: 'comptes_intermediaires' },
                { label: 'Réassureurs', href: 'admin-reassureurs.html', feature: 'comptes_reassureurs' },
                { label: 'Partenaires santé', href: 'admin-hospitals.html', feature: 'comptes_partenaires_sante' },
            ],
        },
        {
            id: 'pole_parametrage',
            label: 'Paramétrage',
            icon: 'gear',
            internalOnly: true,
            children: [
                { label: 'Produits & garanties', href: 'admin-products.html', feature: 'comptes_produits', minLevel: 'edition' },
                { label: 'Tarifaire commun', href: 'admin-tarification.html', feature: 'comptes_produits', minLevel: 'edition' },
                { label: 'Frais et taxes', href: 'admin-tarification-frais.html', feature: 'comptes_produits', minLevel: 'edition' },
                { label: 'Destinations & pays', href: 'admin-destinations.html', feature: 'comptes_produits', minLevel: 'edition' },
                { label: 'Modèles d’attestations', href: 'admin-attestations.html', feature: 'comptes_produits', minLevel: 'edition' },
                { label: 'Hôtels & transporteurs médicaux', href: 'admin-ops.html', feature: 'alerte_sos' },
            ],
        },
        {
            id: 'portails_externes',
            label: 'Portails externes',
            icon: 'globe',
            children: [
                { label: 'Portail réassureur', href: 'reassureur-portal.html', roles: ['agent_verificateur_reassureur'] },
                { label: 'Production', href: 'courtier-production.html', roles: ['agent_production_courtier', 'assistant_souscription'] },
                { label: 'Sinistres', href: 'courtier-sinistres.html', roles: ['agent_sinistre_courtier'] },
                { label: 'Comptabilité', href: 'accounting-portal.html', roles: ['agent_comptable_courtier'] },
                { label: 'Production', href: 'assureur-production.html', roles: ['agent_production_assureur', 'agent_medical_assureur'] },
                { label: 'Sinistres', href: 'assureur-sinistres.html', roles: ['agent_sinistre_assureur'] },
                { label: 'Comptabilité', href: 'assureur-accounting.html', roles: ['agent_comptable_assureur'] },
                { label: 'Portail hôpital', href: 'hospital-dashboard.html', roles: ['hospital_admin', 'medecin_hopital', 'agent_comptable_hopital'] },
                { label: 'Réception — dossiers assignés', href: 'hospital-reception.html', roles: ['hospital_admin', 'agent_reception_hopital'] },
                { label: 'Facturation hôpital', href: 'hospital-invoices.html', roles: ['hospital_admin', 'agent_comptable_hopital'] },
                { label: 'Prise en charge médecin', href: 'hospital-doctor.html', roles: ['hospital_admin', 'medecin_hopital'] },
            ],
        },
        { id: 'reporting', label: 'Reporting', icon: 'chart', href: 'statistics-portal.html', feature: 'encaissement_prime', internalOnly: true },
    ];

    const ROLE_LABELS = (typeof window !== 'undefined' && window.MH_ROLE_LABELS) || {
        admin: 'Administrateur',
    };

    function currentRole() {
        return localStorage.getItem('user_role') || 'user';
    }

    function canSee(item) {
        if (item.section) return true;
        if (item.roles && !item.roles.includes(currentRole())) return false;
        if (item.internalOnly && !(window.MhPermissions && window.MhPermissions.isInternalBackoffice())) return false;
        if (!item.feature && !item.anyFeatures) return true;
        const perms = window.MhPermissions;
        if (!perms || !perms.can) return currentRole() === 'admin';
        if (item.anyFeatures) {
            return item.anyFeatures.some(f => perms.can(f, item.minLevel || 'consultation'));
        }
        return perms.can(item.feature, item.minLevel || 'consultation');
    }

    // Supprime les en-têtes de section sans item visible qui les suit
    // (évite un label "Paramétrage" orphelin si toutes ses entrées sont filtrées).
    function pruneSections(children) {
        const kept = [];
        children.forEach((c, i) => {
            if (!c.section) { kept.push(c); return; }
            const rest = children.slice(i + 1);
            const nextSection = rest.findIndex(x => x.section);
            const itemsBeforeNext = nextSection === -1 ? rest.length : nextSection;
            if (itemsBeforeNext > 0) kept.push(c);
        });
        return kept;
    }

    function currentFile() {
        const path = window.location.pathname;
        return decodeURIComponent(path.substring(path.lastIndexOf('/') + 1)) || 'index.html';
    }

    function currentKey() {
        return currentFile() + window.location.search + window.location.hash;
    }

    // Une seule entrée active dans tout le menu :
    // 1. correspondance exacte fichier + query + ancre,
    // 2. sinon entrée canonique (href sans query/ancre) du même fichier,
    // 3. sinon première entrée pointant vers le même fichier.
    function computeActiveEntry() {
        const all = [];
        MENU.forEach(item => (item.children || [item]).forEach(c => {
            if (c && c.href && !c.section) all.push(c);
        }));
        const exactKey = currentKey();
        let active = all.find(c => c.href === exactKey);
        if (!active) {
            const file = currentFile();
            active = all.find(c =>
                c.href.indexOf('?') < 0 && c.href.indexOf('#') < 0 && c.href === file);
            if (!active) {
                active = all.find(c => c.href.split('?')[0].split('#')[0] === file);
            }
        }
        return active;
    }

    function icon(name) {
        return ICO[name] || ICO.doc;
    }

    // État des accordéons persisté en sessionStorage : survit aux navigations
    // entre les pages statiques (chaque page reconstruit la sidebar).
    const OPEN_STATE_KEY = 'bo_menu_open_groups';

    function getOpenGroups() {
        try {
            return JSON.parse(sessionStorage.getItem(OPEN_STATE_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    function setGroupOpen(id) {
        // Un seul accordéon ouvert à la fois : on ne mémorise que celui-ci.
        sessionStorage.setItem(OPEN_STATE_KEY, JSON.stringify(id ? [id] : []));
    }

    function renderMenu() {
        const ul = document.createElement('ul');
        ul.className = 'bo-menu';
        const openGroups = getOpenGroups();
        const activeEntry = computeActiveEntry();
        MENU.forEach(item => {
            if (!canSee(item)) return;
            const li = document.createElement('li');
            const href = item.dynamicDashboard
                ? (DASHBOARD_BY_ROLE[currentRole()] || 'admin-dashboard.html')
                : item.href;

            if (item.children && item.children.length) {
                const visibleChildren = pruneSections(item.children.filter(canSee));
                if (!visibleChildren.length) return;
                // Un seul lien actif dans tout le menu (calcul global).
                const childActive = c => c === activeEntry;
                const anyChildActive = visibleChildren.some(childActive);
                // Ouvert si : groupe contenant la page active OU préalablement ouvert par l'utilisateur
                const isOpen = anyChildActive || openGroups.includes(item.id);
                li.className = 'bo-group' + (isOpen ? ' open' : '');
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'bo-group-btn' + (anyChildActive ? ' active' : '');
                btn.innerHTML = icon(item.icon) + '<span>' + item.label + '</span>' +
                    '<span class="bo-count bo-count-group" hidden></span>' +
                    '<svg class="bo-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>';
                btn.addEventListener('click', () => {
                    const willOpen = !li.classList.contains('open');
                    // Ferme les autres groupes ouverts (comportement accordéon).
                    ul.querySelectorAll('.bo-group.open').forEach(g => {
                        if (g !== li) g.classList.remove('open');
                    });
                    li.classList.toggle('open', willOpen);
                    setGroupOpen(willOpen ? item.id : null);
                });
                li.appendChild(btn);
                const sub = document.createElement('ul');
                sub.className = 'bo-sub';
                visibleChildren.forEach(child => {
                    const cli = document.createElement('li');
                    if (child.section) {
                        cli.className = 'bo-section';
                        cli.textContent = child.section;
                    } else {
                        const a = document.createElement('a');
                        a.className = 'bo-link' + (childActive(child) ? ' active' : '');
                        a.href = child.href;
                        a.textContent = child.label;
                        if (child.badge) {
                            a.setAttribute('data-badge-key', child.badge);
                            const b = document.createElement('span');
                            b.className = 'bo-count';
                            b.hidden = true;
                            a.appendChild(b);
                        }
                        cli.appendChild(a);
                    }
                    sub.appendChild(cli);
                });
                li.appendChild(sub);
            } else {
                const a = document.createElement('a');
                a.className = 'bo-link' + (item === activeEntry || (item.dynamicDashboard && activeEntry && activeEntry.href === href) ? ' active' : '');
                a.href = href;
                a.innerHTML = icon(item.icon) + '<span>' + item.label + '</span>';
                li.appendChild(a);
            }
            ul.appendChild(li);
        });
        return ul;
    }

    // Badges de comptage — un appel /admin/statistics/nav-counts, mis en
    // cache 60 s en session (les pages statiques reconstruisent la sidebar
    // à chaque navigation).
    const NAV_COUNTS_KEY = 'bo_nav_counts_v1';
    const NAV_COUNTS_TTL = 60 * 1000;

    function applyNavCounts(counts) {
        document.querySelectorAll('[data-badge-key]').forEach(el => {
            const n = el.getAttribute('data-badge-key').split(',')
                .reduce((s, k) => s + (counts[k.trim()] || 0), 0);
            const b = el.querySelector('.bo-count');
            if (!b) return;
            b.textContent = n > 99 ? '99+' : String(n);
            b.hidden = n <= 0;
        });
        document.querySelectorAll('.bo-group').forEach(g => {
            let total = 0;
            g.querySelectorAll('[data-badge-key]').forEach(el => {
                total += el.getAttribute('data-badge-key').split(',')
                    .reduce((s, k) => s + (counts[k.trim()] || 0), 0);
            });
            const b = g.querySelector('.bo-count-group');
            if (!b) return;
            b.textContent = total > 99 ? '99+' : String(total);
            b.hidden = total <= 0;
        });
    }

    function loadNavCounts() {
        if (!(window.MhPermissions && window.MhPermissions.isInternalBackoffice())) return;
        if (typeof apiCall !== 'function') return;
        try {
            const cached = JSON.parse(sessionStorage.getItem(NAV_COUNTS_KEY) || 'null');
            if (cached && Date.now() - cached.ts < NAV_COUNTS_TTL) {
                applyNavCounts(cached.data || {});
                return;
            }
        } catch (e) { /* cache illisible — on recharge */ }
        apiCall('/admin/statistics/nav-counts').then(data => {
            try {
                sessionStorage.setItem(NAV_COUNTS_KEY, JSON.stringify({ ts: Date.now(), data }));
            } catch (e) { /* quota — non bloquant */ }
            applyNavCounts(data || {});
        }).catch(() => { /* badges facultatifs */ });
    }

    function buildSidebar() {
        const aside = document.createElement('aside');
        aside.className = 'bo-sidebar';
        aside.innerHTML =
            '<div class="bo-brand">' +
            '  <img src="assets/logo_mobility_healthcare_officiel.png" alt="Mobility Health Care">' +
            '  <div><a class="bo-brand-name" href="#">Mobility Health Care</a>' +
            '  <div class="bo-brand-tag">Travel safe. Live free.</div></div>' +
            '</div>';
        aside.appendChild(renderMenu());
        const foot = document.createElement('div');
        foot.className = 'bo-sidebar-foot';
        foot.textContent = 'Des soins sans frontières pour un monde en mouvement';
        aside.appendChild(foot);
        // Ramener le lien actif dans la zone visible (scroll de la sidebar
        // uniquement, jamais celui de la page)
        requestAnimationFrame(() => {
            const active = aside.querySelector('.bo-link.active');
            if (!active) return;
            const aRect = active.getBoundingClientRect();
            const sRect = aside.getBoundingClientRect();
            if (aRect.top < sRect.top || aRect.bottom > sRect.bottom) {
                aside.scrollTop += aRect.top - sRect.top - sRect.height / 2;
            }
        });
        return aside;
    }

    function buildTopbar() {
        const bar = document.createElement('header');
        bar.className = 'bo-topbar';
        const role = currentRole();
        const name = localStorage.getItem('user_name') || 'Utilisateur';
        const initials = name.split(/\s+/).map(w => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase() || 'U';
        const roleLabel = ROLE_LABELS[role] || role;

        bar.innerHTML =
            '<button class="bo-burger" type="button" aria-label="Menu">' +
            '  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>' +
            '</button>' +
            '<div class="bo-search">' +
            '  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8a8fa3" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
            '  <input type="search" placeholder="Rechercher un assuré, un dossier, un établissement..." aria-label="Recherche">' +
            '</div>' +
            '<div class="bo-top-actions">' +
            '  <button class="bo-lang" type="button">FR <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg></button>' +
            '  <button class="bo-bell" type="button" aria-label="Notifications">' +
            '    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>' +
            '    <span class="bo-dot"></span>' +
            '  </button>' +
            '  <div class="bo-user" id="boUserChip">' +
            '    <div class="bo-avatar">' + initials + '</div>' +
            '    <div class="bo-user-meta"><span class="bo-user-name"></span><span class="bo-user-role"></span></div>' +
            '    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
            '    <div class="bo-user-menu"><button type="button" id="boLogoutBtn">Déconnexion</button></div>' +
            '  </div>' +
            '</div>';

        bar.querySelector('.bo-user-name').textContent = name;
        bar.querySelector('.bo-user-role').textContent = roleLabel;

        const chip = bar.querySelector('#boUserChip');
        chip.addEventListener('click', e => {
            e.stopPropagation();
            chip.classList.toggle('open');
        });
        document.addEventListener('click', () => chip.classList.remove('open'));
        bar.querySelector('#boLogoutBtn').addEventListener('click', () => {
            if (typeof logout === 'function') logout();
            else { localStorage.clear(); window.location.href = 'login.html'; }
        });
        bar.querySelector('.bo-burger').addEventListener('click', () => {
            document.body.classList.toggle('bo-sidebar-open');
        });
        return bar;
    }

    let renderedPermissions = null;

    function refreshSidebar() {
        const perms = localStorage.getItem('user_permissions');
        if (perms === renderedPermissions) return;
        renderedPermissions = perms;
        const old = document.querySelector('.bo-sidebar');
        if (old) {
            old.replaceWith(buildSidebar());
            loadNavCounts();
        }
    }

    function injectShell() {
        if (!document.body.hasAttribute('data-backoffice')) return;
        if (document.querySelector('.bo-sidebar')) return;
        renderedPermissions = localStorage.getItem('user_permissions');
        document.body.prepend(buildTopbar());
        document.body.prepend(buildSidebar());
        loadNavCounts();
        if (window.MhPermissions && window.MhPermissions.applyDom) {
            window.MhPermissions.applyDom(document);
        }
    }

    document.addEventListener('mhc:permissions', () => {
        refreshSidebar();
        if (window.MhPermissions && window.MhPermissions.applyDom) {
            window.MhPermissions.applyDom(document);
        }
    });

    // ======================================================================
    // UX transverse : toasts, recherche globale, notifications, badge de droit
    // ======================================================================

    window.mhcToast = function (msg, isErr) {
        let wrap = document.getElementById('mhcToasts');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.id = 'mhcToasts';
            wrap.className = 'mhc-toasts';
            document.body.appendChild(wrap);
        }
        const t = document.createElement('div');
        t.className = 'mhc-toast' + (isErr ? ' err' : '');
        t.textContent = msg;
        wrap.appendChild(t);
        setTimeout(() => t.remove(), isErr ? 5200 : 3200);
    };

    // ---- Recherche globale -------------------------------------------------
    const SEARCH_ICONS = { souscription: '📄', alerte: '🚨', assure: '👤', facture: '🧾' };

    function wireGlobalSearch(bar) {
        const input = bar.querySelector('.bo-search input');
        if (!input || typeof apiCall !== 'function') return;
        const box = document.createElement('div');
        box.className = 'bo-search-results';
        input.parentElement.appendChild(box);
        let timer = null;
        input.addEventListener('input', () => {
            clearTimeout(timer);
            const q = input.value.trim();
            if (q.length < 2) { box.innerHTML = ''; return; }
            timer = setTimeout(() => {
                apiCall('/admin/statistics/search?q=' + encodeURIComponent(q))
                    .then(data => {
                        const rows = (data && data.results) || [];
                        box.innerHTML = rows.slice(0, 10).map(r =>
                            '<div class="bo-sres" data-href="' + r.href + '">' +
                            '<span>' + (SEARCH_ICONS[r.type] || '📁') + '</span>' +
                            '<span><b>' + (r.numero || r.label) + '</b>' + (r.numero ? ' — ' + r.label : '') +
                            '<br><small>' + (r.sub || '') + '</small></span></div>'
                        ).join('') || '<div class="bo-sres"><small>Aucun résultat dans votre périmètre.</small></div>';
                        box.querySelectorAll('.bo-sres[data-href]').forEach(el =>
                            el.addEventListener('click', () => {
                                window.location.href = el.getAttribute('data-href');
                            }));
                    })
                    .catch(() => { box.innerHTML = ''; });
            }, 300);
        });
        document.addEventListener('click', e => {
            if (!e.target.closest('.bo-search')) box.innerHTML = '';
        });
    }

    // ---- Notifications -----------------------------------------------------
    function notifHref(n) {
        const t = (n.lien_relation_type || '').toLowerCase();
        if (t === 'sinistre' || t === 'alerte') return 'alert-center.html';
        if (t === 'souscription' || t === 'avenant') return 'admin-subscriptions.html';
        if (t === 'facture' || t === 'invoice') return 'sinistre-invoices.html';
        return 'bo-notifications.html';
    }

    function wireNotifications(bar) {
        const bell = bar.querySelector('.bo-bell');
        if (!bell || typeof apiCall !== 'function') return;
        const dot = bell.querySelector('.bo-dot');
        const drop = document.createElement('div');
        drop.className = 'bo-notif-drop';
        bell.parentElement.appendChild(drop);

        function refresh() {
            apiCall('/notifications/?is_read=false&limit=50').then(list => {
                const n = (list || []).length;
                if (dot) {
                    dot.textContent = n > 99 ? '99+' : String(n);
                    dot.classList.toggle('has', n > 0);
                }
                drop.innerHTML = '<div class="bo-notif-h">Notifications non lues (' + n + ')</div>' +
                    (list || []).slice(0, 8).map(x =>
                        '<div class="bo-notif" data-id="' + x.id + '" data-href="' + notifHref(x) + '">' +
                        '<span class="dot"></span><div><b>' + (x.titre || 'Notification') + '</b>' +
                        '<br><small>' + (x.created_at || '').slice(0, 16).replace('T', ' ') + '</small></div></div>'
                    ).join('') +
                    '<a class="bo-notif-all" href="bo-notifications.html">Tout voir →</a>';
                drop.querySelectorAll('.bo-notif[data-id]').forEach(el =>
                    el.addEventListener('click', () => {
                        apiCall('/notifications/' + el.getAttribute('data-id') + '/read', { method: 'PATCH' }).catch(() => {});
                        window.location.href = el.getAttribute('data-href');
                    }));
            }).catch(() => { if (dot) dot.classList.remove('has'); });
        }

        bell.addEventListener('click', e => {
            e.stopPropagation();
            const open = drop.classList.toggle('open');
            if (open) refresh();
        });
        document.addEventListener('click', e => {
            if (!e.target.closest('.bo-top-actions')) drop.classList.remove('open');
        });
        refresh();
        setInterval(refresh, 60 * 1000);
    }

    // ---- Badge de droit dans l'en-tête -------------------------------------
    const RIGHT_LABELS = { edition: 'Édition', controle: 'Contrôle', consultation: 'Consultation' };

    function currentMenuEntry() {
        const here = location.pathname.split('/').pop() + location.search;
        let best = null, bestLen = -1;
        MENU.forEach(item => {
            (item.children || [item]).forEach(child => {
                if (!child.href) return;
                const base = location.pathname.split('/').pop() + (location.search || '');
                if (base === child.href && child.href.length > bestLen) { best = child; bestLen = child.href.length; }
            });
        });
        if (best) return best;
        // Repli : correspondance fichier seul (page sans query dans le menu)
        const file = location.pathname.split('/').pop();
        MENU.forEach(item => {
            (item.children || [item]).forEach(child => {
                if (child.href && child.href.split('?')[0] === file) best = best || child;
            });
        });
        return best;
    }

    function injectRightBadge() {
        const head = document.querySelector('.bo-page-head h1');
        if (!head || head.querySelector('.bo-right-badge')) return;
        const entry = currentMenuEntry();
        if (!entry || !entry.feature || !window.MhPermissions) return;
        const lvl = window.MhPermissions.level(entry.feature);
        const lbl = RIGHT_LABELS[lvl];
        if (!lbl) return;
        const s = document.createElement('span');
        s.className = 'bo-right-badge';
        s.textContent = 'Droit : ' + lbl;
        head.appendChild(s);
    }

    // ---- Branchement après injection du shell ------------------------------
    const _origInject = injectShell;
    injectShell = function () {
        _origInject();
        const bar = document.querySelector('.bo-topbar');
        if (!bar) return;
        wireGlobalSearch(bar);
        wireNotifications(bar);
        injectRightBadge();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectShell);
    } else {
        injectShell();
    }
})();
