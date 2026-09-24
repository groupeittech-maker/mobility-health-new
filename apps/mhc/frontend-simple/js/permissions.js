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

    window.MhPermissions = { can, level, applyDom, getPermissions };

    document.addEventListener('DOMContentLoaded', function () {
        applyDom(document);
    });
})();
