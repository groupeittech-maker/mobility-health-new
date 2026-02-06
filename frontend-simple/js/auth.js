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
<<<<<<< HEAD
        const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
=======
        const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
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
    localStorage.removeItem('hospital_id');
    localStorage.removeItem('hospital_name');
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
async function requireRole(requiredRole, redirectUrl = 'index.html') {
    const isValid = await requireAuth();
    if (!isValid) {
        return false;
    }
    const userRole = localStorage.getItem('user_role');
    if (userRole !== requiredRole) {
        alert(`Accès refusé. Ce contenu est réservé aux utilisateurs avec le rôle: ${requiredRole}`);
        window.location.href = redirectUrl;
        return false;
    }
    return true;
}

// Fonction pour exiger un des rôles spécifiés
async function requireAnyRole(allowedRoles, redirectUrl = 'index.html') {
    const isValid = await requireAuth();
    if (!isValid) {
        return false;
    }
    const userRole = localStorage.getItem('user_role');
    if (!allowedRoles.includes(userRole)) {
        alert(`Accès refusé. Ce contenu est réservé aux utilisateurs avec les rôles: ${allowedRoles.join(', ')}`);
        window.location.href = redirectUrl;
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

