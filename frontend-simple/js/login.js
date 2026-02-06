// Fonction pour obtenir l'URL du dashboard selon le rôle
function getDashboardUrlForRole(role) {
    const roleMap = {
        'admin': 'admin-dashboard.html',
        'doctor': 'hospital-doctor.html',
        'hospital_admin': 'hospital-dashboard.html',
        'finance_manager': 'accounting-portal.html',
        'sos_operator': 'sos-dashboard.html',
        'medical_reviewer': 'inscriptions-review.html',
        'technical_reviewer': 'technical-review.html',
        'production_agent': 'production-review.html',
        'agent_comptable_mh': 'accounting-portal.html',
        'agent_comptable_assureur': 'assureur-accounting.html',
        'agent_comptable_hopital': 'hospital-dashboard.html',
        'agent_sinistre_mh': 'sinistre-invoices.html',
        'agent_sinistre_assureur': 'sos-dashboard.html',
        'agent_reception_hopital': 'hospital-reception.html',
        'medecin_referent_mh': 'medical-review.html',
        'medecin_hopital': 'hospital-doctor.html',
        'user': 'user-dashboard.html' // Les utilisateurs vont au tableau de bord utilisateur
    };
    return roleMap[role] || 'index.html';
}

document.addEventListener('DOMContentLoaded', async function() {
    const form = document.getElementById('loginForm');
    const loginBtn = document.getElementById('loginBtn');
    const passwordInput = document.getElementById('password');
    const togglePasswordBtn = document.getElementById('togglePassword');
    
    // Fonction pour afficher/masquer le mot de passe
    if (togglePasswordBtn && passwordInput) {
        togglePasswordBtn.addEventListener('click', function() {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                togglePasswordBtn.textContent = '🙈';
                togglePasswordBtn.title = 'Masquer le mot de passe';
            } else {
                passwordInput.type = 'password';
                togglePasswordBtn.textContent = '👁️';
                togglePasswordBtn.title = 'Afficher le mot de passe';
            }
        });
    }
    
    // Nettoyer les paramètres sensibles de l'URL (username, password) immédiatement
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('username') || urlParams.has('password')) {
        // Pré-remplir les champs si les paramètres sont présents (pour faciliter le test)
        const usernameParam = urlParams.get('username');
        const passwordParam = urlParams.get('password');
        if (usernameParam) {
            document.getElementById('username').value = usernameParam;
        }
        if (passwordParam) {
            document.getElementById('password').value = passwordParam;
        }
        
        // Nettoyer l'URL des paramètres sensibles immédiatement
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
    }
    
    // Afficher les messages de succès si présents dans l'URL
    if (urlParams.get('registered') === '1') {
        const successMessage = document.getElementById('registrationSuccess');
        if (successMessage) {
            successMessage.textContent = 'Inscription réussie ! Vous pouvez maintenant vous connecter.';
            successMessage.style.display = 'block';
            setTimeout(() => {
                successMessage.style.display = 'none';
            }, 5000);
        }
    }
    if (urlParams.get('verified') === '1') {
        const successMessage = document.getElementById('registrationSuccess');
        if (successMessage) {
            successMessage.textContent = 'Email vérifié avec succès ! Vous pouvez maintenant vous connecter.';
            successMessage.style.display = 'block';
            successMessage.style.backgroundColor = '#d4edda';
            successMessage.style.borderColor = '#c3e6cb';
            successMessage.style.color = '#155724';
            setTimeout(() => {
                successMessage.style.display = 'none';
            }, 5000);
        }
    }
    if (urlParams.get('inscription_pending') === '1') {
        const successMessage = document.getElementById('registrationSuccess');
        if (successMessage) {
            successMessage.textContent = 'Votre inscription est en cours de validation par le médecin MH. Vous recevrez un email lorsque votre compte sera activé.';
            successMessage.style.display = 'block';
            successMessage.style.backgroundColor = '#cce5ff';
            successMessage.style.borderColor = '#b8daff';
            successMessage.style.color = '#004085';
            setTimeout(() => {
                successMessage.style.display = 'none';
            }, 8000);
        }
    }
    if (urlParams.get('password_reset') === '1') {
        const successMessage = document.getElementById('registrationSuccess');
        if (successMessage) {
            successMessage.textContent = 'Mot de passe réinitialisé avec succès ! Vous pouvez maintenant vous connecter.';
            successMessage.style.display = 'block';
            successMessage.style.backgroundColor = '#d4edda';
            successMessage.style.borderColor = '#c3e6cb';
            successMessage.style.color = '#155724';
            setTimeout(() => {
                successMessage.style.display = 'none';
            }, 5000);
        }
    }
    
    // Vérifier si déjà connecté avec un token valide
    const existingToken = window.MobilityAuth?.getAccessToken
        ? window.MobilityAuth.getAccessToken()
        : localStorage.getItem('access_token');
    if (existingToken) {
        try {
<<<<<<< HEAD
            const apiUrl = window.API_BASE_URL || (window.location && window.location.origin ? window.location.origin + '/api/v1' : 'https://srv1324425.hstgr.cloud/api/v1');
=======
            const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
            const userResponse = await fetch(`${apiUrl}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${existingToken}`
                }
            });
            
            if (userResponse.ok) {
                // Token valide, récupérer le rôle et rediriger vers le dashboard approprié
                const user = await userResponse.json();
                const userRole = user.role || localStorage.getItem('user_role');
                if (userRole) {
                    localStorage.setItem('user_role', userRole);
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
                    if (Object.prototype.hasOwnProperty.call(user, 'hospital_nom') && user.hospital_nom) {
                        localStorage.setItem('hospital_name', user.hospital_nom);
                    }
                    const redirectUrl = getDashboardUrlForRole(userRole);
                    window.location.href = redirectUrl;
                } else {
                    window.location.href = 'admin-dashboard.html';
                }
                return;
            } else {
                // Token invalide, le supprimer
                if (window.MobilityAuth?.clearTokens) {
                    window.MobilityAuth.clearTokens();
                } else {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                }
                localStorage.removeItem('user_role');
                localStorage.removeItem('user_id');
                localStorage.removeItem('user_name');
            }
        } catch (error) {
            // Erreur réseau, supprimer le token et continuer
            if (window.MobilityAuth?.clearTokens) {
                window.MobilityAuth.clearTokens();
            } else {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
            }
            localStorage.removeItem('user_role');
            localStorage.removeItem('user_id');
            localStorage.removeItem('user_name');
        }
    }
    
    // Gestion du lien "Mot de passe oublié"
    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            if (username) {
                window.location.href = `reset-password.html?username=${encodeURIComponent(username)}`;
            } else {
                window.location.href = 'reset-password.html';
            }
        });
    }
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // S'assurer que l'URL est propre avant de soumettre
        if (window.location.search.includes('username') || window.location.search.includes('password')) {
            window.history.replaceState({}, document.title, window.location.pathname);
        }
        
        loginBtn.disabled = true;
        loginBtn.textContent = 'Connexion...';
        
        const formData = new FormData(form);
        const username = formData.get('username');
        const password = formData.get('password');
        
        try {
            // Utiliser FormData pour OAuth2PasswordRequestForm
            const loginFormData = new FormData();
            loginFormData.append('username', username);
            loginFormData.append('password', password);
            
<<<<<<< HEAD
            const apiUrl = window.API_BASE_URL || (window.location && window.location.origin ? window.location.origin + '/api/v1' : 'https://srv1324425.hstgr.cloud/api/v1');
=======
            const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
            const loginUrl = `${apiUrl}/auth/login`;
            
            console.log('Tentative de connexion à:', loginUrl);
            
            const response = await fetch(loginUrl, {
                method: 'POST',
                body: loginFormData,
            }).catch(error => {
                console.error('Erreur réseau lors de la requête:', error);
<<<<<<< HEAD
                const baseUrl = apiUrl.replace('/api/v1', '');
                throw new Error(`Impossible de se connecter au serveur. Vérifiez que l'API est accessible sur ${baseUrl}. Erreur: ${error.message}`);
=======
                console.error('URL tentée:', loginUrl);
                console.error('Type d\'erreur:', error.name);
                throw new Error(`Impossible de se connecter au serveur. Vérifiez que l'API est accessible sur https://mobility-health.ittechmed.com. Erreur: ${error.message}`);
            });
            
            console.log('Réponse reçue:', {
                status: response.status,
                statusText: response.statusText,
                ok: response.ok,
                headers: Object.fromEntries(response.headers.entries())
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `Erreur HTTP ${response.status}` }));
                const errorMessage = errorData.detail || `Erreur HTTP ${response.status}`;
                
                // Vérifier si c'est une erreur d'email non vérifié
                if (response.status === 403 && 
                    (errorMessage.toLowerCase().includes('email') && 
                     (errorMessage.toLowerCase().includes('vérifié') || 
                      errorMessage.toLowerCase().includes('verifie') || 
                      errorMessage.toLowerCase().includes('verified')))) {
                    // Proposer de rediriger vers la vérification si l'identifiant est un email
                    if (username.includes('@')) {
                        const shouldVerify = confirm('Votre email n\'a pas été vérifié. Voulez-vous être redirigé vers la page de vérification ?');
                        if (shouldVerify) {
                            window.location.href = `verify-email.html?email=${encodeURIComponent(username)}`;
                            return;
                        }
                    } else {
                        throw new Error('Votre email n\'a pas été vérifié. Veuillez vérifier votre email avant de vous connecter.');
                    }
                }
                
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            
            if (!data.access_token) {
                throw new Error('Token d\'accès non reçu');
            }
            
            // Stocker les tokens
            const persistedAccessToken = window.MobilityAuth?.setAccessToken
                ? window.MobilityAuth.setAccessToken(data.access_token)
                : data.access_token;
            if (!persistedAccessToken) {
                throw new Error('Token d\'accès invalide retourné par l\'API');
            }
            if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
            }
            
            // Récupérer les infos utilisateur
<<<<<<< HEAD
            const apiUrl2 = window.API_BASE_URL || (window.location && window.location.origin ? window.location.origin + '/api/v1' : 'https://srv1324425.hstgr.cloud/api/v1');
=======
            const apiUrl2 = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
            const userResponse = await fetch(`${apiUrl2}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${persistedAccessToken}`
                }
            });
            
            if (userResponse.ok) {
                const user = await userResponse.json();
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
                if (Object.prototype.hasOwnProperty.call(user, 'hospital_nom') && user.hospital_nom) {
                    localStorage.setItem('hospital_name', user.hospital_nom);
                }
                
                // Nettoyer l'URL avant la redirection
                window.history.replaceState({}, document.title, window.location.pathname);
                
                // Rediriger vers le dashboard approprié selon le rôle
                const redirectUrl = getDashboardUrlForRole(user.role);
                showAlert('Connexion réussie!', 'success');
                
                // Attendre un peu plus pour que les données soient bien stockées
                setTimeout(() => {
                    window.location.replace(redirectUrl); // Utiliser replace au lieu de href pour éviter le retour arrière
                }, 500);
            } else {
                showAlert('Connexion réussie, mais impossible de récupérer les informations utilisateur', 'warning');
                // Rediriger vers l'accueil par défaut
                setTimeout(() => {
                    window.location.replace('index.html');
                }, 1000);
            }
            
        } catch (error) {
            console.error('Erreur de connexion:', error);
<<<<<<< HEAD
            showAlert(`Erreur: ${error.message}`, 'error');
=======
            console.error('Détails de l\'erreur:', {
                message: error.message,
                name: error.name,
                stack: error.stack
            });
            
            // Afficher un message d'erreur plus détaillé
            let errorMessage = error.message || 'Une erreur est survenue lors de la connexion';
            
            // Messages d'erreur plus clairs pour l'utilisateur
            if (errorMessage.includes('Failed to fetch') || errorMessage.includes('Impossible de se connecter au serveur')) {
                errorMessage = 'Impossible de se connecter au serveur. Vérifiez que l\'API est accessible sur https://mobility-health.ittechmed.com';
            } else if (errorMessage.includes('Incorrect username or password')) {
                errorMessage = 'Nom d\'utilisateur ou mot de passe incorrect';
            } else if (errorMessage.includes('User is inactive')) {
                errorMessage = 'Votre compte est désactivé. Contactez un administrateur';
            } else if (errorMessage.includes('Token')) {
                errorMessage = 'Erreur lors de la réception du token d\'authentification';
            }
            
            // Afficher l'alerte si la fonction existe
            if (typeof showAlert === 'function') {
                showAlert(errorMessage, 'error');
            } else {
                // Fallback si showAlert n'est pas disponible
                alert(`Erreur: ${errorMessage}`);
            }
            
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
            loginBtn.disabled = false;
            loginBtn.textContent = 'Se connecter';
        }
    });
});

