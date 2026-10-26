(async function () {
    const ok = await requirePermission('comptes_intermediaires', 'consultation', 'index.html');
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
const agentsApi = {
    available: (role, excludeCourtierId) =>
        apiCall(`/admin/courtiers/agents/available?role=${role}${excludeCourtierId ? `&exclude_courtier_id=${excludeCourtierId}` : ''}`),
    forCourtier: (courtierId) => apiCall(`/admin/courtiers/${courtierId}/agents`),
};

// Rôle -> select du formulaire (liaisons CourtierAgent).
const AGENT_SELECTS = {
    production: { role: 'agent_production_courtier', el: 'agentsProductionIds' },
    souscription: { role: 'assistant_souscription', el: 'agentsSouscriptionIds' },
    sinistre: { role: 'agent_sinistre_courtier', el: 'agentsSinistreIds' },
};

function _userLabel(u) {
    return escapeHtml(
        (u.full_name && String(u.full_name).trim())
        || (u.username && String(u.username).trim())
        || (u.email && String(u.email).trim())
        || `Utilisateur #${u.id}`,
    );
}

function _setMultiValues(elId, values) {
    const el = $(elId);
    if (!el) return;
    const wanted = new Set((values || []).map(String));
    Array.from(el.options).forEach((o) => { o.selected = wanted.has(o.value); });
}

function _getMultiValues(elId) {
    const el = $(elId);
    if (!el) return [];
    return Array.from(el.selectedOptions).map((o) => Number(o.value)).filter((v) => !Number.isNaN(v));
}

async function loadAgentSelects(excludeCourtierId) {
    for (const cfg of Object.values(AGENT_SELECTS)) {
        const el = $(cfg.el);
        if (!el) continue;
        const keep = new Set(Array.from(el.selectedOptions).map((o) => o.value));
        try {
            const rows = asArray(await agentsApi.available(cfg.role, excludeCourtierId || null));
            el.innerHTML = rows.map((u) => `<option value="${u.id}">${_userLabel(u)}</option>`).join('');
            _setMultiValues(cfg.el, Array.from(keep));
        } catch (_) {
            el.innerHTML = '';
        }
    }
}

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

async function fillFormForEdit(c) {
    if (!c) return;
    await loadAgentSelects(c.id);
    try {
        const linked = await agentsApi.forCourtier(c.id);
        _setMultiValues(AGENT_SELECTS.production.el, linked.production);
        _setMultiValues(AGENT_SELECTS.souscription.el, linked.souscription);
        _setMultiValues(AGENT_SELECTS.sinistre.el, linked.sinistre);
    } catch (_) {
        // Liaisons indisponibles : on laisse les sélecteurs vides.
    }
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
    openCourtierModal();
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
    Object.values(AGENT_SELECTS).forEach((cfg) => _setMultiValues(cfg.el, []));
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

function openCourtierModal() {
    const m = $('courtierModal');
    if (m) m.classList.add('open');
}

function closeCourtierModal() {
    const m = $('courtierModal');
    if (m) m.classList.remove('open');
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
        agents_production_ids: _getMultiValues(AGENT_SELECTS.production.el),
        agents_souscription_ids: _getMultiValues(AGENT_SELECTS.souscription.el),
        agents_sinistre_ids: _getMultiValues(AGENT_SELECTS.sinistre.el),
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
    const canEdit = window.MhPermissions
        ? window.MhPermissions.can('comptes_intermediaires', 'edition')
        : true;
    const q = $('searchInput').value.trim().toLowerCase();
    const aid = $('assureurFilter').value;
    const filtered = courtiers.filter((c) => {
        const byName = `${c.nom} ${c.pays}`.toLowerCase().includes(q);
        const byAss = !aid || String(c.assureur_id) === String(aid);
        return byName && byAss;
    });
    if (!filtered.length) {
        $('listMount').innerHTML = '<p class="text-muted" style="padding:1rem;">Aucun courtier.</p>';
        return;
    }
    $('listMount').innerHTML = `
        <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
            <thead>
                <tr>
                    <th>Courtier</th>
                    <th>Pays</th>
                    <th>Assureur</th>
                    <th>Commission</th>
                    <th>Téléphone</th>
                    <th>Comptable courtier</th>
                    <th>Adresse</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
            ${filtered
                .map((c) => {
                    const assureur = assureurs.find((a) => a.id === c.assureur_id);
                    const logoUrl = courtierLogoUrl(c);
                    const nom = escapeHtml(c.nom || '—');
                    const pays = escapeHtml(c.pays || '—');
                    const assureurNom = escapeHtml(assureur ? assureur.nom : (c.assureur_id || '—'));
                    const telephone = escapeHtml(c.telephone || '—');
                    const adresse = escapeHtml(c.adresse || '—');
                    const commission = `${Number(c.commission_pct || 0).toFixed(2)} %`;
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
                    const logo = logoUrl
                        ? `<img src="${logoUrl}?_ts=${Date.now()}" alt="" style="width:26px;height:26px;border-radius:6px;object-fit:cover;">`
                        : `<span style="display:inline-grid;place-items:center;width:26px;height:26px;border-radius:6px;background:#efeaf9;color:#4e267c;font-weight:700;font-size:.72rem;">${fallback}</span>`;
                    return `
                        <tr>
                            <td><div style="display:flex;align-items:center;gap:.55rem;">${logo}<strong>${nom}</strong></div></td>
                            <td>${pays}</td>
                            <td>${assureurNom}</td>
                            <td>${commission}</td>
                            <td>${telephone}</td>
                            <td>${comptableLabel}</td>
                            <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${adresse}">${adresse}</td>
                            <td>
                                ${canEdit ? `<button class="act" data-edit="${c.id}" style="color:#6c5ce7;font-size:.76rem;font-weight:600;background:none;border:none;cursor:pointer;margin-right:.6rem;">Modifier</button>
                                <button class="act" data-delete="${c.id}" style="color:#c81e1e;font-size:.76rem;font-weight:600;background:none;border:none;cursor:pointer;">Supprimer</button>` : '—'}
                            </td>
                        </tr>`;
                })
                .join('')}
            </tbody>
        </table>`;
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
    $('newCourtierBtn')?.addEventListener('click', () => { resetForm(); openCourtierModal(); });
    $('courtierModalClose')?.addEventListener('click', closeCourtierModal);
    $('courtierModalCancel')?.addEventListener('click', closeCourtierModal);
    $('courtierModal')?.addEventListener('click', (e) => {
        if (e.target === $('courtierModal')) closeCourtierModal();
    });
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
            closeCourtierModal();
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
        await loadAgentSelects();
        await refresh();
    } catch (err) {
        $('listMount').textContent = err.message || 'Erreur chargement';
    }
});

