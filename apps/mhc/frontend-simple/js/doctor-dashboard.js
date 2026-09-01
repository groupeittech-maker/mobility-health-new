// Vérifier l'authentification et le rôle doctor
(async function() {
    if (typeof requireRole === 'undefined') {
        console.error('requireRole n\'est pas défini. Vérifiez que auth.js est chargé avant ce script.');
        window.location.href = 'login.html';
        return;
    }
    const isValid = await requireRole('doctor', 'index.html');
    if (!isValid) {
        return; // requireRole() a déjà redirigé
    }
})();

// Afficher le nom de l'utilisateur
const userName = localStorage.getItem('user_name') || 'Médecin';
document.getElementById('userName').textContent = userName;

// Charger les statistiques
async function loadStats() {
    try {
        // Compter les attestations en attente de validation médicale
        try {
            const pendingReviews = await attestationsAPI.getReviews('medecin');
            document.getElementById('pendingAttestationsCount').textContent = pendingReviews.length || 0;
        } catch (e) {
            document.getElementById('pendingAttestationsCount').textContent = '0';
        }

        // Statistique placeholder pour les attestations déjà validées
        document.getElementById('validatedAttestationsCount').textContent = '—';
    } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
    }
}

// Charger les stats au chargement de la page
document.addEventListener('DOMContentLoaded', loadStats);

