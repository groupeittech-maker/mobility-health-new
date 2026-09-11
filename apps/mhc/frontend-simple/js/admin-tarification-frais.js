(async function () {
    const ok = await requireRole('admin', 'index.html');
    if (!ok) return;
    loadParams();
    bindEvents();
})();

let editingCountry = null;
let taxCounter = 0;

function escapeHtml(s) {
    if (s == null || s === '') return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function showAlert(elId, message, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.innerHTML = message
        ? `<div class="${isError ? 'alert alert-error' : 'alert alert-success'}" style="margin:0.5rem 0;">${escapeHtml(message)}</div>`
        : '';
}

function bindEvents() {
    document.getElementById('btnAddTax')?.addEventListener('click', () => addTaxRow());
    document.getElementById('btnSave')?.addEventListener('click', saveParam);
    document.getElementById('paramsList')?.addEventListener('click', handleListClick);
}

function addTaxRow(nom = '', taux = '') {
    const container = document.getElementById('taxesContainer');
    const id = `tax-${taxCounter++}`;
    const div = document.createElement('div');
    div.className = 'taxe-row';
    div.dataset.taxId = id;
    div.innerHTML = `
        <input type="text" class="taxe-nom" placeholder="Nom taxe (ex: TVA)" value="${escapeHtml(nom)}">
        <input type="number" class="taxe-taux" placeholder="%" min="0" max="100" step="0.01" value="${taux}">
        <label><input type="checkbox" class="taxe-actif" checked> Actif</label>
        <button type="button" data-action="remove-tax" title="Supprimer">&times;</button>
    `;
    container.appendChild(div);
    div.querySelector('[data-action="remove-tax"]').addEventListener('click', () => div.remove());
}

function getTaxesFromForm() {
    const rows = document.querySelectorAll('#taxesContainer .taxe-row');
    const taxes = [];
    rows.forEach((row, idx) => {
        const nom = row.querySelector('.taxe-nom').value.trim();
        const taux = parseFloat(row.querySelector('.taxe-taux').value);
        const actif = row.querySelector('.taxe-actif').checked;
        if (nom && Number.isFinite(taux)) {
            taxes.push({
                nom,
                taux_pct: taux,
                actif,
                ordre_affichage: idx,
            });
        }
    });
    return taxes;
}

async function loadParams() {
    showAlert('listAlert', '', false);
    try {
        const params = await apiCall('/admin/tarification/parametres-pays');
        renderParams(params);
    } catch (error) {
        showAlert('listAlert', error.message || 'Impossible de charger les paramètres', true);
    }
}

function renderParams(params) {
    const container = document.getElementById('paramsList');
    if (!container) return;
    if (!params || !params.length) {
        container.innerHTML = '<p class="text-muted">Aucun pays configuré. Les valeurs par défaut s’appliquent (frais = 15 %, taxes = 0).</p>';
        return;
    }
    container.innerHTML = params.map((p) => {
        const statusClass = p.actif ? '' : 'background:#f8f9fa;color:#6c757d;';
        return `
            <div class="country-card" style="${statusClass}">
                <h4>
                    <span>${escapeHtml(p.pays_assureur)}</span>
                    <span class="badge">${p.actif ? 'Actif' : 'Inactif'}</span>
                </h4>
                <p class="muted">Frais de services : <strong>${p.frais_services_pct} %</strong></p>
                <p class="muted">Taxes actives : <strong>${p.nombre_taxes}</strong> (${p.total_taxes_pct} % au total)</p>
                <div style="margin-top:0.75rem;">
                    <button type="button" class="btn btn-sm btn-primary" data-action="edit" data-country="${escapeHtml(p.pays_assureur)}">Modifier</button>
                    <button type="button" class="btn btn-sm btn-danger" data-action="delete" data-country="${escapeHtml(p.pays_assureur)}">Supprimer</button>
                </div>
            </div>
        `;
    }).join('');
}

async function handleListClick(e) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const country = btn.dataset.country;
    if (btn.dataset.action === 'edit') {
        await loadCountryDetail(country);
    } else if (btn.dataset.action === 'delete') {
        if (!confirm(`Supprimer les paramètres pour ${country} ?`)) return;
        try {
            await apiCall(`/admin/tarification/parametres-pays/${encodeURIComponent(country)}`, { method: 'DELETE' });
            resetForm();
            await loadParams();
        } catch (error) {
            showAlert('listAlert', error.message || 'Erreur suppression', true);
        }
    }
}

async function loadCountryDetail(country) {
    showAlert('formAlert', '', false);
    try {
        const p = await apiCall(`/admin/tarification/parametres-pays/${encodeURIComponent(country)}`);
        document.getElementById('countryInput').value = p.pays_assureur;
        document.getElementById('feeInput').value = p.frais_services_pct;
        document.getElementById('activeInput').checked = p.actif;
        editingCountry = p.pays_assureur;
        document.getElementById('taxesContainer').innerHTML = '';
        (p.taxes || []).forEach((t) => addTaxRow(t.nom, t.taux_pct));
    } catch (error) {
        showAlert('formAlert', error.message || 'Impossible de charger le pays', true);
    }
}

function resetForm() {
    editingCountry = null;
    document.getElementById('countryInput').value = '';
    document.getElementById('feeInput').value = '15';
    document.getElementById('activeInput').checked = true;
    document.getElementById('taxesContainer').innerHTML = '';
}

async function saveParam() {
    showAlert('formAlert', '', false);
    const pays = document.getElementById('countryInput').value.trim();
    const frais = parseFloat(document.getElementById('feeInput').value);
    const actif = document.getElementById('activeInput').checked;
    if (!pays) return showAlert('formAlert', 'Le pays est obligatoire', true);
    if (!Number.isFinite(frais) || frais < 0 || frais > 100) {
        return showAlert('formAlert', 'Les frais doivent être un % entre 0 et 100', true);
    }

    const payload = {
        pays_assureur: pays,
        frais_services_pct: frais,
        actif,
        taxes: getTaxesFromForm(),
    };

    try {
        const method = editingCountry ? 'PUT' : 'POST';
        const path = editingCountry
            ? `/admin/tarification/parametres-pays/${encodeURIComponent(editingCountry)}`
            : '/admin/tarification/parametres-pays';
        await apiCall(path, {
            method,
            body: JSON.stringify(payload),
            headers: { 'Content-Type': 'application/json' },
        });
        showAlert('formAlert', 'Paramètres enregistrés.', false);
        resetForm();
        await loadParams();
    } catch (error) {
        showAlert('formAlert', error.message || 'Erreur lors de l’enregistrement', true);
    }
}
