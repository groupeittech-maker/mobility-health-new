// Matrice de permissions MHC — Edition / Contrôle / Consultation.
// Source de vérité : GET /auth/me → user.permissions ({fonctionnalité: niveau}).
// Stockée dans localStorage 'user_permissions' par auth.js (validateAuth).
//
// Usage :
//   MhPermissions.can('production', 'edition')        → true/false
//   MhPermissions.level('sinistres')                  → 'edition'|'controle'|'consultation'|'none'
//   MhPermissions.applyDom()                          → masque [data-requires-permission="feature:niveau"]
//
// Auto-appliqué au DOMContentLoaded sur les éléments portant l'attribut.
(function () {
    const LEVEL_ORDER = { none: 0, consultation: 1, controle: 2, edition: 3 };

    function getPermissions() {
        try {
            return JSON.parse(localStorage.getItem('user_permissions') || '{}') || {};
        } catch (e) {
            return {};
        }
    }

    function getRole() {
        return localStorage.getItem('user_role') || 'user';
    }

    function level(feature) {
        if (getRole() === 'admin') {
            return 'edition';
        }
        const l = getPermissions()[feature];
        return LEVEL_ORDER[l] !== undefined ? l : 'none';
    }

    function can(feature, minLevel) {
        const required = LEVEL_ORDER[minLevel || 'consultation'];
        return LEVEL_ORDER[level(feature)] >= required;
    }

    function applyDom(root) {
        (root || document).querySelectorAll('[data-requires-permission]').forEach(el => {
            const spec = (el.getAttribute('data-requires-permission') || '').split(':');
            const feature = spec[0];
            const minLevel = spec[1] || 'consultation';
            if (!can(feature, minLevel)) {
                el.remove();
            }
        });
    }

    // Profils internes MHC (matrice FONCTIONNALITES_INTERNES) + rôles historiques équivalents.
    const INTERNAL_BACKOFFICE_ROLES = new Set([
        'superviseur_technique', 'production_agent', 'agent_conformite_production',
        'agent_sinistre_mh', 'agent_conformite_sinistre', 'superviseur_affaires_medicales',
        'agent_medical_mhc', 'agent_conformite_medical', 'superviseur_comptable',
        'agent_comptable_mh', 'agent_conformite_comptable', 'medecin_referent_mh',
    ]);

    function isInternalBackoffice() {
        const role = getRole();
        return role === 'admin' || INTERNAL_BACKOFFICE_ROLES.has(role);
    }

    window.MhPermissions = { can, level, applyDom, getPermissions, isInternalBackoffice, INTERNAL_BACKOFFICE_ROLES };

    // Menu d'actions de ligne générique : <select class="action-select">.
    // Options reconnues sur chaque <option> :
    //   data-href="page.html?x=1"          → navigation directe
    //   data-call="fn" data-arg="v" [data-arg2] → window.fn(arg[, arg2])
    //   data-act="clé" data-arg="v"        → window.mhRowAction(act, arg, select, option)
    //                                        (handler métier défini par la page)
    // Le select revient toujours sur son libellé « Actions » après le choix.
    // N'interfère pas avec les selects qui ont leur propre listener
    // (admin-users, admin-subscriptions…) : leurs options n'ont pas ces
    // attributs data-* et leur handler lit la valeur avant ce reset.
    document.addEventListener('change', function (event) {
        const sel = event.target && event.target.closest ? event.target.closest('select.action-select') : null;
        if (!sel || sel.disabled) return;
        const opt = sel.options[sel.selectedIndex];
        sel.selectedIndex = 0;
        if (!opt || !opt.dataset) return;
        const d = opt.dataset;
        if (d.href) { openLateralPage(d.href); return; }
        if (d.call && typeof window[d.call] === 'function') { window[d.call](d.arg, d.arg2); return; }
        if (d.act && typeof window.mhRowAction === 'function') { window.mhRowAction(d.act, d.arg, sel, opt); }
    });

    // Panneau latéral « page » : les options data-href des selects d'actions
    // ouvrent la page cible dans un drawer coulissant (maquette) plutôt que
    // de quitter la liste. Liens externes → navigation normale.
    const MH_DRAWER_ID = 'mhPageDrawer';
    const MH_DRAWER_CSS =
        '#' + MH_DRAWER_ID + '{position:fixed;inset:0;z-index:3000;pointer-events:none;}' +
        '#' + MH_DRAWER_ID + ' .mh-pd-bg{position:absolute;inset:0;background:rgba(20,15,60,.4);opacity:0;transition:opacity .2s ease;}' +
        '#' + MH_DRAWER_ID + ' .mh-pd-panel{position:absolute;top:0;right:0;bottom:0;width:min(1150px,94vw);background:#fff;' +
        'box-shadow:-16px 0 50px rgba(20,15,60,.22);transform:translateX(103%);transition:transform .25s ease;display:flex;flex-direction:column;}' +
        '#' + MH_DRAWER_ID + ' .mh-pd-head{display:flex;align-items:center;justify-content:space-between;padding:.55rem .9rem;' +
        'border-bottom:1px solid #e7e3ee;background:#faf9fc;}' +
        '#' + MH_DRAWER_ID + ' .mh-pd-title{font-size:.8rem;font-weight:700;color:#522880;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}' +
        '#' + MH_DRAWER_ID + ' .mh-pd-tools{display:flex;gap:.4rem;}' +
        '#' + MH_DRAWER_ID + ' .mh-pd-btn{border:1px solid #e7e3ee;background:#fff;border-radius:.45rem;padding:.3rem .6rem;' +
        'font-size:.74rem;font-weight:600;color:#522880;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:.3rem;}' +
        '#' + MH_DRAWER_ID + ' .mh-pd-btn:hover{background:#efe9f6;}' +
        '#' + MH_DRAWER_ID + ' iframe{flex:1;border:0;width:100%;background:#fff;}' +
        '#' + MH_DRAWER_ID + '.open{pointer-events:auto;}' +
        '#' + MH_DRAWER_ID + '.open .mh-pd-bg{opacity:1;}' +
        '#' + MH_DRAWER_ID + '.open .mh-pd-panel{transform:none;}';

    function ensureLateralDrawer() {
        let wrap = document.getElementById(MH_DRAWER_ID);
        if (wrap) return wrap;
        const style = document.createElement('style');
        style.textContent = MH_DRAWER_CSS;
        document.head.appendChild(style);
        wrap = document.createElement('div');
        wrap.id = MH_DRAWER_ID;
        wrap.innerHTML =
            '<div class="mh-pd-bg"></div>' +
            '<div class="mh-pd-panel" role="dialog" aria-modal="true">' +
            '<div class="mh-pd-head">' +
            '<span class="mh-pd-title"></span>' +
            '<span class="mh-pd-tools">' +
            '<a class="mh-pd-btn mh-pd-full" href="#" target="_blank" rel="noopener">↗ Plein écran</a>' +
            '<button type="button" class="mh-pd-btn mh-pd-close">✕ Fermer</button>' +
            '</span></div>' +
            '<iframe title="Contenu du dossier" src="about:blank"></iframe>' +
            '</div>';
        document.body.appendChild(wrap);
        const close = () => closeLateralPage();
        wrap.querySelector('.mh-pd-bg').addEventListener('click', close);
        wrap.querySelector('.mh-pd-close').addEventListener('click', close);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && wrap.classList.contains('open')) close();
        });
        return wrap;
    }

    function openLateralPage(href) {
        if (!href) return;
        if (/^(https?:)?\/\//i.test(href) || href.startsWith('mailto:') || href.startsWith('tel:')) {
            window.location.href = href;
            return;
        }
        const wrap = ensureLateralDrawer();
        const frame = wrap.querySelector('iframe');
        const full = wrap.querySelector('.mh-pd-full');
        const title = wrap.querySelector('.mh-pd-title');
        if (full) full.href = href;
        if (title) title.textContent = href.split('?')[0];
        if (frame) frame.src = href;
        wrap.classList.add('open');
    }

    function closeLateralPage() {
        const wrap = document.getElementById(MH_DRAWER_ID);
        if (!wrap) return;
        wrap.classList.remove('open');
        const frame = wrap.querySelector('iframe');
        if (frame) frame.src = 'about:blank';
    }

    window.openLateralPage = openLateralPage;
    window.closeLateralPage = closeLateralPage;

    document.addEventListener('DOMContentLoaded', function () {
        applyDom(document);
    });
})();
