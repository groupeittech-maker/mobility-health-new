// Gestion de la vérification d'email
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('verifyEmailForm');
    const verifyBtn = document.getElementById('verifyBtn');
    const codeInput = document.getElementById('verification_code');
    const emailDisplay = document.getElementById('emailDisplay');
    const resendLink = document.getElementById('resendLink');
    const resendCooldown = document.getElementById('resendCooldown');
    
    // Récupérer l'email depuis l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const email = urlParams.get('email');
    
    if (!email) {
        showAlert('Email non fourni. Veuillez vous réinscrire.', 'error');
        setTimeout(() => {
            window.location.href = 'register.html';
        }, 2000);
        return;
    }
    
    // Afficher l'email
    emailDisplay.textContent = email;
    
    // Vérifier si déjà connecté
    const existingToken = window.MobilityAuth?.getAccessToken
        ? window.MobilityAuth.getAccessToken()
        : localStorage.getItem('access_token');
    if (existingToken) {
        // Rediriger vers le dashboard approprié
        window.location.href = 'index.html';
        return;
    }
    
    // Limiter l'input au format numérique uniquement
    codeInput.addEventListener('input', function(e) {
        e.target.value = e.target.value.replace(/[^0-9]/g, '');
    });
    
    // Gestion du cooldown pour le renvoi
    let cooldownSeconds = 0;
    let cooldownInterval = null;
    
    function startCooldown(seconds = 60) {
        cooldownSeconds = seconds;
        resendLink.classList.add('disabled');
        resendLink.style.pointerEvents = 'none';
        resendCooldown.style.display = 'inline';
        
        cooldownInterval = setInterval(() => {
            cooldownSeconds--;
            resendCooldown.textContent = `(${cooldownSeconds}s)`;
            
            if (cooldownSeconds <= 0) {
                clearInterval(cooldownInterval);
                resendLink.classList.remove('disabled');
                resendLink.style.pointerEvents = 'auto';
                resendCooldown.style.display = 'none';
            }
        }, 1000);
    }
    
    // Démarrer le cooldown initial
    startCooldown(60);
    
    // Soumission du formulaire
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const code = codeInput.value.trim();
        
        if (code.length !== 6) {
            showAlert('Le code doit contenir 6 chiffres', 'error');
            return;
        }
        
        verifyBtn.disabled = true;
        verifyBtn.textContent = 'Vérification en cours...';
        
        try {
            const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
            const response = await fetch(`${apiUrl}/auth/verify-email`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    code: code
                }),
            }).catch(error => {
                console.error('Erreur réseau lors de la requête:', error);
                throw new Error(`Impossible de se connecter au serveur. Vérifiez que l'API est accessible. Erreur: ${error.message}`);
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `Erreur HTTP ${response.status}` }));
                const errorMessage = errorData.detail || `Erreur HTTP ${response.status}`;
                console.error('Erreur de vérification:', errorMessage);
                
                // Vérifier si c'est une erreur de code invalide ou expiré
                if (errorMessage.toLowerCase().includes('invalid') || 
                    errorMessage.toLowerCase().includes('expiré') ||
                    errorMessage.toLowerCase().includes('expired')) {
                    showAlert('Code de vérification invalide ou expiré. Veuillez demander un nouveau code.', 'error');
                } else if (errorMessage.toLowerCase().includes('déjà vérifié') || 
                           errorMessage.toLowerCase().includes('already verified')) {
                    showAlert('Cet email est déjà vérifié. Vous pouvez vous connecter.', 'success');
                    setTimeout(() => {
                        window.location.href = 'login.html?verified=1';
                    }, 2000);
                    return;
                } else {
                    throw new Error(errorMessage);
                }
            } else {
                const result = await response.json();
                
                console.log('Email vérifié:', result);
                showAlert(result.message || 'Email vérifié. Votre inscription est en cours de validation par le médecin MH.', 'success');
                
                // Rediriger vers la page de connexion (inscription en attente de validation médecin MH)
                setTimeout(() => {
                    window.location.href = 'login.html?inscription_pending=1';
                }, 2000);
            }
            
        } catch (error) {
            console.error('Erreur de vérification:', error);
            showAlert(`Erreur: ${error.message}`, 'error');
            verifyBtn.disabled = false;
            verifyBtn.textContent = 'Vérifier';
        }
    });
    
    // Renvoyer le code
    resendLink.addEventListener('click', async function(e) {
        e.preventDefault();
        
        if (cooldownSeconds > 0 || resendLink.classList.contains('disabled')) {
            return;
        }
        
        resendLink.textContent = 'Envoi en cours...';
        resendLink.style.pointerEvents = 'none';
        
        try {
            const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
            const response = await fetch(`${apiUrl}/auth/resend-verification-code`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email
                }),
            }).catch(error => {
                console.error('Erreur réseau lors de la requête:', error);
                throw new Error(`Impossible de se connecter au serveur. Erreur: ${error.message}`);
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `Erreur HTTP ${response.status}` }));
                const errorMessage = errorData.detail || `Erreur HTTP ${response.status}`;
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            showAlert('Un nouveau code de vérification a été envoyé à votre email.', 'success');
            
            // Redémarrer le cooldown
            startCooldown(60);
            resendLink.textContent = 'Renvoyer le code';
            
        } catch (error) {
            console.error('Erreur lors du renvoi du code:', error);
            showAlert(`Erreur: ${error.message}`, 'error');
            resendLink.textContent = 'Renvoyer le code';
            resendLink.style.pointerEvents = 'auto';
        }
    });
});

