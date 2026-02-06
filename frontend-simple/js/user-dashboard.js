// Gestion du tableau de bord utilisateur
let allSubscriptions = [];
let currentTab = 'all';

function getSafeAccessToken() {
    return window.MobilityAuth?.getAccessToken
        ? window.MobilityAuth.getAccessToken()
        : localStorage.getItem('access_token');
}

// Vérifier l'authentification et le rôle user
(async function() {
    // Attendre un peu pour s'assurer que les données sont bien stockées après la redirection
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Vérifier d'abord si un token existe
    const token = getSafeAccessToken();
    if (!token) {
        console.warn('⚠️ Aucun token trouvé, redirection vers la page de connexion');
        window.location.replace('login.html');
        return;
    }
    
    const isValid = await requireAuth();
    if (!isValid) {
        return; // requireAuth() a déjà redirigé vers login.html
    }
    
    // Vérifier que l'utilisateur est bien un utilisateur standard
    const userRole = localStorage.getItem('user_role');
    if (userRole && userRole !== 'user') {
        // Rediriger vers le dashboard approprié selon le rôle
        const redirectUrl = getDashboardUrlForRole(userRole);
        if (redirectUrl !== 'index.html' && redirectUrl !== 'user-dashboard.html') {
            window.location.replace(redirectUrl); // Utiliser replace pour éviter le retour arrière
            return;
        }
    }
    
    // Afficher le nom de l'utilisateur
    const userName = localStorage.getItem('user_name') || 'Utilisateur';
    const userNameEl = document.getElementById('userName');
    if (userNameEl) {
        userNameEl.textContent = userName;
    }
    
    // Charger les données
    await loadDashboardData();
    
    // Initialiser le champ de recherche
    const searchInput = document.getElementById('subscriptionSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase().trim();
            console.log('🔍 Recherche:', searchTerm);
            filterSubscriptions(searchTerm);
        });
    }
})();

// Fonction pour obtenir l'URL du dashboard selon le rôle (depuis login.js)
function getDashboardUrlForRole(role) {
    const roleMap = {
        'admin': 'admin-dashboard.html',
        'doctor': 'doctor-dashboard.html',
        'hospital_admin': 'hospital-dashboard.html',
        'finance_manager': 'finance-dashboard.html',
        'sos_operator': 'sos-dashboard.html',
        'user': 'user-dashboard.html'
    };
    return roleMap[role] || 'index.html';
}

// Charger toutes les données du dashboard
async function loadDashboardData() {
    await Promise.all([
        loadSubscriptions(),
        loadStats()
    ]);
    initUserNotificationsModule();
}

// Charger les statistiques
async function loadStats() {
    try {
        const subscriptions = await apiCall('/subscriptions/?limit=1000');
        
        // Compter par statut
        const active = subscriptions.filter(s => s.statut === 'active').length;
        const pending = subscriptions.filter(s => s.statut === 'en_attente' || s.statut === 'pending').length;
        const expired = subscriptions.filter(s => s.statut === 'expiree' || s.statut === 'expired').length;
        
        document.getElementById('activeSubscriptionsCount').textContent = active || 0;
        document.getElementById('pendingSubscriptionsCount').textContent = pending || 0;
        document.getElementById('expiredSubscriptionsCount').textContent = expired || 0;
    } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
        document.getElementById('activeSubscriptionsCount').textContent = '0';
        document.getElementById('pendingSubscriptionsCount').textContent = '0';
        document.getElementById('expiredSubscriptionsCount').textContent = '0';
    }
}

// Charger les souscriptions
async function loadSubscriptions() {
    const loadingEl = document.getElementById('subscriptionsLoading');
    loadingEl.style.display = 'block';
    
    try {
        console.log('🔄 Chargement des souscriptions...');
        const userInfo = {
            username: localStorage.getItem('user_name'),
            role: localStorage.getItem('user_role'),
            email: localStorage.getItem('user_email')
        };
        console.log('👤 Utilisateur connecté:', userInfo);
        
        allSubscriptions = await apiCall('/subscriptions/?limit=1000');
        console.log('📋 Souscriptions reçues de l\'API:', allSubscriptions);
        console.log('📊 Nombre total de souscriptions:', allSubscriptions ? allSubscriptions.length : 0);
        
        if (!Array.isArray(allSubscriptions)) {
            console.error('❌ Les souscriptions ne sont pas un tableau:', typeof allSubscriptions);
            allSubscriptions = [];
        }
        
        // Trier les souscriptions par date (plus récentes en premier)
        allSubscriptions.sort((a, b) => {
            const dateA = new Date(a.created_at || a.date_debut);
            const dateB = new Date(b.created_at || b.date_debut);
            return dateB - dateA;
        });
        
        // Filtrer par statut
        const active = allSubscriptions.filter(s => s.statut === 'active');
        const pending = allSubscriptions.filter(s => s.statut === 'en_attente' || s.statut === 'pending');
        const expired = allSubscriptions.filter(s => s.statut === 'expiree' || s.statut === 'expired');
        
        console.log('📊 Répartition par statut:', {
            total: allSubscriptions.length,
            active: active.length,
            pending: pending.length,
            expired: expired.length,
            autres: allSubscriptions.length - active.length - pending.length - expired.length
        });
        
        // Afficher les souscriptions
        displaySubscriptions('subscriptionsAllList', allSubscriptions);
        displaySubscriptions('subscriptionsActiveList', active);
        displaySubscriptions('subscriptionsPendingList', pending);
        displaySubscriptions('subscriptionsExpiredList', expired);
        
        console.log('✅ Affichage des souscriptions terminé');
        loadingEl.style.display = 'none';
    } catch (error) {
        console.error('Erreur lors du chargement des souscriptions:', error);
        const errorMessage = error.message || 'Impossible de charger vos souscriptions';
        
        // Vérifier si c'est une erreur de connexion
        const isConnectionError = errorMessage.includes('connecter') || 
                                  errorMessage.includes('Failed to fetch') ||
                                  errorMessage.includes('backend');
        
        loadingEl.innerHTML = `
            <div class="alert alert-error">
                <h3>Erreur de chargement</h3>
                <p>${errorMessage}</p>
                ${isConnectionError ? `
<<<<<<< HEAD
                    <p><strong>Le serveur backend n'est peut-être pas démarré.</strong></p>
                    <p>Vérifiez que le backend est accessible sur https://srv1324425.hstgr.cloud</p>
                    <p>Vous pouvez le démarrer avec : <code>.\scripts\start_backend.ps1</code></p>
=======
                    <p><strong>Le serveur backend n'est peut-être pas accessible.</strong></p>
                    <p>Vérifiez que l'API est accessible sur https://mobility-health.ittechmed.com</p>
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
                ` : ''}
                <button class="btn btn-primary" onclick="loadSubscriptions()">Réessayer</button>
            </div>
        `;
    }
}

const ROWS_PER_PAGE = 6;
const subscriptionPageMap = {};
const subscriptionDisplayCache = {};

// Afficher les souscriptions dans un conteneur
function displaySubscriptions(containerId, subscriptions) {
    const container = document.getElementById(containerId);
    
    if (!subscriptions || subscriptions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <p>Aucune souscription trouvée</p>
            </div>
        `;
        const pagEl = document.getElementById(containerId + 'Pagination');
        if (pagEl) { pagEl.hidden = true; pagEl.innerHTML = ''; }
        return;
    }
    
    const totalPages = Math.max(1, Math.ceil(subscriptions.length / ROWS_PER_PAGE));
    subscriptionPageMap[containerId] = subscriptionPageMap[containerId] || 0;
    subscriptionPageMap[containerId] = Math.min(subscriptionPageMap[containerId], totalPages - 1);
    const start = subscriptionPageMap[containerId] * ROWS_PER_PAGE;
    const pageData = subscriptions.slice(start, start + ROWS_PER_PAGE);
    
    let html = '';
    pageData.forEach(subscription => {
        const statusClass = getStatusClass(subscription.statut);
        const statusLabel = getStatusLabel(subscription.statut);
        
        html += `
            <div class="subscription-card">
                <div class="subscription-header">
                    <div>
                        <h4 class="subscription-title">${subscription.numero_souscription || 'Souscription #' + subscription.id}</h4>
                        <span class="status-badge ${statusClass}">${statusLabel}</span>
                    </div>
                </div>
                <div class="subscription-info">
                    <div class="subscription-info-item">
                        <span class="subscription-info-label">Produit</span>
                        <span class="subscription-info-value">${subscription.produit_assurance?.nom || 'N/A'}</span>
                    </div>
                    <div class="subscription-info-item">
                        <span class="subscription-info-label">Date de début</span>
                        <span class="subscription-info-value">${formatDate(subscription.date_debut)}</span>
                    </div>
                    <div class="subscription-info-item">
                        <span class="subscription-info-label">Date de fin</span>
                        <span class="subscription-info-value">${subscription.date_fin ? formatDate(subscription.date_fin) : 'N/A'}</span>
                    </div>
                    <div class="subscription-info-item">
                        <span class="subscription-info-label">Prix</span>
                        <span class="subscription-info-value">${formatPrice(subscription.prix_applique)} €</span>
                    </div>
                </div>
                <div class="subscription-actions">
                    ${getSubscriptionActions(subscription)}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    let pagEl = document.getElementById(containerId + 'Pagination');
    if (subscriptions.length > ROWS_PER_PAGE) {
        const end = Math.min(start + ROWS_PER_PAGE, subscriptions.length);
        const pagHtml = `<div class="table-pagination-wrapper"><div class="table-pagination" role="navigation">
            <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${subscriptions.length}</span>
            <div class="table-pagination-buttons">
                <button type="button" class="btn btn-outline btn-sm" data-pag-cont="${containerId}" data-pag-dir="-1" ${subscriptionPageMap[containerId] <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                <span>Page ${subscriptionPageMap[containerId] + 1} / ${totalPages}</span>
                <button type="button" class="btn btn-outline btn-sm" data-pag-cont="${containerId}" data-pag-dir="1" ${subscriptionPageMap[containerId] >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
            </div>
        </div></div>`;
        if (!pagEl) {
            pagEl = document.createElement('div');
            pagEl.id = containerId + 'Pagination';
            pagEl.className = 'table-pagination-wrapper';
            container.parentNode.insertBefore(pagEl, container.nextSibling);
        }
        pagEl.innerHTML = pagHtml;
        pagEl.hidden = false;
        pagEl.querySelectorAll('[data-pag-cont]').forEach(btn => {
            btn.onclick = () => {
                const dir = parseInt(btn.dataset.pagDir, 10);
                subscriptionPageMap[containerId] = Math.max(0, Math.min(totalPages - 1, subscriptionPageMap[containerId] + dir));
                const subs = subscriptionDisplayCache[containerId] || [];
                displaySubscriptions(containerId, subs);
            };
        });
    } else {
        if (pagEl) { pagEl.hidden = true; pagEl.innerHTML = ''; }
    }
}

// Obtenir les actions disponibles pour une souscription
function getSubscriptionActions(subscription) {
    const actions = [];
    
    // Si la souscription est en attente, on peut voir le statut de paiement
    if (subscription.statut === 'en_attente' || subscription.statut === 'pending') {
        actions.push(`<button class="btn btn-primary btn-sm" onclick="viewSubscriptionDetails(${subscription.id})">Voir les détails</button>`);
        actions.push(`<button class="btn btn-secondary btn-sm" onclick="viewAttestations(${subscription.id})">Voir les attestations</button>`);
    }
    
    // Si la souscription est active, on peut voir les attestations et déclarer un sinistre
    if (subscription.statut === 'active') {
        actions.push(`<button class="btn btn-primary btn-sm" onclick="viewSubscriptionDetails(${subscription.id})">Voir les détails</button>`);
        actions.push(`<button class="btn btn-secondary btn-sm" onclick="viewAttestations(${subscription.id})">Mes attestations</button>`);
        actions.push(`<a href="sos-alert.html?subscription_id=${subscription.id}" class="btn btn-danger btn-sm">Déclarer un sinistre</a>`);
    }
    
    // Si la souscription est expirée, on peut voir l'historique
    if (subscription.statut === 'expiree' || subscription.statut === 'expired') {
        actions.push(`<button class="btn btn-secondary btn-sm" onclick="viewSubscriptionDetails(${subscription.id})">Voir l'historique</button>`);
        actions.push(`<button class="btn btn-secondary btn-sm" onclick="viewAttestations(${subscription.id})">Voir les attestations</button>`);
    }
    
    return actions.join(' ');
}

// Obtenir la classe CSS pour le statut
function getStatusClass(statut) {
    const statusMap = {
        'active': 'active',
        'en_attente': 'en_attente',
        'pending': 'en_attente',
        'expiree': 'expiree',
        'expired': 'expiree',
        'suspendue': 'suspendue',
        'resiliee': 'resiliee'
    };
    return statusMap[statut] || 'en_attente';
}

// Obtenir le label du statut
function getStatusLabel(statut) {
    const labelMap = {
        'active': 'En cours',
        'en_attente': 'En attente',
        'pending': 'En attente',
        'expiree': 'Expirée',
        'expired': 'Expirée',
        'suspendue': 'Suspendue',
        'resiliee': 'Résiliée'
    };
    return labelMap[statut] || statut;
}

// Formater une date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Formater un prix
function formatPrice(price) {
    if (!price) return '0';
    return parseFloat(price).toFixed(2);
}

// Changer d'onglet
function switchTab(tab, eventElement) {
    currentTab = tab;
    console.log('🔄 Changement d\'onglet vers:', tab);
    
    // Mettre à jour les onglets
    document.querySelectorAll('.subscriptions-tab').forEach(el => el.classList.remove('active'));
    if (eventElement) {
        eventElement.classList.add('active');
    } else {
        // Si pas d'élément fourni, trouver l'onglet correspondant
        const tabButtons = document.querySelectorAll('.subscriptions-tab');
        tabButtons.forEach(btn => {
            if (btn.textContent.toLowerCase().includes(tab.toLowerCase()) || 
                (tab === 'all' && btn.textContent.toLowerCase().includes('toutes'))) {
                btn.classList.add('active');
            }
        });
    }
    
    // Mettre à jour le contenu
    document.querySelectorAll('.subscriptions-content').forEach(el => el.classList.remove('active'));
    const contentId = `subscriptions${tab.charAt(0).toUpperCase() + tab.slice(1)}`;
    const contentEl = document.getElementById(contentId);
    if (contentEl) {
        contentEl.classList.add('active');
        console.log('✅ Onglet activé:', contentId);
    } else {
        console.error('❌ Élément de contenu non trouvé:', contentId);
    }
}

// Filtrer les souscriptions par terme de recherche
function filterSubscriptions(searchTerm) {
    if (!searchTerm) {
        // Si pas de recherche, réafficher toutes les souscriptions
        displaySubscriptions('subscriptionsAllList', allSubscriptions);
        const active = allSubscriptions.filter(s => s.statut === 'active');
        const pending = allSubscriptions.filter(s => s.statut === 'en_attente' || s.statut === 'pending');
        const expired = allSubscriptions.filter(s => s.statut === 'expiree' || s.statut === 'expired');
        displaySubscriptions('subscriptionsActiveList', active);
        displaySubscriptions('subscriptionsPendingList', pending);
        displaySubscriptions('subscriptionsExpiredList', expired);
        return;
    }
    
    // Filtrer toutes les souscriptions
    const filtered = allSubscriptions.filter(sub => {
        const numero = (sub.numero_souscription || '').toLowerCase();
        const produit = (sub.produit_assurance?.nom || '').toLowerCase();
        const dateDebut = sub.date_debut ? new Date(sub.date_debut).toLocaleDateString('fr-FR') : '';
        const dateFin = sub.date_fin ? new Date(sub.date_fin).toLocaleDateString('fr-FR') : '';
        const searchable = `${numero} ${produit} ${dateDebut} ${dateFin}`.toLowerCase();
        return searchable.includes(searchTerm);
    });
    
    // Filtrer par statut
    const active = filtered.filter(s => s.statut === 'active');
    const pending = filtered.filter(s => s.statut === 'en_attente' || s.statut === 'pending');
    const expired = filtered.filter(s => s.statut === 'expiree' || s.statut === 'expired');
    
    // Afficher les résultats filtrés
    displaySubscriptions('subscriptionsAllList', filtered);
    displaySubscriptions('subscriptionsActiveList', active);
    displaySubscriptions('subscriptionsPendingList', pending);
    displaySubscriptions('subscriptionsExpiredList', expired);
}

// Voir les détails d'une souscription
function viewSubscriptionDetails(subscriptionId) {
    window.location.href = `subscription-details.html?id=${subscriptionId}`;
}

// Voir les attestations d'une souscription
function viewAttestations(subscriptionId) {
    const target = subscriptionId ? `?subscription_id=${subscriptionId}` : '';
    window.location.href = `user-attestations.html${target}`;
}


// Obtenir le statut de validation
function getValidationStatus(attestation) {
    // Si l'attestation a des validations, vérifier le statut
    if (attestation.validations && attestation.validations.length > 0) {
        const allValidated = attestation.validations.every(v => v.statut === 'validee');
        if (allValidated) {
            return { class: 'validee', label: 'Validée' };
        }
        return { class: 'en_attente', label: 'En cours de validation' };
    }
    
    if (typeof attestation.est_valide === 'boolean') {
        return attestation.est_valide
            ? { class: 'validee', label: 'Validée' }
            : { class: 'en_attente', label: 'Non valide' };
    }
    
    // Par défaut, en attente
    return { class: 'en_attente', label: 'En attente de validation' };
}

// Faire défiler vers la section produits
function scrollToProducts() {
    window.location.href = 'user-products.html';
}

// ==================== Gestion des notifications utilisateur ====================

const USER_NOTIFICATION_TYPES = {
    attestation_definitive_ready: {
        label: 'Attestation prête',
        icon: '✅',
        defaultMessage: 'Votre attestation définitive est maintenant disponible.',
    },
    medical_validation_result: {
        label: 'Validation médicale',
        icon: '🏥',
        defaultMessage: 'Le résultat de la validation médicale de votre prise en charge est disponible.',
    },
    questionnaire_long_reminder: {
        label: 'Questionnaire à compléter',
        icon: '📝',
        defaultMessage: 'Veuillez remplir le questionnaire complet pour finaliser votre dossier.',
    },
    questionnaire_completed: {
        label: 'Questionnaire complété',
        icon: '✅',
        defaultMessage: 'Votre questionnaire a été enregistré avec succès.',
    },
};

const USER_NOTIFICATION_ORDER = [
    'questionnaire_completed',
    'questionnaire_long_reminder',
    'medical_validation_result',
    'attestation_definitive_ready',
];

const userNotificationsState = {
    enabled: false,
    items: [],
    elements: {},
    caches: {
        attestations: {},
        souscriptions: {},
    },
};

function initUserNotificationsModule() {
    try {
        const section = document.getElementById('userNotificationsSection');
        if (!section) {
            console.warn('Section userNotificationsSection non trouvée');
            return;
        }

        const role = (localStorage.getItem('user_role') || '').toLowerCase();
        console.log('Rôle utilisateur détecté:', role);
        if (role !== 'user') {
            console.log('Rôle non autorisé, masquage de la section');
            section.style.display = 'none';
            return;
        }
        
        // S'assurer que la section est visible
        section.style.display = 'block';

        userNotificationsState.enabled = true;
        userNotificationsState.elements = {
            section,
            list: document.getElementById('userNotificationsList'),
            empty: document.getElementById('userNotificationsEmpty'),
            loading: document.getElementById('userNotificationsLoading'),
            error: document.getElementById('userNotificationsError'),
            count: document.getElementById('userNotificationsCount'),
            refreshButton: document.getElementById('refreshUserNotificationsBtn'),
        };

        // Vérifier que tous les éléments essentiels existent
        if (!userNotificationsState.elements.list || !userNotificationsState.elements.empty) {
            console.error('Éléments DOM manquants pour les notifications utilisateur', {
                list: !!userNotificationsState.elements.list,
                empty: !!userNotificationsState.elements.empty
            });
            return;
        }

        console.log('Module de notifications utilisateur initialisé avec succès');
        console.log('Éléments DOM:', {
            section: !!userNotificationsState.elements.section,
            list: !!userNotificationsState.elements.list,
            empty: !!userNotificationsState.elements.empty,
            loading: !!userNotificationsState.elements.loading,
            error: !!userNotificationsState.elements.error,
            count: !!userNotificationsState.elements.count,
            refreshButton: !!userNotificationsState.elements.refreshButton
        });

        if (userNotificationsState.elements.refreshButton) {
            userNotificationsState.elements.refreshButton.addEventListener('click', () =>
                loadUserNotifications(true)
            );
        }
        if (userNotificationsState.elements.list) {
            userNotificationsState.elements.list.addEventListener('click', handleUserNotificationCardClick);
            userNotificationsState.elements.list.addEventListener('keydown', handleUserNotificationCardKeyDown);
        }

        // Charger les notifications
        console.log('Démarrage du chargement des notifications...');
        loadUserNotifications().catch((error) => {
            console.error('Erreur lors du chargement initial des notifications:', error);
        });
    } catch (error) {
        console.error('Erreur lors de l\'initialisation du module de notifications utilisateur:', error);
    }
}

async function loadUserNotifications(showToast = false) {
    if (!userNotificationsState.enabled) {
        console.warn('Module de notifications utilisateur non activé');
        return;
    }

    const { error, loading } = userNotificationsState.elements;
    if (!error || !loading) {
        console.error('Éléments DOM manquants pour charger les notifications');
        return;
    }

    if (error) {
        error.hidden = true;
        error.textContent = '';
    }
    if (loading) {
        loading.hidden = false;
    }

    try {
        console.log('Chargement des notifications utilisateur...');
        const response = await apiCall('/notifications?limit=50');
        console.log('Notifications reçues:', response);
        const notifications = Array.isArray(response) ? response : [];
        console.log('Nombre total de notifications:', notifications.length);
        console.log('Types de notifications disponibles:', USER_NOTIFICATION_TYPES);
        
        // Log détaillé de chaque notification
        notifications.forEach((notif, index) => {
            console.log(`Notification ${index}:`, {
                id: notif.id,
                type: notif.type_notification,
                is_read: notif.is_read,
                titre: notif.titre,
                in_types: !!USER_NOTIFICATION_TYPES[notif.type_notification],
                will_show: USER_NOTIFICATION_TYPES[notif.type_notification] && !notif.is_read
            });
        });
        
        const filtered = notifications.filter(
            (item) => USER_NOTIFICATION_TYPES[item.type_notification] && !item.is_read
        );
        console.log('Notifications filtrées:', filtered);
        console.log('Nombre de notifications après filtrage:', filtered.length);
        userNotificationsState.items = sortUserNotifications(filtered);
        renderUserNotifications();
        if (showToast) {
            showAlert('Notifications mises à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des notifications utilisateur:', error);
        if (userNotificationsState.elements.error) {
            userNotificationsState.elements.error.hidden = false;
            userNotificationsState.elements.error.textContent =
                error.message || 'Impossible de charger les notifications.';
        }
        userNotificationsState.items = [];
        renderUserNotifications();
    } finally {
        if (loading) {
            loading.hidden = true;
        }
    }
}

function sortUserNotifications(notifications) {
    return notifications
        .slice()
        .sort((a, b) => {
            const typeIndexA = USER_NOTIFICATION_ORDER.indexOf(a.type_notification);
            const typeIndexB = USER_NOTIFICATION_ORDER.indexOf(b.type_notification);
            if (typeIndexA !== typeIndexB) {
                const safeA = typeIndexA === -1 ? Number.MAX_SAFE_INTEGER : typeIndexA;
                const safeB = typeIndexB === -1 ? Number.MAX_SAFE_INTEGER : typeIndexB;
                return safeA - safeB;
            }
            return new Date(b.created_at || 0) - new Date(a.created_at || 0);
        });
}

function renderUserNotifications() {
    const { list, empty, section } = userNotificationsState.elements;
    if (!list || !empty) {
        console.error('Éléments DOM manquants pour rendre les notifications');
        return;
    }

    // S'assurer que la section est visible
    if (section) {
        section.style.display = 'block';
    }

    const notifications = userNotificationsState.items || [];
    console.log('Rendu des notifications:', notifications.length);
    updateUserNotificationCount(notifications.length);

    if (!notifications.length) {
        console.log('Aucune notification, affichage de l\'état vide');
        list.innerHTML = '';
        if (list) list.hidden = true;
        if (empty) {
            empty.hidden = false;
            empty.style.display = 'block';
        }
        // S'assurer que la section est visible même sans notifications
        if (section) {
            section.style.display = 'block';
            section.hidden = false;
        }
        return;
    }
    
    console.log('Affichage de', notifications.length, 'notifications');

    list.innerHTML = notifications
        .map((notification, index) => buildUserNotificationCard(notification, index))
        .join('');
    if (empty) empty.hidden = true;
    if (list) list.hidden = false;
}

function buildUserNotificationCard(notification, index) {
    try {
        const config = USER_NOTIFICATION_TYPES[notification.type_notification];
        if (!config) {
            return '';
        }
        const timestamp = notification.created_at
            ? new Date(notification.created_at).toLocaleString('fr-FR')
            : '—';
        const title = notification.titre || config.label;
        const body = notification.message || config.defaultMessage;
        const reference = getUserNotificationReference(notification);
        
        // Formater le message pour améliorer la lisibilité
        const formattedBody = formatUserNotificationMessage(body);

        return `
            <div class="card notification-card" data-notification-type="${notification.type_notification}">
                <div
                    class="notification-card__body"
                    role="button"
                    tabindex="0"
                    data-notification-index="${index}"
                    aria-label="Ouvrir le dossier lié à cette notification"
                >
                <div class="notification-card__header">
                    <span class="notification-pill">
                        <span aria-hidden="true">${config.icon}</span>
                        <span>${escapeHtml(config.label)}</span>
                    </span>
                    <span class="notification-time">${escapeHtml(timestamp)}</span>
                </div>
                <h4>${escapeHtml(title)}</h4>
                <div class="notification-body">${formattedBody}</div>
                ${reference ? `<div class="notification-meta">${escapeHtml(reference)}</div>` : ''}
                <div class="notification-link muted">Cliquer pour ouvrir</div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur lors de la construction de la carte de notification:', error);
        return '';
    }
}

function formatUserNotificationMessage(message) {
    if (!message || typeof message !== 'string') {
        return '<p class="muted">Aucun message</p>';
    }
    
    // Supprimer la section "--- Extrait du questionnaire ---" si elle existe
    const excerptIndex = message.indexOf('--- Extrait du questionnaire ---');
    if (excerptIndex !== -1) {
        message = message.substring(0, excerptIndex).trim();
    }
    message = message.replace(/---\s*Extrait du questionnaire\s*---.*$/s, '').trim();
    message = message.replace(/Extrait du questionnaire.*$/s, '').trim();
    
    // Échapper le HTML d'abord
    let formatted = escapeHtml(message);
    
    // Mettre en forme les sections avec des titres
    formatted = formatted.replace(/(📋|📄|🔍|⚠️|🚨|💼|✅|🏥|📝)\s*([^\n]+)/g, '<strong class="notification-section-title">$1 $2</strong>');
    
    // Mettre en forme les listes à puces
    const lines = formatted.split('\n');
    let inList = false;
    let result = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (line.startsWith('•')) {
            if (!inList) {
                result.push('<ul class="notification-list">');
                inList = true;
            }
            const content = line.replace(/^•\s*/, '');
            result.push(`<li>${content}</li>`);
        } else {
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            
            if (line) {
                const enhanced = line.replace(/(Priorité|Adresse|Assuré|Dossier médical|Informations médicales|version|Alerte|Sinistre|Facture|Rapport|Hôpital|Montant TTC|Statut|Votre attestation|Vous avez|Pour compléter|Cliquez|Notes du médecin|Motif du refus):/g, '<strong>$1:</strong>');
                result.push(enhanced);
            } else if (i < lines.length - 1) {
                result.push('<br>');
            }
        }
    }
    
    if (inList) {
        result.push('</ul>');
    }
    
    formatted = result.join('\n');
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

function getUserNotificationReference(notification) {
    if (!notification) {
        return '';
    }
    if (notification.lien_relation_type === 'attestation' && notification.lien_relation_id) {
        return `Attestation #${notification.lien_relation_id}`;
    }
    if (notification.lien_relation_type === 'souscription' && notification.lien_relation_id) {
        return `Souscription #${notification.lien_relation_id}`;
    }
    if (notification.lien_relation_type === 'questionnaire' && notification.lien_relation_id) {
        return `Questionnaire #${notification.lien_relation_id}`;
    }
    return '';
}

function updateUserNotificationCount(value) {
    if (!userNotificationsState.elements.count) {
        return;
    }
    const suffix = value > 1 ? 'notifications' : 'notification';
    userNotificationsState.elements.count.textContent = `${value} ${suffix}`;
}

async function handleUserNotificationCardClick(event) {
    const card = event.target.closest('[data-notification-index]');
    if (!card) {
        return;
    }
    const index = Number(card.dataset.notificationIndex);
    await openUserNotificationTargetByIndex(index, card);
}

async function handleUserNotificationCardKeyDown(event) {
    if (!['Enter', ' '].includes(event.key)) {
        return;
    }
    const card = event.target.closest('[data-notification-index]');
    if (!card) {
        return;
    }
    event.preventDefault();
    const index = Number(card.dataset.notificationIndex);
    await openUserNotificationTargetByIndex(index, card);
}

async function openUserNotificationTargetByIndex(index, cardElement) {
    if (!Number.isFinite(index) || index < 0) {
        return;
    }
    const notifications = userNotificationsState.items || [];
    const notification = notifications[index];
    if (!notification) {
        return;
    }
    if (cardElement) {
        cardElement.classList.add('notification-card--loading');
    }
    try {
        const targetUrl = await resolveUserNotificationLink(notification);
        if (targetUrl) {
        await markUserNotificationAsRead(notification.id);
        userNotificationsState.items = userNotificationsState.items.filter(
            (item) => item.id !== notification.id
        );
        renderUserNotifications();
            if (notification.type_notification === 'questionnaire_long_reminder') {
                // Ouvrir dans le même onglet pour le questionnaire
                window.location.href = targetUrl;
            } else if (notification.type_notification === 'questionnaire_completed') {
                // Ouvrir dans le même onglet pour la confirmation de questionnaire complété
                window.location.href = targetUrl;
            } else {
                // Ouvrir dans un nouvel onglet pour les autres
                window.location.href = targetUrl;
            }
        } else {
            showAlert('Impossible de trouver le dossier associé à cette notification.', 'error');
        }
    } catch (error) {
        console.error('Erreur lors de l\'ouverture du dossier notification:', error);
        showAlert(error.message || 'Ouverture du dossier impossible.', 'error');
    } finally {
        if (cardElement) {
            cardElement.classList.remove('notification-card--loading');
        }
    }
}

async function markUserNotificationAsRead(notificationId) {
    if (!notificationId) {
        return;
    }
    try {
        await apiCall(`/notifications/${notificationId}/read`, {
            method: 'PATCH',
        });
    } catch (error) {
        console.error(`Erreur lors du marquage de la notification ${notificationId} comme lue:`, error);
    }
}

async function resolveUserNotificationLink(notification) {
    if (!notification) {
        return null;
    }
    if (notification.lien_relation_type === 'attestation' && notification.lien_relation_id) {
        return `attestation-view.html?attestation_id=${notification.lien_relation_id}`;
    }
    if (notification.lien_relation_type === 'souscription' && notification.lien_relation_id) {
        if (notification.type_notification === 'questionnaire_long_reminder') {
            // Rediriger vers le formulaire de questionnaire long
            return `forms-medical.html?subscription_id=${notification.lien_relation_id}&mode=long`;
        }
        return `subscription-details.html?subscription_id=${notification.lien_relation_id}`;
    }
    if (notification.lien_relation_type === 'questionnaire' && notification.lien_relation_id) {
        // Pour les notifications de questionnaire complété, récupérer la souscription_id depuis le questionnaire
        try {
            const questionnaire = await apiCall(`/questionnaire/${notification.lien_relation_id}/status`);
            if (questionnaire && questionnaire.souscription_id) {
                return `subscription-details.html?subscription_id=${questionnaire.souscription_id}`;
            }
        } catch (error) {
            console.error('Erreur lors de la récupération du questionnaire:', error);
        }
        // Fallback: rediriger vers le dashboard
        return `user-dashboard.html`;
    }
    return null;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}


