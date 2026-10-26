// Vérifier l'authentification et la permission sur les flux financiers
(async function() {
    if (typeof requirePermission === 'undefined') {
        console.error('requirePermission n\'est pas défini. Vérifiez que auth.js est chargé avant ce script.');
        window.location.href = 'login.html';
        return;
    }
    const isValid = await requirePermission('encaissement_prime', 'consultation', 'bo-dashboard.html');
    if (!isValid) {
        return; // requirePermission() a déjà redirigé
    }
})();

// Afficher le nom de l'utilisateur
const userName = localStorage.getItem('user_name') || 'Gestionnaire Finance';
document.getElementById('userName').textContent = userName;

// Charger les statistiques
async function loadStats() {
    try {
        // Compter les souscriptions
        try {
            const subscriptions = await apiCall('/admin/subscriptions/pending?limit=500');
            document.getElementById('subscriptionsCount').textContent = subscriptions.length || 0;
        } catch (e) {
            document.getElementById('subscriptionsCount').textContent = '0';
        }

        // Compter les paiements en attente
        document.getElementById('pendingPaymentsCount').textContent = '—';

        // Compter les validations techniques à traiter
        try {
            const technicalReviews = await attestationsAPI.getReviews('technique');
            document.getElementById('technicalReviewsCount').textContent = technicalReviews.length || 0;
        } catch (e) {
            document.getElementById('technicalReviewsCount').textContent = '0';
        }
    } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
    }
}

// Charger les stats au chargement de la page
document.addEventListener('DOMContentLoaded', loadStats);

