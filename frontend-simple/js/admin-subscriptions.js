// Vérifier l'authentification et le rôle admin
(async function() {
    // Les souscriptions peuvent être gérées par admin ou finance_manager
    const isValid = await requireAnyRole(['admin', 'finance_manager'], 'index.html');
    if (!isValid) {
        return; // requireAnyRole() a déjà redirigé
    }
})();

// API pour les souscriptions admin
const adminSubscriptionsAPI = {
    getPending: async () => {
        // Limiter à 100 par défaut pour éviter les timeouts
        return apiCall('/admin/subscriptions/pending?limit=100');
    },
    
    getAll: async () => {
        return apiCall('/admin/subscriptions/?limit=1000');
    },
    
    getById: async (id) => {
        return apiCall(`/admin/subscriptions/${id}`);
    },
    
    validate: async (id, data) => {
        return apiCall(`/admin/subscriptions/${id}/validate`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
};

let subscriptionsCache = [];
let searchSubscriptionsTerm = '';
const ROWS_PER_PAGE = 6;
let currentPageSubscriptions = 0;

function getUserDisplayName(sub) {
    if (!sub) return '—';
    const u = sub.user;
    if (u) {
        if (u.full_name && u.full_name.trim()) return u.full_name.trim();
        if (u.email && u.email.trim()) return u.email.trim();
        if (u.username && u.username.trim()) return u.username.trim();
    }
    return sub.user_id != null ? `User #${sub.user_id}` : '—';
}

function escapeHtml(text) {
    if (text == null) return '';
    const s = String(text);
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Charger les souscriptions
async function loadSubscriptions() {
    const container = document.getElementById('subscriptionsTableContainer');
    if (!container) {
        console.error('Container subscriptionsTableContainer non trouvé');
        return;
    }
    
    showLoading(container);
    
    try {
        // Vérifier la connexion au serveur avant de faire l'appel
<<<<<<< HEAD
        const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
=======
        const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
        try {
            const healthCheck = await fetch(`${apiUrl.replace('/api/v1', '')}/health`);
            if (!healthCheck.ok) {
                throw new Error('Serveur backend non disponible');
            }
        } catch (healthError) {
            container.innerHTML = `
                <div class="alert alert-error">
                    <h3>Erreur de connexion</h3>
                    <p>Impossible de se connecter au serveur backend.</p>
                    <p><strong>Vérifications à effectuer :</strong></p>
                    <ul>
<<<<<<< HEAD
                        <li>Le serveur backend est-il accessible sur https://srv1324425.hstgr.cloud ?</li>
=======
                        <li>Le serveur backend est-il accessible sur https://mobility-health.ittechmed.com ?</li>
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
                        <li>Vérifiez la console du navigateur pour plus de détails</li>
                        <li>URL attendue : ${apiUrl}</li>
                    </ul>
                    <p><small>Erreur : ${healthError.message}</small></p>
                    <button class="btn btn-primary" onclick="loadSubscriptions()">Réessayer</button>
                </div>
            `;
            return;
        }
        
        const statusFilter = document.getElementById('statusFilter')?.value || 'all';
        let subscriptions = [];
        
        if (statusFilter === 'pending') {
            subscriptions = await adminSubscriptionsAPI.getPending();
        } else {
            subscriptions = await adminSubscriptionsAPI.getAll();
            if (statusFilter === 'active') {
                subscriptions = subscriptions.filter(s => s.statut === 'active');
            }
        }
        
        if (subscriptions.length === 0) {
            subscriptionsCache = [];
            container.innerHTML = '<p>Aucune souscription trouvée.</p>';
            return;
        }
        
        subscriptionsCache = subscriptions;
        searchSubscriptionsTerm = (document.getElementById('searchSubscriptions')?.value || '').trim().toLowerCase();
        renderSubscriptionsTable();
        bindSubscriptionsSearch();
    } catch (error) {
        console.error('Erreur lors du chargement des souscriptions:', error);
        const errorMessage = error.message || 'Erreur inconnue';
        
        // Vérifier si c'est une erreur de connexion
        const isConnectionError = errorMessage.includes('connecter') || 
                                  errorMessage.includes('Failed to fetch') ||
                                  errorMessage.includes('backend');
        
        container.innerHTML = `
            <div class="alert alert-error">
                <h3>Erreur de chargement</h3>
                <p>${errorMessage}</p>
                ${isConnectionError ? `
                    <p><strong>Le serveur backend n'est peut-être pas démarré.</strong></p>
<<<<<<< HEAD
                    <p>Vérifiez que le backend est accessible sur https://srv1324425.hstgr.cloud</p>
=======
                    <p>Vérifiez que l'API est accessible sur https://mobility-health.ittechmed.com</p>
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
                    <p>Vous pouvez le démarrer avec : <code>.\scripts\start_backend.ps1</code></p>
                ` : ''}
                <p><small>Vérifiez la console pour plus de détails.</small></p>
                <button class="btn btn-primary" onclick="loadSubscriptions()">Réessayer</button>
            </div>
        `;
    }
}

function bindSubscriptionsSearch() {
    const searchEl = document.getElementById('searchSubscriptions');
    if (searchEl && !searchEl.dataset.bound) {
        searchEl.dataset.bound = 'true';
        searchEl.addEventListener('input', () => {
            searchSubscriptionsTerm = (searchEl.value || '').trim().toLowerCase();
            if (subscriptionsCache.length) {
                renderSubscriptionsTable();
            }
        });
    }
}

function renderSubscriptionsTable() {
    const container = document.getElementById('subscriptionsTableContainer');
    if (!container) {
        return;
    }
        const filtered = searchSubscriptionsTerm
        ? subscriptionsCache.filter((sub) => {
            const numero = (sub.numero_souscription || '').toLowerCase();
            const userDisplay = getUserDisplayName(sub).toLowerCase();
            const userId = (sub.user_id != null ? String(sub.user_id) : '').toLowerCase();
            const statut = (sub.statut || '').toLowerCase();
            const date = new Date(sub.created_at).toLocaleDateString('fr-FR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            }).toLowerCase();
            return numero.includes(searchSubscriptionsTerm) || userDisplay.includes(searchSubscriptionsTerm) ||
                userId.includes(searchSubscriptionsTerm) || statut.includes(searchSubscriptionsTerm) ||
                date.includes(searchSubscriptionsTerm);
        })
        : subscriptionsCache;

    if (filtered.length === 0) {
        container.innerHTML = '<p>' + (subscriptionsCache.length ? 'Aucune souscription ne correspond à la recherche.' : 'Aucune souscription trouvée.') + '</p>';
        return;
    }

    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    currentPageSubscriptions = Math.min(currentPageSubscriptions, totalPages - 1);
    const start = currentPageSubscriptions * ROWS_PER_PAGE;
    const pageData = filtered.slice(start, start + ROWS_PER_PAGE);

    let html = '<div class="table-wrapper" style="overflow-x: scroll !important;"><table class="data-table" style="min-width: 100%;"><thead><tr>';
    html += '<th>Numéro</th><th>Utilisateur</th><th>Prix</th><th>Statut</th><th>Date</th><th>Actions</th>';
    html += '</tr></thead><tbody>';

    pageData.forEach(sub => {
        const statusClass = sub.statut === 'active' ? 'status-active' :
            sub.statut === 'en_attente' ? 'status-pending' : 'status-inactive';
        const date = new Date(sub.created_at).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
        const userDisplay = getUserDisplayName(sub);
        html += `
            <tr>
                <td>${sub.numero_souscription}</td>
                <td>${escapeHtml(userDisplay)}</td>
                <td>${parseFloat(sub.prix_applique).toFixed(2)} FCFA</td>
                <td><span class="status-badge ${statusClass}">${sub.statut}</span></td>
                <td>${date}</td>
                <td class="table-actions">
                    <select class="action-select" data-subscription-id="${sub.id}">
                        <option value="">Actions</option>
                        <option value="view">Voir</option>
                    </select>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';
    if (filtered.length > ROWS_PER_PAGE) {
        const end = Math.min(start + ROWS_PER_PAGE, filtered.length);
        html += `
            <div class="table-pagination-wrapper" style="margin-top: 1rem;">
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${filtered.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="subPrev" ${currentPageSubscriptions <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageSubscriptions + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="subNext" ${currentPageSubscriptions >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
    setupSubscriptionsTableActions();
    if (filtered.length > ROWS_PER_PAGE) {
        document.getElementById('subPrev')?.addEventListener('click', () => { currentPageSubscriptions--; renderSubscriptionsTable(); });
        document.getElementById('subNext')?.addEventListener('click', () => { currentPageSubscriptions++; renderSubscriptionsTable(); });
    }

    setTimeout(() => {
        const wrapper = container.querySelector('.table-wrapper');
        if (wrapper) {
            wrapper.style.overflowX = 'scroll';
            const table = wrapper.querySelector('.data-table');
            if (table && table.offsetWidth <= wrapper.clientWidth) {
                table.style.minWidth = `${wrapper.clientWidth + 2}px`;
            }
        }
    }, 100);
}

function viewSubscription(id) {
    // Rediriger vers une page de détail ou afficher dans un modal
    alert(`Détails de la souscription #${id}`);
}

function setupSubscriptionsTableActions() {
    const container = document.getElementById('subscriptionsTableContainer');
    if (!container) {
        return;
    }
    
    container.addEventListener('change', (event) => {
        const select = event.target.closest('.action-select');
        if (!select) {
            return;
        }
        
        const action = select.value;
        if (!action) {
            return;
        }
        
        const subscriptionId = parseInt(select.dataset.subscriptionId, 10);
        if (Number.isNaN(subscriptionId)) {
            return;
        }
        
        switch (action) {
            case 'view':
                viewSubscription(subscriptionId);
                break;
        }
        
        // Réinitialiser le select
        select.value = '';
    });
}

// Charger les souscriptions au chargement de la page
document.addEventListener('DOMContentLoaded', loadSubscriptions);

