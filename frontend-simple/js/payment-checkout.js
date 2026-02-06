const fallbackCurrencyHelper = {
    getLocale: () => 'fr-FR',
    getCurrency: () => 'XOF',
    format: (value, options = {}) => {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return '—';
        }
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'XOF',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
            ...options,
        }).format(numeric);
    },
};

const currencyHelper = window.CurrencyHelper || fallbackCurrencyHelper;

document.addEventListener('DOMContentLoaded', async () => {
    const authenticated = await requireAuth();
    if (!authenticated) {
        return;
    }

    const draftRaw = sessionStorage.getItem('subscription_draft');
    const formsRaw = sessionStorage.getItem('forms_payload');

    if (!draftRaw) {
        showMessage('Aucun voyage sélectionné. Merci de reprendre le parcours.', 'error');
        setTimeout(() => window.location.href = 'project-wizard.html', 1500);
        return;
    }
    if (!formsRaw) {
        showMessage('Les questionnaires doivent être complétés avant le paiement.', 'error');
        setTimeout(() => window.location.href = 'forms-medical.html', 1500);
        return;
    }

    const draft = JSON.parse(draftRaw);
    const forms = JSON.parse(formsRaw);

    const payBtn = document.getElementById('payNowBtn');
    const priceLabel = document.getElementById('priceLabel');
    const productLabel = document.getElementById('productLabel');
    const summaryContainer = document.getElementById('checkoutSummary');

    let project;
    let product;
    let user;

    try {
        [project, product, user] = await Promise.all([
            apiCall(`/voyages/${draft.projectId}`),
            apiCall(`/products/${draft.productId}`),
            apiCall('/auth/me').catch(() => null)
        ]);
    } catch (error) {
        console.error('Erreur chargement checkout', error);
        showMessage(error.message || 'Impossible de charger les informations pour le paiement.', 'error');
        return;
    }

    // Montant selon durée, zone et âge (devis)
    let age = null;
    if (user && user.date_naissance) {
        const birth = new Date(user.date_naissance);
        const today = new Date();
        age = Math.floor((today - birth) / (365.25 * 24 * 60 * 60 * 1000));
    }
    let duree_jours = null;
    if (project.date_depart && project.date_retour) {
        const dep = new Date(project.date_depart);
        const ret = new Date(project.date_retour);
        duree_jours = Math.max(0, Math.ceil((ret - dep) / (24 * 60 * 60 * 1000)));
    }
    const destination_country_id = project.destination_country_id ?? null;
    const quoteParams = { age, destination_country_id, duree_jours };
    const paramsStr = new URLSearchParams(
        Object.fromEntries(
            Object.entries(quoteParams).filter(([, v]) => v != null && v !== '')
        )
    ).toString();
    let montant = product.cout;
    try {
        const quote = await apiCall(`/products/${draft.productId}/quote${paramsStr ? `?${paramsStr}` : ''}`);
        montant = quote.prix;
    } catch (e) {
        console.warn('Devis non disponible, utilisation du prix de base', e);
    }

    priceLabel.textContent = formatCurrency(montant);
    productLabel.textContent = product.nom;
    renderSummary(summaryContainer, project, product, forms.questionnaireMode || project.questionnaire_type || 'long');

    payBtn.addEventListener('click', async () => {
        const method = getSelectedMethod();
        if (!method) {
            showMessage('Merci de sélectionner un mode de paiement.', 'error');
            return;
        }
        payBtn.disabled = true;
        payBtn.textContent = 'Paiement en cours...';

        try {
            const payload = {
                project_id: draft.projectId,
                produit_assurance_id: draft.productId,
                payment_method: method,
                administrative_form: forms.administrative || {},
                medical_form: forms.medical || {},
                age: age,
                duree_jours: duree_jours,
                destination_country_id: destination_country_id
            };

            const response = await apiCall('/payments/checkout', {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            sessionStorage.setItem('payment_info', JSON.stringify(response));
            sessionStorage.removeItem('forms_payload');
            sessionStorage.removeItem('subscription_draft');
            try { sessionStorage.removeItem('tier_info'); } catch (e) {}
            showMessage(`Paiement confirmé ! Attestation provisoire ${response.attestation_number} générée.`, 'success');

            setTimeout(() => {
                window.location.href = 'user-dashboard.html';
            }, 1500);
        } catch (error) {
            console.error('Erreur paiement', error);
            showMessage(error.message || 'Paiement impossible. Merci de réessayer.', 'error');
            payBtn.disabled = false;
            payBtn.textContent = 'Payer maintenant';
        }
    });
});

function getSelectedMethod() {
    const input = document.querySelector('input[name="paymentMethod"]:checked');
    return input ? input.value : null;
}

function renderSummary(container, project, product, questionnaireMode) {
    const modeLabel = questionnaireMode === 'short' ? 'Questionnaire court' : 'Questionnaire long';
    container.innerHTML = `
        <div class="summary-item">
            <span>Voyage</span>
            <strong>${project.titre}</strong>
        </div>
        <div class="summary-item">
            <span>Destination</span>
            <strong>${project.destination || '—'}</strong>
        </div>
        <div class="summary-item">
            <span>Période</span>
            <strong>${formatDate(project.date_depart)} → ${project.date_retour ? formatDate(project.date_retour) : '—'}</strong>
        </div>
        <div class="summary-item">
            <span>Produit</span>
            <strong>${product.nom}</strong>
        </div>
        <div class="summary-item">
            <span>Mode questionnaire</span>
            <strong>${modeLabel}</strong>
        </div>
    `;
}

function formatDate(value) {
    if (!value) return '-';
    return new Date(value).toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}

function formatCurrency(amount) {
    if (amount == null) return '—';
    try {
        return currencyHelper.format(amount, {
            maximumFractionDigits: 0,
        });
    } catch {
        return `${amount} ${currencyHelper.getCurrency ? currencyHelper.getCurrency() : 'XOF'}`;
    }
}

function showMessage(text, type) {
    const box = document.getElementById('paymentMessage');
    if (!box) return;
    box.textContent = text;
    box.className = `message ${type}`;
    box.style.display = 'block';
}

function goBackToQuestionnaire() {
    // Récupérer le projectId et productId depuis sessionStorage ou l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const projectIdFromUrl = urlParams.get('projectId');
    const productIdFromUrl = urlParams.get('productId');
    
    let projectId = projectIdFromUrl;
    let productId = productIdFromUrl;
    
    if (!projectId || !productId) {
        // Essayer de récupérer depuis sessionStorage
        const draftRaw = sessionStorage.getItem('subscription_draft');
        if (draftRaw) {
            try {
                const draft = JSON.parse(draftRaw);
                projectId = projectId || draft.projectId;
                productId = productId || draft.productId;
            } catch (e) {
                console.error('Erreur parsing draft:', e);
            }
        }
    }
    
    // Si on a les IDs, rediriger vers forms-medical.html
    if (projectId && productId) {
        window.location.href = `forms-medical.html?projectId=${projectId}&productId=${productId}`;
    } else {
        // Sinon, utiliser l'historique du navigateur
        window.history.back();
    }
}

// Exposer goBackToQuestionnaire globalement
window.goBackToQuestionnaire = goBackToQuestionnaire;

