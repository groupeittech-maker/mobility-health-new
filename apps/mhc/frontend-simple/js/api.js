// Configuration de l'API
// - En local : frontend et backend (port 8000) → backend local
// - En prod : même domaine (srv1324425.hstgr.cloud) → /api/v1 proxyfié par Nginx vers le backend (évite CORS)
const LOCAL_BACKEND = 'http://localhost:8000/api/v1';
const PROD_API_BASE = 'https://api.srv1324425.hstgr.cloud/api/v1';

function getApiBaseUrl() {
  if (typeof window === 'undefined' || !window.location || !window.location.origin) {
    return LOCAL_BACKEND;
  }
  const origin = window.location.origin;
  if (/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(origin)) {
    return LOCAL_BACKEND;
  }
  // En prod sur srv1324425 : utiliser le même domaine (/api/v1) pour éviter CORS (Nginx proxy)
  if (/^https?:\/\/(www\.)?srv1324425\.hstgr\.cloud$/i.test(origin)) {
    return origin.replace(/\/$/, '') + '/api/v1';
  }
  if (/^https?:\/\/(www\.)?mobility-health\.ittechmed\.com$/i.test(origin)) {
    return origin.replace(/\/$/, '') + '/api/v1';
  }
  return PROD_API_BASE;
}

const API_BASE_URL = getApiBaseUrl();
// Exposer globalement pour utilisation dans d'autres scripts
window.API_BASE_URL = API_BASE_URL;

/**
 * WebSocket SOS (chemin racine du backend FastAPI : /ws/sos, pas sous /api/v1).
 * En prod sur le même hôte que le HTML : Nginx doit avoir un bloc `location /ws/` avec Upgrade
 * (voir deploy/nginx/frontend-with-api-proxy.conf). Sinon la console affiche « WebSocket connection failed ».
 *
 * Secours sans toucher au HTML : définir avant chargement de api.js, par ex. :
 *   window.MH_SOS_WS_ORIGIN = 'https://api.srv1324425.hstgr.cloud';
 * (sous-domaine où /ws/ est déjà proxyfié vers le port 8000).
 */
function getSosWebSocketUrl(token) {
  const q = token ? `?token=${encodeURIComponent(token)}` : '';
  const override =
    typeof window !== 'undefined' && window.MH_SOS_WS_ORIGIN
      ? String(window.MH_SOS_WS_ORIGIN).trim()
      : '';
  const base = override || (typeof window !== 'undefined' && window.API_BASE_URL) || getApiBaseUrl();
  try {
    const u = new URL(base);
    const scheme = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${scheme}//${u.host}/ws/sos${q}`;
  } catch {
    return `ws://localhost:8000/ws/sos${q}`;
  }
}
window.getSosWebSocketUrl = getSosWebSocketUrl;

const ACCESS_TOKEN_STORAGE_KEY = 'access_token';
const tokenWarningState = {
    quotes: false,
    bearerPrefix: false,
    invalid: false,
};

function sanitizeAccessToken(rawToken) {
    if (rawToken === null || rawToken === undefined) {
        return null;
    }
    let token = String(rawToken).trim();
    if (!token) {
        return null;
    }
    const hasDoubleQuotes = token.startsWith('"') && token.endsWith('"');
    const hasSingleQuotes = token.startsWith("'") && token.endsWith("'");
    if (hasDoubleQuotes || hasSingleQuotes) {
        if (!tokenWarningState.quotes) {
            console.warn('🟠 Token détecté avec des guillemets. Nettoyage automatique appliqué.');
            tokenWarningState.quotes = true;
        }
        token = token.slice(1, -1).trim();
    }
    if (/^bearer\s+/i.test(token)) {
        if (!tokenWarningState.bearerPrefix) {
            console.warn('🟠 Token détecté avec le préfixe "Bearer". Il sera nettoyé automatiquement.');
            tokenWarningState.bearerPrefix = true;
        }
        token = token.replace(/^bearer\s+/i, '').trim();
    }
    if (!token || token.toLowerCase() === 'undefined' || token.toLowerCase() === 'null') {
        if (!tokenWarningState.invalid) {
            console.error('❌ Token invalide détecté dans localStorage. Une reconnexion est nécessaire.');
            tokenWarningState.invalid = true;
        }
        return null;
    }
    return token;
}

function persistAccessToken(rawToken, context = 'api') {
    const sanitized = sanitizeAccessToken(rawToken);
    if (!sanitized) {
        console.error(`Token d'accès invalide reçu (${context}). Veuillez vous reconnecter.`);
        localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
        return null;
    }
    localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, sanitized);
    return sanitized;
}

function getAccessTokenMeta() {
    const rawToken = localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
    if (!rawToken) {
        return { token: null, raw: null, mutated: false };
    }
    const sanitized = sanitizeAccessToken(rawToken);
    let mutated = false;
    if (sanitized && sanitized !== rawToken) {
        localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, sanitized);
        mutated = true;
    } else if (!sanitized) {
        localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
        mutated = true;
    }
    return { token: sanitized, raw: rawToken, mutated };
}

function getStoredAccessToken() {
    return getAccessTokenMeta().token;
}

function clearStoredTokens() {
    localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    localStorage.removeItem('refresh_token');
}

function buildAuthorizationHeader(token) {
    return `Bearer ${token}`;
}

window.MobilityAuth = window.MobilityAuth || {};
window.MobilityAuth.getAccessToken = getStoredAccessToken;
window.MobilityAuth.getAccessTokenMeta = getAccessTokenMeta;
window.MobilityAuth.setAccessToken = (token) => persistAccessToken(token, 'external');
window.MobilityAuth.clearTokens = clearStoredTokens;

// Variable pour éviter les boucles infinies de refresh
let isRefreshing = false;
let refreshPromise = null;

// Fonction pour rafraîchir le token d'accès
async function refreshAccessToken() {
    // Si un refresh est déjà en cours, retourner la promesse existante
    if (isRefreshing && refreshPromise) {
        return refreshPromise;
    }
    
    isRefreshing = true;
    refreshPromise = (async () => {
        try {
            const refreshToken = localStorage.getItem('refresh_token');
            if (!refreshToken) {
                throw new Error('Aucun refresh token disponible');
            }
            
            const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Erreur lors du rafraîchissement du token' }));
                throw new Error(errorData.detail || 'Erreur lors du rafraîchissement du token');
            }
            
            const data = await response.json();
            const updatedAccessToken = persistAccessToken(data.access_token, 'refresh');
            if (!updatedAccessToken) {
                throw new Error('Token d\'accès rafraîchi invalide');
            }
            
            if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
            }
            
            return updatedAccessToken;
        } catch (error) {
            // Si le refresh échoue, nettoyer les tokens et rediriger vers la page de connexion
            clearStoredTokens();
            localStorage.removeItem('user_id');
            localStorage.removeItem('user_role');
            localStorage.removeItem('user_name');
            
            // Rediriger vers la page de connexion si on n'est pas déjà dessus
            if (!window.location.pathname.includes('login.html')) {
                const currentPath = window.location.pathname;
                window.location.href = `login.html?redirect=${encodeURIComponent(currentPath)}`;
            }
            
            throw error;
        } finally {
            isRefreshing = false;
            refreshPromise = null;
        }
    })();
    
    return refreshPromise;
}

// Fonction utilitaire pour les appels API
async function apiCall(endpoint, options = {}) {
    // S'assurer que l'URL commence par / si ce n'est pas déjà le cas
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    let url = `${API_BASE_URL}${cleanEndpoint}`;
    if (url.startsWith('http://')) {
        url = url.replace('http://', 'https://');
    }
    const tokenInfo = window.MobilityAuth?.getAccessTokenMeta
        ? window.MobilityAuth.getAccessTokenMeta()
        : { token: localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY), raw: localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY), mutated: false };
    let token = tokenInfo.token;

    const isFormDataBody = typeof FormData !== 'undefined' && (options?.body instanceof FormData);
    const defaultHeaders = isFormDataBody
        ? {}
        : {
            'Content-Type': 'application/json',
        };
    
    const mergedHeaders = {
        ...defaultHeaders,
        ...(options.headers || {}),
    };
    
    if (token && !mergedHeaders['Authorization']) {
        mergedHeaders['Authorization'] = buildAuthorizationHeader(token);
    } else if (mergedHeaders['Authorization'] && typeof mergedHeaders['Authorization'] === 'string') {
        // S'assurer que le header respecte bien le format Bearer <token>
        const headerValue = mergedHeaders['Authorization'].trim();
        if (!/^Bearer\s+/i.test(headerValue) && token) {
            mergedHeaders['Authorization'] = buildAuthorizationHeader(token);
        }
    }
    
    const config = {
        ...options,
        headers: mergedHeaders,
        // Empêcher les redirections automatiques qui pourraient causer des problèmes Mixed Content
        redirect: 'follow', // Suivre les redirections mais seulement si elles sont HTTPS
    };

    try {
        if (url.startsWith('http://')) {
            url = url.replace('http://', 'https://');
        }
        // Log de la requête pour le débogage
        const authHeaderValue = config.headers?.Authorization;
        const authHeaderPreview = authHeaderValue
            ? `${authHeaderValue.split(' ')[0]} ${(authHeaderValue.split(' ')[1] || '').slice(0, 8)}...`
            : 'absent';
        console.log('📤 Requête API:', {
            method: config.method || 'GET',
            url: url,
            hasToken: !!token,
            tokenSanitized: tokenInfo.mutated,
            authHeaderPresent: !!authHeaderValue,
            authHeaderPreview,
            headers: Object.keys(config.headers || {})
        });
        const isLocalhost = url.includes('localhost') || url.includes('127.0.0.1');
        if (!isLocalhost && !url.startsWith('https://')) {
            throw new Error(`URL non sécurisée détectée: ${url}. En production, toutes les requêtes doivent utiliser HTTPS.`);
        }
        const timeoutMs = options.timeoutMs != null ? options.timeoutMs : 30000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        let response;
        try {
            response = await fetch(url, {
                ...config,
                signal: controller.signal
            });
        } finally {
            clearTimeout(timeoutId);
        }
        
        // Log de la réponse
        console.log('📥 Réponse API:', {
            status: response.status,
            statusText: response.statusText,
            ok: response.ok,
            headers: Object.fromEntries(response.headers.entries())
        });
        
        // Vérifier si la réponse est JSON
        let data = null;
        const contentType = response.headers.get('content-type');
        if (response.status === 204 || response.status === 205) {
            data = null;
        } else if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            if (text) {
                throw new Error(`Réponse non-JSON: ${text.substring(0, 100)}`);
            }
        }
        
        // Si on reçoit une erreur 401 (Unauthorized), essayer de rafraîchir le token
        const detailStr = data?.detail ? String(data.detail) : '';
        const isAuthError = detailStr.includes('Could not validate credentials') ||
            detailStr.includes('Invalid') ||
            detailStr.includes('expired') ||
            detailStr.includes('Not authenticated');
        if (response.status === 401 && token && isAuthError) {
            try {
                const newToken = await refreshAccessToken();
                config.headers['Authorization'] = `Bearer ${newToken}`;
                response = await fetch(url, config);
                if (response.headers.get('content-type') && response.headers.get('content-type').includes('application/json')) {
                    data = await response.json();
                } else {
                    const text = await response.text();
                    throw new Error(`Réponse non-JSON: ${text.substring(0, 100)}`);
                }
            } catch (refreshError) {
                throw refreshError;
            }
        }
        
        if (!response.ok) {
            let message = data?.detail || data?.message || `Erreur HTTP: ${response.status} ${response.statusText}`;
            // Format 422 validation errors (FastAPI returns detail + optional message)
            if (response.status === 422) {
                if (typeof data?.message === 'string' && data.message) {
                    message = data.message;
                } else if (Array.isArray(data?.detail)) {
                    const parts = data.detail.map((e) => {
                        const field = Array.isArray(e?.loc) ? e.loc.slice(1).join('.') : '';
                        const msg = e?.msg ?? e?.message ?? '';
                        return field ? `${field}: ${msg}` : String(msg);
                    }).filter(Boolean);
                    message = parts.length ? parts.join(' ; ') : 'Erreur de validation (422)';
                }
            }
            if (typeof message === 'object' && message !== null) {
                message = JSON.stringify(message);
            }
            const error = new Error(typeof message === 'string' ? message : JSON.stringify(message));
            error.status = response.status;
            error.statusText = response.statusText;
            error.payload = data;
            error.detail = data?.detail || data?.message || null;
            console.error('❌ Erreur HTTP dans la réponse:');
            console.error('  Statut:', response.status, response.statusText);
            console.error('  URL:', url);
            console.error('  Message:', message);
            if (data) {
                console.error('  Données d\'erreur:', data);
            }
            throw error;
        }
        
        return data;
    } catch (error) {
        // Améliorer les messages d'erreur avec diagnostics détaillés
        console.error('❌ Erreur API capturée:');
        console.error('  URL:', url);
        console.error('  Méthode:', config.method || 'GET');
        console.error('  Nom de l\'erreur:', error.name);
        console.error('  Message:', error.message);
        if (error.status) {
            console.error('  Statut HTTP:', error.status);
        }
        if (error.statusText) {
            console.error('  Statut texte:', error.statusText);
        }
        if (error.payload) {
            console.error('  Payload d\'erreur:', error.payload);
        }
        if (error.detail) {
            console.error('  Détail:', error.detail);
        }
        if (error.stack) {
            console.error('  Stack:', error.stack);
        }
        console.error('  Objet d\'erreur complet:', error);
        
        // Gérer les erreurs de timeout et de réseau
        if (error.name === 'AbortError' || (error.name === 'TypeError' && (error.message === 'Failed to fetch' || error.message.includes('fetch')))) {
            if (error.name === 'AbortError') {
                console.error('⏱️  Timeout: La requête a pris plus de 30 secondes');
            }
            // Diagnostic détaillé
            const meta = window.MobilityAuth?.getAccessTokenMeta
                ? window.MobilityAuth.getAccessTokenMeta()
                : { token: localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY), raw: localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY), mutated: false };
            const token = meta.token;
            const rawToken = meta.raw;
            const hasToken = !!token;
            const tokenPreview = token ? token.substring(0, 20) + '...' : 'Aucun token';
            const tokenStoredWithQuotes = !!rawToken && /^["'].*["']$/.test(rawToken.trim());
            const tokenStoredWithBearer = !!rawToken && /^["']?\s*bearer\s+/i.test(rawToken.trim());
            const authHeaderValue = config.headers?.Authorization;
            const authHeaderLooksValid = typeof authHeaderValue === 'string' && /^Bearer\s+\S+/.test(authHeaderValue);
            const authHeaderPreview = authHeaderValue ? `${authHeaderValue.split(' ')[0]} ${(authHeaderValue.split(' ')[1] || '').slice(0, 10)}...` : 'absent';
            const userRole = localStorage.getItem('user_role') || 'inconnu';
            const needsAdminRole = endpoint.startsWith('/admin');
            
            console.group('🔍 Diagnostic de l\'erreur API');
            console.error('URL:', url);
            console.error('Origin:', window.location.origin);
            console.error('Token présent:', hasToken, tokenPreview);
            console.error('Authorization header final:', authHeaderPreview);
            
            if (hasToken) {
                if (!authHeaderLooksValid) {
                    console.warn('🟠 Le header Authorization est vide ou mal formé. Il doit être exactement "Authorization: Bearer <token>".');
                }
                if (tokenStoredWithQuotes) {
                    console.warn('🟠 Le token dans localStorage contient des guillemets. Il a été nettoyé automatiquement, mais reconnectez-vous si l\'erreur persiste.');
                }
                if (tokenStoredWithBearer) {
                    console.warn('🟠 Le token stocké inclut déjà le mot-clé "Bearer". Nous le retirons automatiquement pour éviter un header invalide.');
                }
            } else {
                console.error('❌ Aucun token disponible. Connectez-vous sur la page de connexion.');
            }
            
            if (needsAdminRole && userRole !== 'admin') {
                console.warn(`🟠 Cette route nécessite un token ADMIN. Rôle détecté: ${userRole || 'aucun'}.`);
            }
            console.error('Erreur:', error.message);
            console.error('Type d\'erreur:', error.name);
            console.error('Stack:', error.stack);
            
            // Instructions pour vérifier l'onglet Network
            console.warn('📋 Actions à effectuer:');
            console.warn('   1. Ouvrez l\'onglet Network (F12 → Network)');
            console.warn('   2. Rechargez la page');
            console.warn('   3. Cherchez la requête vers:', url);
            console.warn('   4. Vérifiez le statut HTTP et le message d\'erreur');
            console.warn('   5. Si la requête est en rouge, cliquez dessus pour voir les détails');
            
            // Tester la connectivité au backend
            fetch(`${API_BASE_URL.replace('/api/v1', '')}/health`, { method: 'GET' })
                .then(healthResponse => {
                    if (healthResponse.ok) {
                        console.warn('✅ Backend accessible sur /health');
                        console.warn('⚠️ Mais l\'appel API a échoué. Causes possibles:');
                        if (!hasToken) {
                            console.error('❌ PROBLÈME: Aucun token d\'authentification trouvé!');
                            console.error('   Solution: Connectez-vous sur la page de connexion.');
                        } else {
                            console.warn('   - Le navigateur bloque peut-être la requête (vérifiez l\'onglet Network)');
                            console.warn('   - Token peut être invalide, expiré, ou ne correspond pas au rôle requis');
                            console.warn('   - Endpoint peut ne pas exister');
                            console.warn('   - Problème de CORS (mais le preflight devrait passer)');
                        }
                    } else {
                        console.error('❌ Backend health check failed:', healthResponse.status);
                    }
                })
                .catch(healthError => {
                    console.error('❌ Impossible d\'atteindre le backend');
                    const baseUrl = API_BASE_URL.replace('/api/v1', '');
                    console.error(`   Vérifiez: ${baseUrl}/health devrait retourner {"status":"healthy"}`);
                    console.error('   Le backend est peut-être arrêté ou inaccessible.');
                });
            
            console.groupEnd();
            
            // Message d'erreur plus informatif
            if (error.name === 'AbortError') {
                const baseUrl = API_BASE_URL.replace('/api/v1', '');
                throw new Error(`La requête a pris trop de temps (timeout après 30 secondes). Le serveur sur ${baseUrl} est peut-être surchargé ou l'endpoint prend trop de temps à répondre.`);
            } else if (!hasToken) {
                throw new Error('Non authentifié. Veuillez vous connecter sur la page de connexion.');
            } else {
                const baseUrl = API_BASE_URL.replace('/api/v1', '');
                throw new Error(`Impossible de se connecter au serveur. Vérifiez que l'API est accessible sur ${baseUrl}. Ouvrez l'onglet Network (F12) pour voir les détails de la requête.`);
            }
        }
        console.error('Erreur API (catch final):');
        console.error('  URL:', url);
        console.error('  Message:', error.message);
        if (error.status) {
            console.error('  Statut HTTP:', error.status);
        }
        if (error.detail) {
            console.error('  Détail:', error.detail);
        }
        if (error.payload) {
            console.error('  Payload:', error.payload);
        }
        if (error.stack) {
            console.error('  Stack:', error.stack);
        }
        console.error('  Objet d\'erreur complet:', error);
        throw error;
    }
}

// API Questionnaires
const questionnairesAPI = {
    createShort: async (subscriptionId, reponses) => {
        return apiCall(`/subscriptions/${subscriptionId}/questionnaire/short`, {
            method: 'POST',
            body: JSON.stringify(reponses),
        });
    },
    
    createLong: async (subscriptionId, reponses) => {
        return apiCall(`/subscriptions/${subscriptionId}/questionnaire/long`, {
            method: 'POST',
            body: JSON.stringify(reponses),
        });
    },
    
    getStatus: async (questionnaireId) => {
        return apiCall(`/questionnaire/${questionnaireId}/status`);
    },
};

// API Attestations
const attestationsAPI = {
    getBySubscription: async (subscriptionId) => {
        return apiCall(`/subscriptions/${subscriptionId}/attestations`);
    },
    
    getMine: async () => {
        return apiCall(`/users/me/attestations`);
    },
    
    getWithUrl: async (attestationId) => {
        return apiCall(`/attestations/${attestationId}`);
    },
    
    getValidations: async (attestationId) => {
        return apiCall(`/attestations/${attestationId}/validations`);
    },
    
    createValidation: async (attestationId, data) => {
        return apiCall(`/attestations/${attestationId}/validations`, {
            method: 'POST',
            body: JSON.stringify({
                attestation_id: attestationId,
                ...data,
            }),
            timeoutMs: 90000, // 90s : génération attestation définitive + carte peut être lente
        });
    },
    
    getReviews: async (reviewType) => {
        return apiCall(`/attestations/reviews/${reviewType}`);
    },
};
window.attestationsAPI = attestationsAPI;

// API Souscriptions Production (agent de production - validation définitive)
const productionSubscriptionsAPI = {
    getPending: async () => {
        return apiCall('/admin/subscriptions/pending?limit=100');
    },
    getDossier: async (subscriptionId) => {
        return apiCall(`/admin/subscriptions/${subscriptionId}/dossier`);
    },
    approveFinal: async (subscriptionId, data) => {
        return apiCall(`/admin/subscriptions/${subscriptionId}/approve_final`, {
            method: 'POST',
            body: JSON.stringify(data),
            timeoutMs: 90000, // 90s : attestation définitive + e-carte peut être lente
        });
    },
};
window.productionSubscriptionsAPI = productionSubscriptionsAPI;

// Fonction pour afficher les messages
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Fonction pour afficher le chargement
function showLoading(container) {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.innerHTML = '<div class="spinner"></div>';
    container.innerHTML = '';
    container.appendChild(loadingDiv);
}

