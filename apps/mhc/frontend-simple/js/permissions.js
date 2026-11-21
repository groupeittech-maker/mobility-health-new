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
        if (d.href) { window.location.href = d.href; return; }
        if (d.call && typeof window[d.call] === 'function') { window[d.call](d.arg, d.arg2); return; }
        if (d.act && typeof window.mhRowAction === 'function') { window.mhRowAction(d.act, d.arg, sel, opt); }
    });

    document.addEventListener('DOMContentLoaded', function () {
        applyDom(document);
    });
})();
