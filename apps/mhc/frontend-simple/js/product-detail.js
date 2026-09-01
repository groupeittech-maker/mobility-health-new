// Script pour la page de détail du produit

function escapeHtml(s) {
    if (s == null) return '';
    const div = document.createElement('div');
    div.textContent = String(s);
    return div.innerHTML;
}

function formatPrice(value, currencyCode) {
    if (value == null || value === '') return '—';
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    if (typeof window.formatMontantDevis === 'function') {
        return window.formatMontantDevis(n, currencyCode);
    }
    const code = (currencyCode && String(currencyCode).trim()) || 'XAF';
    return `${n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${code}`;
}

document.addEventListener('DOMContentLoaded', async function() {
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('id');

    if (!productId) {
        document.getElementById('product-detail-container').innerHTML =
            '<div class="error-message"><p>Produit non spécifié. <a href="index.html">Retour à l\'accueil</a></p></div>';
        return;
    }

    await loadProductDetail(productId);
});

async function loadProductDetail(productId) {
    const container = document.getElementById('product-detail-container');

    try {
        const product = await apiCall(`/products/${productId}`);

        let guarantees = [];
        if (product.garanties) {
            try {
                guarantees = typeof product.garanties === 'string' ? JSON.parse(product.garanties) : product.garanties;
            } catch (e) {
                guarantees = product.garanties.split(',').map((g) => ({ titre: g.trim() }));
            }
        }
        if (!Array.isArray(guarantees)) guarantees = [];

        let conditions = '';
        if (product.conditions) {
            try {
                const conditionsObj = JSON.parse(product.conditions);
                conditions = typeof conditionsObj === 'string' ? conditionsObj : JSON.stringify(conditionsObj, null, 2);
            } catch (e) {
                conditions = product.conditions;
            }
        }

        const zones = (product.zones_geographiques && product.zones_geographiques.zones)
            ? product.zones_geographiques.zones.join(', ')
            : 'Non précisé';

        const productCur = product.currency;

        function formatGarantieCapitaux(g) {
            const raw = g.capitaux ?? g.plafond ?? g.description;
            if (raw == null || raw === '') return '—';
            if (typeof raw === 'number' && Number.isFinite(raw)) {
                return formatPrice(raw, productCur);
            }
            const str = String(raw).trim();
            if (!str) return '—';
            const compact = str.replace(/[\s\u00a0\u202f]/g, '').replace(/,/g, '');
            if (/^\d+$/.test(compact)) {
                return formatPrice(Number(compact), productCur);
            }
            return escapeHtml(str);
        }

        const garantiesTable =
            guarantees.length > 0
                ? `
            <div class="product-section">
                <h2>Garanties</h2>
                <table class="product-detail-table">
                    <thead><tr><th>Garanties</th><th>Capitaux</th></tr></thead>
                    <tbody>
                        ${guarantees
                            .map((g) => {
                                const lib = g.titre || g.nom || g.libelle || g.garantie || 'Garantie';
                                const cap = formatGarantieCapitaux(g);
                                return `<tr><td>${escapeHtml(lib)}</td><td>${cap}</td></tr>`;
                            })
                            .join('')}
                    </tbody>
                </table>
            </div>`
                : '';

        const pg = product.primes_generees || {};
        const hasPrimes = [pg.prime_nette, pg.accessoire, pg.taxes, pg.prime_total].some((v) => v != null && v !== '');
        const a = (v) => (v != null && v !== '') ? formatPrice(Number(v), productCur) : '—';
        const primesSection = hasPrimes
            ? `
            <div class="product-section">
                <h2>Primes générées</h2>
                <table class="product-detail-table">
                    <tbody>
                        <tr><td>Prime nette</td><td>${a(pg.prime_nette)}</td></tr>
                        <tr><td>Accessoire</td><td>${a(pg.accessoire)}</td></tr>
                        <tr><td>Taxes</td><td>${a(pg.taxes)}</td></tr>
                        <tr><td>Prime total</td><td>${a(pg.prime_total)}</td></tr>
                    </tbody>
                </table>
            </div>`
            : '';

        const characteristicsTable = `
            <div class="product-section">
                <h2>Caractéristiques du produit</h2>
                <table class="product-detail-table">
                    <tbody>
                        <tr><td>Assureur</td><td>${escapeHtml(product.assureur || 'Mobility Health')}</td></tr>
                        <tr><td>Validité</td><td>${product.duree_validite_jours ? product.duree_validite_jours + ' jours' : 'Selon le contrat'}</td></tr>
                        <tr><td>Zones couvertes</td><td>${escapeHtml(zones)}</td></tr>
                        <tr><td>Prix</td><td>${formatPrice(product.cout, productCur)}</td></tr>
                        <tr><td>Statut</td><td><span class="status-badge ${product.est_actif ? 'status-active' : 'status-inactive'}">${product.est_actif ? 'Actif' : 'Inactif'}</span></td></tr>
                    </tbody>
                </table>
            </div>`;

        const formatExclusionItem = (x) => {
            if (x && typeof x === 'object') {
                const ref = String(x.reference ?? x.cle ?? x.libelle ?? '').trim();
                const exc = String(x.exclusion ?? x.valeur ?? x.description ?? '').trim();
                if (ref && exc) return `${ref} — ${exc}`;
                return ref || exc || JSON.stringify(x);
            }
            return String(x);
        };
        const exclusionsSection =
            product.exclusions_generales && Array.isArray(product.exclusions_generales) && product.exclusions_generales.length > 0
                ? `
            <div class="product-section">
                <h2>Exclusions</h2>
                <ul class="guarantees-list">
                    ${product.exclusions_generales.map((x) => `<li>${escapeHtml(formatExclusionItem(x))}</li>`).join('')}
                </ul>
            </div>`
                : '';

        const conditionsSection = conditions
            ? `
            <div class="product-section">
                <h2>Conditions générales</h2>
                <div class="conditions-content">
                    <pre>${escapeHtml(conditions)}</pre>
                </div>
            </div>`
            : '';

        const html = `
            <div class="product-detail">
                <div class="product-detail-header">
                    <div class="product-code">${escapeHtml(product.code)}</div>
                    <h1>${escapeHtml(product.nom)}</h1>
                    <div class="product-price-large">${formatPrice(product.cout, productCur)}</div>
                </div>

                <div class="product-detail-content">
                    <div class="product-section">
                        <h2>Description</h2>
                        <p>${escapeHtml(product.description || 'Aucune description disponible.')}</p>
                    </div>

                    ${characteristicsTable}
                    ${garantiesTable}
                    ${primesSection}
                    ${exclusionsSection}
                    ${conditionsSection}
                </div>

                <div class="product-detail-actions">
                    <a href="subscription-start.html?product_id=${product.id}" class="btn btn-primary btn-large">
                        Souscrire maintenant
                    </a>
                    <a href="index.html#products" class="btn btn-secondary">
                        Retour aux produits
                    </a>
                </div>
            </div>
        `;

        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `
            <div class="error-message">
                <h2>Erreur</h2>
                <p>Impossible de charger les détails du produit: ${escapeHtml(error.message)}</p>
                <a href="index.html" class="btn btn-primary">Retour à l'accueil</a>
            </div>
        `;
    }
}
