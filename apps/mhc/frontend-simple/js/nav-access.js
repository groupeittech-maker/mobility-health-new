// Contrôle d'affichage des liens de navigation en fonction du rôle stocké côté client
(function () {
    function parseRoles(value) {
        return (value || '')
            .split(',')
            .map(role => role.trim())
            .filter(Boolean);
    }

    function shouldDisplay(allowedRoles, userRole) {
        if (allowedRoles.length === 0) {
            return true; // aucun filtre, afficher pour tout le monde
        }
        if (!userRole) {
            return false;
        }
        return allowedRoles.includes(userRole);
    }

    document.addEventListener('DOMContentLoaded', function () {
        const userRole = localStorage.getItem('user_role');
        document.querySelectorAll('[data-visible-roles]').forEach(element => {
            const allowedRoles = parseRoles(element.dataset.visibleRoles);
            if (!shouldDisplay(allowedRoles, userRole)) {
                element.remove();
            }
        });
    });
})();


