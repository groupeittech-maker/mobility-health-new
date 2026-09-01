(async function () {
    const ok = await requireRole('admin', 'index.html');
    if (!ok) return;
})();

let countriesCache = [];
let zonesList = [];
let fenetresList = [];
let tranchesList = [];
let editingZoneIdForPays = null;
let grilleData = { zones: [], fenetres: [], cellules: [] };
let grilleFinaleLignes = [];

function showInlineAlert(elId, message, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.innerHTML = message
        ? `<div class="${isError ? 'alert alert-error' : 'alert alert-success'}" style="margin:0.5rem 0;">${message}</div>`
        : '';
}

async function apiTarif(path, options = {}) {
    return apiCall(`/admin/tarification${path}`, {
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options,
    });
}

function cellKey(zoneId, fenetreId) {
    return `${zoneId}:${fenetreId}`;
}

async function loadVoyageReferencePanel() {
    const el = document.getElementById('voyageReferencePanel');
    if (!el) return;
    if (typeof renderVoyageTariffReference !== 'function') {
        el.innerHTML =
            '<p class="alert alert-error">Script voyage-tariff-reference-ui.js manquant.</p>';
        return;
    }
    await renderVoyageTariffReference(el, () => apiTarif('/voyage-reference'));
}

async function loadCountries() {
    if (countriesCache.length) return countriesCache;
    try {
        const list = await apiCall('/destinations/countries?include_cities=false&actif_seulement=true');
        countriesCache = Array.isArray(list) ? list : [];
    } catch (e) {
        console.warn(e);
        countriesCache = [];
    }
    return countriesCache;
}

async function loadCanonicalVoyageHint() {
    const el = document.getElementById('canonicalVoyageHint');
    if (!el) return;
    try {
        const data = await apiTarif('/canonical-voyage-zones');
        const rows = (data.zones || [])
            .map(
                (z) =>
                    `<li><code>${escapeHtml(z.code)}</code> — ${escapeHtml(z.description || '')}</li>`,
            )
            .join('');
        el.innerHTML = `<ul style="margin:0;padding-left:1.2rem;font-size:0.9rem;">${rows}</ul>`;
    } catch (e) {
        el.innerHTML = `<p class="text-muted small">Impossible de charger (${escapeHtml(e.message || 'erreur')}).</p>`;
    }
}

async function refreshZones() {
    try {
        zonesList = await apiTarif('/zones');
    } catch (e) {
        showInlineAlert('zonesAlert', e.message || 'Impossible de charger les zones', true);
        zonesList = [];
    }
    renderZones();
}

function renderZones() {
    const tbody = document.getElementById('zonesTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (zonesList || []).forEach((z) => {
        const n = (z.destination_country_ids || []).length;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(z.code)}</strong></td>
            <td>${escapeHtml(z.nom)}</td>
            <td>${n} pays</td>
            <td>
                <button type="button" class="btn btn-outline btn-sm" data-action="pays" data-id="${z.id}">Pays</button>
                <button type="button" class="btn btn-outline btn-sm" data-action="edit" data-id="${z.id}">Renommer</button>
                <button type="button" class="icon-button" data-action="del" data-id="${z.id}" title="Supprimer">&times;</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    tbody.querySelectorAll('button[data-action]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const id = Number(btn.dataset.id);
            const action = btn.dataset.action;
            if (action === 'pays') openZonePaysModal(id);
            if (action === 'edit') editZoneNom(id);
            if (action === 'del') deleteZone(id);
        });
    });
}

function escapeHtml(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

async function editZoneNom(id) {
    const z = zonesList.find((x) => x.id === id);
    if (!z) return;
    const nom = window.prompt('Nom de la zone', z.nom);
    if (nom === null || !String(nom).trim()) return;
    try {
        await apiTarif(`/zones/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ nom: String(nom).trim() }),
        });
        showInlineAlert('zonesAlert', 'Zone mise à jour.', false);
        await refreshZones();
        await refreshGrille();
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('zonesAlert', e.message || 'Erreur', true);
    }
}

async function deleteZone(id) {
    if (!confirm('Supprimer cette zone ? Les rattachements pays et cellules grille seront supprimés.')) return;
    try {
        await apiTarif(`/zones/${id}`, { method: 'DELETE' });
        showInlineAlert('zonesAlert', 'Zone supprimée.', false);
        await refreshZones();
        await refreshGrille();
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('zonesAlert', e.message || 'Erreur', true);
    }
}

document.getElementById('btnAddZone')?.addEventListener('click', async () => {
    const code = document.getElementById('newZoneCode')?.value?.trim();
    const nom = document.getElementById('newZoneNom')?.value?.trim();
    const ordre_affichage = parseInt(document.getElementById('newZoneOrdre')?.value, 10) || 0;
    if (!code || !nom) {
        showInlineAlert('zonesAlert', 'Code et nom requis.', true);
        return;
    }
    try {
        await apiTarif('/zones', {
            method: 'POST',
            body: JSON.stringify({
                code,
                nom,
                coefficient: 1,
                ordre_affichage,
                est_actif: true,
            }),
        });
        document.getElementById('newZoneCode').value = '';
        document.getElementById('newZoneNom').value = '';
        showInlineAlert('zonesAlert', 'Zone créée. Rattachez les pays puis renseignez la grille.', false);
        await refreshZones();
        await refreshGrille();
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('zonesAlert', e.message || 'Erreur création zone', true);
    }
});

async function openZonePaysModal(zoneId) {
    editingZoneIdForPays = zoneId;
    const z = zonesList.find((x) => x.id === zoneId);
    const modal = document.getElementById('zonePaysModal');
    const title = document.getElementById('zonePaysModalTitle');
    const list = document.getElementById('zonePaysCheckboxList');
    if (!modal || !list) return;
    title.textContent = z ? `Pays — ${z.nom} (${z.code})` : 'Pays de la zone';
    await loadCountries();
    const selected = new Set(z?.destination_country_ids || []);
    list.innerHTML = countriesCache
        .map((c) => {
            const checked = selected.has(c.id) ? 'checked' : '';
            const label = escapeHtml(c.nom || c.code);
            return `<label style="display:block;margin:0.25rem 0;"><input type="checkbox" value="${c.id}" ${checked}> ${label}</label>`;
        })
        .join('');
    modal.style.display = 'block';
}

function closeZonePaysModal() {
    editingZoneIdForPays = null;
    const modal = document.getElementById('zonePaysModal');
    if (modal) modal.style.display = 'none';
}

async function saveZonePays() {
    if (!editingZoneIdForPays) return;
    const list = document.getElementById('zonePaysCheckboxList');
    const ids = [];
    list?.querySelectorAll('input[type="checkbox"]:checked').forEach((cb) => {
        ids.push(Number(cb.value));
    });
    try {
        await apiTarif(`/zones/${editingZoneIdForPays}/pays`, {
            method: 'PUT',
            body: JSON.stringify({ destination_country_ids: ids }),
        });
        closeZonePaysModal();
        showInlineAlert('zonesAlert', 'Pays enregistrés pour la zone.', false);
        await refreshZones();
        await refreshGrilleFinale();
    } catch (e) {
        alert(e.message || 'Erreur sauvegarde pays');
    }
}

window.closeZonePaysModal = closeZonePaysModal;
window.saveZonePays = saveZonePays;

// --- Fenêtres durée ---
async function refreshFenetres() {
    let rows = [];
    try {
        rows = await apiTarif('/fenetres-duree');
    } catch (e) {
        showInlineAlert('fenetresAlert', e.message || 'Impossible de charger les fenêtres', true);
    }
    fenetresList = Array.isArray(rows) ? rows : [];
    const tbody = document.getElementById('fenetresTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (rows || []).forEach((f) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(f.libelle || '—')}</td>
            <td>${f.duree_min_jours}</td>
            <td>${f.duree_max_jours}</td>
            <td>${f.ordre_priorite}</td>
            <td><button type="button" class="icon-button" data-fdel="${f.id}">&times;</button></td>
        `;
        tr.querySelector('[data-fdel]')?.addEventListener('click', () => deleteFenetre(f.id));
        tbody.appendChild(tr);
    });
}

async function deleteFenetre(id) {
    if (
        !confirm(
            'Supprimer cette fenêtre ? Les cellules grille (référence et finale) associées seront supprimées.'
        )
    )
        return;
    try {
        await apiTarif(`/fenetres-duree/${id}`, { method: 'DELETE' });
        showInlineAlert('fenetresAlert', 'Fenêtre supprimée.', false);
        await refreshFenetres();
        await refreshGrille();
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('fenetresAlert', e.message || 'Erreur', true);
    }
}

document.getElementById('btnAddFenetre')?.addEventListener('click', async () => {
    const libelle = document.getElementById('newFdLibelle')?.value?.trim() || null;
    const duree_min_jours = parseInt(document.getElementById('newFdMin')?.value, 10);
    const duree_max_jours = parseInt(document.getElementById('newFdMax')?.value, 10);
    const ordre_priorite = parseInt(document.getElementById('newFdPriorite')?.value, 10) || 0;
    if (!Number.isFinite(duree_min_jours) || !Number.isFinite(duree_max_jours) || duree_min_jours > duree_max_jours) {
        showInlineAlert('fenetresAlert', 'Durées min/max invalides.', true);
        return;
    }
    try {
        await apiTarif('/fenetres-duree', {
            method: 'POST',
            body: JSON.stringify({
                libelle,
                duree_min_jours,
                duree_max_jours,
                coefficient: 1,
                ordre_priorite,
                est_actif: true,
            }),
        });
        showInlineAlert('fenetresAlert', 'Fenêtre ajoutée.', false);
        await refreshFenetres();
        await refreshGrille();
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('fenetresAlert', e.message || 'Erreur', true);
    }
});

// --- Tranches âge ---
async function refreshTranches() {
    let rows = [];
    try {
        rows = await apiTarif('/tranches-age');
    } catch (e) {
        showInlineAlert('tranchesAlert', e.message || 'Impossible de charger les tranches', true);
    }
    tranchesList = Array.isArray(rows) ? rows : [];
    const tbody = document.getElementById('tranchesTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (rows || []).forEach((t) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(t.libelle || '—')}</td>
            <td>${t.age_min ?? '—'}</td>
            <td>${t.age_max ?? '—'}</td>
            <td>${t.coefficient}</td>
            <td>${t.ordre_priorite}</td>
            <td><button type="button" class="icon-button" data-tdel="${t.id}">&times;</button></td>
        `;
        tr.querySelector('[data-tdel]')?.addEventListener('click', () => deleteTranche(t.id));
        tbody.appendChild(tr);
    });
}

async function deleteTranche(id) {
    if (!confirm('Supprimer cette tranche ? Les lignes de grille finale liées seront supprimées.')) return;
    try {
        await apiTarif(`/tranches-age/${id}`, { method: 'DELETE' });
        showInlineAlert('tranchesAlert', 'Tranche supprimée.', false);
        await refreshTranches();
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('tranchesAlert', e.message || 'Erreur', true);
    }
}

document.getElementById('btnAddTranche')?.addEventListener('click', async () => {
    const libelle = document.getElementById('newTaLibelle')?.value?.trim() || null;
    const minV = document.getElementById('newTaMin')?.value;
    const maxV = document.getElementById('newTaMax')?.value;
    const age_min = minV === '' || minV === undefined ? null : parseInt(minV, 10);
    const age_max = maxV === '' || maxV === undefined ? null : parseInt(maxV, 10);
    const coefficient = parseFloat(document.getElementById('newTaCoeff')?.value);
    const ordre_priorite = parseInt(document.getElementById('newTaPriorite')?.value, 10) || 0;
    if (age_min !== null && Number.isNaN(age_min)) {
        showInlineAlert('tranchesAlert', 'Âge min invalide.', true);
        return;
    }
    if (age_max !== null && Number.isNaN(age_max)) {
        showInlineAlert('tranchesAlert', 'Âge max invalide.', true);
        return;
    }
    if (age_min != null && age_max != null && age_min > age_max) {
        showInlineAlert('tranchesAlert', 'Âge min > max.', true);
        return;
    }
    if (!Number.isFinite(coefficient) || coefficient < 0) {
        showInlineAlert('tranchesAlert', 'Multiplicateur invalide.', true);
        return;
    }
    try {
        await apiTarif('/tranches-age', {
            method: 'POST',
            body: JSON.stringify({
                libelle,
                age_min,
                age_max,
                coefficient,
                ordre_priorite,
                est_actif: true,
            }),
        });
        showInlineAlert('tranchesAlert', 'Tranche ajoutée.', false);
        await refreshTranches();
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('tranchesAlert', e.message || 'Erreur', true);
    }
});

// --- Grille prix ---
async function refreshGrille() {
    try {
        grilleData = await apiTarif('/grille');
    } catch (e) {
        showInlineAlert('grilleAlert', e.message || 'Impossible de charger la grille', true);
        grilleData = { zones: [], fenetres: [], cellules: [] };
    }
    renderGrille();
}

function renderGrille() {
    const table = document.getElementById('grilleMatrixTable');
    const theadRow = table?.querySelector('thead tr');
    const tbody = document.getElementById('grilleMatrixBody');
    if (!table || !theadRow || !tbody) return;

    const zones = grilleData.zones || [];
    const fenetres = grilleData.fenetres || [];
    const prixMap = new Map();
    (grilleData.cellules || []).forEach((c) => {
        prixMap.set(cellKey(c.zone_id, c.fenetre_duree_id), String(c.prix));
    });

    theadRow.innerHTML = '<th>Zone</th>';
    fenetres.forEach((f) => {
        const th = document.createElement('th');
        const label = f.libelle || `${f.duree_min_jours}–${f.duree_max_jours} j`;
        th.textContent = label;
        th.title = `${f.duree_min_jours}–${f.duree_max_jours} j`;
        theadRow.appendChild(th);
    });

    tbody.innerHTML = '';
    if (!zones.length || !fenetres.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = Math.max(1 + fenetres.length, 2);
        td.className = 'text-muted';
        td.textContent =
            !zones.length || !fenetres.length
                ? 'Créez au moins une zone et une fenêtre de durée pour éditer la grille.'
                : '';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    zones.forEach((z) => {
        const tr = document.createElement('tr');
        const tdZ = document.createElement('td');
        tdZ.innerHTML = `<strong>${escapeHtml(z.code)}</strong><br><span class="text-muted small">${escapeHtml(z.nom)}</span>`;
        tr.appendChild(tdZ);

        fenetres.forEach((f) => {
            const td = document.createElement('td');
            const inp = document.createElement('input');
            inp.type = 'number';
            inp.min = '0';
            inp.step = '1';
            inp.className = 'tarif-input';
            inp.style.width = '100px';
            inp.dataset.zoneId = String(z.id);
            inp.dataset.fenetreId = String(f.id);
            const k = cellKey(z.id, f.id);
            if (prixMap.has(k)) inp.value = prixMap.get(k);
            inp.addEventListener('blur', () => saveGrilleCell(z.id, f.id, inp.value));
            td.appendChild(inp);
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
}

function populateGrilleFinaleSelects() {
    const zSel = document.getElementById('gfZone');
    const fSel = document.getElementById('gfFenetre');
    const tSel = document.getElementById('gfTranche');
    if (!zSel || !fSel || !tSel) return;
    const zv = zSel.value;
    const fv = fSel.value;
    const tv = tSel.value;
    zSel.innerHTML =
        '<option value="">— Zone —</option>' +
        (zonesList || [])
            .map((z) => `<option value="${z.id}">${escapeHtml(z.code)} — ${escapeHtml(z.nom)}</option>`)
            .join('');
    fSel.innerHTML =
        '<option value="">— Durée —</option>' +
        (fenetresList || [])
            .map((f) => {
                const lab = f.libelle || `${f.duree_min_jours}–${f.duree_max_jours} j`;
                return `<option value="${f.id}">${escapeHtml(lab)} (${f.duree_min_jours}–${f.duree_max_jours} j)</option>`;
            })
            .join('');
    tSel.innerHTML =
        '<option value="">— Tranche âge —</option>' +
        (tranchesList || [])
            .map((t) => {
                const lab =
                    t.libelle ||
                    `${t.age_min ?? '…'}–${t.age_max ?? '…'} ans (×${t.coefficient})`;
                return `<option value="${t.id}">${escapeHtml(lab)}</option>`;
            })
            .join('');
    if ([...zSel.options].some((o) => o.value === zv)) zSel.value = zv;
    if ([...fSel.options].some((o) => o.value === fv)) fSel.value = fv;
    if ([...tSel.options].some((o) => o.value === tv)) tSel.value = tv;
}

async function refreshGrilleFinale() {
    try {
        const data = await apiTarif('/grille-finale');
        grilleFinaleLignes = data?.lignes || [];
    } catch (e) {
        showInlineAlert('grilleFinaleAlert', e.message || 'Impossible de charger la grille finale', true);
        grilleFinaleLignes = [];
    }
    populateGrilleFinaleSelects();
    renderGrilleFinale();
}

function renderGrilleFinale() {
    const tbody = document.getElementById('grilleFinaleBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (grilleFinaleLignes || []).forEach((L) => {
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
            <td><button type="button" class="icon-button" title="Supprimer" data-gfdel="${L.zone_id}" data-gff="${L.fenetre_duree_id}" data-gft="${L.tranche_age_id}">&times;</button></td>
        `;
        tr.querySelector('[data-gfdel]')?.addEventListener('click', () =>
            deleteGrilleFinaleCell(L.zone_id, L.fenetre_duree_id, L.tranche_age_id)
        );
        tbody.appendChild(tr);
    });
    if (!(grilleFinaleLignes || []).length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 6;
        td.className = 'text-muted';
        td.textContent =
            'Aucune ligne. Ajoutez une cellule (zone × durée × tranche) avec le tarif final affiché au devis.';
        tr.appendChild(td);
        tbody.appendChild(tr);
    }
}

async function deleteGrilleFinaleCell(zoneId, fenetreId, trancheId) {
    if (!confirm('Supprimer cette ligne de grille finale ?')) return;
    try {
        await apiTarif(
            `/grille-finale/cell?zone_id=${zoneId}&fenetre_duree_id=${fenetreId}&tranche_age_id=${trancheId}`,
            { method: 'DELETE' }
        );
        showInlineAlert('grilleFinaleAlert', 'Ligne supprimée.', false);
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('grilleFinaleAlert', e.message || 'Erreur', true);
    }
}

document.getElementById('btnGrilleFinaleSave')?.addEventListener('click', async () => {
    const zone_id = parseInt(document.getElementById('gfZone')?.value, 10);
    const fenetre_duree_id = parseInt(document.getElementById('gfFenetre')?.value, 10);
    const tranche_age_id = parseInt(document.getElementById('gfTranche')?.value, 10);
    const coeffRaw = document.getElementById('gfCoeff')?.value?.trim();
    const tarif_final = parseFloat(document.getElementById('gfTarif')?.value);
    if (!Number.isFinite(zone_id) || !Number.isFinite(fenetre_duree_id) || !Number.isFinite(tranche_age_id)) {
        showInlineAlert('grilleFinaleAlert', 'Choisissez zone, durée et tranche.', true);
        return;
    }
    if (!Number.isFinite(tarif_final) || tarif_final < 0) {
        showInlineAlert('grilleFinaleAlert', 'Tarif final invalide.', true);
        return;
    }
    const body = { zone_id, fenetre_duree_id, tranche_age_id, tarif_final };
    if (coeffRaw !== '') {
        const c = parseFloat(coeffRaw);
        if (!Number.isFinite(c) || c < 0) {
            showInlineAlert('grilleFinaleAlert', 'Coefficient invalide (vide = reprise du multiplicateur de la tranche).', true);
            return;
        }
        body.coefficient_age = c;
    }
    try {
        await apiTarif('/grille-finale/cell', {
            method: 'PUT',
            body: JSON.stringify(body),
        });
        showInlineAlert('grilleFinaleAlert', 'Cellule enregistrée. Ce tarif sera utilisé au devis si âge et voyage correspondent.', false);
        document.getElementById('gfTarif').value = '';
        document.getElementById('gfCoeff').value = '';
        await refreshGrilleFinale();
    } catch (e) {
        showInlineAlert('grilleFinaleAlert', e.message || 'Erreur', true);
    }
});

async function saveGrilleCell(zoneId, fenetreId, raw) {
    const v = String(raw || '').trim();
    try {
        if (v === '') {
            await apiTarif(`/grille/cell?zone_id=${zoneId}&fenetre_duree_id=${fenetreId}`, {
                method: 'DELETE',
            });
            showInlineAlert('grilleAlert', 'Cellule supprimée.', false);
            return;
        }
        const prix = parseFloat(v);
        if (!Number.isFinite(prix) || prix < 0) {
            showInlineAlert('grilleAlert', 'Montant invalide.', true);
            return;
        }
        await apiTarif('/grille/cell', {
            method: 'PUT',
            body: JSON.stringify({
                zone_id: zoneId,
                fenetre_duree_id: fenetreId,
                prix,
            }),
        });
        showInlineAlert('grilleAlert', 'Prix enregistré.', false);
    } catch (e) {
        showInlineAlert('grilleAlert', e.message || 'Erreur sauvegarde', true);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadVoyageReferencePanel();
    await loadCanonicalVoyageHint();
    await refreshZones();
    await refreshFenetres();
    await refreshTranches();
    await refreshGrille();
    await refreshGrilleFinale();
});
