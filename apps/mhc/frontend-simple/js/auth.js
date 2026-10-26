// Gestion de l'authentification
// API_BASE_URL doit être défini dans api.js qui doit être chargé avant ce script

// Fonction pour vérifier si l'utilisateur est connecté
function getStoredAccessToken() {
    if (window.MobilityAuth?.getAccessToken) {
        return window.MobilityAuth.getAccessToken();
    }
    return localStorage.getItem('access_token');
}

function isAuthenticated() {
    return getStoredAccessToken() !== null;
}

// Fonction pour valider et vérifier le token (async)
async function validateAuth() {
    const token = getStoredAccessToken();
    
    if (!token) {
        return false;
    }
    
    try {
        const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
        const response = await fetch(`${apiUrl}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            // Token invalide, nettoyer
            clearAuth();
            return false;
        }
        
        // Token valide, mettre à jour les infos utilisateur si nécessaire
        const user = await response.json();
        localStorage.setItem('user_role', user.role);
        localStorage.setItem('user_id', user.id);
        localStorage.setItem('user_name', user.full_name || user.username);
        if (user.permissions && typeof user.permissions === 'object') {
            localStorage.setItem('user_permissions', JSON.stringify(user.permissions));
        } else {
            localStorage.removeItem('user_permissions');
        }
        // Le menu BO peut avoir été rendu avant cette réponse : le reconstruire.
        document.dispatchEvent(new CustomEvent('mhc:permissions'));
        if (user.pays_residence) {
            localStorage.setItem('user_pays_residence', user.pays_residence);
        } else {
            localStorage.removeItem('user_pays_residence');
        }
        if (Object.prototype.hasOwnProperty.call(user, 'hospital_id')) {
            if (user.hospital_id !== null && user.hospital_id !== undefined) {
                localStorage.setItem('hospital_id', user.hospital_id);
            } else {
                localStorage.removeItem('hospital_id');
                localStorage.removeItem('hospital_name');
            }
        }
        if (Object.prototype.hasOwnProperty.call(user, 'hospital_nom')) {
            if (user.hospital_nom != null && user.hospital_nom !== '') {
                localStorage.setItem('hospital_name', user.hospital_nom);
            } else {
                localStorage.removeItem('hospital_name');
            }
        }
        
        return true;
    } catch (error) {
        console.error('Erreur de validation du token:', error);
        clearAuth();
        return false;
    }
}

// Fonction pour nettoyer les données d'authentification
function clearAuth() {
    if (window.MobilityAuth?.clearTokens) {
        window.MobilityAuth.clearTokens();
    } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_permissions');
    localStorage.removeItem('user_pays_residence');
    localStorage.removeItem('hospital_id');
    localStorage.removeItem('hospital_name');
    localStorage.removeItem('mhc_medecin_conseil_assignments_v1');
}

// Page d'accueil de chaque rôle — utilisée comme destination de repli quand
// un utilisateur connecté atteint une page qui ne lui est pas destinée
// (au lieu de le renvoyer vers login/index, ce qui simulait une déconnexion).
function getRoleHomeUrl(role) {
    const roleMap = {
        'admin': 'bo-dashboard.html',
        'superviseur_technique': 'bo-dashboard.html',
        'superviseur_affaires_medicales': 'bo-dashboard.html',
        'superviseur_comptable': 'bo-dashboard.html',
        'production_agent': 'bo-dashboard.html',
        'agent_conformite_production': 'bo-dashboard.html',
        'agent_conformite_sinistre': 'bo-dashboard.html',
        'agent_conformite_medical': 'bo-dashboard.html',
        'agent_conformite_comptable': 'bo-dashboard.html',
        'agent_medical_mhc': 'bo-dashboard.html',
        'agent_sinistre_mh': 'bo-dashboard.html',
        'agent_comptable_mh': 'bo-dashboard.html',
        'assistant_souscription': 'courtier-production.html',
        'medecin_referent_mh': 'bo-dashboard.html',
        'doctor': 'doctor-dashboard.html',
        'hospital_admin': 'hospital-dashboard.html',
        'medecin_hopital': 'hospital-doctor.html',
        'agent_reception_hopital': 'hospital-reception.html',
        'agent_comptable_hopital': 'hospital-invoices.html',
        'agent_comptable_assureur': 'assureur-accounting.html',
        'agent_comptable_courtier': 'accounting-portal.html',
        'agent_production_assureur': 'assureur-production.html',
        'agent_production_courtier': 'courtier-production.html',
        'agent_sinistre_assureur': 'assureur-sinistres.html',
        'agent_sinistre_courtier': 'courtier-sinistres.html',
        'agent_medical_assureur': 'assureur-production.html',
        'agent_verificateur_reassureur': 'reassureur-portal.html',
        'user': 'user-dashboard.html',
    };
    return roleMap[role] || 'index.html';
}

// Redirection « accès refusé » : on renvoie l'utilisateur vers SA page d'accueil
// plutôt que vers login/index — il reste connecté et retombe sur ses pieds.
function redirectForbidden(fallbackUrl) {
    const home = getRoleHomeUrl(localStorage.getItem('user_role'));
    // Un fallback explicite autre que login/index est respecté s'il diffère
    // de la page courante (évite les boucles).
    const target = (fallbackUrl && fallbackUrl !== 'login.html' && fallbackUrl !== 'index.html')
        ? fallbackUrl
        : home;
    if (!window.location.pathname.endsWith('/' + target) &&
        !window.location.pathname.endsWith(target)) {
        window.location.href = target;
    } else {
        window.location.href = home;
    }
}

// Fonction pour vérifier si l'utilisateur a un rôle spécifique
function hasRole(requiredRole) {
    const userRole = localStorage.getItem('user_role');
    return userRole === requiredRole;
}

// Fonction pour vérifier si l'utilisateur a un des rôles spécifiés
function hasAnyRole(allowedRoles) {
    const userRole = localStorage.getItem('user_role');
    return allowedRoles.includes(userRole);
}

// Fonction pour vérifier si l'utilisateur est admin
function isAdmin() {
    return hasRole('admin');
}

// Fonction pour rediriger vers la page de connexion si non authentifié
// Cette fonction doit être appelée au début de chaque page protégée
async function requireAuth() {
    const isValid = await validateAuth();
    if (!isValid) {
        // Nettoyer l'URL avant la redirection pour éviter les paramètres sensibles
        const currentPath = window.location.pathname;
        window.location.replace('login.html');
        return false;
    }
    return true;
}

// Fonction pour exiger un rôle spécifique (redirige si le rôle ne correspond pas)
async function requireRole(requiredRole, redirectUrl = 'login.html') {
    const isValid = await requireAuth();
    if (!isValid) {
        return false;
    }
    const userRole = localStorage.getItem('user_role');
    if (userRole !== requiredRole) {
        alert(`Accès refusé. Ce contenu est réservé aux utilisateurs avec le rôle: ${requiredRole}`);
        redirectForbidden(redirectUrl);
        return false;
    }
    return true;
}


// Fonction pour exiger une permission de la matrice (fonctionnalité + niveau)
async function requirePermission(feature, minLevel = 'consultation', redirectUrl = 'index.html') {
    const isValid = await requireAuth();
    if (!isValid) {
        return false;
    }
    const ok = window.MhPermissions && window.MhPermissions.can(feature, minLevel);
    if (!ok) {
        alert(`Accès refusé. Permission requise : ${feature} (${minLevel}).`);
        redirectForbidden(redirectUrl);
        return false;
    }
    return true;
}

// Fonction pour exiger l'appartenance au back-office interne MHC
async function requireBackoffice(redirectUrl = 'index.html') {
    const isValid = await requireAuth();
    if (!isValid) {
        return false;
    }
    const ok = window.MhPermissions && window.MhPermissions.isInternalBackoffice();
    if (!ok) {
        alert('Accès refusé. Ce contenu est réservé aux profils internes MHC.');
        redirectForbidden(redirectUrl);
        return false;
    }
    return true;
}

// Fonction pour exiger un des rôles spécifiés
async function requireAnyRole(allowedRoles, redirectUrl = 'login.html') {
    const isValid = await requireAuth();
    if (!isValid) {
        return false;
    }
    const userRole = localStorage.getItem('user_role');
    if (!allowedRoles.includes(userRole)) {
        alert(`Accès refusé. Ce contenu est réservé aux utilisateurs avec les rôles: ${allowedRoles.join(', ')}`);
        redirectForbidden(redirectUrl);
        return false;
    }
    return true;
}

// Fonction de déconnexion (globale)
function logout() {
    clearAuth();
    window.location.href = 'login.html';
}

// Appeler requireAuth au chargement des pages protégées (si le body a la classe 'protected')
if (document.body.classList.contains('protected')) {
    requireAuth();
}

