(async function () {
    const ok = await requireRole('admin', 'index.html');
    if (!ok) {
        throw new Error('Acces refuse');
    }
})();

const courtiersApi = {
    list: (params = '') => {
        const sep = params && params.includes('?') ? '&' : '?';
        return apiCall(`/admin/courtiers${params}${sep}_ts=${Date.now()}`);
    },
    create: (body) => apiCall('/admin/courtiers', { method: 'POST', body: JSON.stringify(body) }),
    update: (id, body) => apiCall(`/admin/courtiers/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    delete: (id) => apiCall(`/admin/courtiers/${id}`, { method: 'DELETE' }),
    uploadLogo: async (courtierId, file) => {
        const formData = new FormData();
        formData.append('file', file);
        return apiCall(`/admin/courtiers/${courtierId}/logo`, {
            method: 'POST',
            body: formData,
        });
    },
};
const assureursApi = {
    list: () => apiCall('/admin/assureurs'),
};
const usersApi = {
    listCourtierAccountants: () => apiCall('/users/?role=agent_comptable_courtier&limit=500'),
};

let courtiers = [];
let assureurs = [];
let comptablesCourtiers = [];

const $ = (id) => document.getElementById(id);
const fieldValue = (id, fallback = '') => {
    const el = $(id);
    if (!el) return fallback;
    return typeof el.value === 'string' ? el.value : fallback;
};
const escapeHtml = (value) => {
    const div = document.createElement('div');
    div.textContent = String(value ?? '');
    return div.innerHTML;
};
const normalize = (v) => String(v || '').trim().toLowerCase();
const asArray = (payload) => {
    if (Array.isArray(payload)) return payload;
    if (!payload || typeof payload !== 'object') return [];
    if (Array.isArray(payload.data)) return payload.data;
    if (Array.isArray(payload.items)) return payload.items;
    if (Array.isArray(payload.results)) return payload.results;
    if (payload.data && Array.isArray(payload.data.items)) return payload.data.items;
    if (payload.data && Array.isArray(payload.data.results)) return payload.data.results;
    return [];
};

function fillFormForEdit(c) {
    if (!c) return;
    if ($('courtierId')) $('courtierId').value = c.id;
    if ($('nom')) $('nom').value = c.nom || '';
    if ($('pays')) $('pays').value = c.pays || '';
    if ($('assureurId')) $('assureurId').value = String(c.assureur_id || '');
    if ($('commissionPct')) $('commissionPct').value = String(c.commission_pct ?? 0);
    if ($('agentComptableId')) $('agentComptableId').value = String(c.agent_comptable_id || '');
    if ($('telephone')) $('telephone').value = c.telephone || '';
    if ($('logoFile')) $('logoFile').value = '';
    if ($('adresse')) $('adresse').value = c.adresse || '';
    if ($('formTitle')) $('formTitle').textContent = `Modifier ${c.nom}`;
    updateLogoPreview(c);
}

function upsertCourtierLocal(saved) {
    if (!saved || !saved.id) return;
    const idx = courtiers.findIndex((c) => Number(c.id) === Number(saved.id));
    if (idx >= 0) {
        courtiers[idx] = { ...courtiers[idx], ...saved };
    } else {
        courtiers.unshift(saved);
    }
}

async function loadExistingByName(nom) {
    const q = encodeURIComponent(String(nom || '').trim());
    if (!q) return null;
    const result = await courtiersApi.list(`?search=${q}`);
    const rows = asArray(result);
    if (!rows.length) return null;
    // Mettre à jour la liste locale pour éviter un écran vide/stale.
    courtiers = rows;
    renderList();
    const target = rows.find((c) => normalize(c.nom) === normalize(nom)) || rows[0];
    return target || null;
}

function resetForm() {
    if ($('courtierId')) $('courtierId').value = '';
    if ($('nom')) $('nom').value = '';
    if ($('pays')) $('pays').value = '';
    if ($('assureurId')) $('assureurId').value = '';
    if ($('commissionPct')) $('commissionPct').value = '0';
    if ($('agentComptableId')) $('agentComptableId').value = '';
    if ($('telephone')) $('telephone').value = '';
    if ($('logoFile')) $('logoFile').value = '';
    if ($('adresse')) $('adresse').value = '';
    if ($('formTitle')) $('formTitle').textContent = 'Nouveau courtier';
    updateLogoPreview(null);
}

function courtierLogoUrl(courtier) {
    if (!courtier || !courtier.id || !courtier.logo_url) return '';
    const raw = String(courtier.logo_url || '').trim();
    if (!raw) return '';
    if (/^https?:\/\//i.test(raw)) return raw;
    const base = (window.API_BASE_URL || '/api/v1').replace(/\/$/, '');
    return `${base}/courtiers/${courtier.id}/logo`;
}

function updateLogoPreview(courtier) {
    const wrap = $('logoPreviewWrap');
    const img = $('logoPreviewImg');
    if (!wrap || !img) return;
    const url = courtierLogoUrl(courtier);
    if (!url) {
        wrap.style.display = 'none';
        img.removeAttribute('src');
        return;
    }
    img.src = `${url}${url.includes('?') ? '&' : '?'}_ts=${Date.now()}`;
    wrap.style.display = 'block';
}

function selectedBody() {
    const assureurRaw = fieldValue('assureurId', '');
    const commissionRaw = fieldValue('commissionPct', '0');
    const agentRaw = fieldValue('agentComptableId', '');
    return {
        nom: fieldValue('nom').trim(),
        pays: fieldValue('pays').trim(),
        assureur_id: Number(assureurRaw || 0),
        commission_pct: Number(commissionRaw || 0),
        agent_comptable_id: agentRaw ? Number(agentRaw) : null,
        telephone: fieldValue('telephone').trim() || null,
        adresse: fieldValue('adresse').trim() || null,
    };
}

function renderAssureursOptions() {
    const opts = ['<option value="">Tous</option>']
        .concat(assureurs.map((a) => `<option value="${a.id}">${a.nom}</option>`))
        .join('');
    $('assureurFilter').innerHTML = opts;
    $('assureurId').innerHTML = `<option value="">Sélectionner</option>${assureurs
        .map((a) => `<option value="${a.id}">${a.nom}</option>`)
        .join('')}`;
    if ($('agentComptableId')) {
        $('agentComptableId').innerHTML = `<option value="">Non affecté</option>${comptablesCourtiers
            .map((u) => {
                const label = escapeHtml(
                    (u.full_name && String(u.full_name).trim())
                        || (u.username && String(u.username).trim())
                        || (u.email && String(u.email).trim())
                        || `Utilisateur #${u.id}`,
                );
                return `<option value="${u.id}">${label}</option>`;
            })
            .join('')}`;
    }
}

function renderList() {
    const q = $('searchInput').value.trim().toLowerCase();
    const aid = $('assureurFilter').value;
    const filtered = courtiers.filter((c) => {
        const byName = `${c.nom} ${c.pays}`.toLowerCase().includes(q);
        const byAss = !aid || String(c.assureur_id) === String(aid);
        return byName && byAss;
    });
    if (!filtered.length) {
        $('listMount').innerHTML = '<p class="text-muted">Aucun courtier.</p>';
        return;
    }
    $('listMount').innerHTML = `
        <div class="courtiers-grid">
            ${filtered
                .map((c) => {
                    const assureur = assureurs.find((a) => a.id === c.assureur_id);
                    const logoUrl = courtierLogoUrl(c);
                    const nom = escapeHtml(c.nom || '—');
                    const pays = escapeHtml(c.pays || '—');
                    const assureurNom = escapeHtml(assureur ? assureur.nom : (c.assureur_id || '—'));
                    const telephone = escapeHtml(c.telephone || '—');
                    const adresse = escapeHtml(c.adresse || '—');
                    const commission = `${Number(c.commission_pct || 0).toFixed(2)}%`;
                    const comptable = comptablesCourtiers.find((u) => Number(u.id) === Number(c.agent_comptable_id));
                    const comptableLabel = escapeHtml(
                        comptable
                            ? ((comptable.full_name && String(comptable.full_name).trim())
                                || (comptable.username && String(comptable.username).trim())
                                || (comptable.email && String(comptable.email).trim())
                                || `#${comptable.id}`)
                            : (c.agent_comptable_id ? `#${c.agent_comptable_id}` : 'Non affecté'),
                    );
                    const fallback = escapeHtml((c.nom || '?').trim().charAt(0).toUpperCase() || '?');
                    return `
                        <article class="courtier-card">
                            <div class="courtier-card__header">
                                <div class="courtier-card__brand">
                                    <div class="courtier-card__logo">
                                        ${logoUrl
                                            ? `<img src="${logoUrl}?_ts=${Date.now()}" alt="Logo ${nom}">`
                                            : `<span>${fallback}</span>`}
                                    </div>
                                    <div class="courtier-card__identity">
                                        <h4>${nom}</h4>
                                        <p>${pays}</p>
                                    </div>
                                </div>
                                <div class="courtier-card__commission">${commission}</div>
                            </div>
                            <div class="courtier-card__meta">
                                <div class="courtier-card__meta-item">
                                    <span>Assureur</span>
                                    <strong>${assureurNom}</strong>
                                </div>
                                <div class="courtier-card__meta-item">
                                    <span>Téléphone</span>
                                    <strong>${telephone}</strong>
                                </div>
                                <div class="courtier-card__meta-item">
                                    <span>Comptable courtier</span>
                                    <strong>${comptableLabel}</strong>
                                </div>
                                <div class="courtier-card__meta-item courtier-card__meta-item--full">
                                    <span>Adresse</span>
                                    <strong>${adresse}</strong>
                                </div>
                            </div>
                            <div class="courtier-card__actions">
                                <button class="btn btn-sm btn-outline" data-edit="${c.id}">Modifier</button>
                                <button class="btn btn-sm btn-danger" data-delete="${c.id}">Supprimer</button>
                            </div>
                        </article>`;
                })
                .join('')}
        </div>`;
    document.querySelectorAll('[data-edit]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const id = Number(btn.getAttribute('data-edit'));
            const c = courtiers.find((x) => x.id === id);
            fillFormForEdit(c);
        });
    });
    document.querySelectorAll('[data-delete]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const id = Number(btn.getAttribute('data-delete'));
            const c = courtiers.find((x) => Number(x.id) === id);
            if (!c) return;
            if (!confirm(`Supprimer le courtier "${c.nom}" ?`)) return;
            try {
                await courtiersApi.delete(id);
                courtiers = courtiers.filter((x) => Number(x.id) !== id);
                if (String(fieldValue('courtierId', '')) === String(id)) {
                    resetForm();
                }
                renderList();
                showAlert('Courtier supprimé.', 'success');
            } catch (err) {
                showAlert(err.message || 'Erreur suppression courtier', 'error');
            }
        });
    });
}

async function refresh() {
    const [as, cs, users] = await Promise.all([
        assureursApi.list(),
        courtiersApi.list(),
        usersApi.listCourtierAccountants(),
    ]);
    assureurs = asArray(as);
    courtiers = asArray(cs);
    comptablesCourtiers = asArray(users);
    renderAssureursOptions();
    renderList();
}

document.addEventListener('DOMContentLoaded', async () => {
    $('newCourtierBtn').addEventListener('click', resetForm);
    $('searchInput').addEventListener('input', renderList);
    $('assureurFilter').addEventListener('change', renderList);
    $('courtierForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = fieldValue('courtierId', '');
        const body = selectedBody();
        const logoFile = $('logoFile').files && $('logoFile').files[0] ? $('logoFile').files[0] : null;
        try {
            let saved;
            if (id) {
                saved = await courtiersApi.update(id, body);
            } else {
                const existing = courtiers.find((c) => normalize(c.nom) === normalize(body.nom));
                if (existing) {
                    fillFormForEdit(existing);
                    showAlert('Ce courtier existe déjà. Le formulaire est passé en mode modification.', 'info');
                    return;
                }
                saved = await courtiersApi.create(body);
            }
            if (logoFile) {
                saved = await courtiersApi.uploadLogo(saved.id, logoFile);
            }
            upsertCourtierLocal(saved);
            updateLogoPreview(saved);
            renderList();
            showAlert('Courtier enregistré.', 'success');
            resetForm();
            await refresh();
        } catch (err) {
            if ((err.message || '').toLowerCase().includes('existe déjà')) {
                let existing = courtiers.find((c) => normalize(c.nom) === normalize(body.nom));
                if (!existing) {
                    try {
                        existing = await loadExistingByName(body.nom);
                    } catch (_) {
                        // Ignore: on garde le message d'erreur initial.
                    }
                }
                if (existing) {
                    fillFormForEdit(existing);
                    showAlert('Ce courtier existe déjà. Formulaire basculé en mode modification.', 'info');
                    return;
                }
            }
            showAlert(err.message || 'Erreur enregistrement courtier', 'error');
        }
    });
    try {
        await refresh();
    } catch (err) {
        $('listMount').textContent = err.message || 'Erreur chargement';
    }
});

