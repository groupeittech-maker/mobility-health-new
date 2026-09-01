/**
 * Module JavaScript pour les statistiques avec serveur MCP
 * Intégration avec l'API Mobility Health
 */

// S'assurer que window existe
if (typeof window === 'undefined') {
    console.error('Stats.js: window n\'est pas défini');
}

const STATS_API_BASE = `${(typeof window !== 'undefined' && window.API_BASE_URL) || 'http://localhost:8000/api/v1'}/stats`;

// Utiliser l'endpoint public si l'utilisateur n'est pas connecté
const USE_PUBLIC_ENDPOINT = true; // Changez à false en production

console.log('Stats.js: Module chargé, STATS_API_BASE =', STATS_API_BASE);

/**
 * Interroge le serveur MCP avec une requête en langage naturel
 * @param {string} query - Requête en langage naturel
 * @param {number|null} userId - ID de l'utilisateur (optionnel, utilise l'utilisateur connecté par défaut)
 * @returns {Promise<Object>} Résultat avec graphiques et interprétations
 */
// Définir la fonction d'abord
async function queryStatistics(query, userId = null) {
    try {
        // Essayer différentes méthodes pour obtenir le token
        let token = null;
        if (typeof getAccessToken === 'function') {
            token = getAccessToken();
        } else if (typeof getStoredAccessToken === 'function') {
            token = getStoredAccessToken();
        } else if (typeof localStorage !== 'undefined') {
            token = localStorage.getItem('access_token');
        }
        
        // Ne pas exiger le token si on utilise l'endpoint public
        // Le token est optionnel pour l'endpoint public

        // Utiliser l'endpoint public si pas de token ou si configuré
        const endpoint = (USE_PUBLIC_ENDPOINT || !token) ? `${STATS_API_BASE}/query-public` : `${STATS_API_BASE}/query`;
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Ajouter le token seulement si disponible et si on utilise l'endpoint authentifié
        if (token && !USE_PUBLIC_ENDPOINT) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                query: query,
                user_id: userId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Erreur HTTP: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Erreur lors de la requête de statistiques:', error);
        throw error;
    }
}

/**
 * Récupère le schéma de la base de données
 * @returns {Promise<Object>} Schéma de la base de données
 */
// Exposer getDatabaseSchema
async function getDatabaseSchema() {
    try {
        const token = getAccessToken();
        if (!token) {
            throw new Error('Vous devez être connecté');
        }

        const response = await fetch(`${STATS_API_BASE}/schema`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Erreur lors de la récupération du schéma:', error);
        throw error;
    }
}

/**
 * Vérifie que le serveur MCP est accessible
 * @returns {Promise<Object>} Statut du serveur MCP
 */
// Exposer checkMCPHealth
async function checkMCPHealth() {
    try {
        const response = await fetch(`${STATS_API_BASE}/health`, {
            method: 'GET'
        });

        return await response.json();
    } catch (error) {
        console.error('Erreur lors de la vérification du serveur MCP:', error);
        return { status: 'error', error: error.message };
    }
}

/**
 * Affiche les graphiques Plotly dans un conteneur
 * @param {Array} charts - Liste des graphiques à afficher
 * @param {string} containerId - ID du conteneur HTML
 */
// Exposer displayCharts
function displayCharts(charts, containerId = 'charts-container') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Conteneur ${containerId} introuvable`);
        return;
    }

    // Vider le conteneur
    container.innerHTML = '';

    if (!charts || charts.length === 0) {
        container.innerHTML = '<p class="text-muted">Aucun graphique disponible pour cette requête.</p>';
        return;
    }

    // Charger Plotly si nécessaire
    if (typeof Plotly === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.plot.ly/plotly-2.27.0.min.js';
        script.onload = () => renderCharts(charts, container);
        script.onerror = () => {
            console.error('Erreur lors du chargement de Plotly');
            container.innerHTML = '<p class="text-danger">Erreur lors du chargement de la bibliothèque de graphiques</p>';
        };
        document.head.appendChild(script);
    } else {
        renderCharts(charts, container);
    }
}

/**
 * Rend les graphiques Plotly
 * @param {Array} charts - Liste des graphiques
 * @param {HTMLElement} container - Conteneur HTML
 */
function renderCharts(charts, container) {
    charts.forEach((chart, index) => {
        const chartDiv = document.createElement('div');
        chartDiv.id = `chart-${index}`;
        chartDiv.className = 'mb-4';
        chartDiv.style.minHeight = '400px';
        container.appendChild(chartDiv);

        try {
            const chartData = JSON.parse(chart.data);
            Plotly.newPlot(`chart-${index}`, chartData.data, chartData.layout, {
                responsive: true,
                displayModeBar: true
            });
        } catch (error) {
            console.error(`Erreur lors de l'affichage du graphique ${index}:`, error);
            chartDiv.innerHTML = `<p class="text-danger">Erreur lors de l'affichage du graphique</p>`;
        }
    });
}

/**
 * Affiche l'interprétation textuelle
 * @param {string} interpretationText - Texte d'interprétation
 * @param {string} containerId - ID du conteneur HTML
 */
// Exposer displayInterpretation
function displayInterpretation(interpretationText, containerId = 'interpretation-container') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Conteneur ${containerId} introuvable`);
        return;
    }

    if (!interpretationText) {
        container.innerHTML = '<p class="text-muted">Aucune interprétation disponible.</p>';
        return;
    }

    // Formater le texte (remplacer les sauts de ligne)
    const formattedText = interpretationText.replace(/\n/g, '<br>');
    container.innerHTML = `<div class="alert alert-info">${formattedText}</div>`;
}

/**
 * Affiche le résumé statistique
 * @param {Object} summary - Résumé statistique
 * @param {string} containerId - ID du conteneur HTML
 */
// Exposer displaySummary
function displaySummary(summary, containerId = 'summary-container') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Conteneur ${containerId} introuvable`);
        return;
    }

    if (!summary || Object.keys(summary).length === 0) {
        container.innerHTML = '';
        return;
    }

    let html = '<div class="row">';
    for (const [key, value] of Object.entries(summary)) {
        const displayValue = typeof value === 'object' && value.avg !== undefined 
            ? value.avg.toFixed(2) 
            : typeof value === 'object' && value.sum !== undefined
            ? value.sum.toFixed(0)
            : value;
        
        html += `
            <div class="col-md-3 mb-3">
                <div class="card">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">${key.replace(/_/g, ' ').toUpperCase()}</h6>
                        <h4 class="card-title">${displayValue}</h4>
                    </div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    container.innerHTML = html;
}

/**
 * Fonction utilitaire pour obtenir le token d'accès
 * @returns {string|null} Token d'accès
 */
function getAccessToken() {
    // Utiliser la fonction de api.js si disponible
    if (typeof getStoredAccessToken === 'function') {
        return getStoredAccessToken();
    }
    // Sinon, récupérer depuis localStorage
    return localStorage.getItem('access_token');
}

// Exposer les fonctions globalement - FORCER l'exposition immédiatement
(function exposeFunctions() {
    'use strict';
    try {
        if (typeof window === 'undefined') {
            console.error('Stats.js: window n\'est pas défini');
            return;
        }
        
        // FORCER l'assignation - écraser toute version précédente
        window.queryStatistics = queryStatistics;
        window.getDatabaseSchema = getDatabaseSchema;
        window.checkMCPHealth = checkMCPHealth;
        window.displayCharts = displayCharts;
        window.displayInterpretation = displayInterpretation;
        window.displaySummary = displaySummary;
        
        // Vérification immédiate
        const exposed = {
            queryStatistics: typeof window.queryStatistics,
            checkMCPHealth: typeof window.checkMCPHealth,
            displayCharts: typeof window.displayCharts,
            displayInterpretation: typeof window.displayInterpretation,
            displaySummary: typeof window.displaySummary
        };
        
        const allOk = Object.values(exposed).every(type => type === 'function');
        
        if (allOk) {
            console.log('✅ Stats.js: Toutes les fonctions exposées avec succès:', exposed);
        } else {
            console.error('❌ Stats.js: Certaines fonctions ne sont pas de type function:', exposed);
        }
    } catch (error) {
        console.error('❌ Stats.js: Erreur lors de l\'exposition des fonctions:', error);
        // En cas d'erreur, essayer quand même d'exposer les fonctions
        try {
            if (typeof window !== 'undefined') {
                window.queryStatistics = queryStatistics;
                window.checkMCPHealth = checkMCPHealth;
                window.displayCharts = displayCharts;
                window.displayInterpretation = displayInterpretation;
                window.displaySummary = displaySummary;
            }
        } catch (e) {
            console.error('❌ Stats.js: Impossible d\'exposer les fonctions:', e);
        }
    }
})();

