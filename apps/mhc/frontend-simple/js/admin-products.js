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

    listTarifs: (productId) => apiCall(`/admin/products/${productId}/tarifs`),

    createTarif: (productId, data) =>
        apiCall(`/admin/products/${productId}/tarifs`, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    updateTarif: (productId, tarifId, data) =>
        apiCall(`/admin/products/${productId}/tarifs/${tarifId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    deleteTarif: (productId, tarifId) =>
        apiCall(`/admin/products/${productId}/tarifs/${tarifId}`, {
            method: 'DELETE',
        }),
};

const adminAssureursAPI = {
    list: async () => apiCall('/admin/assureurs'),
};

/** Métadonnée zones_geographiques.specificites — ce back-office ne gère que l’assurance voyage. */
const PRODUCT_KIND_VOYAGE = 'voyage';

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

/**
 * Garanties-type Mobility Health : tableau 2 colonnes (garantie + capitaux), texte libre pour les capitaux.
 */
const DEFAULT_GARANTIES = [
    { titre: 'Assistance et suivi médical', capitaux: '' },
    { titre: 'Transport médicalisé', capitaux: '1 000 000 FCFA' },
    { titre: 'Frais médicaux et hospitalisations d’urgence à l’étranger', capitaux: '15 000 000 FCFA' },
    { titre: 'Urgence dentaire à l’étranger', capitaux: '100 000 FCFA' },
    {
        titre: 'Rapatriement de corps en cas de décès',
        capitaux: '5 000 000 FCFA Soit 1 000 000 FCFA achat cercueil',
    },
    { titre: 'Rapatriement des proches parents', capitaux: '1 billet d’avion A/R en éco' },
    { titre: 'Accompagnement des enfants de moins de 15 ans', capitaux: '1 billet d’avion A/R en éco' },
    { titre: 'Visite d’un proche parent', capitaux: '1 billet d’avion A/R en éco' },
    { titre: 'Voyage d’un parent sur le lieu du décès', capitaux: '1 billet d’avion A/R en éco' },
    {
        titre: 'Prolongation du séjour d’un proche parent',
        capitaux: '200 000 FCFA pour la durée du séjour',
    },
    { titre: 'Prise en charge des frais d’hébergement', capitaux: '7 jours maximum / 50 000 FCFA par nuit' },
];

/** Exclusions : colonnes Référence + Exclusion (modèle joint). */
const DEFAULT_EXCLUSIONS = [
    {
        reference: 'Exclusion 1',
        exclusion:
            'Les dommages consécutifs à une faute intentionnelle ou dolosive de l’assuré, le suicide ou la tentative de suicide de l’assuré',
    },
    {
        reference: 'Exclusion 2',
        exclusion:
            'Les dommages consécutifs à la consommation d’alcool et/ou l’absorption par l’assuré de médicaments, drogues ou stupéfiants, non prescrits médicalement',
    },
    {
        reference: 'Exclusion 3',
        exclusion:
            'Les dommages causés par la guerre civile ou étrangère, les actes de terrorisme, les émeutes, mouvements populaires, coups d’état, prises d’otage ou la grève',
    },
    {
        reference: 'Exclusion 4',
        exclusion:
            'Les convalescences et les affections en cours de traitement non encore consolidées ainsi que les maladies ou blessures préexistantes diagnostiquées et/ou traitées, ayant fait l’objet d’une hospitalisation dans les 6 mois précédant la demande d’assistance',
    },
    {
        reference: 'Exclusion 5',
        exclusion: 'L’interruption volontaire de grossesse, les fécondations in vitro',
    },
    {
        reference: 'Exclusion 6',
        exclusion: 'Les personnes âgées de plus de 90 ans au jour de la souscription',
    },
    {
        reference: 'Exclusion 7',
        exclusion: 'Les personnes atteintes de maladies mentales diagnostiquées avant la souscription',
    },
    {
        reference: 'Exclusion 8',
        exclusion:
            'Les dommages ou détérioration résultant d’éraflures, de rayures, de déchirures, de taches, d’accident de fumeur',
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
/** Snapshot couverture (API) au chargement du produit — repli si la matrice est vidée */
let productCoverageSnapshot = null;
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
            return nom.includes(searchProductsTerm) || code.includes(searchProductsTerm) ||
                assureurName.includes(searchProductsTerm);
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
    html += '<th>Code</th><th>Nom</th><th>Assureur</th><th>Tarif base</th><th>Statut</th><th>Actions</th>';
    html += '</tr></thead><tbody>';

    pageData.forEach(product => {
        const nom = product.nom || product.name || '—';
        const cout = product.cout !== undefined && product.cout !== null ? product.cout : (product.price !== undefined && product.price !== null ? product.price : 0);
        const estActif = product.est_actif !== undefined ? product.est_actif : (product.isActive !== undefined ? product.isActive : true);
        const statusClass = estActif ? 'status-active' : 'status-inactive';
        const statusText = estActif ? 'Actif' : 'Inactif';
        const cost = formatCurrency(cout);
        const assureurName = (product.assureur_details && product.assureur_details.nom) || product.assureur || '—';

        html += `
            <tr>
                <td>${product.code || '—'}</td>
                <td>${nom}</td>
                <td>${assureurName}</td>
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
    document.getElementById('paysEligibles').value = '';
    document.getElementById('conditions_sante').value = '';
    ['age_minimum', 'age_maximum', 'duree_max_jours'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    setPricingOption('fixe');
    const coutEl = document.getElementById('cout');
    if (coutEl) coutEl.value = '1';
    const commEl = document.getElementById('commission_assureur_pct');
    if (commEl) commEl.value = '';
    const dvEl = document.getElementById('duree_validite_jours');
    if (dvEl) dvEl.value = '';
    preservedSpecificites = [];
    productCoverageSnapshot = null;
    setSelectedZones([]);
    resetGuaranteeList();
    resetExclusionsList(DEFAULT_EXCLUSIONS);
    resetProductTarifsMatrix(null);
    ['surprime_moins_18_pct', 'surprime_70_75_pct', 'surprime_76_80_pct', 'surprime_81_89_pct'].forEach((fid) => {
        const el = document.getElementById(fid);
        if (el) el.value = '';
    });
    const qr = document.getElementById('quoteSimResult');
    if (qr) qr.textContent = '';
    if (assureurSelectEl) {
        assureurSelectEl.value = '';
    }
    updateAssureurSummary('');
    void loadProductGrilleFinale('');
}

function setPricingOption(option) {
    const cr = document.getElementById('cle_repartition');
    if (cr) {
        cr.value = option;
    }
    const block = document.getElementById('tarifsPrimeBlock');
    if (block) {
        block.style.display = 'block';
    }
}

function initPricingSelector() {
    /* Puces « mode tarif » retirées du formulaire : clé de répartition = champ caché (fixe par défaut). */
}

function initGuaranteeBuilder() {
    const addButton = document.getElementById('addGuaranteeBtn');
    if (addButton) {
        addButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            addGuaranteeRow({});
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
    if (items.length === 0) addExclusionRow({ libelle: '', valeur: '' });
}

function normalizeExclusionItem(item) {
    if (item && typeof item === 'object') {
        const refRaw = item.reference ?? item.libelle ?? item.cle ?? '';
        const excRaw = item.exclusion ?? item.valeur ?? '';
        if (refRaw !== '' || excRaw !== '') {
            return {
                reference: String(refRaw).trim(),
                exclusion: String(excRaw).trim(),
            };
        }
    }
    if (typeof item === 'string') {
        const idx = item.indexOf(' : ');
        if (idx !== -1) {
            return {
                reference: item.slice(0, idx).trim(),
                exclusion: item.slice(idx + 3).trim(),
            };
        }
        const idx2 = item.indexOf(':');
        if (idx2 !== -1) {
            return {
                reference: item.slice(0, idx2).trim(),
                exclusion: item.slice(idx2 + 1).trim(),
            };
        }
        return { reference: '', exclusion: item.trim() };
    }
    return { reference: '', exclusion: '' };
}

function addExclusionRow(item = { reference: '', exclusion: '' }) {
    const list = document.getElementById('exclusionsList');
    if (!list) return;
    const norm = normalizeExclusionItem(item);
    const uid = `exclusion-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const row = document.createElement('div');
    row.className = 'exclusion-row';
    row.innerHTML = `
        <input type="text" id="${uid}-reference" data-field="reference" value="${escapeHtmlAttr(norm.reference)}" placeholder="Référence (ex. Exclusion 1)" aria-label="Référence">
        <input type="text" id="${uid}-exclusion" data-field="exclusion" value="${escapeHtmlAttr(norm.exclusion)}" placeholder="Texte de l’exclusion" aria-label="Exclusion">
        <button type="button" class="icon-button" data-action="remove-exclusion" aria-label="Supprimer la ligne">&times;</button>
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
        const reference =
            row.querySelector('[data-field="reference"]')?.value?.trim() ||
            row.querySelector('[data-field="libelle"]')?.value?.trim() ||
            row.querySelector('[data-field="cle"]')?.value?.trim() ||
            '';
        const exclusion =
            row.querySelector('[data-field="exclusion"]')?.value?.trim() ||
            row.querySelector('[data-field="valeur"]')?.value?.trim() ||
            '';
        if (reference || exclusion) {
            out.push({
                reference: reference || '',
                exclusion: exclusion || '',
            });
        }
    });
    return out;
}

function parseSurprimePctInput(elementId) {
    const v = parseOptionalFloat(document.getElementById(elementId)?.value);
    return v == null ? 0 : v;
}

/**
 * Agrège zone / durée max / bornes d’âge à partir des lignes valides de la matrice (DOM).
 * Une ligne est valide si durées min/max cohérentes et tarif ≥ 0.
 */
function aggregateTarifMatrixCoverage() {
    const tbody = document.getElementById('productTarifsMatrixBody');
    if (!tbody) {
        return {
            hasValidRows: false,
            age_min: null,
            age_max: null,
            duree_max: null,
            zoneCodes: [],
        };
    }
    const ageMins = [];
    const ageMaxs = [];
    let dureeMax = null;
    const zoneSet = new Set();
    let countValid = 0;

    tbody.querySelectorAll('tr').forEach((tr) => {
        const dm = parseInt(tr.querySelector('[data-tf="duree_min"]')?.value, 10);
        const dx = parseInt(tr.querySelector('[data-tf="duree_max"]')?.value, 10);
        const prix = parseFloat(tr.querySelector('[data-tf="prix"]')?.value);
        if (!Number.isFinite(dm) || !Number.isFinite(dx) || dm > dx) {
            return;
        }
        if (!Number.isFinite(prix) || prix < 0) {
            return;
        }
        countValid += 1;
        if (dureeMax == null || dx > dureeMax) {
            dureeMax = dx;
        }

        const aminRaw = tr.querySelector('[data-tf="age_min"]')?.value;
        const amaxRaw = tr.querySelector('[data-tf="age_max"]')?.value;
        if (aminRaw !== '' && aminRaw !== undefined) {
            const a = parseInt(aminRaw, 10);
            if (Number.isFinite(a)) {
                ageMins.push(a);
            }
        }
        if (amaxRaw !== '' && amaxRaw !== undefined) {
            const a = parseInt(amaxRaw, 10);
            if (Number.isFinite(a)) {
                ageMaxs.push(a);
            }
        }

        const zc = tr.querySelector('[data-tf="zone_code"]')?.value?.trim();
        if (zc) {
            zoneSet.add(zc);
        }
    });

    if (countValid === 0) {
        return {
            hasValidRows: false,
            age_min: null,
            age_max: null,
            duree_max: null,
            zoneCodes: [],
        };
    }
    return {
        hasValidRows: true,
        age_min: ageMins.length ? Math.min(...ageMins) : null,
        age_max: ageMaxs.length ? Math.max(...ageMaxs) : null,
        duree_max: dureeMax,
        zoneCodes: Array.from(zoneSet),
    };
}

function syncCoverageAfterMatrixChange() {
    const agg = aggregateTarifMatrixCoverage();
    const setNum = (id, v) => {
        const el = document.getElementById(id);
        if (!el) {
            return;
        }
        if (v == null || v === '') {
            el.value = '';
        } else {
            el.value = String(v);
        }
    };
    if (agg.hasValidRows) {
        setNum('age_minimum', agg.age_min);
        setNum('age_maximum', agg.age_max);
        setNum('duree_max_jours', agg.duree_max);
        setSelectedZones(agg.zoneCodes);
        return;
    }
    if (productCoverageSnapshot) {
        setNum('age_minimum', productCoverageSnapshot.age_minimum);
        setNum('age_maximum', productCoverageSnapshot.age_maximum);
        setNum('duree_max_jours', productCoverageSnapshot.duree_max_jours);
        setSelectedZones(productCoverageSnapshot.zones || []);
        return;
    }
    setNum('age_minimum', '');
    setNum('age_maximum', '');
    setNum('duree_max_jours', '');
    setSelectedZones([]);
}

/** Les lignes matrice sont enregistrées en API par produit : il faut un id (après 1er enregistrement). */
function syncTarifMatrixAddButtonState() {
    const btn = document.getElementById('addProductTarifRowBtn');
    if (!btn) return;
    const pid = document.getElementById('productId')?.value?.trim();
    const hasId = Boolean(pid);
    btn.disabled = !hasId;
    btn.title = hasId
        ? 'Ajouter une ligne (enregistrée dès que les champs sont valides)'
        : 'Enregistrez le produit une première fois avec « Enregistrer », puis cliquez ici.';
}

function resetProductTarifsMatrix(productId) {
    const tbody = document.getElementById('productTarifsMatrixBody');
    const hint = document.getElementById('productTarifsMatrixHint');
    if (tbody) tbody.innerHTML = '';
    if (hint) {
        hint.textContent = productId
            ? ''
            : 'Enregistrez d’abord le produit pour activer « + Ajouter une ligne tarifaire » (sauvegarde serveur à chaque ligne).';
    }
    syncTarifMatrixAddButtonState();
}

async function loadProductTarifsMatrix(productId) {
    resetProductTarifsMatrix(productId);
    if (!productId) {
        syncCoverageAfterMatrixChange();
        return;
    }
    try {
        const rows = await adminProductsAPI.listTarifs(productId);
        rows.forEach((r) => appendTarifMatrixRow(r));
    } catch (e) {
        console.error(e);
        showAlert(e.message || 'Impossible de charger les tarifs produit.', 'error');
    }
    syncCoverageAfterMatrixChange();
    syncTarifMatrixAddButtonState();
}

function appendTarifMatrixRow(row = {}) {
    const tbody = document.getElementById('productTarifsMatrixBody');
    if (!tbody) return;
    const tr = document.createElement('tr');
    const id = row.id != null ? String(row.id) : '';
    tr.dataset.tarifId = id;
    tr.innerHTML = `
        <td><input type="text" data-tf="zone_code" class="tarif-input" style="min-width:100px" value="${escapeHtmlAttr(row.zone_code || '')}" placeholder="Code zone"></td>
        <td><input type="number" data-tf="duree_min" class="tarif-input" min="0" style="width:72px" value="${row.duree_min_jours ?? ''}"></td>
        <td><input type="number" data-tf="duree_max" class="tarif-input" min="0" style="width:72px" value="${row.duree_max_jours ?? ''}"></td>
        <td><input type="number" data-tf="age_min" class="tarif-input" min="0" max="120" style="width:64px" value="${row.age_min ?? ''}" placeholder="—"></td>
        <td><input type="number" data-tf="age_max" class="tarif-input" min="0" max="120" style="width:64px" value="${row.age_max ?? ''}" placeholder="—"></td>
        <td><input type="number" data-tf="prix" class="tarif-input" min="0" step="1" style="width:100px" value="${row.prix ?? ''}"></td>
        <td><input type="number" data-tf="ordre" class="tarif-input" min="0" style="width:64px" value="${row.ordre_priorite ?? 0}"></td>
        <td><button type="button" class="icon-button" data-action="del-tarif" aria-label="Supprimer">&times;</button></td>
    `;
    tr.querySelectorAll('input[data-tf]').forEach((inp) => {
        inp.addEventListener('blur', () => saveTarifMatrixRow(tr));
    });
    tr.querySelector('[data-action="del-tarif"]')?.addEventListener('click', () => deleteTarifMatrixRow(tr));
    tbody.appendChild(tr);
}

async function saveTarifMatrixRow(tr) {
    const productId = document.getElementById('productId')?.value;
    if (!productId) return;
    const zc = tr.querySelector('[data-tf="zone_code"]')?.value?.trim() || null;
    const dm = parseInt(tr.querySelector('[data-tf="duree_min"]')?.value, 10);
    const dx = parseInt(tr.querySelector('[data-tf="duree_max"]')?.value, 10);
    const aminRaw = tr.querySelector('[data-tf="age_min"]')?.value;
    const amaxRaw = tr.querySelector('[data-tf="age_max"]')?.value;
    const prix = parseFloat(tr.querySelector('[data-tf="prix"]')?.value);
    const op = parseInt(tr.querySelector('[data-tf="ordre"]')?.value, 10);
    const ordre_priorite = Number.isFinite(op) ? op : 0;
    if (!Number.isFinite(dm) || !Number.isFinite(dx) || dm > dx) {
        return;
    }
    if (!Number.isFinite(prix) || prix < 0) {
        return;
    }
    let age_min = null;
    let age_max = null;
    if (aminRaw !== '' && aminRaw !== undefined) {
        age_min = parseInt(aminRaw, 10);
        if (Number.isNaN(age_min)) return;
    }
    if (amaxRaw !== '' && amaxRaw !== undefined) {
        age_max = parseInt(amaxRaw, 10);
        if (Number.isNaN(age_max)) return;
    }
    const body = {
        duree_min_jours: dm,
        duree_max_jours: dx,
        zone_code: zc,
        destination_country_id: null,
        age_min,
        age_max,
        prix,
        ordre_priorite,
        currency: 'XAF',
    };
    const tid = tr.dataset.tarifId;
    try {
        if (tid) {
            await adminProductsAPI.updateTarif(productId, tid, body);
        } else {
            const created = await adminProductsAPI.createTarif(productId, body);
            tr.dataset.tarifId = String(created.id);
        }
        syncCoverageAfterMatrixChange();
    } catch (e) {
        showAlert(e.message || 'Sauvegarde de la ligne tarifaire impossible.', 'error');
    }
}

async function deleteTarifMatrixRow(tr) {
    const productId = document.getElementById('productId')?.value;
    const tid = tr.dataset.tarifId;
    if (tid && productId) {
        try {
            await adminProductsAPI.deleteTarif(productId, tid);
        } catch (e) {
            showAlert(e.message || 'Suppression impossible.', 'error');
            return;
        }
    }
    tr.remove();
    syncCoverageAfterMatrixChange();
}

// --- Grille finale par produit (tarif devis) ---
let pfGrilleZones = [];
let pfGrilleFenetres = [];
let pfGrilleTranches = [];
let pfGrilleFinaleLignes = [];
let pfTarifRefsLoaded = false;

function escapeHtml(s) {
    if (s == null || s === '') return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function showPgfGrilleAlert(message, isError) {
    const el = document.getElementById('pgfGrilleFinaleAlert');
    if (!el) return;
    el.innerHTML = message
        ? `<div class="${isError ? 'alert alert-error' : 'alert alert-success'}" style="margin:0.5rem 0;">${escapeHtml(message)}</div>`
        : '';
}

async function loadPfTarifReferences() {
    if (pfTarifRefsLoaded) return;
    try {
        const [zones, fenetres, tranches] = await Promise.all([
            apiCall('/admin/tarification/zones'),
            apiCall('/admin/tarification/fenetres-duree'),
            apiCall('/admin/tarification/tranches-age'),
        ]);
        pfGrilleZones = Array.isArray(zones) ? zones : [];
        pfGrilleFenetres = Array.isArray(fenetres) ? fenetres : [];
        pfGrilleTranches = Array.isArray(tranches) ? tranches : [];
        pfTarifRefsLoaded = true;
    } catch (e) {
        console.warn(e);
        pfGrilleZones = [];
        pfGrilleFenetres = [];
        pfGrilleTranches = [];
    }
}

function populatePgfGrilleFinaleSelects() {
    const zSel = document.getElementById('pgfZone');
    const fSel = document.getElementById('pgfFenetre');
    const tSel = document.getElementById('pgfTranche');
    if (!zSel || !fSel || !tSel) return;
    const zv = zSel.value;
    const fv = fSel.value;
    const tv = tSel.value;
    zSel.innerHTML =
        '<option value="">— Zone —</option>' +
        pfGrilleZones
            .map((z) => `<option value="${z.id}">${escapeHtml(z.code)} — ${escapeHtml(z.nom)}</option>`)
            .join('');
    fSel.innerHTML =
        '<option value="">— Durée —</option>' +
        pfGrilleFenetres.map((f) => {
            const lab = f.libelle || `${f.duree_min_jours}–${f.duree_max_jours} j`;
            return `<option value="${f.id}">${escapeHtml(lab)} (${f.duree_min_jours}–${f.duree_max_jours} j)</option>`;
        }).join('');
    tSel.innerHTML =
        '<option value="">— Tranche âge —</option>' +
        pfGrilleTranches.map((t) => {
            const lab =
                t.libelle ||
                `${t.age_min ?? '…'}–${t.age_max ?? '…'} ans (×${t.coefficient})`;
            return `<option value="${t.id}">${escapeHtml(lab)}</option>`;
        }).join('');
    if ([...zSel.options].some((o) => o.value === zv)) zSel.value = zv;
    if ([...fSel.options].some((o) => o.value === fv)) fSel.value = fv;
    if ([...tSel.options].some((o) => o.value === tv)) tSel.value = tv;
}

function renderProductGrilleFinale() {
    const tbody = document.getElementById('pgfGrilleFinaleBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (pfGrilleFinaleLignes || []).forEach((L) => {
        const dlab =
            L.fenetre_libelle || `${L.duree_min_jours}–${L.duree_max_jours} j`;
        const tlab =
            L.tranche_libelle ||
            `${L.tranche_age_min ?? '—'}–${L.tranche_age_max ?? '—'} ans`;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(L.zone_code)}</strong><br><span class="text-muted small">${escapeHtml(L.zone_nom)}</span></td>
            <td>${escapeHtml(dlab)}<br><span class="text-muted small">${L.duree_min_jours}–${L.duree_max_jours} j</span></td>
            <td>${escapeHtml(tlab)}</td>
            <td>${L.coefficient_age}</td>
            <td><strong>${L.tarif_final}</strong></td>
            <td><button type="button" class="icon-button" title="Supprimer" data-pgf-del="${L.zone_id}" data-pgf-f="${L.fenetre_duree_id}" data-pgf-t="${L.tranche_age_id}">&times;</button></td>
        `;
        tr.querySelector('[data-pgf-del]')?.addEventListener('click', () =>
            deletePgfGrilleFinaleCell(L.zone_id, L.fenetre_duree_id, L.tranche_age_id)
        );
        tbody.appendChild(tr);
    });
    if (!(pfGrilleFinaleLignes || []).length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 6;
        td.className = 'text-muted';
        const pid = document.getElementById('productId')?.value;
        td.textContent = pid
            ? 'Aucune ligne pour ce produit. Ajoutez une cellule ci-dessus.'
            : 'Enregistrez le produit pour configurer la grille finale.';
        tr.appendChild(td);
        tbody.appendChild(tr);
    }
}

async function loadProductGrilleFinale(productId) {
    const hint = document.getElementById('pgfGrilleFinaleHint');
    if (!productId) {
        pfGrilleFinaleLignes = [];
        renderProductGrilleFinale();
        if (hint) {
            hint.textContent =
                'Enregistrez le produit pour configurer la grille finale (rattachée à ce produit).';
        }
        return;
    }
    if (hint) hint.textContent = '';
    try {
        await loadPfTarifReferences();
        const data = await apiCall(`/admin/products/${productId}/grille-finale`);
        pfGrilleFinaleLignes = data?.lignes || [];
    } catch (e) {
        showPgfGrilleAlert(e.message || 'Impossible de charger la grille finale produit.', true);
        pfGrilleFinaleLignes = [];
    }
    populatePgfGrilleFinaleSelects();
    renderProductGrilleFinale();
}

async function deletePgfGrilleFinaleCell(zoneId, fenetreId, trancheId) {
    if (!confirm('Supprimer cette ligne de grille finale pour ce produit ?')) return;
    const pid = document.getElementById('productId')?.value;
    if (!pid) return;
    try {
        await apiCall(
            `/admin/products/${pid}/grille-finale/cell?zone_id=${zoneId}&fenetre_duree_id=${fenetreId}&tranche_age_id=${trancheId}`,
            { method: 'DELETE' }
        );
        showPgfGrilleAlert('Ligne supprimée.', false);
        await loadProductGrilleFinale(Number(pid));
    } catch (e) {
        showPgfGrilleAlert(e.message || 'Erreur', true);
    }
}

async function runQuoteSimulation() {
    const pid = document.getElementById('productId')?.value;
    const out = document.getElementById('quoteSimResult');
    if (!out) return;
    if (!pid) {
        out.textContent = 'Enregistrez le produit pour simuler le tarif.';
        return;
    }
    const z = document.getElementById('quoteSimZone')?.value?.trim() || '';
    const d = document.getElementById('quoteSimDuree')?.value;
    const a = document.getElementById('quoteSimAge')?.value;
    const params = new URLSearchParams();
    if (z) params.set('zone_code', z);
    if (d !== '' && d !== undefined) params.set('duree_jours', d);
    if (a !== '' && a !== undefined) params.set('age', a);
    out.textContent = 'Calcul…';
    try {
        const q = await apiCall(`/products/${pid}/quote?${params.toString()}`);
        let msg = `Tarif : ${formatCurrency(q.prix)} — moteur : ${q.moteur_tarifaire || '—'}.`;
        if (q.zone_geographique_code) {
            msg += ` Zone : ${q.zone_geographique_code}.`;
        }
        if (q.tranche_duree_code) {
            msg += ` Tranche durée : ${q.tranche_duree_code}.`;
        }
        if (q.tarif_base != null && Number(q.tarif_base) !== Number(q.prix)) {
            msg += ` Base : ${formatCurrency(q.tarif_base)}.`;
        }
        if (q.montant_surprime != null && Number(q.montant_surprime) > 0) {
            msg += ` Surprime : ${formatCurrency(q.montant_surprime)}.`;
        }
        if (q.pct_surprime_applique != null && Number(q.pct_surprime_applique) > 0) {
            msg += ` (+${q.pct_surprime_applique} %).`;
        }
        out.textContent = msg;
    } catch (e) {
        out.textContent = e.message || 'Erreur lors du calcul.';
    }
}

function initExclusionsBuilder() {
    const addBtn = document.getElementById('addExclusionBtn');
    if (addBtn) {
        addBtn.addEventListener('click', () => addExclusionRow({ reference: '', exclusion: '' }));
    }
    resetExclusionsList(DEFAULT_EXCLUSIONS);
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
    garanties.forEach((garantie) => {
        addGuaranteeRow(garantie);
    });
}

function addGuaranteeRow(garantie = {}) {
    const list = document.getElementById('garantiesList');
    if (!list) {
        console.error('garantiesList element not found');
        return;
    }
    const titre = garantie.titre || garantie.garantie || garantie.nom || '';
    let capitauxStr = '';
    if (garantie.capitaux != null && garantie.capitaux !== '') {
        capitauxStr = String(garantie.capitaux);
    } else if (garantie.plafond != null && garantie.plafond !== '') {
        capitauxStr = String(garantie.plafond);
    } else if (garantie.description) {
        capitauxStr = String(garantie.description);
    }
    const uid = `garantie-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const tr = document.createElement('tr');
    tr.className = 'guarantee-edit-row';
    tr.innerHTML = `
        <td>
            <input type="text" id="${uid}-titre" data-field="titre" value="${escapeHtmlAttr(titre)}" placeholder="Intitulé de la garantie" aria-label="Garantie">
        </td>
        <td>
            <input type="text" id="${uid}-capitaux" data-field="capitaux" value="${escapeHtmlAttr(capitauxStr)}" placeholder="FCFA, montants, libellé libre…" aria-label="Capitaux">
        </td>
        <td class="guarantees-edit-table__actions">
            <button type="button" class="icon-button" data-action="remove-guarantee" aria-label="Supprimer la ligne">&times;</button>
        </td>
    `;
    const removeBtn = tr.querySelector('[data-action="remove-guarantee"]');
    if (removeBtn) {
        removeBtn.addEventListener('click', () => {
            const totalRows = list.querySelectorAll('.guarantee-edit-row').length;
            if (totalRows <= 1) {
                showAlert('Au moins une garantie est requise.', 'error');
                return;
            }
            tr.remove();
        });
    }
    list.appendChild(tr);
    tr.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function collectGaranties() {
    const list = document.getElementById('garantiesList');
    if (!list) {
        console.error('garantiesList not found');
        return [];
    }

    const rows = list.querySelectorAll('.guarantee-edit-row');
    const garanties = [];

    rows.forEach((row) => {
        const titre = row.querySelector('[data-field="titre"]')?.value.trim() || '';
        const capitauxRaw = row.querySelector('[data-field="capitaux"]')?.value.trim() || '';
        if (!titre && !capitauxRaw) {
            return;
        }
        const capitaux = capitauxRaw === '' ? null : capitauxRaw;
        garanties.push({
            titre,
            capitaux,
            franchise: null,
            obligatoire: false,
            description: null,
        });
    });

    return garanties.filter((g) => g.titre);
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
    if (!chipsContainer) {
        return;
    }
    chipsContainer.innerHTML = '';
    if (selectedZones.size === 0) {
        chipsContainer.innerHTML = '<span class="text-muted">Aucune zone sélectionnée</span>';
    } else {
        selectedZones.forEach(({ value }) => {
            const chip = document.createElement('span');
            chip.className = 'selected-zone-chip';
            chip.textContent = value;
            chipsContainer.appendChild(chip);
        });
    }
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

function buildZonesPayload(zonesOverride) {
    const zones = Array.isArray(zonesOverride)
        ? [...new Set(zonesOverride.map((z) => String(z).trim()).filter(Boolean))]
        : getSelectedZones();
    const paysEligibles = parseCommaSeparated(document.getElementById('paysEligibles')?.value);

    const payload = {};
    if (zones.length) {
        payload.zones = zones;
    }
    if (paysEligibles.length) {
        payload.pays_eligibles = paysEligibles;
    }

    const specificites = [...preservedSpecificites];
    specificites.push(`type_produit:${PRODUCT_KIND_VOYAGE}`);
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
        await loadProductTarifsMatrix(productId);
        await loadProductGrilleFinale(productId);
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
    document.getElementById('age_minimum').value = product.age_minimum ?? '';
    document.getElementById('age_maximum').value = product.age_maximum ?? '';
    document.getElementById('duree_max_jours').value = product.duree_max_jours ?? '';
    document.getElementById('conditions_sante').value = product.conditions_sante || '';
    document.getElementById('paysEligibles').value = (product.zones_geographiques?.pays_eligibles || []).join(', ');

    setPricingOption(product.cle_repartition || 'fixe');

    const zones = product.zones_geographiques?.zones || [];
    setSelectedZones(zones);

    productCoverageSnapshot = {
        age_minimum: product.age_minimum ?? null,
        age_maximum: product.age_maximum ?? null,
        duree_max_jours: product.duree_max_jours ?? null,
        zones: [...zones],
    };

    if (assureurSelectEl) {
        const assureurId = product.assureur_id ? String(product.assureur_id) : '';
        assureurSelectEl.value = assureurId;
        updateAssureurSummary(assureurId, product.assureur || '');
    }

    const raw = Array.isArray(product.garanties) ? product.garanties : [];
    const garanties = raw.map((g) => {
        const titre = g.titre || g.garantie || g.nom || '';
        let capitauxCell = '';
        if (g.capitaux != null && g.capitaux !== '') {
            capitauxCell = String(g.capitaux);
        } else if (g.plafond != null && g.plafond !== '') {
            capitauxCell = String(g.plafond);
        } else if (g.description) {
            capitauxCell = String(g.description);
        }
        return { titre, capitaux: capitauxCell };
    });

    resetGuaranteeList(garanties.length ? garanties : DEFAULT_GARANTIES);

    const rawExclusions = Array.isArray(product.exclusions_generales) ? product.exclusions_generales : [];
    resetExclusionsList(rawExclusions.length ? rawExclusions : []);

    ['surprime_moins_18_pct', 'surprime_70_75_pct', 'surprime_76_80_pct', 'surprime_81_89_pct'].forEach((fid) => {
        const el = document.getElementById(fid);
        if (!el) return;
        const v = product[fid];
        el.value = v !== undefined && v !== null ? v : '';
    });
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

    const garanties = collectGaranties();

    if (garanties.length === 0) {
        showAlert('Ajoutez au moins une ligne de garantie avec un intitulé (colonne Garantie).', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Enregistrer';
        return;
    }

    const productId = document.getElementById('productId').value;

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
        showAlert(`Le tarif de base doit être supérieur à 0 ${currencyLabel}.`, 'error');
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

    const payload = {
        code: codeValue,
        nom: nomValue,
        description: document.getElementById('description').value?.trim() || null,
        assureur_id: Number(selectedAssureurId),
        assureur: selectedAssureur.nom,
        cout: coutValue,
        cle_repartition: document.getElementById('cle_repartition').value,
        commission_assureur_pct: (() => {
            const v = parseOptionalFloat(document.getElementById('commission_assureur_pct')?.value);
            if (v == null) return null;
            return Math.min(100, Math.max(0, v));
        })(),
        duree_validite_jours: parseOptionalInt(document.getElementById('duree_validite_jours').value),
        est_actif: document.getElementById('statut').value === 'active',
        conditions_sante: document.getElementById('conditions_sante').value?.trim() || null,
        garanties: Array.from(garanties),
        exclusions_generales: collectExclusions(),
        surprime_moins_18_pct: parseSurprimePctInput('surprime_moins_18_pct'),
        surprime_70_75_pct: parseSurprimePctInput('surprime_70_75_pct'),
        surprime_76_80_pct: parseSurprimePctInput('surprime_76_80_pct'),
        surprime_81_89_pct: parseSurprimePctInput('surprime_81_89_pct'),
    };

    const agg = aggregateTarifMatrixCoverage();
    if (agg.hasValidRows) {
        payload.age_minimum = agg.age_min;
        payload.age_maximum = agg.age_max;
        payload.duree_max_jours = agg.duree_max;
    } else {
        payload.age_minimum = parseOptionalInt(document.getElementById('age_minimum').value);
        payload.age_maximum = parseOptionalInt(document.getElementById('age_maximum').value);
        payload.duree_max_jours = parseOptionalInt(document.getElementById('duree_max_jours').value);
    }

    const zonesPayload = agg.hasValidRows
        ? buildZonesPayload(agg.zoneCodes)
        : buildZonesPayload();
    if (zonesPayload) {
        payload.zones_geographiques = zonesPayload;
    }

    try {
        if (productId) {
            await adminProductsAPI.update(Number(productId), payload);
            showAlert('Produit mis à jour avec succès.', 'success');
        } else {
            const created = await adminProductsAPI.create(payload);
            showAlert('Produit créé. Vous pouvez ajouter les lignes tarifaires ci-dessous.', 'success');
            if (created && created.id) {
                document.getElementById('productId').value = String(created.id);
                const mt = document.getElementById('modalTitle');
                if (mt) mt.textContent = 'Modifier un produit';
                syncTarifMatrixAddButtonState();
                await loadProductTarifsMatrix(created.id);
                await loadProductGrilleFinale(created.id);
            }
        }

        if (productId) {
            closeProductModal();
        }
        await loadProducts();
    } catch (error) {
        console.error('Erreur lors de la sauvegarde du produit:', error);
        if (error.status === 422 && error.detail && Array.isArray(error.detail)) {
            console.error('Détails validation 422:', error.detail);
        }
        var msg = error.message || "Impossible d'enregistrer ce produit.";

        if (error.status === 422 && error.detail && Array.isArray(error.detail)) {

            msg = error.detail.map(function (e) {

                var field = Array.isArray(e.loc) ? e.loc.slice(1).join('.') : '';

                return field ? field + ': ' + (e.msg || '') : (e.msg || '');

            }).join(' ; ');

        }

        showAlert(msg, 'error');
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
    document.getElementById('addProductTarifRowBtn')?.addEventListener('click', () => {
        const pid = document.getElementById('productId')?.value?.trim();
        if (!pid) {
            return;
        }
        appendTarifMatrixRow({});
    });
    document.getElementById('quoteSimBtn')?.addEventListener('click', () => {
        runQuoteSimulation();
    });
    document.getElementById('btnPgfGrilleFinaleSave')?.addEventListener('click', async () => {
        const pid = document.getElementById('productId')?.value;
        if (!pid) {
            showPgfGrilleAlert('Enregistrez d’abord le produit.', true);
            return;
        }
        const zone_id = parseInt(document.getElementById('pgfZone')?.value, 10);
        const fenetre_duree_id = parseInt(document.getElementById('pgfFenetre')?.value, 10);
        const tranche_age_id = parseInt(document.getElementById('pgfTranche')?.value, 10);
        const coeffRaw = document.getElementById('pgfCoeff')?.value?.trim();
        const tarif_final = parseFloat(document.getElementById('pgfTarif')?.value);
        if (!Number.isFinite(zone_id) || !Number.isFinite(fenetre_duree_id) || !Number.isFinite(tranche_age_id)) {
            showPgfGrilleAlert('Choisissez zone, durée et tranche.', true);
            return;
        }
        if (!Number.isFinite(tarif_final) || tarif_final < 0) {
            showPgfGrilleAlert('Tarif final invalide.', true);
            return;
        }
        const body = { zone_id, fenetre_duree_id, tranche_age_id, tarif_final };
        if (coeffRaw !== '') {
            const c = parseFloat(coeffRaw);
            if (!Number.isFinite(c) || c < 0) {
                showPgfGrilleAlert('Coefficient invalide.', true);
                return;
            }
            body.coefficient_age = c;
        }
        try {
            await apiCall(`/admin/products/${pid}/grille-finale/cell`, {
                method: 'PUT',
                body: JSON.stringify(body),
            });
            showPgfGrilleAlert('Cellule enregistrée pour ce produit.', false);
            document.getElementById('pgfTarif').value = '';
            document.getElementById('pgfCoeff').value = '';
            await loadProductGrilleFinale(Number(pid));
        } catch (e) {
            showPgfGrilleAlert(e.message || 'Erreur', true);
        }
    });
    productForm.addEventListener('submit', handleProductFormSubmit);
    syncTarifMatrixAddButtonState();
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
    const tariffMount = document.getElementById('productsVoyageTariffMount');
    if (tariffMount && typeof renderVoyageTariffReference === 'function') {
        renderVoyageTariffReference(tariffMount, () => apiCall('/admin/tarification/voyage-reference'));
    }
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

