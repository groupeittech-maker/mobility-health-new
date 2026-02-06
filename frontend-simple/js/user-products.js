const ROWS_PER_PAGE = 6;
let currentPageUserProducts = 0;

let subscriptionsState = {
    data: [],
    filter: 'all',
    searchTerm: '',
};

document.addEventListener('DOMContentLoaded', async () => {
    const isValid = await requireAuth();
    if (!isValid) {
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const initialFilter = params.get('filter');
    if (initialFilter) {
        subscriptionsState.filter = initialFilter;
    }

    bindProductFilters();
    await loadProducts();
});

function bindProductFilters() {
    document.querySelectorAll('#productFilters .filter-tab').forEach(button => {
        const filter = button.dataset.filter;
        if (filter === subscriptionsState.filter) {
            button.classList.add('active');
        }
        button.addEventListener('click', () => {
            document.querySelectorAll('#productFilters .filter-tab').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            subscriptionsState.filter = filter;
            renderProducts();
        });
    });
    const searchEl = document.getElementById('searchUserProducts');
    if (searchEl) {
        searchEl.addEventListener('input', () => {
            subscriptionsState.searchTerm = (searchEl.value || '').trim();
            renderProducts();
        });
    }
}

async function loadProducts() {
    const loadingEl = document.getElementById('productsLoading');
    const container = document.getElementById('productsContainer');
    loadingEl.style.display = 'block';
    container.innerHTML = '';

    try {
        const subscriptions = await apiCall('/subscriptions/?limit=1000');
        subscriptionsState.data = (subscriptions || []).sort((a, b) => {
            const dateA = new Date(a.created_at || a.date_debut);
            const dateB = new Date(b.created_at || b.date_debut);
            return dateB - dateA;
        });

        updateProductStats();
        renderProducts();
    } catch (error) {
        console.error('Erreur lors du chargement des produits:', error);
        container.innerHTML = `
            <div class="alert alert-error">
                Impossible de charger vos produits. ${error.message || ''}
            </div>
        `;
    } finally {
        loadingEl.style.display = 'none';
    }
}

function updateProductStats() {
    const total = subscriptionsState.data.length;
    const active = subscriptionsState.data.filter(sub => normalizeStatus(sub.statut) === 'active').length;
    const pending = subscriptionsState.data.filter(sub => normalizeStatus(sub.statut) === 'pending').length;
    const expired = subscriptionsState.data.filter(sub => normalizeStatus(sub.statut) === 'expired').length;

    document.getElementById('productsTotal').textContent = total;
    document.getElementById('productsActive').textContent = active;
    document.getElementById('productsPending').textContent = pending;
    document.getElementById('productsExpired').textContent = expired;
}

function renderProducts() {
    const container = document.getElementById('productsContainer');
    let filtered = subscriptionsState.data.filter(sub => {
        if (subscriptionsState.filter === 'all') return true;
        return normalizeStatus(sub.statut) === subscriptionsState.filter;
    });

    if (subscriptionsState.searchTerm) {
        const term = subscriptionsState.searchTerm.trim().toLowerCase();
        filtered = filtered.filter(sub => {
            const productName = ((sub.produit_assurance && sub.produit_assurance.nom) || '').toLowerCase();
            const numero = (sub.numero_souscription || '').toLowerCase();
            const statut = (sub.statut || '').toLowerCase();
            const statusLabel = (getStatusMeta(sub.statut).label || '').toLowerCase();
            return productName.includes(term) || numero.includes(term) || statut.includes(term) || statusLabel.includes(term);
        });
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                ${subscriptionsState.searchTerm ? 'Aucun produit ne correspond à la recherche.' : 'Aucun produit ne correspond à ce filtre.'}
            </div>
        `;
        const pagEl = document.getElementById('productsPagination');
        if (pagEl) { pagEl.hidden = true; pagEl.innerHTML = ''; }
        return;
    }

    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    currentPageUserProducts = Math.min(currentPageUserProducts, totalPages - 1);
    const start = currentPageUserProducts * ROWS_PER_PAGE;
    const pageData = filtered.slice(start, start + ROWS_PER_PAGE);
    container.innerHTML = pageData.map(buildProductCard).join('');

    const pagEl = document.getElementById('productsPagination');
    if (pagEl) {
        if (filtered.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, filtered.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${filtered.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="prodPrev" ${currentPageUserProducts <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageUserProducts + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="prodNext" ${currentPageUserProducts >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('prodPrev')?.addEventListener('click', () => { currentPageUserProducts--; renderProducts(); });
            document.getElementById('prodNext')?.addEventListener('click', () => { currentPageUserProducts++; renderProducts(); });
        }
    }
}

function buildProductCard(subscription) {
    const statusMeta = getStatusMeta(subscription.statut);
    const product = subscription.produit_assurance || {};

    return `
        <article class="product-card">
            <div class="product-card-header">
                <div>
                    <h3>${product.nom || 'Produit Mobility Health'}</h3>
                    <p style="margin:0; color: var(--secondary-color); font-size: 0.95rem;">
                        ${subscription.numero_souscription || 'Souscription #' + subscription.id}
                    </p>
                </div>
                <span class="status-badge ${statusMeta.className}">${statusMeta.label}</span>
            </div>
            <div class="product-meta">
                <div class="meta-item">
                    <span class="meta-label">Date d'effet</span>
                    <span class="meta-value">${formatDate(subscription.date_debut)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Date de fin</span>
                    <span class="meta-value">${formatDate(subscription.date_fin)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Statut</span>
                    <span class="meta-value">${statusMeta.description}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Prime</span>
                    <span class="meta-value">${formatPrice(subscription.prix_applique)} €</span>
                </div>
            </div>
            <div class="card-actions">
                <a class="btn btn-secondary btn-sm" href="user-attestations.html?subscription_id=${subscription.id}">
                    Voir les attestations
                </a>
                ${statusMeta.key === 'active'
                    ? `<a class="btn btn-danger btn-sm" href="sos-alert.html?subscription_id=${subscription.id}">Déclarer un sinistre</a>`
                    : ''
                }
            </div>
        </article>
    `;
}

function getStatusMeta(status) {
    const normalized = normalizeStatus(status);
    const map = {
        active: {
            key: 'active',
            className: 'status-active',
            label: 'Active',
            description: 'Assuré et actif',
        },
        pending: {
            key: 'pending',
            className: 'status-pending',
            label: 'En attente',
            description: 'Validation en cours',
        },
        expired: {
            key: 'expired',
            className: 'status-expired',
            label: 'Expiré',
            description: 'Couverture terminée',
        },
        other: {
            key: 'other',
            className: 'status-other',
            label: 'Suspendu',
            description: 'Contactez le support',
        },
    };

    if (map[normalized]) {
        return map[normalized];
    }
    return map.other;
}

function normalizeStatus(status) {
    switch (status) {
        case 'active':
            return 'active';
        case 'pending':
        case 'en_attente':
            return 'pending';
        case 'expiree':
        case 'expired':
            return 'expired';
        default:
            return 'other';
    }
}

function formatDate(value) {
    if (!value) {
        return '—';
    }
    const date = new Date(value);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });
}

function formatPrice(value) {
    if (!value) {
        return '0.00';
    }
    const number = typeof value === 'number' ? value : parseFloat(value);
    if (isNaN(number)) {
        return String(value);
    }
    return number.toFixed(2);
}

