// Gestion de la réinitialisation du mot de passe
let currentStep = 1;
let resetEmail = '';
let resetToken = '';
let remainingTime = 600; // 10 minutes en secondes
let timerInterval = null;
let remainingAttempts = 5;

// Fonction pour changer d'étape
function goToStep(step) {
    console.log(`goToStep appelé avec step=${step}`);
    
    // Masquer toutes les étapes
    document.querySelectorAll('.step-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
    
    // Afficher l'étape demandée
    const stepElement = document.getElementById(`step${step}`);
    const stepIndicator = document.getElementById(`step${step}Indicator`);
    
    if (!stepElement) {
        console.error(`Élément step${step} non trouvé!`);
        return;
    }
    if (!stepIndicator) {
        console.error(`Indicateur step${step}Indicator non trouvé!`);
        return;
    }
    
    stepElement.classList.add('active');
    stepIndicator.classList.add('active');
    
    currentStep = step;
    console.log(`Passage à l'étape ${step} réussi`);
}

// Fonction pour formater le temps
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Fonction pour démarrer le timer
function startTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    
    timerInterval = setInterval(() => {
        if (remainingTime > 0) {
            remainingTime--;
            updateTimerDisplay();
        } else {
            clearInterval(timerInterval);
        }
    }, 1000);
    
    updateTimerDisplay();
}

// Fonction pour mettre à jour l'affichage du timer
function updateTimerDisplay() {
    const timerDisplay = document.getElementById('timerDisplay');
    const timerDisplayStep2 = document.getElementById('timerDisplayStep2');
    
    if (timerDisplay) {
        timerDisplay.textContent = `Temps restant : ${formatTime(remainingTime)}`;
        timerDisplay.className = remainingTime < 60 ? 'timer warning' : 'timer normal';
    }
    
    if (timerDisplayStep2) {
        timerDisplayStep2.textContent = `Temps restant : ${formatTime(remainingTime)}`;
        timerDisplayStep2.className = remainingTime < 60 ? 'timer warning' : 'timer normal';
    }
}

// Fonction pour masquer un email
function maskEmail(email) {
    const parts = email.split('@');
    if (parts.length === 2) {
        const local = parts[0];
        const domain = parts[1];
        const maskedLocal = local.length > 2 ? local.substring(0, 2) + '***' : '***';
        return `${maskedLocal}@${domain}`;
    }
    return '***@***';
}

// Vérification de la force du mot de passe
document.addEventListener('DOMContentLoaded', function() {
    const newPasswordInput = document.getElementById('new_password');
    const newPasswordConfirmInput = document.getElementById('new_password_confirm');
    const passwordStrength = document.getElementById('passwordStrength');
    const passwordMatch = document.getElementById('passwordMatch');
    
    // Étape 1: formulaire email
    const requestEmailForm = document.getElementById('requestEmailForm');
    const sendCodeBtn = document.getElementById('sendCodeBtn');

    if (requestEmailForm) {
        requestEmailForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const emailInput = document.getElementById('emailInput');
            const emailValue = emailInput.value.trim();
            if (!emailValue) {
                showAlert('Veuillez saisir votre email', 'error');
                return;
            }

            sendCodeBtn.disabled = true;
            sendCodeBtn.textContent = 'Vérification...';

            try {
                await handleEmailSubmission(emailValue);
            } catch (error) {
                console.error(error);
                showAlert(error.message || 'Erreur', 'error');
                sendCodeBtn.disabled = false;
                sendCodeBtn.textContent = 'Envoyer le code';
            }
        });
    }

    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            const password = newPasswordInput.value;
            const strength = checkPasswordStrength(password);
            passwordStrength.textContent = strength.text;
            passwordStrength.className = 'password-strength ' + strength.class;
        });
    }
    
    if (newPasswordConfirmInput) {
        newPasswordConfirmInput.addEventListener('input', function() {
            const password = newPasswordInput.value;
            const confirmPassword = newPasswordConfirmInput.value;
            
            if (confirmPassword.length === 0) {
                passwordMatch.textContent = '';
                return;
            }
            
            if (password === confirmPassword) {
                passwordMatch.textContent = '✓ Les mots de passe correspondent';
                passwordMatch.style.color = 'var(--success-color)';
            } else {
                passwordMatch.textContent = '✗ Les mots de passe ne correspondent pas';
                passwordMatch.style.color = 'var(--danger-color)';
            }
        });
    }
    
<<<<<<< HEAD
    // Limiter l'input du code aux chiffres uniquement
    const resetCodeInput = document.getElementById('reset_code');
    if (resetCodeInput) {
        resetCodeInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
=======
    // Étape 1: Demander la réinitialisation
    const requestResetForm = document.getElementById('requestResetForm');
    if (requestResetForm) {
        requestResetForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const email = document.getElementById('email').value;
            resetEmail = email;
            
            const btn = document.getElementById('requestResetBtn');
            btn.disabled = true;
            btn.textContent = 'Envoi en cours...';
            
            try {
                const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
                const response = await fetch(`${apiUrl}/auth/forgot-password`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email }),
                }).catch(error => {
                    throw new Error(`Impossible de se connecter au serveur. Erreur: ${error.message}`);
                });
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: 'Erreur lors de l\'envoi' }));
                    throw new Error(errorData.detail || 'Erreur lors de l\'envoi du code');
                }
                
                showAlert('Code de réinitialisation envoyé par email', 'success');
                goToStep(2);
            } catch (error) {
                console.error('Erreur:', error);
                showAlert(`Erreur: ${error.message}`, 'error');
                btn.disabled = false;
                btn.textContent = 'Envoyer le code';
            }
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
        });
    }
    
    // Étape 2: Vérifier le code
    const verifyCodeForm = document.getElementById('verifyCodeForm');
    if (verifyCodeForm) {
        verifyCodeForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const code = document.getElementById('reset_code').value;
            
            const btn = document.getElementById('verifyCodeBtn');
            btn.disabled = true;
            btn.textContent = 'Vérification...';
            
            try {
<<<<<<< HEAD
                const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
=======
                const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
                const response = await fetch(`${apiUrl}/auth/verify-reset-code`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email: resetEmail, code }),
                }).catch(error => {
                    throw new Error(`Impossible de se connecter au serveur. Erreur: ${error.message}`);
                });
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: 'Code invalide' }));
                    const errorMessage = errorData.detail || 'Code invalide';
                    
                    // Gérer les tentatives
                    if (errorMessage.includes('tentative')) {
                        const attemptsMatch = errorMessage.match(/(\d+) tentative/);
                        if (attemptsMatch) {
                            remainingAttempts = parseInt(attemptsMatch[1]);
                            const attemptsWarning = document.getElementById('attemptsWarning');
                            if (attemptsWarning) {
                                attemptsWarning.textContent = `Tentatives restantes : ${remainingAttempts}`;
                                attemptsWarning.style.display = 'block';
                            }
                        }
                    }
                    
                    // Gérer le blocage
                    if (errorMessage.includes('bloqué') || errorMessage.includes('2 heures') || response.status === 429) {
                        showAlert(errorMessage, 'error');
                        // Désactiver le formulaire
                        btn.disabled = true;
                        btn.textContent = 'Trop de tentatives - Bloqué';
                        return;
                    }
                    
                    throw new Error(errorMessage);
                }
                
                const data = await response.json();
                console.log('Réponse de vérification du code:', data);
                
                if (!data.token) {
                    throw new Error('Token non reçu du serveur. Veuillez réessayer.');
                }
                
                resetToken = data.token;
                console.log('Token stocké:', resetToken ? 'présent' : 'absent');
                
                showAlert('Code vérifié avec succès', 'success');
                clearInterval(timerInterval);
                goToStep(3);
            } catch (error) {
                console.error('Erreur:', error);
                showAlert(`Erreur: ${error.message}`, 'error');
                btn.disabled = false;
                btn.textContent = 'Vérifier le code';
            }
        });
    }
    
    // Étape 3: Réinitialiser le mot de passe
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Formulaire soumis, vérification des données...');
            console.log('resetEmail:', resetEmail);
            console.log('resetToken:', resetToken ? 'présent' : 'absent');
            
            const newPassword = document.getElementById('new_password').value;
            const newPasswordConfirm = document.getElementById('new_password_confirm').value;
            
            console.log('Mots de passe saisis:', { 
                password: newPassword ? 'présent (' + newPassword.length + ' caractères)' : 'vide',
                confirm: newPasswordConfirm ? 'présent' : 'vide'
            });
            
            if (newPassword !== newPasswordConfirm) {
                showAlert('Les mots de passe ne correspondent pas', 'error');
                return;
            }
            
            if (newPassword.length < 8) {
                showAlert('Le mot de passe doit contenir au moins 8 caractères', 'error');
                return;
            }
            
            const btn = document.getElementById('resetPasswordBtn');
            btn.disabled = true;
            btn.textContent = 'Réinitialisation...';
            
            // Vérifier que resetEmail et resetToken sont définis
            if (!resetEmail || !resetToken) {
                showAlert('Erreur: Veuillez d\'abord vérifier le code de réinitialisation', 'error');
                btn.disabled = false;
                btn.textContent = 'Réinitialiser le mot de passe';
                return;
            }
            
            try {
<<<<<<< HEAD
                const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
                console.log('Envoi de la requête de réinitialisation:', { email: resetEmail, token: resetToken ? 'présent' : 'absent' });
                
=======
                const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
                const response = await fetch(`${apiUrl}/auth/reset-password`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: resetEmail,
                        token: resetToken,
                        new_password: newPassword,
                    }),
                }).catch(error => {
                    throw new Error(`Impossible de se connecter au serveur. Erreur: ${error.message}`);
                });
                
                console.log('Réponse du serveur:', response.status, response.statusText);
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: 'Erreur lors de la réinitialisation' }));
                    console.error('Erreur du serveur:', errorData);
                    throw new Error(errorData.detail || 'Erreur lors de la réinitialisation');
                }
                
                const result = await response.json();
                console.log('Réinitialisation réussie:', result);
                
                showAlert('Mot de passe réinitialisé avec succès !', 'success');
                
                // Rediriger vers la page de connexion après 2 secondes
                setTimeout(() => {
                    window.location.href = 'login.html?password_reset=1';
                }, 2000);
            } catch (error) {
                console.error('Erreur complète:', error);
                showAlert(`Erreur: ${error.message}`, 'error');
                btn.disabled = false;
                btn.textContent = 'Réinitialiser le mot de passe';
            }
        });
    }
});

// Traitement de la soumission d'email (étape 1)
async function handleEmailSubmission(emailValue) {
    console.log('Vérification de l\'email:', emailValue);
    const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';

    // Vérifier si l'email existe et récupérer l'email masqué
    const response = await fetch(`${apiUrl}/auth/get-masked-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username_or_email: emailValue }),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur lors de la vérification' }));
        throw new Error(errorData.detail || 'Erreur lors de la vérification de l\'email');
    }

    const data = await response.json();
    console.log('Réponse get-masked-email:', data);
    
    const emailExists = data.exists || false;
    const actualEmail = data.email;

    if (!emailExists || !actualEmail) {
        throw new Error('Cet email n\'existe pas dans le système.');
    }

    // Sauvegarder l'email réel
    resetEmail = actualEmail;
    console.log('Email valide trouvé:', resetEmail);

    // Lancer l'envoi de code (qui passera automatiquement à l'étape 2)
    await sendResetCode();
}

// Fonction pour envoyer le code de réinitialisation
async function sendResetCode() {
    if (!resetEmail) {
        showAlert('Email non disponible', 'error');
        return;
    }
    
    const sendBtn = document.getElementById('sendCodeBtn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = 'Envoi en cours...';
    }
    
    try {
        const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
        const response = await fetch(`${apiUrl}/auth/forgot-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: resetEmail }),
        }).catch(error => {
            throw new Error(`Impossible de se connecter au serveur. Erreur: ${error.message}`);
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Erreur lors de l\'envoi' }));
            const errorMessage = errorData.detail || 'Erreur lors de l\'envoi du code';
            
            // Vérifier si c'est un blocage
            if (errorMessage.includes('bloqué') || errorMessage.includes('trop de tentatives') || response.status === 429) {
                showAlert(errorMessage, 'error');
                sendBtn.disabled = true;
                sendBtn.textContent = 'Trop de tentatives - Bloqué';
                return;
            }
            
            throw new Error(errorMessage);
        }
        
        const responseData = await response.json();
        
        // Vérifier si un code a déjà été envoyé
        if (responseData.code_already_sent) {
            showAlert('Un code a déjà été envoyé. Veuillez patienter.', 'warning');
            // Démarrer le timer même si le code était déjà envoyé
            remainingTime = 600;
            startTimer();
            document.getElementById('codeSentMessage').style.display = 'block';
            sendBtn.style.display = 'none';
            setTimeout(() => {
                goToStep(2);
            }, 1500);
            return;
        }
        
        showAlert('Code de réinitialisation envoyé par email', 'success');
        
        // Afficher le message de code envoyé
        const codeSentMessage = document.getElementById('codeSentMessage');
        if (codeSentMessage) {
            codeSentMessage.style.display = 'block';
        }
        if (sendBtn) {
            sendBtn.style.display = 'none';
        }
        
        // Démarrer le timer
        remainingTime = 600; // 10 minutes
        startTimer();
        
        // Mettre à jour l'affichage de l'email masqué pour l'étape 2
        const maskedEmailStep2 = document.getElementById('maskedEmailStep2');
        if (maskedEmailStep2) {
            maskedEmailStep2.textContent = maskEmail(resetEmail);
        }
        const maskedEmailDisplay = document.getElementById('maskedEmailDisplay');
        if (maskedEmailDisplay) {
            maskedEmailDisplay.textContent = `Envoyé à : ${maskEmail(resetEmail)}`;
        }
        
        console.log('Code envoyé avec succès, passage à l\'étape 2 dans 1.5s...');
        
        // Passer à l'étape 2 après un court délai
        setTimeout(() => {
            console.log('Passage à l\'étape 2 maintenant');
            goToStep(2);
        }, 1500);
    } catch (error) {
        console.error('Erreur:', error);
        showAlert(`Erreur: ${error.message}`, 'error');
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = 'Envoyer le code';
        }
    }
}

// Fonction pour vérifier la force du mot de passe
function checkPasswordStrength(password) {
    if (password.length === 0) {
        return { text: '', class: '' };
    }
    
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    if (strength <= 2) {
        return { text: 'Faible', class: 'weak' };
    } else if (strength <= 4) {
        return { text: 'Moyen', class: 'medium' };
    } else {
        return { text: 'Fort', class: 'strong' };
    }
}




