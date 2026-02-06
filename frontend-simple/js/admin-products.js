// Vérifier l'authentification et le rôle admin
(async function () {
    const isValid = await requireRole('admin', 'index.html');
    if (!isValid) {
        return;
    }
})();

// API pour les produits admin
const adminProductsAPI = {
    getAll: async (estActif = null) => {
        const params = estActif !== null ? `?est_actif=${estActif}` : '';
        return apiCall(`/admin/products${params}`);
    },

    getById: async (id) => {
        return apiCall(`/admin/products/${id}`);
    },

    create: async (data) => {
        return apiCall('/admin/products', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    update: async (id, data) => {
        return apiCall(`/admin/products/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    delete: async (id) => {
        return apiCall(`/admin/products/${id}`, {
            method: 'DELETE',
        });
    },

    getTarifs: async (productId) => {
        return apiCall(`/admin/products/${productId}/tarifs`);
    },
    createTarif: async (productId, data) => {
        return apiCall(`/admin/products/${productId}/tarifs`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
    updateTarif: async (productId, tarifId, data) => {
        return apiCall(`/admin/products/${productId}/tarifs/${tarifId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },
    deleteTarif: async (productId, tarifId) => {
        return apiCall(`/admin/products/${productId}/tarifs/${tarifId}`, {
            method: 'DELETE',
        });
    },
};

const adminAssureursAPI = {
    list: async () => apiCall('/admin/assureurs'),
};

const PRODUCT_TYPE_LABELS = {
    voyage: 'Voyage',
    sante: 'Santé',
    auto: 'Auto',
    habitation: 'Habitation',
    entreprise: 'Entreprise',
    autre: 'Autre',
};

const ZONE_PRESETS = [
    'Afrique',
    'Afrique centrale',
    'Afrique de l’Ouest',
    'Europe',
    'Monde entier',
    'Amériques',
    'Asie',
    'Océanie',
];

const DEFAULT_GARANTIES = [
    {
        titre: 'Frais médicaux',
        description: 'Prise en charge des frais médicaux d’urgence à l’étranger.',
        franchise: 0,
        capitaux: 5000000,
        obligatoire: true,
    },
];

const fallbackCurrencyHelper = {
    getLocale: () => 'fr-FR',
    getCurrency: () => 'XOF',
    getSymbol: () => 'F CFA',
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

let assureursOptions = [];
let assureursLoadingPromise = null;
let assureurSelectEl = null;
let assureurSummaryCard = null;
let assureurHelperText = null;
let submitProductBtn = null;

let currentEditingProduct = null;
let selectedZones = new Map();
let preservedSpecificites = [];
let productForm = null;
let productsCache = [];
let searchProductsTerm = '';
const ROWS_PER_PAGE = 6;
let currentPageProducts = 0;

async function ensureAssureursLoaded(force = false) {
    if (assureursLoadingPromise && !force) {
        return assureursLoadingPromise;
    }
    assureursLoadingPromise = (async () => {
        try {
            assureursOptions = await adminAssureursAPI.list();
            populateAssureurSelect();
            toggleAssureurControlsAvailability();
            return assureursOptions;
        } catch (error) {
            console.error('Erreur chargement assureurs:', error);
            if (assureurSelectEl) {
                assureurSelectEl.innerHTML = '<option value="">Erreur de chargement</option>';
            }
            toggleAssureurControlsAvailability(true);
            showAlert(error.message || 'Impossible de charger les assureurs.', 'error');
            throw error;
        }
    })();
    return assureursLoadingPromise;
}

function populateAssureurSelect(selectedId = null) {
    if (!assureurSelectEl) {
        return;
    }
    const previousValue = selectedId ?? assureurSelectEl.value;
    if (!assureursOptions.length) {
        assureurSelectEl.innerHTML = '<option value="">Aucun assureur disponible</option>';
        assureurSelectEl.value = '';
        updateAssureurSummary('', '');
        return;
    }
    const optionsHtml = [
        '<option value="">Sélectionner un assureur</option>',
        ...assureursOptions.map(
            (assureur) => `<option value="${assureur.id}">${assureur.nom} — ${assureur.pays}</option>`
        ),
    ];
    assureurSelectEl.innerHTML = optionsHtml.join('');
    const exists = assureursOptions.some((assureur) => String(assureur.id) === String(previousValue));
    assureurSelectEl.value = exists ? previousValue : '';
    updateAssureurSummary(assureurSelectEl.value);
}

function toggleAssureurControlsAvailability(forceDisabled = false) {
    const hasAssureurs = assureursOptions.length > 0 && !forceDisabled;
    if (assureurSelectEl) {
        assureurSelectEl.disabled = !hasAssureurs;
    }
    if (submitProductBtn) {
        submitProductBtn.disabled = !hasAssureurs;
    }
    if (assureurHelperText) {
        assureurHelperText.textContent = hasAssureurs
            ? 'Sélectionnez un assureur pour ce produit.'
            : 'Créez un assureur dans le back office avant de créer un produit.';
    }
}

function getAssureurById(id) {
    if (!id) {
        return null;
    }
    return assureursOptions.find((assureur) => String(assureur.id) === String(id)) || null;
}

function updateAssureurSummary(selectedId, legacyName = '') {
    if (!assureurSummaryCard) {
        return;
    }
    if (!selectedId) {
        if (legacyName) {
            assureurSummaryCard.classList.remove('text-muted');
            assureurSummaryCard.innerHTML = `
                <div>
                    <strong>${legacyName}</strong>
                    <p class="text-muted">Assureur hérité détecté. Sélectionnez un assureur enregistré pour mettre à jour ce produit.</p>
                </div>
            `;
        } else {
            assureurSummaryCard.classList.add('text-muted');
            assureurSummaryCard.innerHTML = 'Sélectionnez un assureur pour afficher ses détails (pays, logo, agent comptable).';
        }
        return;
    }

    const assureur = getAssureurById(selectedId);
    if (!assureur) {
        assureurSummaryCard.classList.remove('text-muted');
        assureurSummaryCard.innerHTML = `
            <div>
                <strong>${legacyName || 'Assureur introuvable'}</strong>
                <p class="text-muted">Cet assureur n’est plus disponible. Sélectionnez une compagnie active.</p>
            </div>
        `;
        return;
    }

    assureurSummaryCard.classList.remove('text-muted');
    const agentLabel = assureur.agent_comptable
        ? (assureur.agent_comptable.full_name || assureur.agent_comptable.username)
        : 'Agent non assigné';
    assureurSummaryCard.innerHTML = `
        <div class="assureur-summary-grid">
            <div>
                <strong>${assureur.nom}</strong>
                <p class="text-muted">${assureur.pays}</p>
                ${assureur.telephone ? `<p>📞 ${assureur.telephone}</p>` : ''}
                ${assureur.adresse ? `<p>📍 ${assureur.adresse}</p>` : ''}
                <p>👤 ${agentLabel}</p>
            </div>
            ${
                (() => {
                    const url = assureur.logo_url && assureur.logo_url.startsWith('http')
                        ? assureur.logo_url
                        : (assureur.logo_url ? `${window.API_BASE_URL || '/api/v1'}/assureurs/${assureur.id}/logo` : '');
                    return url ? `<div><img src="${url}" alt="Logo ${assureur.nom}" onerror="this.style.display='none'"></div>` : '';
                })()
            }
        </div>
    `;
}

function handleAssureurChange(event) {
    const selectedValue = event.target.value;
    updateAssureurSummary(selectedValue);
}

// Charger les produits
async function loadProducts() {
    const container = document.getElementById('productsTableContainer');
    showLoading(container);

    try {
        const statusFilter = document.getElementById('statusFilter').value;
        const estActif = statusFilter === '' ? null : statusFilter === 'true';

        const products = await adminProductsAPI.getAll(estActif);
        productsCache = Array.isArray(products) ? products : [];

        if (productsCache.length === 0) {
            container.innerHTML = '<p>Aucun produit trouvé.</p>';
            return;
        }

        searchProductsTerm = (document.getElementById('searchProducts')?.value || '').trim().toLowerCase();
        renderProductsTable();
    } catch (error) {
        container.innerHTML = `<div class="alert alert-error">Erreur: ${error.message}</div>`;
    }
}

function renderProductsTable() {
    const container = document.getElementById('productsTableContainer');
    if (!container) {
        return;
    }
    const filtered = searchProductsTerm
        ? productsCache.filter((product) => {
            const nom = (product.nom || product.name || '').toLowerCase();
            const code = (product.code || '').toLowerCase();
            const assureurName = ((product.assureur_details && product.assureur_details.nom) || product.assureur || '').toLowerCase();
            const typeValue = formatProductType(extractTypeFromProduct(product)).toLowerCase();
            return nom.includes(searchProductsTerm) || code.includes(searchProductsTerm) ||
                assureurName.includes(searchProductsTerm) || typeValue.includes(searchProductsTerm);
        })
        : productsCache;

    if (filtered.length === 0) {
        container.innerHTML = '<p>Aucun produit ne correspond à la recherche.</p>';
        return;
    }

    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    currentPageProducts = Math.min(currentPageProducts, totalPages - 1);
    const start = currentPageProducts * ROWS_PER_PAGE;
    const pageData = filtered.slice(start, start + ROWS_PER_PAGE);

    let html = '<div class="table-wrapper" style="overflow-x: scroll !important;"><table class="data-table" style="min-width: 100%;"><thead><tr>';
    html += '<th>Code</th><th>Nom</th><th>Assureur</th><th>Type</th><th>Coût</th><th>Statut</th><th>Actions</th>';
    html += '</tr></thead><tbody>';

    pageData.forEach(product => {
        const nom = product.nom || product.name || '—';
        const cout = product.cout !== undefined && product.cout !== null ? product.cout : (product.price !== undefined && product.price !== null ? product.price : 0);
        const estActif = product.est_actif !== undefined ? product.est_actif : (product.isActive !== undefined ? product.isActive : true);
        const statusClass = estActif ? 'status-active' : 'status-inactive';
        const statusText = estActif ? 'Actif' : 'Inactif';
        const typeValue = formatProductType(extractTypeFromProduct(product));
        const cost = formatCurrency(cout);
        const assureurName = (product.assureur_details && product.assureur_details.nom) || product.assureur || '—';

        html += `
            <tr>
                <td>${product.code || '—'}</td>
                <td>${nom}</td>
                <td>${assureurName}</td>
                <td><span class="pill">${typeValue}</span></td>
                <td>${cost}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td class="table-actions">
                    <select class="action-select" data-product-id="${product.id}">
                        <option value="">Actions</option>
                        <option value="edit">Modifier</option>
                        <option value="delete">Supprimer</option>
                    </select>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';
    if (filtered.length > ROWS_PER_PAGE) {
        const end = Math.min(start + ROWS_PER_PAGE, filtered.length);
        html += `<div class="table-pagination-wrapper"><div class="table-pagination" role="navigation">
            <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${filtered.length}</span>
            <div class="table-pagination-buttons">
                <button type="button" class="btn btn-outline btn-sm" id="prodPrev" ${currentPageProducts <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                <span>Page ${currentPageProducts + 1} / ${totalPages}</span>
                <button type="button" class="btn btn-outline btn-sm" id="prodNext" ${currentPageProducts >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
            </div>
        </div></div>`;
    }
    container.innerHTML = html;
    setupProductsTableActions();
    if (filtered.length > ROWS_PER_PAGE) {
        document.getElementById('prodPrev')?.addEventListener('click', () => { currentPageProducts--; renderProductsTable(); });
        document.getElementById('prodNext')?.addEventListener('click', () => { currentPageProducts++; renderProductsTable(); });
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

function setupProductsTableActions() {
    const container = document.getElementById('productsTableContainer');
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
        
        const productId = parseInt(select.dataset.productId, 10);
        if (Number.isNaN(productId)) {
            return;
        }
        
        switch (action) {
            case 'edit':
                editProduct(productId);
                break;
            case 'delete':
                deleteProduct(productId);
                break;
        }
        
        // Réinitialiser le select
        select.value = '';
    });
}

function formatCurrency(value) {
    const number = Number(value || 0);
    if (!Number.isFinite(number)) {
        return '—';
    }
    return currencyHelper.format(number, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    });
}

function formatProductType(value) {
    if (!value) {
        return '—';
    }
    return PRODUCT_TYPE_LABELS[value] || value;
}

// Afficher le modal de produit
async function showProductModal(productId = null) {
    const modal = document.getElementById('productModal');
    const title = document.getElementById('modalTitle');

    await ensureAssureursLoaded();
    currentEditingProduct = productId;

    if (productId) {
        title.textContent = 'Modifier un produit';
        await loadProductForEdit(productId);
    } else {
        title.textContent = 'Nouveau produit';
        resetProductForm();
    }

    modal.style.display = 'block';
}

// Fermer le modal
function closeProductModal() {
    document.getElementById('productModal').style.display = 'none';
    currentEditingProduct = null;
    resetProductForm();
}

function resetProductForm() {
    if (!productForm) {
        return;
    }
    productForm.reset();
    document.getElementById('productId').value = '';
    document.getElementById('statut').value = 'active';
    document.getElementById('type_produit').value = 'voyage';
    document.getElementById('paysEligibles').value = '';
    document.getElementById('conditions_sante').value = '';
    setPricingOption('fixe');
    preservedSpecificites = [];
    setSelectedZones([]);
    resetGuaranteeList();
    resetExclusionsList([]);
    tarifsPrimeLoadedIds = [];
    const tarifsBlock = document.getElementById('tarifsPrimeBlock');
    const tarifsBody = document.getElementById('tarifsPrimeBody');
    if (tarifsBlock) tarifsBlock.style.display = 'none';
    if (tarifsBody) tarifsBody.innerHTML = '';
    if (assureurSelectEl) {
        assureurSelectEl.value = '';
    }
    updateAssureurSummary('');
}

function setPricingOption(option) {
    const select = document.getElementById('cle_repartition');
    const chips = document.querySelectorAll('[data-pricing-option]');
    chips.forEach(chip => {
        if (chip.dataset.pricingOption === option) {
            chip.classList.add('active');
        } else {
            chip.classList.remove('active');
        }
    });
    if (select) {
        select.value = option;
    }
    const productId = document.getElementById('productId')?.value;
    const block = document.getElementById('tarifsPrimeBlock');
    const addBtn = document.getElementById('addTarifPrimeBtn');
    if (!block) return;
    const showTarifs = productId || option === 'par_duree' || option === 'par_destination';
    if (showTarifs) {
        block.style.display = 'block';
        ensureDestinationCountriesLoaded().then(() => {
            if (!productId) {
                const tbody = document.getElementById('tarifsPrimeBody');
                if (tbody && tbody.querySelectorAll('tr').length === 0) {
                    tarifsPrimeLoadedIds = [];
                    if (addBtn) addBtn.onclick = () => addTarifPrimeRow({});
                }
            }
        });
    } else {
        block.style.display = 'none';
    }
}

let destinationCountriesCache = [];
let tarifsPrimeLoadedIds = [];

function initPricingSelector() {
    const chips = document.querySelectorAll('[data-pricing-option]');
    chips.forEach(chip => {
        chip.addEventListener('click', () => setPricingOption(chip.dataset.pricingOption));
    });
}

async function ensureDestinationCountriesLoaded() {
    if (destinationCountriesCache.length) return destinationCountriesCache;
    try {
        const list = await apiCall('/destinations/countries');
        destinationCountriesCache = Array.isArray(list) ? list : [];
        return destinationCountriesCache;
    } catch (e) {
        console.warn('Impossible de charger les pays de destination', e);
        return [];
    }
}

function buildZoneSelectOptions(selectedValue) {
    let opts = '<option value="">— Toute zone —</option><option value="zone:MONDE">MONDE</option><option value="zone:EU">EU</option><option value="zone:AFRIQUE">AFRIQUE</option>';
    destinationCountriesCache.forEach((c) => {
        const val = `country:${c.id}`;
        const label = c.nom || c.code || val;
        opts += `<option value="${val}">${label}</option>`;
    });
    return opts;
}

function getZoneSelectValue(tarif) {
    if (tarif.destination_country_id) return `country:${tarif.destination_country_id}`;
    if (tarif.zone_code) return `zone:${tarif.zone_code}`;
    return '';
}

function parseZoneSelectValue(val) {
    if (!val) return { zone_code: null, destination_country_id: null };
    if (val.startsWith('zone:')) return { zone_code: val.slice(5), destination_country_id: null };
    if (val.startsWith('country:')) return { zone_code: null, destination_country_id: parseInt(val.slice(8), 10) };
    return { zone_code: null, destination_country_id: null };
}

function addTarifPrimeRow(tarif = {}) {
    const tbody = document.getElementById('tarifsPrimeBody');
    if (!tbody) return;
    const row = document.createElement('tr');
    row.dataset.tarifId = tarif.id || '';
    const zoneVal = getZoneSelectValue(tarif);
    const currencyLabel = currencyHelper.getSymbol ? currencyHelper.getSymbol() : (currencyHelper.getCurrency ? currencyHelper.getCurrency() : 'XAF');
    row.innerHTML = `
        <td><input type="number" class="tarif-input" data-field="duree_min_jours" min="0" value="${tarif.duree_min_jours ?? ''}" placeholder="0"></td>
        <td><input type="number" class="tarif-input" data-field="duree_max_jours" min="0" value="${tarif.duree_max_jours ?? ''}" placeholder="365"></td>
        <td><select class="tarif-input tarif-zone-select" data-field="zone">${buildZoneSelectOptions(zoneVal)}</select></td>
        <td><input type="number" class="tarif-input" data-field="age_min" min="0" max="120" value="${tarif.age_min ?? ''}" placeholder="—"></td>
        <td><input type="number" class="tarif-input" data-field="age_max" min="0" max="120" value="${tarif.age_max ?? ''}" placeholder="—"></td>
        <td><input type="number" class="tarif-input" data-field="prix" min="0" step="1" value="${tarif.prix ?? ''}" placeholder="0"></td>
        <td><input type="number" class="tarif-input" data-field="ordre_priorite" min="0" value="${tarif.ordre_priorite ?? 0}"></td>
        <td><button type="button" class="icon-button tarif-remove-btn" aria-label="Supprimer">&times;</button></td>
    `;
    const sel = row.querySelector('.tarif-zone-select');
    if (sel) sel.value = zoneVal;
    row.querySelector('.tarif-remove-btn').addEventListener('click', () => row.remove());
    tbody.appendChild(row);
}

function collectTarifRowsData() {
    const tbody = document.getElementById('tarifsPrimeBody');
    if (!tbody) return [];
    const rows = tbody.querySelectorAll('tr');
    const out = [];
    rows.forEach((tr) => {
        const dureeMin = parseInt(tr.querySelector('[data-field="duree_min_jours"]')?.value, 10);
        const dureeMax = parseInt(tr.querySelector('[data-field="duree_max_jours"]')?.value, 10);
        const zoneSel = tr.querySelector('[data-field="zone"]');
        const zoneParsed = zoneSel ? parseZoneSelectValue(zoneSel.value) : {};
        const ageMin = tr.querySelector('[data-field="age_min"]')?.value;
        const ageMax = tr.querySelector('[data-field="age_max"]')?.value;
        const prix = parseFloat(tr.querySelector('[data-field="prix"]')?.value);
        const ordre = parseInt(tr.querySelector('[data-field="ordre_priorite"]')?.value, 10);
        if (!Number.isFinite(dureeMin) || !Number.isFinite(dureeMax) || !Number.isFinite(prix)) return;
        out.push({
            tarifId: tr.dataset.tarifId || null,
            duree_min_jours: dureeMin,
            duree_max_jours: dureeMax,
            zone_code: zoneParsed.zone_code || null,
            destination_country_id: zoneParsed.destination_country_id || null,
            age_min: ageMin === '' || ageMin === undefined ? null : parseInt(ageMin, 10),
            age_max: ageMax === '' || ageMax === undefined ? null : parseInt(ageMax, 10),
            prix,
            ordre_priorite: Number.isNaN(ordre) ? 0 : ordre,
        });
    });
    return out;
}

async function loadTarifsPrime(productId) {
    const block = document.getElementById('tarifsPrimeBlock');
    const tbody = document.getElementById('tarifsPrimeBody');
    const addBtn = document.getElementById('addTarifPrimeBtn');
    if (!block || !tbody) return;
    block.style.display = 'none';
    tarifsPrimeLoadedIds = [];
    if (!productId) return;
    await ensureDestinationCountriesLoaded();
    block.style.display = 'block';
    try {
        const tarifs = await adminProductsAPI.getTarifs(productId);
        tbody.innerHTML = '';
        (tarifs || []).forEach((t) => {
            addTarifPrimeRow(t);
            const lastRow = tbody.querySelector('tr:last-child');
            if (lastRow) lastRow.dataset.tarifId = t.id;
            tarifsPrimeLoadedIds.push(t.id);
        });
    } catch (e) {
        console.warn('Chargement des tarifs échoué', e);
        tbody.innerHTML = '';
    }
    if (addBtn) {
        addBtn.onclick = () => addTarifPrimeRow({});
    }
}

async function saveTarifsPrime(productId) {
    const rowsData = collectTarifRowsData();
    const currentIds = rowsData.map((r) => r.tarifId).filter(Boolean);
    const toDelete = tarifsPrimeLoadedIds.filter((id) => !currentIds.includes(String(id)));
    for (const id of toDelete) {
        try {
            await adminProductsAPI.deleteTarif(productId, id);
        } catch (e) {
            console.warn('Suppression tarif échouée', id, e);
        }
    }
    for (const row of rowsData) {
        const { tarifId, ...data } = row;
        try {
            if (tarifId) {
                await adminProductsAPI.updateTarif(productId, tarifId, data);
            } else {
                await adminProductsAPI.createTarif(productId, data);
            }
        } catch (e) {
            console.warn('Sauvegarde tarif échouée', row, e);
        }
    }
}

function initGuaranteeBuilder() {
    const addButton = document.getElementById('addGuaranteeBtn');
    if (addButton) {
        addButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            addGuaranteeCard();
        });
    }
    resetGuaranteeList();
}

function resetExclusionsList(exclusions = []) {
    const list = document.getElementById('exclusionsList');
    if (!list) return;
    list.innerHTML = '';
    const items = Array.isArray(exclusions) ? exclusions : [];
    items.forEach((item) => addExclusionRow(normalizeExclusionItem(item)));
    if (items.length === 0) addExclusionRow({ cle: '', valeur: '' });
}

function normalizeExclusionItem(item) {
    if (item && typeof item === 'object' && ('cle' in item || 'valeur' in item)) {
        return { cle: item.cle || '', valeur: item.valeur || '' };
    }
    if (typeof item === 'string') {
        const idx = item.indexOf(' : ');
        if (idx !== -1) return { cle: item.slice(0, idx).trim(), valeur: item.slice(idx + 3).trim() };
        const idx2 = item.indexOf(':');
        if (idx2 !== -1) return { cle: item.slice(0, idx2).trim(), valeur: item.slice(idx2 + 1).trim() };
        return { cle: item, valeur: '' };
    }
    return { cle: '', valeur: '' };
}

function addExclusionRow(item = { cle: '', valeur: '' }) {
    const list = document.getElementById('exclusionsList');
    if (!list) return;
    const uid = `exclusion-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const row = document.createElement('div');
    row.className = 'exclusion-row';
    row.innerHTML = `
        <input type="text" id="${uid}-cle" data-field="cle" value="${escapeHtmlAttr(item.cle || '')}" placeholder="Clé (ex: couleur)">
        <span class="exclusion-sep">:</span>
        <input type="text" id="${uid}-valeur" data-field="valeur" value="${escapeHtmlAttr(item.valeur || '')}" placeholder="Valeur (ex: verte)">
        <button type="button" class="icon-button" data-action="remove-exclusion" aria-label="Supprimer">&times;</button>
    `;
    const removeBtn = row.querySelector('[data-action="remove-exclusion"]');
    if (removeBtn) removeBtn.addEventListener('click', () => row.remove());
    list.appendChild(row);
}

function escapeHtmlAttr(s) {
    if (s == null) return '';
    const div = document.createElement('div');
    div.textContent = String(s);
    return div.innerHTML.replace(/"/g, '&quot;');
}

function collectExclusions() {
    const list = document.getElementById('exclusionsList');
    if (!list) return [];
    const rows = list.querySelectorAll('.exclusion-row');
    const out = [];
    rows.forEach((row) => {
        const cle = row.querySelector('[data-field="cle"]')?.value?.trim();
        const valeur = row.querySelector('[data-field="valeur"]')?.value?.trim();
        if (cle || valeur) out.push({ cle: cle || '', valeur: valeur || '' });
    });
    return out;
}

function initExclusionsBuilder() {
    const addBtn = document.getElementById('addExclusionBtn');
    if (addBtn) addBtn.addEventListener('click', () => addExclusionRow({ cle: '', valeur: '' }));
    resetExclusionsList([]);
}

function resetGuaranteeList(garanties = DEFAULT_GARANTIES) {
    const list = document.getElementById('garantiesList');
    if (!list) {
        console.error('garantiesList element not found in resetGuaranteeList');
        return;
    }
    list.innerHTML = '';
    if (!garanties.length) {
        garanties = DEFAULT_GARANTIES;
    }
    console.log(`Resetting guarantee list with ${garanties.length} guarantees`);
    garanties.forEach((garantie, index) => {
        console.log(`Adding guarantee ${index + 1}:`, garantie.titre || garantie.nom || 'Untitled');
        addGuaranteeCard(garantie);
    });
    console.log(`Total guarantee cards in DOM: ${list.querySelectorAll('.guarantee-card').length}`);
}

function addGuaranteeCard(garantie = {}) {
    const list = document.getElementById('garantiesList');
    if (!list) {
        console.error('garantiesList element not found');
        return;
    }
    const uid = `garantie-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const currencyLabel = currencyHelper.getSymbol
        ? currencyHelper.getSymbol()
        : (currencyHelper.getCurrency ? currencyHelper.getCurrency() : 'XOF');
    const card = document.createElement('div');
    card.className = 'guarantee-card';
    card.innerHTML = `
        <div class="guarantee-card__header">
            <div>
                <strong>Garantie</strong>
                <p>Décrivez les conditions de prise en charge.</p>
            </div>
            <button type="button" class="icon-button" data-action="remove-guarantee" aria-label="Supprimer la garantie">&times;</button>
        </div>
        <div class="guarantee-card__grid">
            <div class="form-group">
                <label for="${uid}-titre">Intitulé *</label>
                <input type="text" id="${uid}-titre" data-field="titre" value="${garantie.titre || ''}" placeholder="Ex: Frais médicaux">
            </div>
            <div class="form-group">
                <label for="${uid}-franchise">Franchise (${currencyLabel})</label>
                <input type="number" id="${uid}-franchise" data-field="franchise" min="0" step="1" value="${garantie.franchise ?? ''}" placeholder="Ex: 0">
            </div>
            <div class="form-group">
                <label for="${uid}-capitaux">Capitaux (${currencyLabel})</label>
                <input type="number" id="${uid}-capitaux" data-field="capitaux" min="0" step="1" value="${garantie.capitaux ?? garantie.plafond ?? ''}" placeholder="Ex: 5000000">
            </div>
            <div class="form-group">
                <label>Obligatoire</label>
                <label class="switch">
                    <input type="checkbox" data-field="obligatoire" ${garantie.obligatoire ? 'checked' : ''}>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="form-group full-width">
                <label for="${uid}-description">Description *</label>
                <textarea id="${uid}-description" rows="2" data-field="description" placeholder="Que couvre cette garantie ?">${garantie.description || ''}</textarea>
            </div>
        </div>
    `;

    const removeBtn = card.querySelector('[data-action="remove-guarantee"]');
    if (removeBtn) {
        removeBtn.addEventListener('click', () => {
            const totalCards = list.querySelectorAll('.guarantee-card').length;
            if (totalCards <= 1) {
                showAlert('Au moins une garantie est requise.', 'error');
                return;
            }
            card.remove();
        });
    }

    list.appendChild(card);
    const total = list.querySelectorAll('.guarantee-card').length;
    console.log('Guarantee card added. Total in DOM:', total);
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function collectGaranties() {
    const list = document.getElementById('garantiesList');
    if (!list) {
        console.error('garantiesList not found');
        return [];
    }
    
    const cards = list.querySelectorAll('.guarantee-card');
    const garanties = [];

    console.log(`Collecting ${cards.length} guarantee cards`);

    cards.forEach((card, index) => {
        const titre = card.querySelector('[data-field="titre"]')?.value.trim();
        const description = card.querySelector('[data-field="description"]')?.value.trim();
        const franchiseRaw = card.querySelector('[data-field="franchise"]')?.value;
        const capitauxRaw = card.querySelector('[data-field="capitaux"]')?.value;
        const obligatoire = card.querySelector('[data-field="obligatoire"]')?.checked ?? false;

        console.log(`Card ${index + 1}: titre="${titre}", description="${description?.substring(0, 30)}..."`);

        if (!titre && !description) {
            console.warn(`Card ${index + 1} skipped: missing titre and description`);
            return;
        }

        garanties.push({
            titre,
            description,
            franchise: franchiseRaw ? Number(franchiseRaw) : null,
            capitaux: capitauxRaw ? Number(capitauxRaw) : null,
            obligatoire,
        });
    });

    const filtered = garanties.filter(g => g.titre && g.description);
    console.log(`Collected ${filtered.length} valid guarantees`);
    return filtered;
}

function initZoneSelector() {
    const selector = document.getElementById('zonesSelector');
    if (!selector) {
        return;
    }

    selector.innerHTML = '';
    ZONE_PRESETS.forEach(zone => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'chip-option';
        chip.dataset.zoneValue = zone;
        chip.textContent = zone;
        chip.addEventListener('click', () => togglePresetZone(zone));
        selector.appendChild(chip);
    });

    const customInput = document.getElementById('customZoneInput');
    if (customInput) {
        customInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && customInput.value.trim()) {
                event.preventDefault();
                addCustomZone(customInput.value.trim());
                customInput.value = '';
            }
        });
    }

    setSelectedZones([]);
}

function togglePresetZone(zone) {
    if (selectedZones.has(zone)) {
        selectedZones.delete(zone);
    } else {
        selectedZones.set(zone, { value: zone, isCustom: false });
    }
    renderSelectedZones();
}

function addCustomZone(zone) {
    selectedZones.set(zone, { value: zone, isCustom: true });
    renderSelectedZones();
}

function removeZone(zone) {
    selectedZones.delete(zone);
    renderSelectedZones();
}

function setSelectedZones(zones = []) {
    selectedZones = new Map();
    zones.forEach(zone => {
        selectedZones.set(zone, {
            value: zone,
            isCustom: !ZONE_PRESETS.includes(zone),
        });
    });
    renderSelectedZones();
}

function renderSelectedZones() {
    const chipsContainer = document.getElementById('selectedZonesChips');
    const presetButtons = document.querySelectorAll('[data-zone-value]');

    if (chipsContainer) {
        chipsContainer.innerHTML = '';
        if (selectedZones.size === 0) {
            chipsContainer.innerHTML = '<span class="text-muted">Aucune zone sélectionnée</span>';
        } else {
            selectedZones.forEach(({ value }) => {
                const chip = document.createElement('span');
                chip.className = 'selected-zone-chip';
                chip.textContent = value;
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.innerHTML = '&times;';
                removeBtn.addEventListener('click', () => removeZone(value));
                chip.appendChild(removeBtn);
                chipsContainer.appendChild(chip);
            });
        }
    }

    presetButtons.forEach(button => {
        const value = button.dataset.zoneValue;
        if (selectedZones.has(value)) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
}

function getSelectedZones() {
    return Array.from(selectedZones.values()).map(item => item.value);
}

function parseCommaSeparated(value) {
    if (!value) {
        return [];
    }
    return value.split(',').map(entry => entry.trim()).filter(Boolean);
}

function buildZonesPayload(typeProduit) {
    const zones = getSelectedZones();
    const paysEligibles = parseCommaSeparated(document.getElementById('paysEligibles')?.value);

    const payload = {};
    if (zones.length) {
        payload.zones = zones;
    }
    if (paysEligibles.length) {
        payload.pays_eligibles = paysEligibles;
    }

    const specificites = [...preservedSpecificites];
    if (typeProduit) {
        specificites.push(`type_produit:${typeProduit}`);
    }
    if (specificites.length) {
        payload.specificites = specificites;
    }

    return Object.keys(payload).length ? payload : null;
}

async function loadProductForEdit(productId) {
    try {
        const product = await adminProductsAPI.getById(productId);
        await ensureAssureursLoaded();
        populateProductForm(product);
    } catch (error) {
        console.error('Erreur lors du chargement du produit:', error);
        showAlert(error.message || 'Impossible de charger ce produit.', 'error');
    }
}

function populateProductForm(product) {
    preservedSpecificites = (product.zones_geographiques?.specificites || [])
        .filter(item => !String(item).startsWith('type_produit:'));

    // Gérer les valeurs qui pourraient être undefined (compatibilité avec les alias)
    const nom = product.nom || product.name || '';
    const cout = product.cout !== undefined && product.cout !== null ? product.cout : (product.price !== undefined && product.price !== null ? product.price : '');
    const estActif = product.est_actif !== undefined ? product.est_actif : (product.isActive !== undefined ? product.isActive : true);

    document.getElementById('productId').value = product.id || '';
    document.getElementById('code').value = product.code || '';
    document.getElementById('nom').value = nom;
    document.getElementById('description').value = product.description || '';
    document.getElementById('cout').value = cout;
    document.getElementById('cle_repartition').value = product.cle_repartition || 'fixe';
    document.getElementById('commission_assureur_pct').value = product.commission_assureur_pct ?? '';
    document.getElementById('statut').value = estActif ? 'active' : 'inactive';
    document.getElementById('duree_validite_jours').value = product.duree_validite_jours || '';
    const pg = product.primes_generees || {};
    document.getElementById('prime_nette').value = pg.prime_nette ?? '';
    document.getElementById('accessoire').value = pg.accessoire ?? '';
    document.getElementById('taxes').value = pg.taxes ?? '';
    document.getElementById('prime_total').value = pg.prime_total ?? '';
    document.getElementById('age_minimum').value = product.age_minimum ?? '';
    document.getElementById('age_maximum').value = product.age_maximum ?? '';
    document.getElementById('duree_max_jours').value = product.duree_max_jours ?? '';
    document.getElementById('conditions_sante').value = product.conditions_sante || '';
    document.getElementById('paysEligibles').value = (product.zones_geographiques?.pays_eligibles || []).join(', ');

    const typeProduit = extractTypeFromProduct(product);
    document.getElementById('type_produit').value = typeProduit || 'voyage';
    setPricingOption(product.cle_repartition || 'fixe');

    const zones = product.zones_geographiques?.zones || [];
    setSelectedZones(zones);

    if (assureurSelectEl) {
        const assureurId = product.assureur_id ? String(product.assureur_id) : '';
        assureurSelectEl.value = assureurId;
        updateAssureurSummary(assureurId, product.assureur || '');
    }

    const raw = Array.isArray(product.garanties) ? product.garanties : [];
    console.log(`Loading product: received ${raw.length} guarantees from backend`);
    console.log('Raw guarantees:', JSON.stringify(raw, null, 2));
    
    const garanties = raw.map((g) => ({
        ...g,
        capitaux: g.capitaux ?? g.plafond,
    }));
    
    console.log(`Prepared ${garanties.length} guarantees for display`);
    resetGuaranteeList(garanties.length ? garanties : DEFAULT_GARANTIES);

    const rawExclusions = Array.isArray(product.exclusions_generales) ? product.exclusions_generales : [];
    resetExclusionsList(rawExclusions.length ? rawExclusions : []);

    loadTarifsPrime(product.id);
}

function extractTypeFromProduct(product) {
    const specificites = product.zones_geographiques?.specificites || [];
    const typeTag = specificites.find(item => String(item).startsWith('type_produit:'));
    if (typeTag) {
        return typeTag.split(':')[1];
    }
    if (product.categories_assures && product.categories_assures.length > 0) {
        return product.categories_assures[0];
    }
    return 'voyage';
}

// Éditer un produit
async function editProduct(productId) {
    showProductModal(productId);
}

// Supprimer un produit
async function deleteProduct(productId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce produit ?')) {
        return;
    }

    try {
        await adminProductsAPI.delete(productId);
        showAlert('Produit supprimé avec succès.', 'success');
        loadProducts();
    } catch (error) {
        showAlert(error.message || 'Impossible de supprimer ce produit.', 'error');
    }
}

async function handleProductFormSubmit(event) {
    event.preventDefault();
    const submitBtn = document.getElementById('submitProductBtn');
    if (!submitBtn) {
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Enregistrement...';

    const list = document.getElementById('garantiesList');
    const cardCount = list ? list.querySelectorAll('.guarantee-card').length : 0;
    console.log('Submit: guarantee cards in DOM before collect:', cardCount);

    const garanties = collectGaranties();
    console.log('Submit: collected guarantees count:', garanties.length, garanties.map(g => g.titre));

    if (garanties.length === 0) {
        showAlert('Ajoutez au moins une garantie complète (Intitulé + Description).', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
        return;
    }

    const productId = document.getElementById('productId').value;
    const typeProduit = document.getElementById('type_produit').value;

    const codeValue = document.getElementById('code').value?.trim();
    const nomValue = document.getElementById('nom').value?.trim();
    const coutValue = Number(document.getElementById('cout').value);

    if (!codeValue) {
        showAlert('Le code produit est obligatoire.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
        return;
    }

    if (!nomValue) {
        showAlert('Le nom du produit est obligatoire.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
        return;
    }

    if (!Number.isFinite(coutValue) || coutValue <= 0) {
        const currencyLabel = currencyHelper.getSymbol
            ? currencyHelper.getSymbol()
            : (currencyHelper.getCurrency ? currencyHelper.getCurrency() : 'XOF');
        showAlert(`Le prix fixe doit être supérieur à 0 ${currencyLabel}.`, 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
        return;
    }

    const selectedAssureurId = assureurSelectEl ? assureurSelectEl.value : '';
    if (!assureursOptions.length) {
        showAlert('Créez un assureur avant d’enregistrer un produit.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
        return;
    }
    if (!selectedAssureurId) {
        showAlert('Sélectionnez un assureur pour ce produit.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
        return;
    }
    const selectedAssureur = getAssureurById(selectedAssureurId);
    if (!selectedAssureur) {
        showAlert('Assureur sélectionné introuvable. Rafraîchissez la liste.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
        return;
    }

    const primeNette = parseOptionalInt(document.getElementById('prime_nette')?.value);
    const accessoire = parseOptionalInt(document.getElementById('accessoire')?.value);
    const taxes = parseOptionalInt(document.getElementById('taxes')?.value);
    const primeTotal = parseOptionalInt(document.getElementById('prime_total')?.value);
    const primesGenerees =
        primeNette != null || accessoire != null || taxes != null || primeTotal != null
            ? {
                prime_nette: primeNette ?? null,
                accessoire: accessoire ?? null,
                taxes: taxes ?? null,
                prime_total: primeTotal ?? null,
            }
            : null;

    const payload = {
        code: codeValue,
        nom: nomValue,
        description: document.getElementById('description').value?.trim() || null,
        assureur_id: Number(selectedAssureurId),
        assureur: selectedAssureur.nom,
        cout: coutValue,
        cle_repartition: document.getElementById('cle_repartition').value,
        commission_assureur_pct: parseOptionalFloat(document.getElementById('commission_assureur_pct')?.value),
        duree_validite_jours: parseOptionalInt(document.getElementById('duree_validite_jours').value),
        est_actif: document.getElementById('statut').value === 'active',
        age_minimum: parseOptionalInt(document.getElementById('age_minimum').value),
        age_maximum: parseOptionalInt(document.getElementById('age_maximum').value),
        duree_max_jours: parseOptionalInt(document.getElementById('duree_max_jours').value),
        conditions_sante: document.getElementById('conditions_sante').value?.trim() || null,
        garanties: Array.from(garanties),
        exclusions_generales: collectExclusions(),
        primes_generees: primesGenerees,
    };

    const zonesPayload = buildZonesPayload(typeProduit);
    if (zonesPayload) {
        payload.zones_geographiques = zonesPayload;
    }

    const numGaranties = payload.garanties.length;
    console.log(`Sending ${numGaranties} guarantee(s):`, payload.garanties.map(g => g.titre));
    if (numGaranties > 1) {
        console.warn('Multiple guarantees being sent:', numGaranties);
    }

    try {
        const tarifsToCreate = !productId ? collectTarifRowsData() : [];
        if (productId) {
            await adminProductsAPI.update(Number(productId), payload);
            await saveTarifsPrime(Number(productId));
            showAlert('Produit mis à jour avec succès.', 'success');
        } else {
            const created = await adminProductsAPI.create(payload);
            if (created && created.id && tarifsToCreate.length > 0) {
                for (const row of tarifsToCreate) {
                    const { tarifId, ...data } = row;
                    try {
                        await adminProductsAPI.createTarif(created.id, data);
                    } catch (e) {
                        console.warn('Création tarif échouée', row, e);
                    }
                }
            }
            showAlert('Produit créé avec succès.', 'success');
        }

        closeProductModal();
        await loadProducts();
    } catch (error) {
        console.error('Erreur lors de la sauvegarde du produit:', error);
        showAlert(error.message || 'Impossible d’enregistrer ce produit.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
    }
}

function parseOptionalInt(value) {
    if (value === undefined || value === null || value === '') {
        return null;
    }
    const parsed = parseInt(value, 10);
    return Number.isNaN(parsed) ? null : parsed;
}

function parseOptionalFloat(value) {
    if (value === undefined || value === null || value === '') {
        return null;
    }
    const parsed = parseFloat(value);
    return Number.isNaN(parsed) ? null : parsed;
}

function initializeProductForm() {
    productForm = document.getElementById('productForm');
    if (!productForm) {
        return;
    }
    assureurSelectEl = document.getElementById('assureurSelect');
    assureurSummaryCard = document.getElementById('assureurSummaryCard');
    assureurHelperText = document.getElementById('assureurHelperText');
    submitProductBtn = document.getElementById('submitProductBtn');
    if (assureurSelectEl) {
        assureurSelectEl.addEventListener('change', handleAssureurChange);
    }

    initPricingSelector();
    initGuaranteeBuilder();
    initExclusionsBuilder();
    initZoneSelector();
    productForm.addEventListener('submit', handleProductFormSubmit);
    ensureAssureursLoaded();
}

// Fermer le modal en cliquant en dehors
window.onclick = function (event) {
    const modal = document.getElementById('productModal');
    if (event.target === modal) {
        closeProductModal();
    }
};

document.addEventListener('DOMContentLoaded', () => {
    initializeProductForm();
    loadProducts();
    const searchProductsEl = document.getElementById('searchProducts');
    if (searchProductsEl) {
        searchProductsEl.addEventListener('input', () => {
            searchProductsTerm = (searchProductsEl.value || '').trim().toLowerCase();
            if (productsCache.length) {
                renderProductsTable();
            }
        });
    }
});

