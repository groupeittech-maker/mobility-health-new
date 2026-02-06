const ROWS_PER_PAGE = 6;
let currentPageAttestations = 0;

let attestationsState = {
    data: [],
    typeFilter: 'all',
    statusFilter: 'all',
    subscriptionFilter: null,
    searchTerm: '',
};

let subscriptionMap = new Map();

document.addEventListener('DOMContentLoaded', async () => {
    const isValid = await requireAuth();
    if (!isValid) {
        return;
    }

    // Initialiser les filtres avec des valeurs par défaut
    attestationsState.typeFilter = 'all';
    attestationsState.statusFilter = 'all';
    attestationsState.subscriptionFilter = null;

    const params = new URLSearchParams(window.location.search);
    const subscriptionId = parseInt(params.get('subscription_id'), 10);
    if (!isNaN(subscriptionId)) {
        attestationsState.subscriptionFilter = subscriptionId;
    }

    // Initialiser les boutons de filtre
    updateFilterButtons();
    
    bindFilterEvents();
    await loadAttestations();
    
    // Vérifier si on doit surligner une attestation depuis l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const highlightAttestationId = urlParams.get('highlight_attestation');
    if (highlightAttestationId) {
        // Attendre que les attestations soient chargées
        setTimeout(() => {
            highlightAttestation(parseInt(highlightAttestationId));
        }, 500);
    }
});

function bindFilterEvents() {
    document.querySelectorAll('#typeFilters .filter-btn').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('#typeFilters .filter-btn').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const filterValue = button.dataset.type;
            console.log('🔘 Filtre type cliqué:', filterValue);
            attestationsState.typeFilter = filterValue;
            renderAttestations();
        });
    });

    document.querySelectorAll('#statusFilters .filter-btn').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('#statusFilters .filter-btn').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const filterValue = button.dataset.status;
            console.log('🔘 Filtre statut cliqué:', filterValue);
            attestationsState.statusFilter = filterValue;
            renderAttestations();
        });
    });

    const searchEl = document.getElementById('searchAttestations');
    if (searchEl) {
        searchEl.addEventListener('input', () => {
            attestationsState.searchTerm = (searchEl.value || '').trim();
            renderAttestations();
        });
    }
}

// Fonction pour mettre à jour l'état visuel des boutons de filtre
function updateFilterButtons() {
    // Mettre à jour le filtre de type
    document.querySelectorAll('#typeFilters .filter-btn').forEach(btn => {
        if (btn.dataset.type === attestationsState.typeFilter) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Mettre à jour le filtre de statut
    document.querySelectorAll('#statusFilters .filter-btn').forEach(btn => {
        if (btn.dataset.status === attestationsState.statusFilter) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

async function loadAttestations() {
    const loadingEl = document.getElementById('attestationsLoading');
    const container = document.getElementById('attestationsContainer');
    loadingEl.style.display = 'block';
    container.innerHTML = '';

    try {
        console.log('🔄 Début du chargement des attestations...');
        console.log('📋 Filtre de souscription:', attestationsState.subscriptionFilter);
        
        // Charger les attestations et les souscriptions en parallèle
        let attestations, subscriptions;
        try {
            // Si on filtre par souscription, utiliser l'endpoint spécifique
            if (attestationsState.subscriptionFilter) {
                console.log('🔍 Chargement des attestations pour la souscription:', attestationsState.subscriptionFilter);
                [attestations, subscriptions] = await Promise.all([
                    attestationsAPI.getBySubscription(attestationsState.subscriptionFilter),
                    apiCall('/subscriptions/?limit=1000'),
                ]);
            } else {
                // Sinon, charger toutes les attestations de l'utilisateur
                [attestations, subscriptions] = await Promise.all([
                    attestationsAPI.getMine(),
                    apiCall('/subscriptions/?limit=1000'),
                ]);
            }
        } catch (apiError) {
            console.error('❌ Erreur lors de l\'appel API:', apiError);
            throw apiError;
        }

        console.log('📥 Données reçues:', {
            attestations: Array.isArray(attestations) ? attestations.length : 'non-array',
            attestationsType: typeof attestations,
            attestationsValue: attestations,
            subscriptions: Array.isArray(subscriptions) ? subscriptions.length : 'non-array',
            subscriptionsType: typeof subscriptions,
            subscriptionFilter: attestationsState.subscriptionFilter
        });
        
        // Log détaillé si le tableau est vide
        if (Array.isArray(attestations) && attestations.length === 0 && attestationsState.subscriptionFilter) {
            console.warn('⚠️ Aucune attestation retournée pour la souscription:', attestationsState.subscriptionFilter);
            console.warn('💡 Vérifiez que cette souscription a bien des attestations dans la base de données');
            console.warn('💡 Vérifiez les logs du serveur backend pour plus de détails');
        }

        // Vérifier que les attestations sont un tableau
        if (!Array.isArray(attestations)) {
            console.error('❌ Les attestations ne sont pas un tableau:', attestations);
            // Si ce n'est pas un tableau mais qu'on a un objet avec une propriété, essayer de l'extraire
            if (attestations && typeof attestations === 'object' && 'data' in attestations) {
                console.warn('⚠️ Tentative d\'extraction depuis attestations.data');
                attestations = attestations.data;
            } else {
                throw new Error('Format de données invalide: les attestations doivent être un tableau');
            }
        }
        
        // Vérifier à nouveau après la tentative d'extraction
        if (!Array.isArray(attestations)) {
            console.error('❌ Les attestations ne sont toujours pas un tableau après extraction:', attestations);
            throw new Error('Format de données invalide: les attestations doivent être un tableau');
        }
        
        console.log('✅ Attestations valides:', attestations.length);

        // Vérifier que les souscriptions sont un tableau
        if (!Array.isArray(subscriptions)) {
            console.warn('⚠️ Les souscriptions ne sont pas un tableau, utilisation d\'un tableau vide');
            subscriptions = [];
        }

        subscriptionMap = new Map(subscriptions.map(sub => [sub.id, sub]));

        attestationsState.data = attestations.map(att => {
            if (!att || typeof att !== 'object') {
                console.warn('⚠️ Attestation invalide ignorée:', att);
                return null;
            }
            const subscription = subscriptionMap.get(att.souscription_id);
            return {
                ...att,
                subscription_label: subscription?.numero_souscription || `Souscription #${att.souscription_id}`,
                product_label: subscription?.produit_assurance?.nom || 'Produit non renseigné',
            };
        }).filter(att => att !== null) // Filtrer les attestations invalides
        .sort((a, b) => {
            const dateA = a.created_at ? new Date(a.created_at) : new Date(0);
            const dateB = b.created_at ? new Date(b.created_at) : new Date(0);
            return dateB - dateA;
        });

        console.log('📦 Attestations traitées:', {
            total: attestationsState.data.length,
            types: [...new Set(attestationsState.data.map(att => att.type_attestation))],
            sample: attestationsState.data.slice(0, 2).map(att => ({
                id: att.id,
                type: att.type_attestation,
                est_valide: att.est_valide,
                souscription_id: att.souscription_id
            }))
        });

        if (attestationsState.data.length === 0) {
            console.warn('⚠️ Aucune attestation trouvée après traitement');
            if (attestationsState.subscriptionFilter) {
                console.info(`💡 Aucune attestation trouvée pour la souscription #${attestationsState.subscriptionFilter}`);
                console.info('   - Vérifiez que cette souscription a bien des attestations associées');
                console.info('   - Pour une souscription en attente, une attestation provisoire devrait exister');
            } else {
                console.info('💡 Vérifications à faire:');
                console.info('   1. Vérifiez que vous avez des souscriptions actives');
                console.info('   2. Vérifiez que ces souscriptions ont des attestations associées');
                console.info('   3. Vérifiez l\'onglet Network (F12) pour voir la réponse de l\'API');
            }
        }

        updateStats();
        renderSubscriptionFilter();
        
        // Si on filtre par souscription, vérifier si c'est une souscription en attente
        // et dans ce cas, filtrer automatiquement sur les attestations provisoires
        if (attestationsState.subscriptionFilter) {
            const subscription = subscriptionMap.get(attestationsState.subscriptionFilter);
            if (subscription) {
                console.log('📋 Souscription filtrée:', {
                    id: subscription.id,
                    statut: subscription.statut,
                    numero: subscription.numero_souscription
                });
                
                if (subscription.statut === 'en_attente' || subscription.statut === 'pending') {
                    // Pour une souscription en attente, afficher les attestations provisoires
                    console.log('✅ Souscription en attente détectée, filtrage automatique sur les attestations provisoires');
                    attestationsState.typeFilter = 'provisoire';
                }
            } else {
                console.warn('⚠️ Souscription non trouvée pour l\'ID:', attestationsState.subscriptionFilter);
            }
        }
        
        // Mettre à jour les boutons de filtre pour refléter l'état actuel
        updateFilterButtons();
        
        renderAttestations();
    } catch (error) {
        console.error('❌ Erreur lors du chargement des attestations:', {
            error: error,
            message: error.message,
            stack: error.stack,
            name: error.name
        });
        container.innerHTML = `
            <div class="alert alert-error">
                <strong>Erreur lors du chargement des attestations</strong><br>
                ${error.message || 'Une erreur inattendue s\'est produite'}<br>
                <small>Vérifiez la console (F12) pour plus de détails.</small>
            </div>
        `;
    } finally {
        loadingEl.style.display = 'none';
    }
}

function renderSubscriptionFilter() {
    const container = document.getElementById('subscriptionFilterContainer');
    if (!attestationsState.subscriptionFilter) {
        container.innerHTML = '';
        return;
    }

    const subscription = subscriptionMap.get(attestationsState.subscriptionFilter);
    const label = subscription
        ? `${subscription.numero_souscription} • ${subscription.produit_assurance?.nom || 'Produit'}`
        : `Souscription #${attestationsState.subscriptionFilter}`;

    container.innerHTML = `
        <div class="subscription-filter">
            Filtré sur ${label}
            <button type="button" onclick="clearSubscriptionFilter()" aria-label="Retirer le filtre">×</button>
        </div>
    `;
}

function clearSubscriptionFilter() {
    attestationsState.subscriptionFilter = null;
    const params = new URLSearchParams(window.location.search);
    params.delete('subscription_id');
    const newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
    window.history.replaceState({}, '', newUrl);
    renderSubscriptionFilter();
    renderAttestations();
}

function renderAttestations() {
    const container = document.getElementById('attestationsContainer');
    
    // S'assurer que les filtres ont des valeurs par défaut
    if (!attestationsState.typeFilter) {
        attestationsState.typeFilter = 'all';
    }
    if (!attestationsState.statusFilter) {
        attestationsState.statusFilter = 'all';
    }
    
    console.log('🎨 Rendu des attestations:', {
        dataLength: attestationsState.data?.length || 0,
        typeFilter: attestationsState.typeFilter,
        statusFilter: attestationsState.statusFilter,
        subscriptionFilter: attestationsState.subscriptionFilter
    });
    
    // Vérifier que les données sont chargées
    if (!attestationsState.data || !Array.isArray(attestationsState.data) || attestationsState.data.length === 0) {
        console.warn('⚠️ Aucune donnée dans attestationsState.data');
        container.innerHTML = `
            <div class="empty-state">
                Aucune attestation trouvée.
            </div>
        `;
        return;
    }
    
    const filtered = filterAttestations();

    console.log('📊 Résultat après filtrage:', {
        filteredLength: filtered.length,
        dataLength: attestationsState.data.length
    });

    if (filtered.length === 0) {
        // Distinguer entre "aucune attestation du tout" et "aucune avec les filtres"
        const hasFilters = attestationsState.typeFilter !== 'all' || 
                          attestationsState.statusFilter !== 'all' || 
                          attestationsState.subscriptionFilter !== null;
        
        console.warn('⚠️ Aucune attestation après filtrage:', {
            hasFilters,
            typeFilter: attestationsState.typeFilter,
            statusFilter: attestationsState.statusFilter,
            subscriptionFilter: attestationsState.subscriptionFilter,
            totalData: attestationsState.data.length,
            sampleData: attestationsState.data.slice(0, 3).map(att => ({
                id: att.id,
                type: att.type_attestation,
                est_valide: att.est_valide,
                souscription_id: att.souscription_id
            }))
        });
        
        const hasSearch = (attestationsState.searchTerm || '').trim().length > 0;
        const message = hasFilters || hasSearch
            ? "Aucune attestation ne correspond à vos filtres ou à la recherche."
            : "Aucune attestation trouvée.";

        container.innerHTML = `
            <div class="empty-state">
                ${message}
            </div>
        `;
        return;
    }

    try {
        const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
        currentPageAttestations = Math.min(currentPageAttestations, totalPages - 1);
        const start = currentPageAttestations * ROWS_PER_PAGE;
        const pageData = filtered.slice(start, start + ROWS_PER_PAGE);
        const html = pageData.map(attestation => {
            try {
                return buildAttestationCard(attestation);
            } catch (error) {
                console.error('❌ Erreur lors de la construction de la carte:', error, attestation);
                return ''; // Retourner une chaîne vide en cas d'erreur
            }
        }).filter(html => html !== '').join('');
        
        container.innerHTML = html;
        console.log('✅ Attestations rendues avec succès:', pageData.length);
        const pagEl = document.getElementById('attestationsPagination');
        if (pagEl) {
            if (filtered.length <= ROWS_PER_PAGE) {
                pagEl.hidden = true;
                pagEl.innerHTML = '';
            } else {
                pagEl.hidden = false;
                const end = Math.min(start + ROWS_PER_PAGE, filtered.length);
                pagEl.innerHTML = `
                    <div class="table-pagination" role="navigation">
                        <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${filtered.length}</span>
                        <div class="table-pagination-buttons">
                            <button type="button" class="btn btn-outline btn-sm" id="attPrev" ${currentPageAttestations <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                            <span>Page ${currentPageAttestations + 1} / ${totalPages}</span>
                            <button type="button" class="btn btn-outline btn-sm" id="attNext" ${currentPageAttestations >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                        </div>
                    </div>
                `;
                document.getElementById('attPrev')?.addEventListener('click', () => { currentPageAttestations--; renderAttestations(); });
                document.getElementById('attNext')?.addEventListener('click', () => { currentPageAttestations++; renderAttestations(); });
            }
        }
    } catch (error) {
        console.error('❌ Erreur lors du rendu des attestations:', error);
        container.innerHTML = `
            <div class="alert alert-error">
                Erreur lors de l'affichage des attestations. Vérifiez la console pour plus de détails.
            </div>
        `;
    }
}

function filterAttestations() {
    // Vérifier que les données sont disponibles
    if (!attestationsState.data || !Array.isArray(attestationsState.data) || attestationsState.data.length === 0) {
        console.warn('⚠️ filterAttestations: Aucune donnée disponible');
        return [];
    }

    console.log('🔍 Filtrage des attestations:', {
        total: attestationsState.data.length,
        typeFilter: attestationsState.typeFilter,
        statusFilter: attestationsState.statusFilter,
        subscriptionFilter: attestationsState.subscriptionFilter
    });

    // Commencer avec toutes les attestations
    let filtered = [...attestationsState.data];

    // Filtre par souscription
    if (attestationsState.subscriptionFilter !== null && attestationsState.subscriptionFilter !== undefined) {
        filtered = filtered.filter(att => {
            return att && att.souscription_id === attestationsState.subscriptionFilter;
        });
        console.log('📋 Après filtre souscription:', filtered.length);
    }

    // Filtre par type d'attestation
    if (attestationsState.typeFilter && attestationsState.typeFilter !== 'all') {
        filtered = filtered.filter(att => {
            if (!att || !att.type_attestation) return false;
            const attType = String(att.type_attestation).trim().toLowerCase();
            const filterType = String(attestationsState.typeFilter).trim().toLowerCase();
            return attType === filterType;
        });
        console.log('📋 Après filtre type:', filtered.length);
    }

    // Filtre par statut
    if (attestationsState.statusFilter && attestationsState.statusFilter !== 'all') {
        filtered = filtered.filter(att => {
            if (!att) return false;
            // est_valide est considéré comme "active" sauf si explicitement false
            const isActive = att.est_valide !== false && att.est_valide !== null && att.est_valide !== undefined;
            const statusKey = isActive ? 'active' : 'inactive';
            return statusKey === attestationsState.statusFilter;
        });
        console.log('📋 Après filtre statut:', filtered.length);
    }

    // Filtre par recherche texte
    if (attestationsState.searchTerm) {
        const term = attestationsState.searchTerm.trim().toLowerCase();
        filtered = filtered.filter(att => {
            if (!att) return false;
            const numero = (att.numero_attestation || '').toLowerCase();
            const subscriptionLabel = (att.subscription_label || '').toLowerCase();
            const productLabel = (att.product_label || '').toLowerCase();
            const dateStr = att.created_at ? new Date(att.created_at).toLocaleDateString('fr-FR').toLowerCase() : '';
            return numero.includes(term) || subscriptionLabel.includes(term) || productLabel.includes(term) || dateStr.includes(term);
        });
    }

    console.log('✅ Résultat final du filtrage:', {
        filtré: filtered.length,
        total: attestationsState.data.length,
        typesTrouvés: [...new Set(filtered.map(att => att.type_attestation))]
    });
    
    // Trier par date de création (plus récentes en premier)
    return filtered.sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at) : new Date(0);
        const dateB = b.created_at ? new Date(b.created_at) : new Date(0);
        if (isNaN(dateA.getTime())) return 1;
        if (isNaN(dateB.getTime())) return -1;
        return dateB - dateA;
    });
}

function buildAttestationCard(attestation) {
    const isProvisional = attestation.type_attestation === 'provisoire';
    const badgeClass = isProvisional ? 'badge-provisoire' : 'badge-definitive';
    const typeLabel = isProvisional ? 'Attestation provisoire' : 'Attestation définitive';
    const isActive = attestation.est_valide !== false;
    const statusClass = isActive ? 'status-active' : 'status-inactive';
    const statusLabel = isActive ? 'Active' : 'Invalide';

    return `
        <article class="attestation-card" id="attestation-${attestation.id}" data-attestation-id="${attestation.id}">
            <div class="attestation-card-header">
                <div>
                    <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; color: var(--dark-text);">${attestation.numero_attestation}</h3>
                    <div style="display:flex; gap:0.4rem; flex-wrap:wrap; margin-top: 0.5rem;">
                        <span class="badge ${badgeClass}">${isProvisional ? 'Provisoire' : 'Définitive'}</span>
                        <span class="status-pill ${statusClass}">${statusLabel}</span>
                    </div>
                </div>
            </div>
            <div class="attestation-meta">
                <div class="meta-item">
                    <span class="meta-label">Date de création</span>
                    <span class="meta-value">${formatDate(attestation.created_at)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Souscription</span>
                    <span class="meta-value">${attestation.subscription_label}</span>
                </div>
                ${attestation.date_expiration ? `
                <div class="meta-item">
                    <span class="meta-label">Date d'expiration</span>
                    <span class="meta-value">${formatDate(attestation.date_expiration)}</span>
                </div>
                ` : ''}
            </div>
            <div class="card-actions">
                ${attestation.url_signee ? `
                    <button type="button" class="btn btn-primary btn-sm" 
                       onclick="handleAttestationDownload(event, ${attestation.id})">
                        Télécharger l'attestation PDF
                    </button>
                ` : ''}
            </div>
        </article>
    `;
}

function updateStats() {
    const total = attestationsState.data.length;
    const provisional = attestationsState.data.filter(att => att.type_attestation === 'provisoire').length;
    const definitive = attestationsState.data.filter(att => att.type_attestation === 'definitive').length;
    const active = attestationsState.data.filter(att => att.est_valide !== false).length;

    document.getElementById('statTotal').textContent = total;
    document.getElementById('statProvisional').textContent = provisional;
    document.getElementById('statFinal').textContent = definitive;
    document.getElementById('statActive').textContent = active;
}

function formatDate(value) {
    if (!value) {
        return '—';
    }
    const date = new Date(value);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

// Fonction pour gérer le téléchargement d'une attestation
async function handleAttestationDownload(event, attestationId) {
    // Le téléchargement se fait via l'endpoint API qui gère l'authentification
    // et récupère le fichier depuis Minio de manière sécurisée
    event.preventDefault();
    
    try {
        // Récupérer le token d'authentification
        const token = localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || localStorage.getItem('token');
        if (!token) {
            alert('Vous devez être connecté pour télécharger l\'attestation');
            return;
        }
        
        // Construire l'URL de téléchargement
        const apiBaseUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
        const downloadUrl = `${apiBaseUrl}/attestations/${attestationId}/download`;
        
        // Récupérer le numéro d'attestation depuis les données si disponible
        const attestation = attestationsState.data.find(att => att.id === attestationId);
        const numeroAttestation = attestation?.numero_attestation || attestationId;
        
        // Ajouter le token dans les headers via fetch puis créer un blob
        const response = await fetch(downloadUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                alert('Votre session a expiré. Veuillez vous reconnecter.');
                window.location.href = '/login.html';
                return;
            }
            const errorData = await response.json().catch(() => ({}));
            const detail = errorData.detail;
            const message = typeof detail === 'string'
                ? detail
                : Array.isArray(detail)
                    ? (detail[0]?.msg || detail[0]?.loc?.join('.') || JSON.stringify(detail))
                    : (errorData.message || `Erreur ${response.status}`);
            throw new Error(message);
        }
        
        // Créer un blob et télécharger
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `attestation-${numeroAttestation}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Erreur lors du téléchargement:', error);
        alert(`Erreur lors du téléchargement: ${error.message}`);
    }
}

// Fonction pour rafraîchir l'URL d'une attestation
async function refreshAttestationUrl(attestationId) {
    try {
        console.log('🔄 Rafraîchissement de l\'URL pour l\'attestation:', attestationId);
        const attestation = await attestationsAPI.getWithUrl(attestationId);
        
        // Mettre à jour l'attestation dans les données
        const index = attestationsState.data.findIndex(att => att.id === attestationId);
        if (index !== -1) {
            attestationsState.data[index].url_signee = attestation.url_signee;
            attestationsState.data[index].date_expiration_url = attestation.date_expiration_url;
            
            // Re-rendre les attestations pour mettre à jour les liens
            renderAttestations();
            
            // Ouvrir la nouvelle URL
            if (attestation.url_signee) {
                window.location.href = attestation.url_signee;
            }
        }
    } catch (error) {
        console.error('❌ Erreur lors du rafraîchissement de l\'URL:', error);
        alert('Impossible de rafraîchir l\'URL de l\'attestation. Veuillez recharger la page.');
    }
}

// Fonction pour surligner une attestation
function highlightAttestation(attestationId) {
    // Retirer la surbrillance précédente
    document.querySelectorAll('.attestation-card').forEach(card => {
        card.classList.remove('highlighted');
        card.style.transition = '';
    });
    
    // Trouver la carte d'attestation
    const card = document.getElementById(`attestation-${attestationId}`);
    if (!card) {
        return;
    }
    
    // Ajouter la classe de surbrillance
    card.classList.add('highlighted');
    card.style.transition = 'all 0.3s ease';
    card.style.boxShadow = '0 4px 20px rgba(28, 119, 255, 0.4)';
    card.style.border = '2px solid var(--primary-color)';
    card.style.transform = 'scale(1.02)';
    
    // Faire défiler jusqu'à la carte
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    // Retirer la surbrillance après 5 secondes
    setTimeout(() => {
        card.classList.remove('highlighted');
        card.style.boxShadow = '';
        card.style.border = '';
        card.style.transform = '';
        
        // Nettoyer l'URL
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.delete('highlight_attestation');
        const newUrl = `${window.location.pathname}${urlParams.toString() ? '?' + urlParams.toString() : ''}`;
        window.history.replaceState({}, '', newUrl);
    }, 5000);
}

