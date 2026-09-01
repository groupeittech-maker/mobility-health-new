// Vérifier l'authentification avec validation du token
(async function() {
    if (typeof requireAuth === 'undefined') {
        console.error('requireAuth n\'est pas défini. Vérifiez que auth.js est chargé avant ce script.');
        window.location.href = 'login.html';
        return;
    }
    const isValid = await requireAuth();
    if (!isValid) {
        return; // requireAuth() a déjà redirigé vers login.html
    }
})();

function ensureCourtierMenuLink() {
    const navMenu = document.querySelector('.nav-menu');
    if (!navMenu) return;

    const hasCourtiers = !!navMenu.querySelector('a[href="admin-courtiers.html"]');
    if (hasCourtiers) return;

    const courtierItem = document.createElement('li');
    const courtierLink = document.createElement('a');
    courtierLink.href = 'admin-courtiers.html';
    courtierLink.textContent = 'Courtiers';
    courtierItem.appendChild(courtierLink);

    const subscriptionsItem = navMenu.querySelector('a[href="admin-subscriptions.html"]')?.closest('li');
    if (subscriptionsItem) {
        navMenu.insertBefore(courtierItem, subscriptionsItem);
    } else {
        const logoutItem = navMenu.querySelector('a[onclick*="logout"]')?.closest('li');
        if (logoutItem) {
            navMenu.insertBefore(courtierItem, logoutItem);
        } else {
            navMenu.appendChild(courtierItem);
        }
    }
}

// Afficher le nom de l'utilisateur
const userName = localStorage.getItem('user_name') || 'Administrateur';
document.getElementById('userName').textContent = userName;

// Fonction de déconnexion
function logout() {
    if (typeof clearAuth === 'undefined') {
        console.error('clearAuth n\'est pas défini. Vérifiez que auth.js est chargé.');
        localStorage.clear();
    } else {
        clearAuth();
    }
    window.location.href = 'login.html';
}

// Charger les statistiques
async function loadStats() {
    try {
        // Compter les produits
        try {
            const products = await apiCall('/admin/products?limit=1000');
            document.getElementById('productsCount').textContent = products.length || 0;
        } catch (e) {
            document.getElementById('productsCount').textContent = '0';
        }

        // Compter les souscriptions en attente (utiliser l'endpoint stats pour un comptage efficace)
        try {
            const stats = await apiCall('/dashboard/stats');
            document.getElementById('subscriptionsCount').textContent = stats.subscriptions_pending || 0;
        } catch (e) {
            // Fallback: essayer avec une limite réduite
            try {
                const subscriptions = await apiCall('/admin/subscriptions/pending?limit=100');
                document.getElementById('subscriptionsCount').textContent = subscriptions.length || 0;
            } catch (e2) {
                document.getElementById('subscriptionsCount').textContent = '0';
            }
        }

        // Compter les utilisateurs
        try {
            const users = await apiCall('/users?limit=1000');
            document.getElementById('usersCount').textContent = users.length || 0;
        } catch (e) {
            document.getElementById('usersCount').textContent = '0';
        }

        // Pour les attestations, on affichera "-" car il n'y a pas d'endpoint de liste globale
        document.getElementById('attestationsCount').textContent = '-';
    } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
    }
}

// Charger les stats au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    ensureCourtierMenuLink();
    loadStats();
});

