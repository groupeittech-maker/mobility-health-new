// Script pour la page d'accueil

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getSafeAccessToken() {
    return window.MobilityAuth?.getAccessToken
        ? window.MobilityAuth.getAccessToken()
        : localStorage.getItem('access_token');
}

// Vérifier l'authentification au chargement
document.addEventListener('DOMContentLoaded', async function() {
    await checkAuthStatus();
    await loadProducts();
    setupCalculator();
    setupSmoothScroll();
});

// Vérifier le statut d'authentification
async function checkAuthStatus() {
    const token = getSafeAccessToken();
    const loginLink = document.getElementById('login-link');
    const userInfo = document.getElementById('user-info');
    const userName = document.getElementById('user-name');
    
    if (token) {
        try {
            const user = await validateAuth();
            if (user) {
                loginLink.style.display = 'none';
                userInfo.style.display = 'inline';
                const name = localStorage.getItem('user_name') || 'Utilisateur';
                userName.textContent = name;
                var productionDocsLink = document.getElementById('production-docs-link');
                if (productionDocsLink) {
                    var role = localStorage.getItem('user_role') || '';
                    productionDocsLink.style.display = (role === 'production_agent' || role === 'admin') ? 'inline' : 'none';
                }
            }
        } catch (error) {
            // Token invalide, afficher le lien de connexion
            loginLink.style.display = 'inline';
            userInfo.style.display = 'none';
        }
    } else {
        loginLink.style.display = 'inline';
        userInfo.style.display = 'none';
    }
}

// Charger les produits
async function loadProducts() {
    const container = document.getElementById('products-container');
    const loading = document.getElementById('products-loading');
    const error = document.getElementById('products-error');
    
    try {
        const products = await apiCall('/products?est_actif=true&limit=6');
        
        if (products.length === 0) {
            container.innerHTML = '<p style="text-align: center; padding: 2rem;">Aucun produit disponible pour le moment.</p>';
            container.style.display = 'block';
            loading.style.display = 'none';
            return;
        }
        
        let html = '';
        products.forEach(product => {
            html += `
                <div class="product-card">
                    <div class="product-header">
                        <div class="product-code">${product.code}</div>
                        <h3 class="product-name">${product.nom}</h3>
                    </div>
                    <p class="product-description">${product.description || 'Protection complète pour vos voyages'}</p>
                    <div class="product-price">${parseFloat(product.cout).toFixed(2)} €</div>
                    ${product.garanties ? (() => {
                        let garantiesList = [];
                        try {
                            if (Array.isArray(product.garanties)) {
                                garantiesList = product.garanties;
                            } else if (typeof product.garanties === 'string') {
                                garantiesList = JSON.parse(product.garanties);
                            } else if (product.garanties && typeof product.garanties === 'object') {
                                garantiesList = Object.values(product.garanties);
                            }
                        } catch (e) {
                            console.warn('Erreur lors du parsing des garanties:', e);
                            garantiesList = [];
                        }
                        if (garantiesList.length > 0) {
                            const garantiesDisplay = garantiesList.slice(0, 3).map(g => {
                                if (typeof g === 'string') return escapeHtml(g);
                                if (g && typeof g === 'object') {
                                    const text = g.nom || g.name || g.libelle || g.titre || JSON.stringify(g);
                                    return escapeHtml(String(text));
                                }
                                return escapeHtml(String(g));
                            });
                            return `
                                <ul class="product-features">
                                    ${garantiesDisplay.map(g => `<li>${g}</li>`).join('')}
                                </ul>
                            `;
                        }
                        return '';
                    })() : ''}
                    <div class="product-actions">
                        <a href="product-detail.html?id=${product.id}" class="btn btn-secondary">En savoir plus</a>
                        <a href="subscription-start.html?product_id=${product.id}" class="btn btn-primary">Souscrire</a>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        container.style.display = 'grid';
        loading.style.display = 'none';
    } catch (error) {
        console.error('Erreur lors du chargement des produits:', error);
        loading.style.display = 'none';
        error.style.display = 'block';
    }
}

// Configuration du calculateur de tarif
function setupCalculator() {
    const form = document.getElementById('quick-calc-form');
    const result = document.getElementById('calc-result');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const destination = document.getElementById('calc-destination').value;
        const duration = parseInt(document.getElementById('calc-duration').value);
        const participants = parseInt(document.getElementById('calc-participants').value);
        const age = parseInt(document.getElementById('calc-age').value);
        
        // Calcul simplifié du tarif
        // En production, cela devrait appeler un endpoint API dédié
        const basePrice = 50; // Prix de base
        const destinationMultiplier = getDestinationMultiplier(destination);
        const durationMultiplier = Math.max(1, duration / 30); // Multiplicateur basé sur la durée
        const ageMultiplier = getAgeMultiplier(age);
        const participantsMultiplier = participants;
        
        const estimatedPrice = basePrice * destinationMultiplier * durationMultiplier * ageMultiplier * participantsMultiplier;
        
        document.getElementById('estimated-price').textContent = estimatedPrice.toFixed(2);
        result.style.display = 'block';
        
        // Scroll vers le résultat
        result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
}

// Multiplicateur selon la destination
function getDestinationMultiplier(destination) {
    const destinationLower = destination.toLowerCase();
    
    // Europe
    if (destinationLower.includes('france') || 
        destinationLower.includes('espagne') || 
        destinationLower.includes('italie') ||
        destinationLower.includes('allemagne')) {
        return 1.0;
    }
    
    // Amérique du Nord
    if (destinationLower.includes('usa') || 
        destinationLower.includes('états-unis') ||
        destinationLower.includes('canada')) {
        return 1.5;
    }
    
    // Asie
    if (destinationLower.includes('chine') || 
        destinationLower.includes('japon') ||
        destinationLower.includes('inde')) {
        return 1.3;
    }
    
    // Afrique
    if (destinationLower.includes('afrique')) {
        return 1.2;
    }
    
    // Par défaut
    return 1.1;
}

// Multiplicateur selon l'âge
function getAgeMultiplier(age) {
    if (age < 30) return 1.0;
    if (age < 40) return 1.1;
    if (age < 50) return 1.2;
    if (age < 60) return 1.4;
    if (age < 70) return 1.6;
    return 2.0;
}

// Configuration du défilement fluide
function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Fonction de validation d'authentification (utilise la fonction de auth.js)
async function validateAuth() {
    const token = getSafeAccessToken();
    
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
            return false;
        }
        
        const user = await response.json();
        if (!localStorage.getItem('user_name')) {
            localStorage.setItem('user_role', user.role);
            localStorage.setItem('user_id', user.id);
            localStorage.setItem('user_name', user.full_name || user.username);
        }
        
        return user;
    } catch (error) {
        console.error('Erreur de validation:', error);
        return false;
    }
}




