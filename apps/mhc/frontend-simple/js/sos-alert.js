// Page SOS web simplifiée : un seul bouton, comme sur mobile.

(async function initSosPage() {
    const isValid = await requireAuth();
    if (!isValid) {
        return; // requireAuth() a déjà redirigé vers login.html
    }

    await loadMedecinConseilBlock();
    await loadAlertesBlock();
})();

function getSosButton() {
    return document.getElementById('sosBtn');
}

function getStatusContainer() {
    return document.getElementById('sosStatus');
}

function setSosButtonLoading(loading) {
    const btn = getSosButton();
    if (!btn) return;
    btn.disabled = loading;
    btn.textContent = loading ? '⏳ Envoi en cours…' : '🚨 Déclencher l\'alerte SOS';
}

function showSosStatus(message, type) {
    const container = getStatusContainer();
    if (!container) return;
    container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

function clearSosStatus() {
    const container = getStatusContainer();
    if (container) container.innerHTML = '';
}

async function loadMedecinConseilBlock() {
    const container = document.getElementById('medecinConseilContainer');
    if (!container) return;

    const cached = readMedecinConseilCache();
    if (cached.length) {
        container.innerHTML = renderMedecinConseilSection(cached, { fromCache: true });
    }

    try {
        const result = await loadMedecinConseilAssignments({ souscriptionId: null });
        container.innerHTML = renderMedecinConseilSection(result.items, { fromCache: result.fromCache });
    } catch (error) {
        console.error('Erreur chargement médecin-conseil:', error);
    }
}

async function loadAlertesBlock() {
    const container = document.getElementById('alertesList');
    if (!container) return;

    try {
        const alertes = await apiCall('/sos/');
        container.innerHTML = renderAlertesList(alertes || []);
    } catch (error) {
        console.error('Erreur chargement alertes:', error);
        container.innerHTML = '';
    }
}

function renderAlertesList(alertes) {
    if (!alertes.length) {
        return '';
    }

    const items = alertes.map((a) => {
        const numero = a.numero_alerte || `Alerte #${a.id}`;
        const statut = a.statut || 'en_attente';
        const created = a.created_at
            ? new Date(a.created_at).toLocaleString('fr-FR')
            : '';
        return `
            <div class="alerte-item" style="border:1px solid #e2e8f0; border-radius:8px; padding:1rem; margin-bottom:0.75rem; background:#fff;">
                <strong>${numero}</strong>
                <span style="text-transform:capitalize; color:#64748b;"> • ${statut}</span>
                ${created ? `<div style="font-size:0.85rem; color:#64748b; margin-top:0.25rem;">${created}</div>` : ''}
            </div>
        `;
    }).join('');

    return `
        <h3 style="margin: 2rem 0 1rem;">Mes alertes</h3>
        ${items}
    `;
}

function triggerSosAlert() {
    clearSosStatus();

    if (!navigator.geolocation) {
        showSosStatus('La géolocalisation n\'est pas supportée par votre navigateur. Activez-la pour envoyer une alerte.', 'error');
        return;
    }

    setSosButtonLoading(true);

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const latitude = parseFloat(position.coords.latitude.toFixed(6));
            const longitude = parseFloat(position.coords.longitude.toFixed(6));

            try {
                const response = await apiCall('/sos/trigger', {
                    method: 'POST',
                    body: JSON.stringify({
                        latitude,
                        longitude,
                        priorite: 'normale',
                    }),
                });

                showSosStatus(
                    `Alerte envoyée avec succès (${response.numero_alerte || 'Alerte #' + response.id}). Un agent va vous contacter rapidement.`,
                    'success'
                );

                // Recharger la liste des alertes
                await loadAlertesBlock();

                // Rediriger vers le tableau de bord après 3 secondes
                setTimeout(() => {
                    window.location.href = 'user-dashboard.html';
                }, 3000);
            } catch (error) {
                console.error('Erreur lors de l\'envoi de l\'alerte:', error);
                showSosStatus(`Erreur : ${error.message || 'Impossible d\'envoyer l\'alerte'}`, 'error');
            } finally {
                setSosButtonLoading(false);
            }
        },
        (error) => {
            console.error('Erreur de géolocalisation:', error);
            setSosButtonLoading(false);
            showSosStatus('Impossible d\'obtenir votre position. Vérifiez les autorisations de localisation et réessayez.', 'error');
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0,
        }
    );
}
