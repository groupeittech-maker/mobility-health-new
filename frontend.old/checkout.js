/**
 * Service de checkout pour l'intégration avec le provider de paiement simulé
 */

class CheckoutService {
    constructor(apiBaseUrl = 'http://localhost:8000/api/v1') {
        this.apiBaseUrl = apiBaseUrl;
    }

    /**
     * Initialiser un paiement
     * @param {number} subscriptionId - ID de la souscription
     * @param {number} amount - Montant du paiement
     * @param {string} token - Token d'authentification
     * @returns {Promise<Object>} Réponse avec payment_id et payment_url
     */
    async initiatePayment(subscriptionId, amount, token) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/payments/initiate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    subscription_id: subscriptionId,
                    amount: amount,
                    payment_type: 'carte_bancaire'
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to initiate payment');
            }

            return await response.json();
        } catch (error) {
            console.error('Error initiating payment:', error);
            throw error;
        }
    }

    /**
     * Obtenir le statut d'un paiement
     * @param {number} paymentId - ID du paiement
     * @param {string} token - Token d'authentification
     * @returns {Promise<Object>} Statut du paiement
     */
    async getPaymentStatus(paymentId, token) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/payments/${paymentId}/status`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to get payment status');
            }

            return await response.json();
        } catch (error) {
            console.error('Error getting payment status:', error);
            throw error;
        }
    }

    /**
     * Simuler un paiement (pour le provider simulé)
     * @param {number} paymentId - ID du paiement
     * @param {Object} cardData - Données de la carte
     * @returns {Promise<Object>} Résultat du paiement
     */
    async simulatePayment(paymentId, cardData) {
        // Simuler un délai de traitement
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Simuler une validation de carte
        // En production, cela appellerait le vrai provider
        const cardNumber = cardData.cardNumber.replace(/\s/g, '');
        
        // Simuler un échec pour certaines cartes
        if (cardNumber.endsWith('0000')) {
            return {
                success: false,
                status: 'failed',
                message: 'Carte refusée'
            };
        }

        // Simuler un succès
        return {
            success: true,
            status: 'success',
            external_reference: `EXT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        };
    }

    /**
     * Rediriger vers la page de checkout
     * @param {number} paymentId - ID du paiement
     * @param {string} token - Token de transaction
     * @param {number} amount - Montant
     * @param {number} subscriptionId - ID de la souscription
     */
    redirectToCheckout(paymentId, token, amount, subscriptionId) {
        const checkoutUrl = `/checkout.html?payment_id=${paymentId}&token=${token}&amount=${amount}&subscription_id=${subscriptionId}&api_url=${this.apiBaseUrl}`;
        window.location.href = checkoutUrl;
    }
}

// Export pour utilisation dans d'autres fichiers
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CheckoutService;
}




