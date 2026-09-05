// Gestion de la déclaration d'alerte SOS / sinistre

// Vérifier l'authentification
(async function() {
    const isValid = await requireAuth();
    if (!isValid) {
        return; // requireAuth() a déjà redirigé vers login.html
    }
    
    // Charger les souscriptions actives
    await loadActiveSubscriptions();
    await loadMedecinConseilBlock();
})();

async function loadMedecinConseilBlock() {
    const container = document.getElementById('medecinConseilContainer');
    if (!container) return;
    const urlParams = new URLSearchParams(window.location.search);
    const subscriptionIdParam = urlParams.get('subscription_id');
    const souscriptionId = subscriptionIdParam ? parseInt(subscriptionIdParam, 10) : null;
    const cached = readMedecinConseilCache();
    const cachedItems = souscriptionId
        ? cached.filter((item) => String(item.souscription_id) === String(souscriptionId))
        : cached;
    if (cachedItems.length) {
        container.innerHTML = renderMedecinConseilSection(cachedItems, { fromCache: true });
    }
    const result = await loadMedecinConseilAssignments({
        souscriptionId: Number.isNaN(souscriptionId) ? null : souscriptionId,
    });
    container.innerHTML = renderMedecinConseilSection(result.items, { fromCache: result.fromCache });
}

// Charger les souscriptions actives
async function loadActiveSubscriptions() {
    const select = document.getElementById('subscription_id');
    
    try {
        const subscriptions = await apiCall('/subscriptions/?limit=1000');
        const activeSubscriptions = subscriptions.filter(s => s.statut === 'active');
        
        if (activeSubscriptions.length === 0) {
            select.innerHTML = '<option value="">Aucune souscription active</option>';
            select.disabled = true;
            showAlert('Vous devez avoir une souscription active pour déclarer un sinistre.', 'warning');
            return;
        }
        
        // Vérifier si une souscription_id est passée en paramètre URL
        const urlParams = new URLSearchParams(window.location.search);
        const subscriptionIdParam = urlParams.get('subscription_id');
        
        activeSubscriptions.forEach(sub => {
            const option = document.createElement('option');
            option.value = sub.id;
            option.textContent = `${sub.numero_souscription || 'Souscription #' + sub.id} - ${sub.produit_assurance?.nom || 'Produit'}`;
            if (subscriptionIdParam && sub.id.toString() === subscriptionIdParam) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erreur lors du chargement des souscriptions:', error);
        select.innerHTML = '<option value="">Erreur de chargement</option>';
        select.disabled = true;
        showAlert('Impossible de charger vos souscriptions. Veuillez réessayer.', 'error');
    }
}

// Obtenir la position actuelle
function getCurrentLocation() {
    const latInput = document.getElementById('latitude');
    const lonInput = document.getElementById('longitude');
    
    if (!navigator.geolocation) {
        showAlert('La géolocalisation n\'est pas supportée par votre navigateur.', 'error');
        return;
    }
    
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '📍 Localisation en cours...';
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            latInput.value = position.coords.latitude.toFixed(6);
            lonInput.value = position.coords.longitude.toFixed(6);
            btn.disabled = false;
            btn.textContent = '📍 Utiliser ma position actuelle';
            showAlert('Position géolocalisée avec succès !', 'success');
        },
        function(error) {
            console.error('Erreur de géolocalisation:', error);
            btn.disabled = false;
            btn.textContent = '📍 Utiliser ma position actuelle';
            showAlert('Impossible d\'obtenir votre position. Veuillez entrer les coordonnées manuellement.', 'error');
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

// Gestion du formulaire
document.getElementById('sosAlertForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Envoi en cours...';
    
    const formData = new FormData(e.target);
    const data = {
        souscription_id: formData.get('subscription_id') ? parseInt(formData.get('subscription_id')) : null,
        description: formData.get('description') || null,
        latitude: parseFloat(formData.get('latitude')),
        longitude: parseFloat(formData.get('longitude')),
        adresse: null, // Peut être ajouté plus tard si nécessaire
        priorite: formData.get('type_urgence') === 'medicale' || formData.get('type_urgence') === 'accident' ? 'urgente' : 'normale'
    };
    
    // Validation
    if (!data.souscription_id) {
        showAlert('Veuillez sélectionner une souscription.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = '🚨 Envoyer l\'alerte';
        return;
    }
    
    if (!data.latitude || !data.longitude) {
        showAlert('Veuillez fournir vos coordonnées GPS.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = '🚨 Envoyer l\'alerte';
        return;
    }
    
    try {
        const response = await apiCall('/sos/trigger', {
            method: 'POST',
            body: JSON.stringify(data),
        });
        
        showAlert('Alerte envoyée avec succès ! Un agent va vous contacter rapidement.', 'success');
        
        // Rediriger vers le tableau de bord après 3 secondes
        setTimeout(() => {
            window.location.href = 'user-dashboard.html';
        }, 3000);
        
    } catch (error) {
        console.error('Erreur lors de l\'envoi de l\'alerte:', error);
        showAlert(`Erreur: ${error.message || 'Impossible d\'envoyer l\'alerte'}`, 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = '🚨 Envoyer l\'alerte';
    }
});

