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
        admin: 'admin-dashboard.html',
        superviseur_technique: 'admin-dashboard.html',
        production_agent: 'admin-subscriptions.html',
        agent_conformite_production: 'production-review.html',
        agent_sinistre_mh: 'sos-dashboard.html',
        agent_conformite_sinistre: 'sos-dashboard.html',
        superviseur_affaires_medicales: 'sos-dashboard.html',
        agent_medical_mhc: 'sos-dashboard.html',
        agent_conformite_medical: 'sos-dashboard.html',
        superviseur_comptable: 'finance-dashboard.html',
        agent_comptable_mh: 'finance-dashboard.html',
        agent_conformite_comptable: 'finance-dashboard.html',
        finance_manager: 'finance-dashboard.html',
        sos_operator: 'sos-dashboard.html',
        medical_reviewer: 'medical-review.html',
        technical_reviewer: 'technical-review.html',
        medecin_referent_mh: 'doctor-dashboard.html',
        doctor: 'doctor-dashboard.html',
        hospital_admin: 'hospital-dashboard.html',
        medecin_hopital: 'hospital-doctor.html',
        agent_reception_hopital: 'hospital-reception.html',
        agent_comptable_hopital: 'hospital-invoices.html',
        agent_production_assureur: 'assureur-production.html',
        agent_sinistre_assureur: 'assureur-sinistres.html',
        agent_comptable_assureur: 'assureur-accounting.html',
        agent_medical_assureur: 'assureur-production.html',
        agent_production_courtier: 'assureur-production.html',
        agent_sinistre_courtier: 'assureur-sinistres.html',
        agent_comptable_courtier: 'accounting-portal.html',
        assistant_souscription: 'admin-subscriptions.html',
        agent_verificateur_reassureur: 'reassureur-portal.html',
    };

    const MENU = [
        { id: 'dashboard', label: 'Tableau de bord', icon: 'dashboard', dynamicDashboard: true },
        { id: 'alertes', label: "Centre d'alertes urgence", icon: 'alert', href: 'sos-dashboard.html', feature: 'alerte_sos' },
        { id: 'production', label: 'Production', icon: 'production', href: 'admin-subscriptions.html', feature: 'production' },
        { id: 'sinistres', label: 'Sinistres', icon: 'claim', href: 'sinistre-invoices.html', feature: 'sinistres' },
        { id: 'assures', label: 'Assurés', icon: 'users', href: 'admin-users.html', feature: 'comptes_utilisateurs' },
        { id: 'reassureurs', label: 'Réassureurs', icon: 'shield', href: 'admin-reassureurs.html', feature: 'comptes_reassureurs' },
        { id: 'intermediaires', label: 'Intermédiaires', icon: 'partners', href: 'admin-courtiers.html', feature: 'comptes_intermediaires' },
        { id: 'partenaires_sante', label: 'Partenaires santé', icon: 'medical', href: 'admin-hospitals.html', feature: 'comptes_partenaires_sante' },
        { id: 'medecins_conseil', label: 'Médecins-conseil', icon: 'stetho', href: 'admin-users.html?role=medecin_referent_mh', feature: 'comptes_medecins_conseil' },
        {
            id: 'affaires_medicales',
            label: 'Affaires médicales',
            icon: 'medical',
            feature: 'prise_en_charge',
            children: [
                { label: 'Alertes SOS', href: 'sos-dashboard.html' },
                { label: 'Prises en charge', href: 'sos-alerts-map.html' },
                { label: 'Validations médicales', href: 'medical-validations.html' },
                { label: 'Factures médicales', href: 'sinistre-invoices.html' },
            ],
        },
        { id: 'reassureur_portal', label: 'Portail réassureur', icon: 'shield', href: 'reassureur-portal.html', roles: ['agent_verificateur_reassureur'] },
        { id: 'hotels', label: 'Hôtels', icon: 'partners', href: 'admin-ops.html', feature: 'alerte_sos' },
        { id: 'transport', label: 'Transport médical', icon: 'globe', href: 'admin-ops.html?tab=providers', feature: 'alerte_sos' },
        {
            id: 'tarification',
            label: 'Tarification',
            icon: 'tag',
            feature: 'comptes_produits',
            children: [
                { label: 'Produits', href: 'admin-products.html' },
                { label: 'Zones', href: 'admin-tarification.html#zones' },
                { label: 'Tarifs', href: 'admin-tarification.html#grille' },
                { label: 'Surprimes', href: 'admin-tarification.html#tranches' },
                { label: 'Simulateur', href: 'admin-products.html#simulateur' },
                { label: 'Historique', href: 'admin-products.html#historique' },
                { label: 'Frais et taxes', href: 'admin-tarification-frais.html' },
            ],
        },
        {
            id: 'finance',
            label: 'Finance et comptabilité',
            icon: 'money',
            feature: 'encaissement_prime',
            children: [
                { label: 'Tableau financier', href: 'finance-dashboard.html' },
                { label: 'Paiements sortants', href: 'finance-outbound.html' },
                { label: 'Portail comptable', href: 'accounting-portal.html' },
                { label: 'Grand livre', href: 'accounting-ledger.html' },
                { label: 'Factures', href: 'mh-invoices.html' },
            ],
        },
        { id: 'attestations', label: 'Attestations', icon: 'doc', href: 'admin-attestations.html', feature: 'production' },
        { id: 'destinations', label: 'Destinations', icon: 'globe', href: 'admin-destinations.html', feature: 'comptes_produits' },
        { id: 'reporting', label: 'Reporting', icon: 'chart', href: 'statistics-portal.html', feature: 'encaissement_prime' },
        { id: 'parametres', label: 'Paramètres', icon: 'gear', href: 'admin-users.html', roles: ['admin'] },
    ];

    const ROLE_LABELS = (typeof window !== 'undefined' && window.MH_ROLE_LABELS) || {
        admin: 'Administrateur',
    };

    function currentRole() {
        return localStorage.getItem('user_role') || 'user';
    }

    function canSee(item) {
        if (item.roles && !item.roles.includes(currentRole())) return false;
        if (!item.feature) return true;
        const perms = window.MhPermissions;
        if (!perms || !perms.can) return currentRole() === 'admin';
        return perms.can(item.feature, item.minLevel || 'consultation');
    }

    function currentFile() {
        const path = window.location.pathname;
        return decodeURIComponent(path.substring(path.lastIndexOf('/') + 1)) || 'index.html';
    }

    function linkIsActive(href) {
        if (!href) return false;
        const file = href.split('?')[0].split('#')[0];
        return file === currentFile();
    }

    function icon(name) {
        return ICO[name] || ICO.doc;
    }

    function renderMenu() {
        const ul = document.createElement('ul');
        ul.className = 'bo-menu';
        MENU.forEach(item => {
            if (!canSee(item)) return;
            const li = document.createElement('li');
            const href = item.dynamicDashboard
                ? (DASHBOARD_BY_ROLE[currentRole()] || 'admin-dashboard.html')
                : item.href;

            if (item.children && item.children.length) {
                const anyChildActive = item.children.some(c => linkIsActive(c.href));
                li.className = 'bo-group' + (anyChildActive ? ' open' : '');
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'bo-group-btn' + (anyChildActive ? ' active' : '');
                btn.innerHTML = icon(item.icon) + '<span>' + item.label + '</span>' +
                    '<svg class="bo-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>';
                btn.addEventListener('click', () => li.classList.toggle('open'));
                li.appendChild(btn);
                const sub = document.createElement('ul');
                sub.className = 'bo-sub';
                item.children.forEach(child => {
                    const cli = document.createElement('li');
                    const a = document.createElement('a');
                    a.className = 'bo-link' + (linkIsActive(child.href) ? ' active' : '');
                    a.href = child.href;
                    a.textContent = child.label;
                    cli.appendChild(a);
                    sub.appendChild(cli);
                });
                li.appendChild(sub);
            } else {
                const a = document.createElement('a');
                a.className = 'bo-link' + (linkIsActive(href) ? ' active' : '');
                a.href = href;
                a.innerHTML = icon(item.icon) + '<span>' + item.label + '</span>';
                li.appendChild(a);
            }
            ul.appendChild(li);
        });
        return ul;
    }

    function buildSidebar() {
        const aside = document.createElement('aside');
        aside.className = 'bo-sidebar';
        aside.innerHTML =
            '<div class="bo-brand">' +
            '  <img src="assets/logo_mobility_healthcare_officiel.png" alt="Mobility Health">' +
            '  <div><a class="bo-brand-name" href="#">Mobility Health Care</a>' +
            '  <div class="bo-brand-tag">Travel safe. Live free.</div></div>' +
            '</div>';
        aside.appendChild(renderMenu());
        const foot = document.createElement('div');
        foot.className = 'bo-sidebar-foot';
        foot.textContent = 'Des soins sans frontières pour un monde en mouvement';
        aside.appendChild(foot);
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

    function injectShell() {
        if (!document.body.hasAttribute('data-backoffice')) return;
        if (document.querySelector('.bo-sidebar')) return;
        document.body.prepend(buildTopbar());
        document.body.prepend(buildSidebar());
        if (window.MhPermissions && window.MhPermissions.applyDom) {
            window.MhPermissions.applyDom(document);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectShell);
    } else {
        injectShell();
    }
})();
