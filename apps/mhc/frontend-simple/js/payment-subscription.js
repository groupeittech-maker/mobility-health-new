function escapeHtmlPay(s) {
    if (s == null || s === '') return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

const fallbackCurrencyHelperPay = {
    getLocale: () => 'fr-FR',
    getCurrency: () => 'XOF',
    format: (value, options = {}) => {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) return '—';
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'XOF',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
            ...options,
        }).format(numeric);
    },
};
const currencyHelperPay = window.CurrencyHelper || fallbackCurrencyHelperPay;

function formatCurrencyPay(amount) {
    if (amount == null) return '—';
    try {
        return currencyHelperPay.format(amount, { maximumFractionDigits: 0 });
    } catch {
        return `${amount} ${currencyHelperPay.getCurrency ? currencyHelperPay.getCurrency() : 'XOF'}`;
    }
}

function showMessagePay(text, type) {
    const box = document.getElementById('paymentMessage');
    if (!box) return;
    box.innerHTML = text;
    box.className = `message ${type}`;
    box.style.display = 'block';
}

function showReviewNotice(text) {
    const box = document.getElementById('reviewNotice');
    if (!box) return;
    box.innerHTML = text;
    box.style.display = 'block';
}

function hideReviewNotice() {
    const box = document.getElementById('reviewNotice');
    if (box) box.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', async () => {
    const authenticated = await requireAuth();
    if (!authenticated) return;

    const params = new URLSearchParams(window.location.search);
    const subscriptionId = Number(params.get('subscription_id'));
    if (!subscriptionId) {
        showMessagePay('Aucun dossier sélectionné.', 'error');
        return;
    }

    const submitBtn = document.getElementById('submitDossierBtn');
    const checkBtn = document.getElementById('checkStatusBtn');
    const payBtn = document.getElementById('payNowBtn');
    const methodsBlock = document.getElementById('paymentMethodsBlock');
    const statusBox = document.getElementById('dossierStatus');

    let souscription = null;

    function renderSummary() {
        const produit = souscription.produit_assurance || {};
        const projet = souscription.projet_voyage || {};
        document.getElementById('productLabel').textContent =
            produit.nom || produit.libelle || `Produit #${souscription.produit_assurance_id}`;
        document.getElementById('priceLabel').textContent =
            formatCurrencyPay(souscription.prix_applique);
        document.getElementById('checkoutSummary').innerHTML = `
            <div class="summary-item"><span>N° souscription</span><strong>${escapeHtmlPay(souscription.numero_souscription || '#' + souscription.id)}</strong></div>
            <div class="summary-item"><span>Produit</span><strong>${escapeHtmlPay(produit.nom || '—')}</strong></div>
            <div class="summary-item"><span>Voyage</span><strong>${escapeHtmlPay(projet.titre || '—')}</strong></div>
            <div class="summary-item"><span>Destination</span><strong>${escapeHtmlPay(projet.destination_display || projet.destination || '—')}</strong></div>
            <div class="summary-item"><span>Créée le</span><strong>${souscription.created_at ? new Date(souscription.created_at).toLocaleDateString('fr-FR') : '—'}</strong></div>
        `;
    }

    function renderState() {
        const statut = souscription.statut;
        submitBtn.style.display = 'none';
        checkBtn.style.display = 'none';
        payBtn.style.display = 'none';
        methodsBlock.style.display = 'none';
        hideReviewNotice();

        if (statut === 'en_attente_paiement') {
            statusBox.innerHTML = '<span class="status-pill payable">Dossier approuvé — à payer</span>';
            methodsBlock.style.display = 'block';
            payBtn.style.display = 'inline-block';
        } else if (statut === 'en_attente_validation') {
            statusBox.innerHTML = '<span class="status-pill review">En validation humaine</span>';
            showReviewNotice(
                'Votre dossier est en cours de validation humaine — cela peut prendre plusieurs jours ' +
                'le temps de l\'enquête. Vous serez informé dès qu\'il est approuvé.'
            );
            checkBtn.style.display = 'inline-block';
        } else if (statut === 'refusee') {
            statusBox.innerHTML = '<span class="status-pill refused">Dossier refusé</span>';
            showMessagePay('Votre dossier a été refusé après revue. Contactez le service client.', 'error');
        } else if (statut === 'active') {
            statusBox.innerHTML = '<span class="status-pill payable">Souscription active</span>';
            showMessagePay('Cette souscription est déjà payée et active.', 'success');
        } else {
            // en_attente : le dossier n'a pas encore été soumis à la décision
            statusBox.innerHTML = '<span class="status-pill review">Brouillon — à soumettre</span>';
            submitBtn.style.display = 'inline-block';
        }
    }

    async function refresh() {
        souscription = await apiCall(`/subscriptions/${subscriptionId}`);
        renderSummary();
        renderState();
    }

    try {
        await refresh();
    } catch (error) {
        showMessagePay(error.message || 'Impossible de charger le dossier.', 'error');
        return;
    }

    // « Soumettre le dossier » → décision automatique
    submitBtn.addEventListener('click', async () => {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Soumission en cours...';
        try {
            const result = await apiCall(`/subscriptions/${subscriptionId}/evaluate`, {
                method: 'POST',
                body: JSON.stringify({}),
            });
            await refresh();
            if (result.decision === 'approve') {
                showMessagePay('Dossier approuvé — vous pouvez procéder au paiement.', 'success');
            } else if (result.decision === 'review') {
                const reasons = Array.isArray(result.reasons) && result.reasons.length
                    ? `<br><small>${result.reasons.map(escapeHtmlPay).join('<br>')}</small>`
                    : '';
                showReviewNotice(
                    'Votre dossier a été soumis à une validation humaine — cela peut prendre plusieurs ' +
                    'jours. Vous serez informé dès qu\'il est approuvé.' + reasons
                );
            } else {
                showMessagePay(
                    'Votre dossier a été refusé.' +
                    (result.reasons?.length ? '<br><small>' + result.reasons.map(escapeHtmlPay).join('<br>') + '</small>' : ''),
                    'error'
                );
            }
        } catch (error) {
            showMessagePay(error.message || 'Impossible de soumettre le dossier.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Soumettre le dossier';
        }
    });

    // « Vérifier le statut » pendant la revue humaine
    checkBtn.addEventListener('click', async () => {
        checkBtn.disabled = true;
        checkBtn.textContent = 'Vérification...';
        try {
            await refresh();
            if (souscription.statut === 'en_attente_paiement') {
                showMessagePay('Dossier approuvé — vous pouvez procéder au paiement.', 'success');
            } else if (souscription.statut === 'en_attente_validation') {
                showReviewNotice('Le dossier est toujours en cours de validation humaine.');
            }
        } catch (error) {
            showMessagePay(error.message || 'Impossible de vérifier le statut.', 'error');
        } finally {
            checkBtn.disabled = false;
            checkBtn.textContent = 'Vérifier le statut';
        }
    });

    // « Payer maintenant » → POST /payments/confirm
    payBtn.addEventListener('click', async () => {
        const method = document.querySelector('input[name="paymentMethod"]:checked')?.value || 'carte_bancaire';
        payBtn.disabled = true;
        payBtn.textContent = 'Paiement en cours...';
        try {
            const response = await apiCall('/payments/confirm', {
                method: 'POST',
                body: JSON.stringify({
                    souscription_id: subscriptionId,
                    montant: Number(souscription.prix_applique),
                    methode_paiement: method,
                }),
            });
            sessionStorage.setItem('payment_info', JSON.stringify(response));
            showMessagePay('Paiement confirmé ! Votre attestation définitive est générée.', 'success');
            setTimeout(() => { window.location.href = 'user-dashboard.html'; }, 1500);
        } catch (error) {
            showMessagePay(error.message || 'Paiement impossible. Merci de réessayer.', 'error');
            payBtn.disabled = false;
            payBtn.textContent = 'Payer maintenant';
            // Le statut a pu changer (ex. remis en revue) — resynchroniser.
            try { await refresh(); } catch (_) {}
        }
    });
});
